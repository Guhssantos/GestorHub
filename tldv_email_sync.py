"""
tldv_email_sync.py
------------------
Lê os e-mails automáticos que o tl;dv envia após cada reunião e salva
os resumos em resumos.json — o mesmo formato consumido pelo GestorHub.

Requisitos:
    pip install google-auth google-auth-oauthlib google-api-python-client beautifulsoup4

Configuração:
    1. Acesse https://console.cloud.google.com e crie um projeto.
    2. Ative a Gmail API.
    3. Crie credenciais OAuth 2.0 (tipo "App de computador").
    4. Baixe o JSON e salve como gmail_credentials.json nesta pasta.
    5. Execute este script uma vez — ele abrirá o navegador para autorizar.
    6. Nas próximas execuções, rode via cron/agendador.

Uso:
    python tldv_email_sync.py              # processa últimas 24h
    python tldv_email_sync.py --days 7    # processa últimos 7 dias
"""

import os
import json
import re
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_FILE = Path(__file__).parent / "resumos.json"
CREDS_FILE = Path(__file__).parent / "gmail_credentials.json"
TOKEN_FILE = Path(__file__).parent / "gmail_token.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Remetente oficial dos e-mails do tl;dv
TLDV_SENDER = "no-reply@tldv.io"


# ── Autenticação Gmail ────────────────────────────────────────────────────────

def _get_gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                raise FileNotFoundError(
                    f"Arquivo '{CREDS_FILE}' não encontrado.\n"
                    "Baixe as credenciais OAuth 2.0 do Google Cloud Console e salve como gmail_credentials.json."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ── Parser do e-mail do tl;dv ─────────────────────────────────────────────────

def _parse_tldv_email(subject: str, body_html: str, body_plain: str, date_str: str) -> dict | None:
    """
    Extrai título, resumo, link da gravação e ações do corpo do e-mail do tl;dv.
    Retorna None se não conseguir identificar o padrão.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(body_html or "", "html.parser")

    # Título da reunião — está no assunto do e-mail após "Meeting notes:"
    titulo = subject
    for prefix in ["Meeting notes:", "Meeting notes -", "Notas da reunião:"]:
        if prefix.lower() in subject.lower():
            titulo = subject[subject.lower().index(prefix.lower()) + len(prefix):].strip(" :-")
            break

    # Link da gravação
    link = ""
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "tldv.io" in href and ("recording" in href or "meeting" in href):
            link = href
            break

    # Resumo — tenta bloco de texto principal
    resumo = ""
    # Estratégia 1: parágrafo com mais de 80 chars que não é CTA
    for p in soup.find_all(["p", "div"]):
        texto = p.get_text(separator=" ", strip=True)
        if len(texto) > 80 and "unsubscribe" not in texto.lower() and "click here" not in texto.lower():
            resumo = texto
            break

    # Estratégia 2: fallback para texto plano
    if not resumo and body_plain:
        linhas = [l.strip() for l in body_plain.splitlines() if len(l.strip()) > 60]
        resumo = " ".join(linhas[:3])

    if not titulo and not resumo:
        return None

    # Data — converte para YYYY-MM-DD
    data_iso = ""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        data_iso = dt.date().isoformat()
    except Exception:
        data_iso = datetime.now(timezone.utc).date().isoformat()

    # Ações — busca lista ordenada ou não-ordenada após keywords
    acoes = []
    action_keywords = ["action item", "next step", "follow-up", "ação", "próximo passo"]
    for el in soup.find_all(["ul", "ol"]):
        prev = el.find_previous(string=True)
        if prev and any(kw in prev.lower() for kw in action_keywords):
            for li in el.find_all("li"):
                texto_acao = li.get_text(strip=True)
                if texto_acao:
                    acoes.append({"text": texto_acao, "completed": False})

    return {
        "titulo": titulo or "Reunião tl;dv",
        "data": data_iso,
        "resumo": resumo or "(Resumo não extraído — veja a gravação)",
        "link": link,
        "acoes": acoes,
    }


# ── Busca e processamento de e-mails ─────────────────────────────────────────

def _get_message_body(service, msg_id: str) -> tuple[str, str, str, str]:
    """Retorna (subject, html_body, plain_body, date)."""
    import base64

    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("Subject", "")
    date_str = headers.get("Date", "")

    html_body = ""
    plain_body = ""

    def _extract_parts(parts):
        nonlocal html_body, plain_body
        for part in parts:
            mime = part.get("mimeType", "")
            data = (part.get("body") or {}).get("data", "")
            if data:
                decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
                if mime == "text/html":
                    html_body = decoded
                elif mime == "text/plain":
                    plain_body = decoded
            if "parts" in part:
                _extract_parts(part["parts"])

    payload = msg.get("payload", {})
    if "parts" in payload:
        _extract_parts(payload["parts"])
    else:
        data = (payload.get("body") or {}).get("data", "")
        if data:
            plain_body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

    return subject, html_body, plain_body, date_str


def _carregar_db() -> list:
    if DB_FILE.exists():
        try:
            return json.loads(DB_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def _salvar_db(dados: list):
    DB_FILE.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


def sincronizar(days: int = 1):
    """Busca e-mails do tl;dv dos últimos `days` dias e salva no DB."""
    service = _get_gmail_service()

    after = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    query = f"from:{TLDV_SENDER} after:{after}"

    print(f"🔍 Buscando e-mails tl;dv dos últimos {days} dia(s)...")
    result = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
    mensagens = result.get("messages", [])

    if not mensagens:
        print("📭 Nenhum e-mail tl;dv encontrado no período.")
        return

    db = _carregar_db()
    links_existentes = {r.get("link", "") for r in db}
    novos = 0

    for m in mensagens:
        subject, html, plain, date_str = _get_message_body(service, m["id"])
        resumo = _parse_tldv_email(subject, html, plain, date_str)
        if resumo is None:
            continue
        if resumo["link"] and resumo["link"] in links_existentes:
            print(f"  ⏭  Já existe: {resumo['titulo']}")
            continue
        db.insert(0, resumo)
        links_existentes.add(resumo["link"])
        novos += 1
        print(f"  ✅ Importado: {resumo['titulo']} ({resumo['data']})")

    if novos:
        _salvar_db(db)
        print(f"\n✨ {novos} resumo(s) novo(s) salvo(s) em {DB_FILE}")
    else:
        print("🟰 Nenhum resumo novo para importar.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sincroniza resumos tl;dv via Gmail")
    parser.add_argument("--days", type=int, default=1, help="Quantos dias para trás buscar (padrão: 1)")
    args = parser.parse_args()
    sincronizar(days=args.days)
