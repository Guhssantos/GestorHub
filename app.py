import streamlit as st
import streamlit.components.v1 as components
import msal
import requests
import pandas as pd
import html as html_lib
from datetime import datetime, date
from zoneinfo import ZoneInfo
import base64
import json
import os

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GestorHub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CONFIGURAÇÕES ─────────────────────────────────────────────────────────────
def _secret(key: str, default: str = "") -> str:
    """Lê segredo com fallback seguro — compatível com qualquer versão do Streamlit."""
    try:
        return st.secrets[key] or default
    except (KeyError, FileNotFoundError):
        return default

CLIENT_ID     = _secret("AZURE_CLIENT_ID",     "SEU_CLIENT_ID_AQUI")
CLIENT_SECRET = _secret("AZURE_CLIENT_SECRET", "SEU_CLIENT_SECRET_AQUI")
AUTHORITY     = "https://login.microsoftonline.com/common"
REDIRECT_URI  = _secret("REDIRECT_URI", "https://gestor-app.streamlit.app").rstrip("/")
SCOPE         = ["User.Read", "Calendars.ReadWrite", "Files.Read"]
TZ_SP         = ZoneInfo("America/Sao_Paulo")
TZ_UTC        = ZoneInfo("UTC")
POWER_BI_URL  = _secret(
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
# CSS GLOBAL
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
.card-hd { display:flex; align-items:center; justify-content:space-between;
           padding:14px 20px; border-bottom:1px solid rgba(13,13,13,.07); }
.card-title { font-size:13px; font-weight:500; color:#0D0D0D; }
.card-meta  { font-size:11px; color:#8A8A8A; }

/* EVENTOS */
.event-row { display:flex; align-items:center; gap:14px; padding:12px 20px;
             border-bottom:1px solid rgba(13,13,13,.06); transition:background .1s;
             font-family:'DM Sans',sans-serif; }
.event-row:last-child { border-bottom:none; }
.event-row:hover { background:#F5F3EF; }
.ev-times { width:48px; flex-shrink:0; text-align:right; }
.ev-time  { font-family:'DM Mono',monospace; font-size:11px; color:#8A8A8A; line-height:1.5; }
.ev-bar   { width:3px; border-radius:2px; flex-shrink:0; align-self:stretch; min-height:36px; }
.ev-body  { flex:1; min-width:0; }
.ev-title { font-size:13px; font-weight:500; color:#0D0D0D;
            white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ev-sub   { font-size:11px; color:#8A8A8A; margin-top:2px; }
.btn-join { font-size:11px; font-weight:500; padding:6px 13px; border-radius:6px;
            background:#0D0D0D; color:#fff !important; border:none;
            text-decoration:none !important; flex-shrink:0; transition:opacity .12s;
            font-family:'DM Sans',sans-serif; cursor:pointer; }
.btn-join:hover { opacity:.75; }
.no-link  { font-size:11px; color:#CCC; flex-shrink:0; }
.allday-badge { font-size:10px; font-weight:500; padding:3px 8px; border-radius:4px;
                background:#F0EDE8; color:#8A8A8A; flex-shrink:0; }
.empty-box { text-align:center; padding:36px 20px; }
.empty-box .ei { font-size:26px; }
.empty-box p   { font-size:13px; color:#8A8A8A; margin-top:8px; }

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
.dp-tl-wrap   { padding:0 0 12px; display:flex; flex-direction:column; }
.dp-tl-hd     { font-size:9px; font-weight:500; letter-spacing:.07em; text-transform:uppercase;
                 color:#8A8A8A; padding:10px 20px 4px; }
.dp-row       { display:grid; grid-template-columns:42px 3px 1fr;
                gap:0 8px; padding:5px 20px 5px 14px; align-items:center;
                transition:background .1s; }
.dp-row:hover { background:#F5F3EF; }
.dp-times     { display:flex; flex-direction:column; align-items:flex-end; gap:1px; }
.dp-t         { font-family:'DM Mono',monospace; font-size:9.5px; color:#8A8A8A; line-height:1.2; }
.dp-seg       { border-radius:2px; align-self:stretch; min-height:30px; }
.dp-seg-busy  { background:#B5D4F4; }
.dp-seg-free  { background:#9FE1CB; }
.dp-row-body  { display:flex; flex-direction:column; gap:2px; }
.dp-pill      { display:inline-flex; align-items:center; font-size:9px; font-weight:500;
                letter-spacing:.04em; padding:2px 6px; border-radius:4px;
                align-self:flex-start; }
.dp-pill-busy { background:#E8EEF6; color:#1A4F8A; }
.dp-pill-free { background:#D6EDE5; color:#1C6C4E; }
.dp-row-name  { font-size:11.5px; font-weight:500; color:#0D0D0D;
                white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* DAY PULSE — eventos simultâneos (sobrepostos) */
.dp-seg-overlap  { background: linear-gradient(180deg,#B5D4F4 0%,#F4B5B5 100%); }
.dp-row-overlap  { align-items: flex-start !important; }
.dp-pill-overlap { background:#FEF3CD; color:#8C5A00;
                   font-size:9px; font-weight:600; letter-spacing:.04em;
                   padding:2px 7px; border-radius:4px;
                   display:inline-flex; align-items:center; align-self:flex-start; }
.dp-overlap-item { display:flex; align-items:flex-start; gap:6px;
                   padding:4px 0 2px; border-top:1px solid rgba(13,13,13,.06); }
.dp-overlap-item:first-of-type { border-top: none; padding-top: 2px; }
.dp-overlap-bar  { width:2px; border-radius:2px; background:#1A4F8A;
                   align-self:stretch; min-height:22px; flex-shrink:0; margin-top:2px; }
.dp-overlap-time { font-family:'DM Mono',monospace; font-size:9px; color:#8A8A8A;
                   display:block; margin-bottom:1px; white-space:nowrap; }

/* POWER BI */
.pbi-wrap  { background:#fff; border:1px solid rgba(13,13,13,.09);
             border-radius:14px; padding:4px; overflow:hidden; }
.pbi-ratio { position:relative; width:100%; padding-bottom:62%; height:0; overflow:hidden; border-radius:10px; }
.pbi-ratio iframe { position:absolute; top:0; left:0; width:100% !important; height:100% !important; border:none; }

/* RESUMOS */
.resumo-card { background:#fff; border:1px solid rgba(13,13,13,.09); border-radius:14px;
               overflow:hidden; margin-bottom:14px; transition:box-shadow .15s; }
.resumo-card:hover { box-shadow:0 8px 32px rgba(0,0,0,.07); }
.resumo-top  { padding:18px 20px; }
.resumo-row  { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:10px; }
.resumo-tit  { font-size:14px; font-weight:500; color:#0D0D0D; letter-spacing:-.2px; }
.resumo-when { font-size:11px; color:#8A8A8A; margin-top:3px; }
.resumo-body { font-size:13px; color:#3A3A3A; line-height:1.65; margin:10px 0; }
.tags        { display:flex; gap:5px; flex-wrap:wrap; }
.tag { display:inline-flex; align-items:center; font-size:10px; font-weight:500;
       letter-spacing:.04em; padding:3px 8px; border-radius:4px; }
.tag-blue  { background:#D8E8F8; color:#1A4F8A; }
.tag-amber { background:#FFF0CC; color:#8C5A00; }
.tag-green { background:#D6EDE5; color:#1C6C4E; }
.tag-gray  { background:#F0EDE8; color:#8A8A8A; }
.actions-box { background:#F5F3EF; border-radius:8px; padding:11px 13px; margin-top:10px; }
.actions-lbl { font-size:10px; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
               color:#8A8A8A; margin-bottom:8px; }
.act-row     { display:flex; align-items:flex-start; gap:9px; padding:7px 0;
               border-bottom:1px solid rgba(13,13,13,.06); }
.act-row:last-child { border-bottom:none; padding-bottom:0; }
.act-chk     { width:15px; height:15px; border-radius:4px;
               border:1.5px solid rgba(13,13,13,.20); flex-shrink:0; margin-top:2px; }
.act-chk.done { background:#0D0D0D; border-color:#0D0D0D; }
.act-text    { font-size:12.5px; line-height:1.5; color:#0D0D0D; }
.act-who     { font-size:11px; color:#8A8A8A; margin-top:1px; }
.resumo-footer { display:flex; align-items:center; gap:7px; padding:11px 20px;
                 border-top:1px solid rgba(13,13,13,.07); background:#FAFAF8; }
.btn-sm { font-size:11px; font-weight:500; padding:6px 13px; border-radius:6px;
          border:1px solid rgba(13,13,13,.10); background:#fff; cursor:pointer;
          color:#0D0D0D; text-decoration:none !important; display:inline-flex;
          align-items:center; gap:5px; transition:all .12s; font-family:'DM Sans',sans-serif; }
.btn-sm:hover { background:#0D0D0D; color:#fff !important; border-color:#0D0D0D; }
.btn-sm-pri { font-size:11px; font-weight:500; padding:6px 13px; border-radius:6px;
              border:none; background:#0D0D0D; cursor:pointer; color:#fff !important;
              text-decoration:none !important; display:inline-flex; align-items:center;
              gap:5px; transition:opacity .12s; font-family:'DM Sans',sans-serif; }
.btn-sm-pri:hover { opacity:.75; }

/* Botão sair sidebar */
[data-testid="stSidebar"] button {
    background:rgba(184,50,50,.12) !important; color:#F5C6C6 !important;
    border:1px solid rgba(184,50,50,.22) !important;
    font-weight:500 !important; border-radius:8px !important;
    font-family:'DM Sans',sans-serif !important; }
[data-testid="stSidebar"] button:hover { background:rgba(184,50,50,.25) !important; }

/* Selectbox sidebar */
[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background:#1A1A1A !important; color:#F5F3EF !important;
    border:1px solid rgba(255,255,255,.10) !important; border-radius:8px !important; }
[data-testid="stSidebar"] div[data-baseweb="select"] span,
[data-testid="stSidebar"] div[data-baseweb="select"] div { color:#F5F3EF !important; }
[data-testid="stSidebar"] div[data-baseweb="select"] svg { fill:#8A8A8A !important; }
ul[data-baseweb="menu"] { background:#1A1A1A !important;
    border:1px solid rgba(255,255,255,.10) !important; border-radius:8px !important; }
ul[data-baseweb="menu"] li { color:#F5F3EF !important; font-family:'DM Sans',sans-serif !important; }
ul[data-baseweb="menu"] li:hover { background:#2A2A2A !important; }

div[data-testid="stHtml"] { overflow:visible !important; }

/* Botões de navegação de data (Anterior / Hoje / Próximo) */
[data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"]:first-of-type button {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    border: 1px solid rgba(13,13,13,.12) !important;
    padding: 6px 10px !important;
    height: 34px !important;
    min-height: 34px !important;
    transition: all .12s !important;
}
/* Sobrescreve o estilo escuro injetado pelo sidebar */
[data-testid="stMainBlockContainer"] button:not([data-testid="stSidebar"] button) {
    background: #fff !important;
    color: #0D0D0D !important;
    border: 1px solid rgba(13,13,13,.12) !important;
}
[data-testid="stMainBlockContainer"] button[kind="primary"] {
    background: #0D0D0D !important;
    color: #fff !important;
    border-color: #0D0D0D !important;
}
[data-testid="stMainBlockContainer"] button:hover:not([kind="primary"]) {
    background: #F5F3EF !important;
    border-color: rgba(13,13,13,.20) !important;
}

/* Garante que botões do calendário nunca herdem o estilo escuro da sidebar */
div.cal-grid-wrap button,
div.cal-nav-area button {
    background: transparent !important;
    color: #111827 !important;
    border: none !important;
    box-shadow: none !important;
}

/* ── Isola os botões BaseWeb do calendário dos estilos globais de button ──
   O popup é renderizado no <body> fora do sidebar, mas regras globais
   de [data-testid="stSidebar"] button podem vazar via herança.
   Este bloco garante aparência correta no light mode.                     */
div[data-baseweb="calendar"] button {
    background: transparent !important;
    color: #111827 !important;
    border: none !important;
    box-shadow: none !important;
    font-weight: 400 !important;
}

/* Sobrescreve para dark via classe injetada pelo JS detector de tema */
body.gh-dark-mode div[data-baseweb="calendar"] button {
    color: #E5E7EB !important;
    background: transparent !important;
    border: none !important;
}
@media (prefers-color-scheme: dark) {
    div[data-baseweb="calendar"] button {
        color: #E5E7EB !important;
        background: transparent !important;
    }
}

/* MOBILE */
@media (max-width: 768px) {
  [data-testid="stSidebar"] { display: none !important; }
  [data-testid="stMainBlockContainer"] {
    padding-bottom: calc(72px + env(safe-area-inset-bottom, 0px)) !important;
    padding-left: 12px !important;
    padding-right: 12px !important;
  }
  [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    width: 100% !important; min-width: 100% !important; }

  /* Topbar compacta em mobile */
  .gh-topbar {
    padding: 12px 16px !important;
    margin-bottom: 16px !important;
    flex-wrap: wrap;
    gap: 4px;
  }
  .gh-topbar h2 { font-size: 15px !important; }
  .gh-topbar p  { font-size: 11px !important; }

  /* Cards com menos padding lateral */
  .gh-card { margin-bottom: 12px !important; }
  .resumo-card { margin-bottom: 10px !important; }
  .resumo-top { padding: 14px 14px !important; }
  .resumo-footer { padding: 10px 14px !important; flex-wrap: wrap; gap: 6px !important; }
  .resumo-body { font-size: 12.5px !important; }

  /* Botões de ação maiores para toque */
  .btn-sm, .btn-sm-pri {
    padding: 8px 14px !important;
    font-size: 12px !important;
    min-height: 36px;
  }

  /* Navegação de datas — botões lado a lado */
  .date-nav-wrap {
    display: flex !important;
    gap: 6px;
    margin-bottom: 12px;
  }
  .date-nav-btn {
    flex: 1;
    text-align: center;
    padding: 9px 8px;
    font-size: 12px;
    font-weight: 500;
    border-radius: 8px;
    border: 1px solid rgba(13,13,13,.12);
    background: #fff;
    color: #0D0D0D;
    cursor: pointer;
    font-family: 'DM Sans', sans-serif;
    transition: all .12s;
    -webkit-tap-highlight-color: transparent;
  }
  .date-nav-btn:active { background: #0D0D0D; color: #fff; }
  .date-nav-btn.today  { background: #0D0D0D; color: #fff; border-color: #0D0D0D; }

  /* Skeleton loader */
  .skeleton {
    background: linear-gradient(90deg, #F0EDE8 25%, #E8E4DE 50%, #F0EDE8 75%);
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.4s infinite;
    border-radius: 8px;
  }
  @keyframes skeleton-shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
  .skeleton-row {
    height: 56px;
    margin-bottom: 4px;
    border-radius: 8px;
  }

  /* Mobile nav */
  .mobile-nav {
    display: flex !important;
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;
    background: #0D0D0D; border-top: 1px solid rgba(255,255,255,.08);
    height: 64px; align-items: center; justify-content: space-around;
    padding: 0 8px;
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }
  .mob-nav-btn {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 3px; flex: 1; cursor: pointer; background: none; border: none;
    color: rgba(255,255,255,.38); font-family: 'DM Sans', sans-serif;
    font-size: 10px; font-weight: 500; padding: 8px 4px; border-radius: 8px;
    transition: color .15s; -webkit-tap-highlight-color: transparent;
  }
  .mob-nav-btn.active { color: #fff; }
  .mob-nav-btn .mob-icon { font-size: 20px; line-height: 1; }

  /* Esconde coluna lateral do calendário em telas muito pequenas */
  @media (max-width: 480px) {
    .pbi-ratio { padding-bottom: 90% !important; }
  }
}
@media (min-width: 769px) {
  .mobile-nav { display: none !important; }
  .date-nav-wrap { display: none !important; }
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TELA DE LOGIN
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["logado_ms"]:
    auth_url = get_msal_app().get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    logo_b64  = get_logo_b64()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:26px;opacity:.55;">' if logo_b64 else "GestorHub"

    st.markdown("""
    <style>
    [data-testid="stSidebar"]            { display:none !important; }
    [data-testid="stMainBlockContainer"] { padding:0 !important; max-width:100% !important; }
    [data-testid="stMain"]               { padding:0 !important; }
    .block-container                     { padding:0 !important; max-width:100% !important; }
    </style>
    """, unsafe_allow_html=True)

    login_html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}
  html, body {{ height:100%; background:#F5F3EF; font-family:'DM Sans',system-ui,sans-serif;
    display:flex; align-items:center; justify-content:center; }}
  .card {{ display:flex; width:880px; max-width:97vw; border-radius:18px; overflow:hidden;
    box-shadow:0 20px 80px rgba(0,0,0,.13); min-height:500px; }}
  .left {{ width:50%; background:#0D0D0D; padding:44px; display:flex; flex-direction:column;
    justify-content:space-between; position:relative; overflow:hidden; }}
  .left::before {{ content:''; position:absolute; width:460px; height:460px; border-radius:50%;
    border:1px solid rgba(255,255,255,.05); top:-190px; left:-170px; pointer-events:none; }}
  .left::after {{ content:''; position:absolute; width:320px; height:320px; border-radius:50%;
    border:1px solid rgba(255,255,255,.04); bottom:-110px; right:-60px; pointer-events:none; }}
  .wordmark {{ font-size:11px; font-weight:500; letter-spacing:.10em; text-transform:uppercase;
    color:rgba(255,255,255,.24); position:relative; z-index:1; }}
  .hero {{ position:relative; z-index:1; }}
  .hero h1 {{ font-size:34px; font-weight:300; line-height:1.18; color:#fff;
    letter-spacing:-.5px; margin-bottom:13px; }}
  .hero h1 em {{ font-style:italic; color:rgba(255,255,255,.36); }}
  .hero p {{ font-size:13px; color:rgba(255,255,255,.30); max-width:250px; line-height:1.7; }}
  .badges {{ display:flex; gap:6px; flex-wrap:wrap; position:relative; z-index:1; }}
  .badge {{ font-size:10px; font-weight:500; padding:4px 11px; border-radius:999px;
    border:1px solid rgba(255,255,255,.10); color:rgba(255,255,255,.30); }}
  .right {{ flex:1; background:#fff; padding:44px; display:flex; flex-direction:column; justify-content:center; }}
  .right h2 {{ font-size:21px; font-weight:500; color:#0D0D0D; margin-bottom:6px; letter-spacing:-.3px; }}
  .right p {{ font-size:13px; color:#8A8A8A; line-height:1.65; margin-bottom:28px; }}
  .ms-btn {{ display:flex; align-items:center; justify-content:center; gap:12px;
    width:100%; padding:14px 20px; background:#0D0D0D; color:#fff; border:none;
    border-radius:10px; font-family:'DM Sans',sans-serif; font-size:14px; font-weight:500;
    cursor:pointer; text-decoration:none; transition:opacity .15s; }}
  .ms-btn:hover {{ opacity:.82; }}
  .ms-icon {{ width:20px; height:20px; flex-shrink:0; }}
  .terms {{ font-size:11px; color:#BBBBBB; text-align:center; margin-top:16px; line-height:1.6; }}
  @media (max-width:640px) {{ .left {{ display:none; }} .right {{ padding:36px 28px; }} }}
</style></head><body>
<div class="card">
  <div class="left">
    <div class="wordmark">GestorHub</div>
    <div class="hero">
      <h1>Centro de<br>Comando<br><em>Executivo</em></h1>
      <p>Agenda, reuniões e chamados integrados em um único painel sincronizado com sua conta Microsoft.</p>
    </div>
    <div class="badges">
      <span class="badge">📅 MS Calendar</span>
      <span class="badge">🎥 tl;dv</span>
      <span class="badge">📊 Power BI</span>
    </div>
  </div>
  <div class="right">
    <h2>Bom dia, Gestor.</h2>
    <p>Acesse com sua conta corporativa Microsoft para carregar sua agenda e seus painéis em tempo real.</p>
    <button class="ms-btn" onclick="doLogin()">
      <svg class="ms-icon" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="1" y="1" width="9" height="9" fill="#F25022"/>
        <rect x="11" y="1" width="9" height="9" fill="#7FBA00"/>
        <rect x="1" y="11" width="9" height="9" fill="#00A4EF"/>
        <rect x="11" y="11" width="9" height="9" fill="#FFB900"/>
      </svg>
      Entrar com Microsoft 365
    </button>
    <p class="terms">
      Seus dados são sincronizados apenas com sua conta corporativa.<br>
      Nenhuma informação é armazenada em servidores externos.
    </p>
  </div>
</div>
<script>
  var AUTH_URL = {repr(auth_url)};
  function doLogin() {{
    try {{ window.top.location.href = AUTH_URL; }}
    catch(e) {{ window.open(AUTH_URL, '_blank'); }}
  }}
</script>
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
    st.markdown('<span class="sb-wordmark">GestorHub</span><span class="sb-label">Principal</span>',
                unsafe_allow_html=True)
    opcao = st.selectbox("nav",
        ["🏠  Início", "🎥  Resumos tl;dv", "📊  Chamados"],
        index={"inicio": 0, "resumos": 1, "chamados": 2}.get(st.query_params.get("page", ""), 0),
        label_visibility="collapsed")
    _ativo = {"🏠  Início": 0, "🎥  Resumos tl;dv": 1, "📊  Chamados": 2}[opcao]
    nav_html = ""
    for i, (icon, lbl) in enumerate([("🏠","Início"), ("🎥","Resumos"), ("📊","Chamados")]):
        cls = "nav-item active" if i == _ativo else "nav-item"
        nav_html += f'<div class="{cls}"><span class="nav-icon">{icon}</span> {lbl}</div>'
    st.markdown(nav_html, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="user-chip">
        <div class="user-avatar">{iniciais}</div>
        <div style="overflow:hidden;">
            <div class="user-name">{html_lib.escape(nome)}</div>
            <div class="user-role">{html_lib.escape(cargo)}</div>
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sair da conta", use_container_width=True):
        st.session_state.clear(); st.rerun()


# ── MOBILE NAV ────────────────────────────────────────────────────────────────
_mob_active   = {"🏠  Início": 0, "🎥  Resumos tl;dv": 1, "📊  Chamados": 2}.get(opcao, 0)
_mob_nav_items = [("🏠","Início","inicio"),("🎥","Resumos","resumos"),("📊","Chamados","chamados")]
_mob_pg_map   = {"inicio":"🏠  Início","resumos":"🎥  Resumos tl;dv","chamados":"📊  Chamados"}
_mob_target   = st.query_params.get("mob_nav","")
if _mob_target and _mob_target in _mob_pg_map:
    st.query_params.clear()
    st.query_params["page"] = _mob_target
    st.rerun()
_mob_btns = ""
for _i, (_ico, _lbl, _pg_key) in enumerate(_mob_nav_items):
    _cls = "mob-nav-btn active" if _i == _mob_active else "mob-nav-btn"
    _mob_btns += f'<button class="{_cls}" onclick="mobNav(\'{_pg_key}\')" aria-label="{_lbl}"><span class="mob-icon">{_ico}</span>{_lbl}</button>'
st.markdown(f"""
<div class="mobile-nav">{_mob_btns}</div>
<script>
function mobNav(page){{
  var t=window.top||window.parent||window;
  try{{var u=new URL(t.location.href);u.searchParams.set("page",page);t.location.href=u.toString();}}
  catch(e){{window.parent.location.href="?page="+page;}}
}}
</script>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def topbar(titulo: str, subtitulo: str):
    hoje_sp = datetime.now(tz=TZ_SP)
    dias    = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
    dstr    = f"{dias[hoje_sp.weekday()]}, {hoje_sp.day} de {MESES_PT[hoje_sp.month-1]} de {hoje_sp.year}"
    st.markdown(f"""
    <div class="gh-topbar">
        <div>
            <h2>{html_lib.escape(str(titulo))}</h2>
            <p>{html_lib.escape(str(subtitulo))} · {dstr}</p>
        </div>
    </div>""", unsafe_allow_html=True)


def _calendar_widget(label: str, hoje_iso: str, sel_iso: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:'DM Sans',system-ui,sans-serif}}
html,body{{background:transparent;padding:4px 0 6px}}
.bar{{display:flex;align-items:center;gap:10px}}
.cal-btn{{background:#FFF;border:1px solid rgba(13,13,13,.10);border-radius:8px;
  padding:7px 14px 7px 10px;display:inline-flex;align-items:center;gap:8px;
  font-size:13px;font-weight:500;color:#0D0D0D;user-select:none;cursor:default}}
.dot{{width:5px;height:5px;border-radius:50%;background:#1C6C4E;display:inline-block}}
</style></head><body>
<div class="bar">
  <div class="cal-btn">
    <span class="dot"></span><span>{label}</span>
  </div>
</div>
</body></html>"""


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: INÍCIO
# ══════════════════════════════════════════════════════════════════════════════
def pagina_inicio():
    h = datetime.now(tz=TZ_SP).hour
    saudacao = "Bom dia" if h < 12 else "Boa tarde" if h < 18 else "Boa noite"
    topbar(f"{saudacao}, {nome.split()[0] if nome else 'Gestor'} 👋",
           "Agenda sincronizada com a Microsoft")

    hoje_sp = datetime.now(tz=TZ_SP).date()

    # ── Inicializa estados ──────────────────────────────────────────────────
    if st.session_state["data_agenda"] is None:
        st.session_state["data_agenda"] = hoje_sp
    if st.session_state["cal_month"] is None:
        st.session_state["cal_month"] = st.session_state["data_agenda"].replace(day=1)

    data_sel  = st.session_state["data_agenda"]
    cal_month = st.session_state["cal_month"]
    label     = "Hoje" if data_sel == hoje_sp else f"{data_sel.day} {MESES_ABR[data_sel.month-1]} {data_sel.year}"

    # ── Navegação de datas — botões Anterior / Hoje / Próximo (mobile-first) ─
    import datetime as _dt
    _col_prev, _col_hoje, _col_prox, _col_label = st.columns([1, 1, 1, 3], gap="small")
    with _col_prev:
        if st.button("← Ant.", use_container_width=True, key="btn_prev_dia"):
            _nd = data_sel - _dt.timedelta(days=1)
            st.session_state["data_agenda"] = _nd
            st.session_state["cal_month"]   = _nd.replace(day=1)
            st.rerun()
    with _col_hoje:
        _hoje_disabled = data_sel == hoje_sp
        if st.button("Hoje", use_container_width=True, key="btn_hoje",
                     type="primary" if not _hoje_disabled else "secondary"):
            st.session_state["data_agenda"] = hoje_sp
            st.session_state["cal_month"]   = hoje_sp.replace(day=1)
            st.rerun()
    with _col_prox:
        if st.button("Prox. →", use_container_width=True, key="btn_prox_dia"):
            _nd = data_sel + _dt.timedelta(days=1)
            st.session_state["data_agenda"] = _nd
            st.session_state["cal_month"]   = _nd.replace(day=1)
            st.rerun()
    with _col_label:
        _dia_semana = DIAS_SEM[(data_sel.weekday() + 1) % 7]
        st.markdown(
            f'<div style="display:flex;align-items:center;height:38px;'
            f'font-size:13px;font-weight:500;color:#0D0D0D;padding-left:4px;">'
            f'{_dia_semana}, {data_sel.day} de {MESES_PT[data_sel.month-1]}</div>',
            unsafe_allow_html=True,
        )

    # Calendário mini (widget) — mantido para desktop
    components.html(_calendar_widget(label, hoje_sp.isoformat(), data_sel.isoformat()),
                    height=52, scrolling=False)

    col_agenda, col_side = st.columns([1.5, 1], gap="medium")

    # ═══════════════════════════════════════════════════════════════════════
    # COLUNA AGENDA
    # ═══════════════════════════════════════════════════════════════════════
    with col_agenda:
        with st.spinner("Carregando agenda..."):
            eventos = buscar_agenda(st.session_state["access_token"], data_sel)
        if eventos == "EXPIRADO":
            st.session_state.clear(); st.rerun()

        # ── Toast: alerta de próxima reunião (só no dia de hoje) ────────────
        if data_sel == hoje_sp and isinstance(eventos, list):
            _agora = datetime.now(tz=TZ_SP)
            for _ev in eventos:
                if _ev.get("_allday"):
                    continue
                try:
                    _s = pd.to_datetime(_ev["start"]["dateTime"])
                    if _s.tzinfo is None:
                        _s = _s.tz_localize("UTC")
                    _s = _s.tz_convert(TZ_SP)
                    _diff = (_s - _agora).total_seconds() / 60
                    if 0 < _diff <= 15:
                        _titulo_ev = str(_ev.get("subject") or "Reunião")[:40]
                        _min_str = f"{int(_diff)} min"
                        st.toast(f"🔔 **{_titulo_ev}** começa em {_min_str}", icon="📅")
                        break
                except Exception:
                    continue

        def _fmt_dur(a, b):
            d = int((b - a).total_seconds() / 60)
            if d <= 0: return ""
            h, m = divmod(d, 60)
            return f"{h}h{m:02d}" if h and m else f"{h}h" if h else f"{m}min"

        # Coleta TODOS os eventos sem cortar por horário
        _ev_data = []
        for ev in eventos:
            if ev.get("_allday"): continue
            try:
                s = pd.to_datetime(ev["start"]["dateTime"])
                e = pd.to_datetime(ev["end"]["dateTime"])
                if s.tzinfo is None: s = s.tz_localize("UTC")
                if e.tzinfo is None: e = e.tz_localize("UTC")
                s = s.tz_convert(TZ_SP); e = e.tz_convert(TZ_SP)
                if s >= e: continue
                lnk = (ev.get("onlineMeeting") or {}).get("joinUrl") or ev.get("onlineMeetingUrl","")
                u   = ev.get("onlineMeetingUrl","") or ""
                plt = "Teams" if "teams.microsoft" in u else "Zoom" if "zoom.us" in u else "Meet" if "meet.google" in u else ""
                _ev_data.append((s, e, str(ev.get("subject") or "Sem título"), lnk, plt))
            except Exception: continue

        _ev_data.sort(key=lambda x: x[0])

        # Define janela dinâmica: do início da 1ª reunião até o fim da última
        # (ou 08:00–18:00 se não houver eventos)
        _DEFAULT_START = datetime(data_sel.year, data_sel.month, data_sel.day, 8,  0, tzinfo=TZ_SP)
        _DEFAULT_END   = datetime(data_sel.year, data_sel.month, data_sel.day, 18, 0, tzinfo=TZ_SP)
        if _ev_data:
            _TL_START = min(_ev_data[0][0], _DEFAULT_START)
            _TL_END   = max(_ev_data[-1][1], _DEFAULT_END)
        else:
            _TL_START = _DEFAULT_START
            _TL_END   = _DEFAULT_END

        # NÃO mescla reuniões — cada uma aparece individualmente
        # Reuniões sobrepostas são mostradas separadamente na timeline
        _timeline = []
        cursor = _TL_START
        for s, e, subj, lnk, plt in _ev_data:
            # Bloco livre antes desta reunião (se houver gap)
            if s > cursor:
                _timeline.append({"type":"livre","hi":cursor.strftime("%H:%M"),
                                   "hf":s.strftime("%H:%M"),"dur":_fmt_dur(cursor,s),
                                   "subject":"","link":"","platform":""})
            # A própria reunião
            _timeline.append({"type":"ocupado","hi":s.strftime("%H:%M"),
                               "hf":e.strftime("%H:%M"),"dur":_fmt_dur(s,e),
                               "subject":subj,"link":lnk,"platform":plt})
            cursor = max(cursor, e)
        # Bloco livre após a última reunião
        if cursor < _TL_END:
            _timeline.append({"type":"livre","hi":cursor.strftime("%H:%M"),
                               "hf":_TL_END.strftime("%H:%M"),"dur":_fmt_dur(cursor,_TL_END),
                               "subject":"","link":"","platform":""})

        total_ev = len([t for t in _timeline if t["type"] == "ocupado"])

        if not _timeline:
            tl_rows = '<div class="empty-box"><div class="ei">🎉</div><p>Nenhum evento neste dia.</p></div>'
        else:
            tl_rows = ""
            for blk in _timeline:
                if blk["type"] == "ocupado":
                    subj_safe = html_lib.escape(blk["subject"])
                    sub_parts = [p for p in [blk["platform"]] if p]
                    sub_html  = f'<div class="tl-sub">{" · ".join(sub_parts)}</div>' if sub_parts else ""
                    btn_html  = (f'<a href="{html_lib.escape(blk["link"])}" target="_blank" class="btn-join">Entrar</a>'
                                 if blk["link"] else '<span class="no-link">Sem link</span>')
                    tl_rows += f"""
                    <div class="tl-row tl-busy">
                      <div class="tl-times">
                        <div class="tl-t">{blk["hi"]}</div>
                        <div class="tl-sep"></div>
                        <div class="tl-t">{blk["hf"]}</div>
                      </div>
                      <div class="tl-bar tl-bar-busy"></div>
                      <div class="tl-body">
                        <div class="tl-label-tag tl-tag-busy">Reunião · {blk["dur"]}</div>
                        <div class="tl-title">{subj_safe}</div>{sub_html}
                      </div>{btn_html}
                    </div>"""
                else:
                    tl_rows += f"""
                    <div class="tl-row tl-free">
                      <div class="tl-times">
                        <div class="tl-t tl-t-free">{blk["hi"]}</div>
                        <div class="tl-sep tl-sep-free"></div>
                        <div class="tl-t tl-t-free">{blk["hf"]}</div>
                      </div>
                      <div class="tl-bar tl-bar-free"></div>
                      <div class="tl-body">
                        <div class="tl-label-tag tl-tag-free">Disponível · {blk["dur"]}</div>
                      </div>
                    </div>"""

        agenda_html = f"""
        <div class="gh-card">
          <div class="card-hd">
            <span class="card-title">Agenda do dia</span>
            <span class="card-meta">{total_ev} reunião{'ões' if total_ev!=1 else ''}</span>
          </div>{tl_rows}
        </div>"""

        _tl_height = max(140, 56 + len(_timeline) * 72)
        components.html(f"""<!DOCTYPE html><html><head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
        *{{box-sizing:border-box;margin:0;padding:0}}
        html,body{{background:#F5F3EF;font-family:'DM Sans',system-ui,sans-serif}}
        .gh-card{{background:#FFF;border:1px solid rgba(13,13,13,.09);border-radius:14px;overflow:hidden;margin-bottom:4px}}
        .card-hd{{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid rgba(13,13,13,.07)}}
        .card-title{{font-size:13px;font-weight:500;color:#0D0D0D}}
        .card-meta{{font-size:11px;color:#8A8A8A}}
        .tl-row{{display:flex;align-items:stretch;gap:12px;padding:10px 20px;border-bottom:1px solid rgba(13,13,13,.05);transition:background .1s}}
        .tl-row:last-child{{border-bottom:none}}
        .tl-busy:hover{{background:#F9F8F6}}
        .tl-free{{background:#FAFAF8}}
        .tl-free:hover{{background:#F5F3EF}}
        .tl-times{{display:flex;flex-direction:column;align-items:flex-end;width:44px;flex-shrink:0;padding-top:2px;gap:3px}}
        .tl-t{{font-family:'DM Mono',monospace;font-size:10px;color:#8A8A8A;line-height:1}}
        .tl-t-free{{color:#AAAAAA}}
        .tl-sep{{flex:1;width:1px;background:rgba(13,13,13,.10);align-self:center;min-height:14px;margin:3px 0}}
        .tl-sep-free{{background:rgba(13,13,13,.06)}}
        .tl-bar{{width:3px;border-radius:2px;flex-shrink:0;align-self:stretch;min-height:40px}}
        .tl-bar-busy{{background:#1A4F8A}}
        .tl-bar-free{{background:#D6EDE5}}
        .tl-body{{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center;gap:3px}}
        .tl-label-tag{{display:inline-flex;align-items:center;font-size:10px;font-weight:500;letter-spacing:.04em;padding:2px 7px;border-radius:4px;width:fit-content}}
        .tl-tag-busy{{background:#E8EEF6;color:#1A4F8A}}
        .tl-tag-free{{background:#D6EDE5;color:#1C6C4E}}
        .tl-title{{font-size:13px;font-weight:500;color:#0D0D0D;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
        .tl-sub{{font-size:11px;color:#8A8A8A}}
        .btn-join{{font-size:11px;font-weight:500;padding:6px 13px;border-radius:6px;background:#0D0D0D;color:#fff!important;border:none;text-decoration:none!important;flex-shrink:0;transition:opacity .12s;cursor:pointer;align-self:center}}
        .btn-join:hover{{opacity:.75}}
        .no-link{{font-size:11px;color:#CCC;flex-shrink:0;align-self:center}}
        .empty-box{{text-align:center;padding:36px 20px}}
        .empty-box .ei{{font-size:26px}}
        .empty-box p{{font-size:13px;color:#8A8A8A;margin-top:8px}}
        </style></head><body>{agenda_html}</body></html>""",
        height=_tl_height, scrolling=False)

    # ═══════════════════════════════════════════════════════════════════════
    # COLUNA LATERAL
    # ═══════════════════════════════════════════════════════════════════════
    with col_side:

        # ── DAY PULSE ──────────────────────────────────────────────────────
        WIN_START        = datetime(data_sel.year, data_sel.month, data_sel.day, 8, 0, tzinfo=TZ_SP)
        _win_end_default = datetime(data_sel.year, data_sel.month, data_sel.day, 18, 0, tzinfo=TZ_SP)

        _evs_raw = []
        for ev in eventos:
            if ev.get("_allday"): continue
            try:
                s = pd.to_datetime(ev["start"]["dateTime"])
                e = pd.to_datetime(ev["end"]["dateTime"])
                if s.tzinfo is None: s = s.tz_localize("UTC")
                if e.tzinfo is None: e = e.tz_localize("UTC")
                s = s.tz_convert(TZ_SP); e = e.tz_convert(TZ_SP)
                _evs_raw.append((s, e, str(ev.get("subject") or "Reunião")))
            except Exception: continue

        WIN_END  = max(_win_end_default, max((e for _, e, _ in _evs_raw), default=_win_end_default))
        BASE_MIN = int((WIN_END - WIN_START).total_seconds() / 60)

        _evs_clipped = []
        for s, e, subj in _evs_raw:
            sc = max(s, WIN_START); ec = min(e, WIN_END)
            if sc < ec: _evs_clipped.append((sc, ec, subj))
        _evs_clipped.sort(key=lambda x: x[0])

        # ── Versão mesclada usada apenas para cálculos de tempo ────────────
        merged = []
        for s, e, subj in _evs_clipped:
            if merged and s < merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e), merged[-1][2])
            else:
                merged.append((s, e, subj))

        def _dp_fmt(a, b):
            d = int((b - a).total_seconds() / 60)
            if d <= 0: return ""
            h2, m2 = divmod(d, 60)
            return f"{h2}h{m2:02d}" if h2 and m2 else f"{h2}h" if h2 else f"{m2}min"

        total_eventos     = len([ev for ev in eventos if not ev.get("_allday")])
        tempo_ocupado_min = sum((e - s).total_seconds() / 60 for s, e, _ in merged)
        tempo_livre_min   = max(0, BASE_MIN - tempo_ocupado_min)
        pct_raw           = tempo_ocupado_min / BASE_MIN * 100 if BASE_MIN > 0 else 0
        pct               = min(100, int(pct_raw))
        fim_ultimo        = merged[-1][1].strftime("%H:%M") if merged else "--:--"
        h_oc  = int(tempo_ocupado_min // 60); m_oc  = int(tempo_ocupado_min % 60)
        h_liv = int(tempo_livre_min   // 60); m_liv = int(tempo_livre_min   % 60)

        intervalos_livres = []
        _cur = WIN_START
        for s, e, _ in merged:
            if s > _cur: intervalos_livres.append((_cur, s))
            _cur = e
        if _cur < WIN_END: intervalos_livres.append((_cur, WIN_END))

        if intervalos_livres:
            maior = max(intervalos_livres, key=lambda x: (x[1]-x[0]).total_seconds())
            _md = int((maior[1]-maior[0]).total_seconds()/60)
            _mh, _mm = divmod(_md, 60)
            maior_txt = (f"{maior[0].strftime('%H:%M')} – {maior[1].strftime('%H:%M')} "
                         f"({_mh}h{_mm:02d})" if _mh and _mm else
                         f"{maior[0].strftime('%H:%M')} – {maior[1].strftime('%H:%M')} "
                         f"({_mh}h)" if _mh else
                         f"{maior[0].strftime('%H:%M')} – {maior[1].strftime('%H:%M')} "
                         f"({_md}min)")
        else:
            maior_txt = "Nenhum intervalo livre"

        bar_color = "#1C6C4E" if pct_raw < 50 else "#8C5A00" if pct_raw < 80 else "#B83232"

        # ── Linha do tempo individual (igual à Agenda do dia) ───────────────
        # Agrupa eventos sobrepostos em "slots" para exibição lado a lado.
        # Um slot é uma lista de eventos que se sobrepõem entre si no tempo.
        def _build_dp_slots(evs):
            """
            Retorna lista de entradas na ordem cronológica.
            Cada entrada é um dict com type='livre'|'ocupado'|'grupo'.
            'grupo' contém uma lista de eventos simultâneos.
            """
            if not evs:
                return []

            # Agrupa eventos sobrepostos: se o início de um evento for
            # anterior ao fim do último evento do grupo atual, entram juntos.
            groups = []   # cada grupo: lista de (s, e, subj)
            for ev in evs:
                s, e, subj = ev
                if groups and s < max(x[1] for x in groups[-1]):
                    groups[-1].append(ev)
                else:
                    groups.append([ev])

            # Monta timeline intercalando blocos livres e grupos
            slots = []
            cursor = WIN_START
            for grp in groups:
                grp_start = min(x[0] for x in grp)
                grp_end   = max(x[1] for x in grp)
                # Bloco livre antes do grupo
                if grp_start > cursor:
                    slots.append({
                        "type": "livre",
                        "hi": cursor.strftime("%H:%M"),
                        "hf": grp_start.strftime("%H:%M"),
                        "dur": _dp_fmt(cursor, grp_start),
                    })
                # Grupo de eventos (1 ou mais simultâneos)
                slots.append({
                    "type": "grupo",
                    "events": grp,
                })
                cursor = max(cursor, grp_end)
            # Bloco livre após o último grupo
            if cursor < WIN_END:
                slots.append({
                    "type": "livre",
                    "hi": cursor.strftime("%H:%M"),
                    "hf": WIN_END.strftime("%H:%M"),
                    "dur": _dp_fmt(cursor, WIN_END),
                })
            return slots

        _dp_slots = _build_dp_slots(_evs_clipped)

        # ── Renderiza HTML da linha do tempo ────────────────────────────────
        _dp_rows = ""
        for slot in _dp_slots:
            if slot["type"] == "livre":
                _dp_rows += (
                    '<div class="dp-row">'
                      '<div class="dp-times">'
                        f'<span class="dp-t">{slot["hi"]}</span>'
                        f'<span class="dp-t">{slot["hf"]}</span>'
                      '</div>'
                      '<div class="dp-seg dp-seg-free"></div>'
                      '<div class="dp-row-body">'
                        f'<span class="dp-pill dp-pill-free">Disponível · {slot["dur"]}</span>'
                      '</div>'
                    '</div>'
                )
            else:
                grp = slot["events"]
                if len(grp) == 1:
                    # Evento único — layout normal
                    s, e, subj = grp[0]
                    _dp_rows += (
                        '<div class="dp-row">'
                          '<div class="dp-times">'
                            f'<span class="dp-t">{s.strftime("%H:%M")}</span>'
                            f'<span class="dp-t">{e.strftime("%H:%M")}</span>'
                          '</div>'
                          '<div class="dp-seg dp-seg-busy"></div>'
                          '<div class="dp-row-body">'
                            f'<span class="dp-pill dp-pill-busy">Reunião · {_dp_fmt(s,e)}</span>'
                            f'<span class="dp-row-name">{html_lib.escape(subj)}</span>'
                          '</div>'
                        '</div>'
                    )
                else:
                    # Múltiplos eventos simultâneos — agrupa em um bloco com
                    # badge de sobreposição e lista cada reunião separada
                    grp_start = min(x[0] for x in grp)
                    grp_end   = max(x[1] for x in grp)
                    n = len(grp)
                    # Linha de horário do bloco
                    _dp_rows += (
                        '<div class="dp-row dp-row-overlap">'
                          '<div class="dp-times">'
                            f'<span class="dp-t">{grp_start.strftime("%H:%M")}</span>'
                            f'<span class="dp-t">{grp_end.strftime("%H:%M")}</span>'
                          '</div>'
                          '<div class="dp-seg dp-seg-overlap"></div>'
                          '<div class="dp-row-body" style="gap:4px;">'
                            f'<span class="dp-pill dp-pill-overlap">'
                              f'⚡ {n} simultâneas · {_dp_fmt(grp_start,grp_end)}'
                            '</span>'
                    )
                    for s, e, subj in grp:
                        _dp_rows += (
                            '<div class="dp-overlap-item">'
                              '<div class="dp-overlap-bar"></div>'
                              '<div style="min-width:0;flex:1;">'
                                f'<span class="dp-overlap-time">{s.strftime("%H:%M")}–{e.strftime("%H:%M")}</span>'
                                f'<span class="dp-row-name" style="font-size:11px;">'
                                  f'{html_lib.escape(subj)}'
                                '</span>'
                              '</div>'
                            '</div>'
                        )
                    _dp_rows += '</div></div>'

        _dp_rows_or_empty = _dp_rows or '<div style="padding:14px 20px;font-size:12px;color:#8A8A8A;text-align:center;">Dia livre 🎉</div>'

        _dp_html = (
            '<div class="gh-card">'
              '<div class="card-hd"><span class="card-title">Day Pulse</span>'
                '<span class="card-meta">Resumo do dia</span></div>'
              '<div class="dp-hero">'
                '<div class="dp-hero-lbl">Você ainda tem livre hoje</div>'
                f'<div class="dp-hero-val">{h_liv}h {m_liv}m</div>'
                f'<div class="dp-hero-sub">Maior bloco: {html_lib.escape(maior_txt)}</div>'
              '</div>'
              '<div class="dp-stats">'
                f'<div class="dp-stat"><div class="dp-stat-lbl">Ocupado</div><div class="dp-stat-val">{h_oc}h {m_oc}m</div></div>'
                f'<div class="dp-stat"><div class="dp-stat-lbl">Reuniões</div><div class="dp-stat-val">{total_eventos}</div></div>'
                f'<div class="dp-stat"><div class="dp-stat-lbl">Término</div><div class="dp-stat-val dp-stat-red">{fim_ultimo}</div></div>'
              '</div>'
              '<div class="prog-wrap"><div class="prog-lbl"><span>Ocupação</span>'
                f'<span>{pct}%</span></div>'
                f'<div class="prog-track"><div class="prog-fill" style="width:{pct}%;background:{bar_color}"></div></div>'
              '</div>'
              '<div class="dp-tl-wrap">'
                f'<div class="dp-tl-hd">Linha do tempo · 08:00 – {WIN_END.strftime("%H:%M")}</div>'
            + _dp_rows_or_empty +
              '</div></div>')
        st.markdown(_dp_html, unsafe_allow_html=True)

        # ── CALENDÁRIO ─────────────────────────────────────────────────────────
        st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════
   CALENDÁRIO — Light mode base
   ═══════════════════════════════════════════════════════════════ */

/* Card wrapper */
div[data-testid="stDateInput"] {
    background: #fff !important;
    border: 1px solid rgba(13,13,13,.08) !important;
    border-radius: 14px !important;
    padding: 14px 16px 10px !important;
    margin-top: 12px !important;
}
div[data-testid="stDateInput"] label {
    font-size: 13px !important; font-weight: 500 !important;
    color: #0D0D0D !important; display: block !important;
    padding-bottom: 10px !important;
    border-bottom: 1px solid rgba(13,13,13,.07) !important;
    margin-bottom: 10px !important;
}
div[data-testid="stDateInput"] input {
    background: #F5F3EF !important; border: 1px solid #E5E7EB !important;
    border-radius: 8px !important; color: #111827 !important;
    font-size: 13px !important; padding: 8px 12px !important;
}
div[data-testid="stDateInput"] > div > div {
    background: transparent !important; border: none !important; box-shadow: none !important;
}

/* Popup do calendário — light */
div[data-baseweb="calendar"] {
    background: #fff !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 24px rgba(0,0,0,.10) !important;
}
div[data-baseweb="calendar"] * {
    font-family: 'DM Sans', sans-serif !important;
    color: #111827 !important;
}
div[data-baseweb="calendar"] button {
    background: transparent !important;
    color: #111827 !important;
    border-radius: 50% !important;
    border: none !important;
    font-size: 13px !important;
}
div[data-baseweb="calendar"] button:hover {
    background: #F3F4F6 !important;
    color: #111827 !important;
}
div[data-baseweb="calendar"] div[aria-selected="true"] button {
    background: #E8533C !important;
    color: #fff !important;
    font-weight: 700 !important;
}
div[data-baseweb="calendar"] div[data-today="true"] button {
    border: 2px solid #E8533C !important;
    color: #E8533C !important;
}
div[data-baseweb="calendar"] div[data-outside-month="true"] button {
    color: #D1D5DB !important;
}
div[data-baseweb="calendar"] div[role="columnheader"],
div[data-baseweb="calendar"] div[role="columnheader"] * {
    color: #9CA3AF !important;
    font-size: 11px !important;
    font-weight: 600 !important;
}
div[data-baseweb="calendar"] select {
    background: #fff !important; color: #0D0D0D !important;
    border: 1px solid #E5E7EB !important; border-radius: 6px !important;
    font-size: 13px !important; font-weight: 500 !important;
    padding: 2px 6px !important;
}
div[data-baseweb="calendar"] select option { color: #0D0D0D !important; background: #fff !important; }
div[data-baseweb="calendar"] button[aria-label*="previous"],
div[data-baseweb="calendar"] button[aria-label*="next"],
div[data-baseweb="calendar"] button[aria-label*="Previous"],
div[data-baseweb="calendar"] button[aria-label*="Next"] {
    background: transparent !important; color: #374151 !important;
    border-radius: 8px !important;
}
div[data-baseweb="calendar"] button[aria-label*="previous"]:hover,
div[data-baseweb="calendar"] button[aria-label*="next"]:hover,
div[data-baseweb="calendar"] button[aria-label*="Previous"]:hover,
div[data-baseweb="calendar"] button[aria-label*="Next"]:hover {
    background: #F3F4F6 !important;
}

/* ═══════════════════════════════════════════════════════════════
   CALENDÁRIO — Dark mode
   Estratégia tripla:
   1) .gh-dark-mode  (classe injetada via JS que detecta o tema Streamlit)
   2) @media prefers-color-scheme: dark  (preferência do sistema)
   3) .stApp[data-theme="dark"]  (atributo alternativo do Streamlit)
   ═══════════════════════════════════════════════════════════════ */

/* --- Bloco de regras dark compartilhado via classe .gh-dark-mode no <body> --- */
body.gh-dark-mode div[data-testid="stDateInput"],
body.gh-dark-mode div[data-baseweb="popover"] div[data-testid="stDateInput"] {
    background: #1E2130 !important;
    border-color: rgba(255,255,255,.12) !important;
}
body.gh-dark-mode div[data-testid="stDateInput"] label {
    color: #E5E7EB !important;
    border-bottom-color: rgba(255,255,255,.08) !important;
}
body.gh-dark-mode div[data-testid="stDateInput"] input {
    background: #141622 !important;
    border-color: rgba(255,255,255,.14) !important;
    color: #F9FAFB !important;
}

/* Popup dark */
body.gh-dark-mode div[data-baseweb="calendar"],
body.gh-dark-mode div[data-baseweb="popover"] div[data-baseweb="calendar"] {
    background: #1E2130 !important;
    border-color: rgba(255,255,255,.10) !important;
    box-shadow: 0 12px 40px rgba(0,0,0,.55) !important;
}

/* TODOS os textos/elementos dentro do calendário — reset forçado */
body.gh-dark-mode div[data-baseweb="calendar"],
body.gh-dark-mode div[data-baseweb="calendar"] *,
body.gh-dark-mode div[data-baseweb="calendar"] div,
body.gh-dark-mode div[data-baseweb="calendar"] span,
body.gh-dark-mode div[data-baseweb="calendar"] button,
body.gh-dark-mode div[data-baseweb="calendar"] [role="gridcell"],
body.gh-dark-mode div[data-baseweb="calendar"] [role="gridcell"] *,
body.gh-dark-mode div[data-baseweb="calendar"] [role="row"] *,
body.gh-dark-mode div[data-baseweb="calendar"] [role="columnheader"] * {
    color: #E5E7EB !important;
    background-color: transparent !important;
}

/* Botões dos dias — dark */
body.gh-dark-mode div[data-baseweb="calendar"] button {
    background: transparent !important;
    color: #E5E7EB !important;
    border: none !important;
    border-radius: 50% !important;
}
body.gh-dark-mode div[data-baseweb="calendar"] button:hover {
    background: rgba(255,255,255,.12) !important;
    color: #fff !important;
}

/* Dia selecionado — dark */
body.gh-dark-mode div[data-baseweb="calendar"] div[aria-selected="true"] button,
body.gh-dark-mode div[data-baseweb="calendar"] [aria-selected="true"] button {
    background: #E8533C !important;
    color: #fff !important;
    font-weight: 700 !important;
    border-radius: 50% !important;
}

/* Dia de hoje — dark */
body.gh-dark-mode div[data-baseweb="calendar"] div[data-today="true"] button {
    border: 2px solid #E8533C !important;
    color: #E8533C !important;
    background: transparent !important;
}

/* Dias fora do mês — dark */
body.gh-dark-mode div[data-baseweb="calendar"] div[data-outside-month="true"] button {
    color: rgba(229,231,235,.28) !important;
}

/* Cabeçalhos dos dias da semana — dark */
body.gh-dark-mode div[data-baseweb="calendar"] div[role="columnheader"],
body.gh-dark-mode div[data-baseweb="calendar"] div[role="columnheader"] * {
    color: rgba(229,231,235,.50) !important;
    background: transparent !important;
    font-size: 11px !important;
    font-weight: 600 !important;
}

/* Selects de mês/ano — dark */
body.gh-dark-mode div[data-baseweb="calendar"] select {
    background: #141622 !important;
    color: #E5E7EB !important;
    border: 1px solid rgba(255,255,255,.15) !important;
    border-radius: 6px !important;
}
body.gh-dark-mode div[data-baseweb="calendar"] select option {
    background: #1E2130 !important;
    color: #E5E7EB !important;
}

/* Setas de navegação — dark */
body.gh-dark-mode div[data-baseweb="calendar"] button[aria-label*="previous"],
body.gh-dark-mode div[data-baseweb="calendar"] button[aria-label*="next"],
body.gh-dark-mode div[data-baseweb="calendar"] button[aria-label*="Previous"],
body.gh-dark-mode div[data-baseweb="calendar"] button[aria-label*="Next"] {
    background: transparent !important;
    color: rgba(229,231,235,.75) !important;
    border-radius: 8px !important;
    border: none !important;
}
body.gh-dark-mode div[data-baseweb="calendar"] button[aria-label*="previous"]:hover,
body.gh-dark-mode div[data-baseweb="calendar"] button[aria-label*="next"]:hover,
body.gh-dark-mode div[data-baseweb="calendar"] button[aria-label*="Previous"]:hover,
body.gh-dark-mode div[data-baseweb="calendar"] button[aria-label*="Next"]:hover {
    background: rgba(255,255,255,.10) !important;
}

/* Fundo da grade do calendário (cell rows) — dark */
body.gh-dark-mode div[data-baseweb="calendar"] [role="row"],
body.gh-dark-mode div[data-baseweb="calendar"] [role="presentation"] {
    background: transparent !important;
}

/* ── Fallback: @media prefers-color-scheme (cobre quando JS não carregou) ── */
@media (prefers-color-scheme: dark) {
    div[data-baseweb="calendar"] {
        background: #1E2130 !important;
        border-color: rgba(255,255,255,.10) !important;
        box-shadow: 0 12px 40px rgba(0,0,0,.55) !important;
    }
    div[data-baseweb="calendar"],
    div[data-baseweb="calendar"] *,
    div[data-baseweb="calendar"] button,
    div[data-baseweb="calendar"] [role="gridcell"],
    div[data-baseweb="calendar"] [role="gridcell"] * {
        color: #E5E7EB !important;
        background-color: transparent !important;
    }
    div[data-baseweb="calendar"] button {
        background: transparent !important;
        color: #E5E7EB !important;
        border: none !important;
        border-radius: 50% !important;
    }
    div[data-baseweb="calendar"] button:hover {
        background: rgba(255,255,255,.12) !important;
    }
    div[data-baseweb="calendar"] div[aria-selected="true"] button {
        background: #E8533C !important;
        color: #fff !important;
    }
    div[data-baseweb="calendar"] div[data-today="true"] button {
        border: 2px solid #E8533C !important;
        color: #E8533C !important;
        background: transparent !important;
    }
    div[data-baseweb="calendar"] div[data-outside-month="true"] button {
        color: rgba(229,231,235,.28) !important;
    }
    div[data-baseweb="calendar"] div[role="columnheader"],
    div[data-baseweb="calendar"] div[role="columnheader"] * {
        color: rgba(229,231,235,.50) !important;
    }
    div[data-baseweb="calendar"] select {
        background: #141622 !important;
        color: #E5E7EB !important;
        border-color: rgba(255,255,255,.15) !important;
    }
    div[data-baseweb="calendar"] button[aria-label*="previous"],
    div[data-baseweb="calendar"] button[aria-label*="next"],
    div[data-baseweb="calendar"] button[aria-label*="Previous"],
    div[data-baseweb="calendar"] button[aria-label*="Next"] {
        color: rgba(229,231,235,.75) !important;
        background: transparent !important;
    }
}
</style>

<script>
/* ── Detector de tema Streamlit — injeta .gh-dark-mode no body ──
   O Streamlit não expõe [data-theme] no DOM público; a estratégia
   mais confiável é ler a variável CSS --background-color definida
   pelo tema e comparar sua luminância.                              */
(function ghDetectTheme() {
    function applyTheme() {
        try {
            var app = document.querySelector('.stApp') || document.body;
            var bg  = window.getComputedStyle(app).backgroundColor;
            // Extrai r,g,b do rgb(r, g, b)
            var m = bg.match(/\\d+/g);
            if (!m || m.length < 3) return;
            var r = parseInt(m[0]), g = parseInt(m[1]), b = parseInt(m[2]);
            // Luminância relativa (fórmula WCAG)
            var lum = (0.299 * r + 0.587 * g + 0.114 * b);
            if (lum < 128) {
                document.body.classList.add('gh-dark-mode');
            } else {
                document.body.classList.remove('gh-dark-mode');
            }
        } catch(e) {}
    }
    // Roda imediatamente e também observa mudanças no DOM
    applyTheme();
    var obs = new MutationObserver(function(muts) {
        // Só re-detecta se houver mudança de atributo class no .stApp
        for (var i = 0; i < muts.length; i++) {
            if (muts[i].target.classList &&
                (muts[i].target.classList.contains('stApp') ||
                 muts[i].target === document.body)) {
                applyTheme(); break;
            }
        }
    });
    obs.observe(document.documentElement, { attributes: true, subtree: true, attributeFilter: ['class','style'] });
    // Também roda em intervalos curtos nos primeiros 3 segundos (garante pós-hydration)
    var ticks = 0;
    var iv = setInterval(function() {
        applyTheme();
        if (++ticks >= 6) clearInterval(iv);
    }, 500);
})();
</script>
""", unsafe_allow_html=True)

        _nova_data = st.date_input(
            "Calendário", value=data_sel, key="cal_date_input",
            format="DD/MM/YYYY",
        )

        # Traduz o calendário para português via JS
        st.markdown("""
        <script>
        (function translateCalendar() {
            var DIAS = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'];
            var MESES_EN = ['January','February','March','April','May','June',
                            'July','August','September','October','November','December'];
            var MESES_PT = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                            'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
            function translate() {
                document.querySelectorAll('div[role="columnheader"]').forEach(function(el, i) {
                    if (DIAS[i]) el.textContent = DIAS[i];
                });
                document.querySelectorAll('div[data-baseweb="calendar"] select').forEach(function(sel) {
                    Array.from(sel.options).forEach(function(opt) {
                        var idx = MESES_EN.indexOf(opt.text.trim());
                        if (idx !== -1) opt.text = MESES_PT[idx];
                    });
                });
            }
            var obs = new MutationObserver(translate);
            obs.observe(document.body, { childList: true, subtree: true });
            translate();
        })();
        </script>
        """, unsafe_allow_html=True)

        if _nova_data != data_sel:
            st.session_state["data_agenda"] = _nova_data
            st.session_state["cal_month"]   = _nova_data.replace(day=1)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: RESUMOS
# ══════════════════════════════════════════════════════════════════════════════

DB_RESUMOS   = "resumos.json"
# Caminho do arquivo Excel no OneDrive (configurável via secret EXCEL_FILE_PATH)
# Exemplo: "GestorHub/resumos.xlsx"  →  raiz do OneDrive / pasta GestorHub
_EXCEL_DEFAULT = "GestorHub/resumos.xlsx"


@st.cache_data(ttl=120, show_spinner=False)
def _carregar_resumos_excel(token: str) -> list:
    """
    Lê a planilha Excel do OneDrive via Microsoft Graph API.
    Usa o mesmo token OAuth já presente na sessão — sem credenciais extras.
    Espera colunas: titulo | data | resumo | link | acoes
    """
    if not token:
        return []
    excel_path = _secret("EXCEL_FILE_PATH", _EXCEL_DEFAULT)
    try:
        url = (
            "https://graph.microsoft.com/v1.0/me/drive/root:/"
            f"{excel_path}:/workbook/worksheets/Sheet1/usedRange"
        )
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code == 404:
            return []          # arquivo ainda não criado
        if r.status_code == 401:
            return []          # token expirado — sessão vai renovar no próximo ciclo
        if not r.ok:
            return []

        values = r.json().get("values", [])
        if len(values) < 2:   # só cabeçalho ou vazio
            return []

        headers = [str(h).lower().strip() for h in values[0]]
        resumos = []
        for row in values[1:]:
            # Garante que a linha tem células suficientes
            row = list(row) + [""] * max(0, len(headers) - len(row))
            r_dict = dict(zip(headers, row))
            # Ignora linhas completamente vazias
            if not any(str(v).strip() for v in r_dict.values()):
                continue
            acoes_raw = str(r_dict.get("acoes", "") or "")
            try:
                acoes = json.loads(acoes_raw) if acoes_raw.startswith("[") else []
            except (json.JSONDecodeError, ValueError):
                acoes = []
            resumos.append({
                "titulo": str(r_dict.get("titulo", "") or "").strip(),
                "data":   str(r_dict.get("data",   "") or "").strip(),
                "resumo": str(r_dict.get("resumo", "") or "").strip(),
                "link":   str(r_dict.get("link",   "") or "").strip(),
                "acoes":  acoes,
            })
        return list(reversed(resumos))   # mais recentes primeiro
    except Exception:
        return []


def _carregar_resumos() -> list:
    """Lê do Excel/OneDrive; fallback para arquivo local (dev)."""
    token = st.session_state.get("access_token", "")
    dados = _carregar_resumos_excel(token) if token else []
    if dados:
        return dados
    if not os.path.exists(DB_RESUMOS):
        return []
    try:
        with open(DB_RESUMOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _salvar_resumos(dados: list):
    with open(DB_RESUMOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def _formatar_data_resumo(data_str: str) -> str:
    """Converte 'YYYY-MM-DD' para '29 Abr, 2025'."""
    try:
        d = datetime.strptime(data_str[:10], "%Y-%m-%d").date()
        hoje = date.today()
        if d == hoje:
            return "Hoje"
        if d == hoje.replace(day=hoje.day - 1):
            return "Ontem"
        return f"{d.day} {MESES_ABR[d.month - 1]}"
    except Exception:
        return data_str or "—"


def _renderizar_acoes(acoes: list, resumo_idx: int) -> str:
    if not acoes:
        return ""
    linhas = ""
    for i, acao in enumerate(acoes):
        concluida = acao.get("completed", False)
        chk_class = "act-chk done" if concluida else "act-chk"
        texto = html_lib.escape(str(acao.get("text", "")))
        responsavel = html_lib.escape(str(acao.get("assigned_to", "")))
        prazo = html_lib.escape(str(acao.get("due_date", "")))
        meta = " · ".join(filter(None, [responsavel, f"Prazo: {prazo}" if prazo else ""]))
        linhas += f"""
          <div class="act-row">
            <div class="{chk_class}" data-idx="{resumo_idx}" data-acao="{i}"></div>
            <div>
              <div class="act-text">{texto}</div>
              {f'<div class="act-who">{meta}</div>' if meta else ''}
            </div>
          </div>"""
    return f'<div class="actions-box"><div class="actions-lbl">Ações extraídas</div>{linhas}</div>'


def _card_resumo(r: dict, idx: int) -> str:
    titulo = html_lib.escape(str(r.get("titulo", "Sem título")))
    data_fmt = _formatar_data_resumo(r.get("data", ""))
    resumo_txt = html_lib.escape(str(r.get("resumo", "")))
    link = html_lib.escape(str(r.get("link", "#")))
    acoes_html = _renderizar_acoes(r.get("acoes", []), idx)
    btn_gravacao = f'<a href="{link}" target="_blank" class="btn-sm-pri">🎬 Ver gravação</a>' if link and link != "#" else ""

    return f"""
    <div class="resumo-card">
      <div class="resumo-top">
        <div class="resumo-row">
          <div>
            <div class="resumo-tit">{titulo}</div>
            <div class="resumo-when">{data_fmt} · via tl;dv</div>
          </div>
          <div class="tags"><span class="tag tag-gray">tl;dv</span></div>
        </div>
        <div class="resumo-body">{resumo_txt}</div>
        {acoes_html}
      </div>
      <div class="resumo-footer">
        {btn_gravacao}
      </div>
    </div>"""


def pagina_resumos():
    topbar("Resumos de Reuniões", "Insights extraídos via tl;dv · sincronizado via webhook")

    resumos = _carregar_resumos()

    # Barra de busca
    busca = st.text_input("", placeholder="🔍  Buscar por título ou conteúdo...", label_visibility="collapsed")
    if busca:
        termo = busca.lower()
        resumos = [r for r in resumos if termo in r.get("titulo", "").lower() or termo in r.get("resumo", "").lower()]

    if not resumos:
        if busca:
            st.markdown("""
            <div class="resumo-card" style="text-align:center;padding:2rem;color:#8A8A8A;">
              <div style="font-size:2rem;margin-bottom:.5rem;">🔍</div>
              <div>Nenhum resumo encontrado para "<strong>{}</strong>"</div>
            </div>""".format(html_lib.escape(busca)), unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="resumo-card" style="text-align:center;padding:2.5rem;color:#8A8A8A;">
              <div style="font-size:2.5rem;margin-bottom:.75rem;">🎥</div>
              <div style="font-size:1rem;font-weight:600;margin-bottom:.5rem;color:#0D0D0D;">Nenhum resumo ainda</div>
              <div style="font-size:.875rem;line-height:1.5;">
                Configure o webhook do tl;dv apontando para o endpoint<br>
                <code style="background:#F5F3EF;padding:2px 6px;border-radius:4px;">/webhook/tldv</code>
                para receber resumos automaticamente.
              </div>
            </div>""", unsafe_allow_html=True)
        return

    cards_html = "\n".join(_card_resumo(r, i) for i, r in enumerate(resumos))
    st.markdown(cards_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: CHAMADOS
# ══════════════════════════════════════════════════════════════════════════════
def pagina_chamados():
    topbar("Chamados", "Acompanhamento de SLAs em tempo real")
    st.markdown(f"""
    <div class="pbi-wrap">
      <div class="pbi-ratio">
        <iframe src="{POWER_BI_URL}" allowFullScreen="true" title="Power BI — Chamados"></iframe>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROTEADOR
# ══════════════════════════════════════════════════════════════════════════════
if opcao == "🏠  Início":
    pagina_inicio()
elif opcao == "🎥  Resumos tl;dv":
    pagina_resumos()
elif opcao == "📊  Chamados":
    pagina_chamados()
