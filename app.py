import streamlit as st
import streamlit.components.v1 as components
import msal
import requests
import pandas as pd
import html as html_lib
from datetime import datetime, date
from zoneinfo import ZoneInfo
import base64
import os

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GestorHub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CONFIGURAÇÕES ─────────────────────────────────────────────────────────────
CLIENT_ID     = st.secrets.get("AZURE_CLIENT_ID",     "SEU_CLIENT_ID_AQUI")
CLIENT_SECRET = st.secrets.get("AZURE_CLIENT_SECRET", "SEU_CLIENT_SECRET_AQUI")
AUTHORITY     = "https://login.microsoftonline.com/common"
REDIRECT_URI  = st.secrets.get("REDIRECT_URI", "https://gestor-app.streamlit.app")
SCOPE         = ["User.Read", "Calendars.ReadWrite"]
TZ_SP         = ZoneInfo("America/Sao_Paulo")
TZ_UTC        = ZoneInfo("UTC")
POWER_BI_URL  = st.secrets.get(
    "POWER_BI_URL",
    "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14",
)

MESES_PT  = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
             "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
MESES_ABR = ["Jan","Fev","Mar","Abr","Mai","Jun",
             "Jul","Ago","Set","Out","Nov","Dez"]
DIAS_SEM  = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]


# ── LOGO ──────────────────────────────────────────────────────────────────────
def get_logo_b64(path: str = "logo.png") -> str:
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


# ── MSAL ──────────────────────────────────────────────────────────────────────
def get_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )


# ── GRAPH API ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def buscar_agenda(token: str, data_alvo: date):
    inicio_sp = datetime(data_alvo.year, data_alvo.month, data_alvo.day, 0, 0, 0, tzinfo=TZ_SP)
    fim_sp    = datetime(data_alvo.year, data_alvo.month, data_alvo.day, 23, 59, 59, tzinfo=TZ_SP)
    ini_utc   = inicio_sp.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S")
    fim_utc   = fim_sp.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S")
    url       = "https://graph.microsoft.com/v1.0/me/calendarView"
    params    = {"startDateTime": f"{ini_utc}Z", "endDateTime": f"{fim_utc}Z",
                 "$orderby": "start/dateTime", "$top": 50}
    headers   = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 401:
            return "EXPIRADO"
        if r.status_code != 200:
            st.error(f"Erro ao buscar eventos ({r.status_code})")
            return []
        resultado = []
        for ev in r.json().get("value", []):
            start_raw = ev["start"]
            if "dateTime" not in start_raw:
                resultado.append({**ev, "_allday": True}); continue
            dt_utc = pd.to_datetime(start_raw["dateTime"])
            if dt_utc.tzinfo is None: dt_utc = dt_utc.tz_localize("UTC")
            if dt_utc.tz_convert(TZ_SP).date() == data_alvo:
                resultado.append({**ev, "_allday": False})
        return resultado
    except Exception as e:
        st.error(f"Erro: {e}"); return []


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_usuario(token: str) -> dict:
    try:
        r = requests.get("https://graph.microsoft.com/v1.0/me",
                         headers={"Authorization": f"Bearer {token}"}, timeout=8)
        if r.status_code == 200: return r.json()
    except Exception: pass
    return {}


def _parse_horario(ev: dict, campo: str) -> str:
    raw = ev[campo]
    if "dateTime" not in raw: return "–"
    dt = pd.to_datetime(raw["dateTime"])
    if dt.tzinfo is None: dt = dt.tz_localize("UTC")
    return dt.tz_convert(TZ_SP).strftime("%H:%M")


def _duracao_min(ev: dict) -> float:
    if ev.get("_allday"): return 0
    try:
        s = pd.to_datetime(ev["start"]["dateTime"])
        e = pd.to_datetime(ev["end"]["dateTime"])
        if s.tzinfo is None: s = s.tz_localize("UTC")
        if e.tzinfo is None: e = e.tz_localize("UTC")
        return (e - s).total_seconds() / 60
    except Exception: return 0


# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k, v in {"logado_ms": False, "access_token": None,
              "data_agenda": None, "cal_month": None, "usuario": {}}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── OAUTH CALLBACK ────────────────────────────────────────────────────────────
qp = st.query_params
if "code" in qp and not st.session_state["logado_ms"]:
    res = get_msal_app().acquire_token_by_authorization_code(
        qp["code"], scopes=SCOPE, redirect_uri=REDIRECT_URI)
    if "access_token" in res:
        st.session_state["access_token"] = res["access_token"]
        st.session_state["logado_ms"]    = True
        st.session_state["usuario"]      = buscar_usuario(res["access_token"])
        st.query_params.clear()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CSS GLOBAL E DARK MODE FIXES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #F5F3EF !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* DARK MODE FIXES PARA CALENDÁRIO */
[data-theme="dark"] .stDateInput *,
[data-theme="dark"] .calendar *,
[data-theme="dark"] [role="gridcell"] {
    color: #fff !important;
}
[data-theme="dark"] .stDateInput {
    background-color: #1f2937;
}
[data-theme="dark"] .stDateInput .selected,
[data-theme="dark"] .stDateInput [aria-selected="true"] {
    background-color: #ef4444;
    color: #fff;
}
[data-testid="stDateInput"] div[role="gridcell"] {
    color: white !important;
}

header[data-testid="stHeader"]          { display: none !important; }
.stAppDeployButton                      { display: none !important; }
#MainMenu, footer                       { visibility: hidden !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
button[data-testid="collapsedControl"]  { display: none !important; }
[data-testid="stToolbar"]               { display: none !important; }

/* SIDEBAR */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: #0D0D0D !important;
    width: 220px !important; min-width: 220px !important;
}
[data-testid="stSidebar"] * { font-family: 'DM Sans', sans-serif !important; }

.sb-wordmark { font-size:12px; font-weight:500; letter-spacing:.10em; text-transform:uppercase;
               color:rgba(255,255,255,.28); padding:0 10px; margin-bottom:24px; display:block; }
.sb-label    { font-size:10px; font-weight:500; letter-spacing:.09em; text-transform:uppercase;
               color:rgba(255,255,255,.22); padding:0 10px; margin:18px 0 5px; display:block; }
.nav-item    { display:flex; align-items:center; gap:10px; padding:9px 10px; border-radius:8px;
               color:rgba(255,255,255,.38); font-size:13px; font-weight:400;
               margin-bottom:1px; border:1px solid transparent; }
.nav-item.active { background:rgba(255,255,255,.10); color:#fff; border-color:rgba(255,255,255,.07); }
.nav-icon    { font-size:15px; width:20px; text-align:center; }
.user-chip   { display:flex; align-items:center; gap:10px; padding:10px; border-radius:8px;
               margin-top:14px; border-top:1px solid rgba(255,255,255,.06); padding-top:14px; }
.user-avatar { width:30px; height:30px; border-radius:50%; background:rgba(255,255,255,.10);
               display:flex; align-items:center; justify-content:center;
               font-size:11px; font-weight:600; color:rgba(255,255,255,.55); flex-shrink:0; }
.user-name   { font-size:12px; font-weight:500; color:rgba(255,255,255,.72);
               white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.user-role   { font-size:10px; color:rgba(255,255,255,.28); }

/* TOPBAR */
.gh-topbar { display:flex; align-items:center; justify-content:space-between;
             padding:16px 32px; background:#FFF;
             border-bottom:1px solid rgba(13,13,13,.08); margin-bottom:28px; }
.gh-topbar h2 { font-size:16px; font-weight:500; color:#0D0D0D; margin:0; letter-spacing:-.2px; }
.gh-topbar p  { font-size:12px; color:#8A8A8A; margin:1px 0 0; }

/* CARDS */
.gh-card { background:#FFF; border:1px solid rgba(13,13,13,.09); border-radius:14px;
           overflow:hidden; font-family:'DM Sans',sans-serif; margin-bottom:16px; }

/* DAY PULSE */
.dp-hero      { padding:18px 20px 14px; border-bottom:1px solid rgba(13,13,13,.07); }
.dp-hero-lbl  { font-size:9px; font-weight:500; letter-spacing:.08em; text-transform:uppercase;
                color:#8A8A8A; margin-bottom:5px; }
.dp-hero-val  { font-size:36px; font-weight:300; letter-spacing:-.8px; color:#1C6C4E;
                line-height:1; margin-bottom:4px; }
.dp-hero-sub  { font-size:11px; color:#8A8A8A; }
.dp-stats     { display:grid; grid-template-columns:1fr 1fr 1fr;
                gap:1px; background:rgba(13,13,13,.07);
                border-bottom:1px solid rgba(13,13,13,.07); }
.dp-stat      { background:#fff; padding:11px 14px; }
.dp-stat-lbl  { font-size:9px; font-weight:500; letter-spacing:.07em;
                text-transform:uppercase; color:#8A8A8A; margin-bottom:3px; }
.dp-stat-val  { font-size:16px; font-weight:500; color:#0D0D0D; }
.dp-stat-red  { color:#B83232; }
.prog-wrap    { padding:10px 20px; }
.prog-lbl     { display:flex; justify-content:space-between; font-size:11px; color:#8A8A8A; margin-bottom:6px; }
.prog-track   { height:4px; background:#F0EDE8; border-radius:99px; overflow:hidden; }
.prog-fill    { height:100%; border-radius:99px; }

/* MOBILE */
@media (max-width: 768px) {
  [data-testid="stSidebar"] { display: none !important; }
  [data-testid="stMainBlockContainer"] { padding-bottom: 80px !important; }
  .mobile-nav {
    display: flex !important;
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;
    background: #0D0D0D; border-top: 1px solid rgba(255,255,255,.08);
    height: 64px; align-items: center; justify-content: space-around;
    padding: 0 8px; padding-bottom: env(safe-area-inset-bottom, 0px); }
  .mob-nav-btn {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 3px; flex: 1; cursor: pointer; background: none; border: none;
    color: rgba(255,255,255,.38); font-family: 'DM Sans', sans-serif;
    font-size: 10px; font-weight: 500; padding: 8px 4px; border-radius: 8px;
    transition: color .15s; -webkit-tap-highlight-color: transparent; }
  .mob-nav-btn.active { color: #fff; }
  .mob-nav-btn .mob-icon { font-size: 20px; line-height: 1; }
}
@media (min-width: 769px) { .mobile-nav { display: none !important; } }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TELA DE LOGIN
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["logado_ms"]:
    auth_url = get_msal_app().get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    logo_b64  = get_logo_b64()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"]            { display:none !important; }
    [data-testid="stMainBlockContainer"] { padding:0 !important; max-width:100% !important; }
    </style>
    """, unsafe_allow_html=True)

    login_html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  html, body {{ height:100%; background:#F5F3EF; font-family:'DM Sans',sans-serif; display:flex; align-items:center; justify-content:center; margin:0; }}
  .card {{ display:flex; width:880px; max-width:97vw; border-radius:18px; overflow:hidden; box-shadow:0 20px 80px rgba(0,0,0,.13); }}
  .left {{ width:50%; background:#0D0D0D; padding:44px; color:#fff; }}
  .right {{ flex:1; background:#fff; padding:44px; display:flex; flex-direction:column; justify-content:center; }}
  .ms-btn {{ display:flex; align-items:center; justify-content:center; gap:12px; width:100%; padding:14px; background:#0D0D0D; color:#fff; border-radius:10px; cursor:pointer; text-decoration:none; font-weight:500; }}
</style></head><body>
<div class="card">
  <div class="left"><h1>GestorHub</h1><p>Centro de Comando Executivo</p></div>
  <div class="right">
    <h2>Bom dia, Gestor.</h2>
    <a class="ms-btn" href="{auth_url}" target="_top">Entrar com Microsoft 365</a>
  </div>
</div>
</body></html>"""
    components.html(login_html, height=580, scrolling=False)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
usuario  = st.session_state.get("usuario", {})
nome     = usuario.get("displayName") or "Gestor"
iniciais = "".join([p[0].upper() for p in nome.split()[:2]]) if nome else "GH"
cargo    = usuario.get("jobTitle") or "Colaborador"

with st.sidebar:
    st.markdown('<span class="sb-wordmark">GestorHub</span><span class="sb-label">Principal</span>', unsafe_allow_html=True)
    opcao = st.selectbox("nav", ["🏠  Início", "🎥  Resumos tl;dv", "📊  Chamados"], label_visibility="collapsed")
    
    if st.button("Sair da conta", use_container_width=True):
        st.session_state.clear(); st.rerun()


# ── HELPERS ───────────────────────────────────────────────────────────────────
def topbar(titulo: str, subtitulo: str):
    hoje_sp = datetime.now(tz=TZ_SP)
    dstr    = f"{hoje_sp.day} de {MESES_PT[hoje_sp.month-1]} de {hoje_sp.year}"
    st.markdown(f'<div class="gh-topbar"><div><h2>{titulo}</h2><p>{subtitulo} · {dstr}</p></div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: INÍCIO
# ══════════════════════════════════════════════════════════════════════════════
def pagina_inicio():
    h = datetime.now(tz=TZ_SP).hour
    saudacao = "Bom dia" if h < 12 else "Boa tarde" if h < 18 else "Boa noite"
    topbar(f"{saudacao}, {nome.split()[0]} 👋", "Agenda sincronizada")

    hoje_sp = datetime.now(tz=TZ_SP).date()
    if st.session_state["data_agenda"] is None: st.session_state["data_agenda"] = hoje_sp

    col_agenda, col_side = st.columns([1.5, 1], gap="medium")

    with col_agenda:
        with st.spinner("Buscando agenda..."):
            eventos = buscar_agenda(st.session_state["access_token"], st.session_state["data_agenda"])
        if eventos == "EXPIRADO": st.session_state.clear(); st.rerun()
        st.write("Agenda carregada com sucesso.")

    with col_side:
        # --- BLOCO DO CALENDÁRIO COM CORREÇÃO DARK MODE ---
        st.markdown("""<style>
            div[data-testid="stDateInput"] {
                background: #fff !important;
                border: 1px solid rgba(13,13,13,.08) !important;
                border-radius: 14px !important;
                padding: 14px 16px !important;
            }
            /* Garantir que números apareçam em qualquer tema */
            div[data-testid="stDateInput"] div[role="gridcell"] {
                color: #0D0D0D !important;
            }
            [data-theme="dark"] div[data-testid="stDateInput"] div[role="gridcell"] {
                color: #fff !important;
            }
            /* Estilo dos dias selecionados */
            div[data-baseweb="calendar"] div[aria-selected="true"] button {
                background: #E8533C !important; color: #fff !important;
            }
        </style>""", unsafe_allow_html=True)

        _nova_data = st.date_input("Selecionar Data", value=st.session_state["data_agenda"])
        if _nova_data != st.session_state["data_agenda"]:
            st.session_state["data_agenda"] = _nova_data
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ROTEADOR
# ══════════════════════════════════════════════════════════════════════════════
if opcao == "🏠  Início":
    pagina_inicio()
elif opcao == "🎥  Resumos tl;dv":
    st.title("Resumos")
elif opcao == "📊  Chamados":
    st.title("Chamados")
