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
              "data_agenda": None, "usuario": {}}.items():
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

div[data-testid="stDateInput"] {
    position: absolute !important; opacity: 0 !important;
    pointer-events: none !important; height: 0 !important;
    overflow: hidden !important; z-index: -1 !important;
}

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
.pulse-grid { display:grid; grid-template-columns:1fr 1fr;
              gap:1px; background:rgba(13,13,13,.07); }
.pulse-cell { background:#fff; padding:16px; }
.pulse-lbl  { font-size:9px; font-weight:500; letter-spacing:.08em;
              text-transform:uppercase; color:#8A8A8A; }
.pulse-val  { font-size:21px; font-weight:300; letter-spacing:-.5px; margin-top:5px; color:#0D0D0D; }
.c-blue  { color:#1A4F8A; } .c-green { color:#1C6C4E; } .c-red { color:#B83232; }
.prog-wrap  { padding:13px 20px; }
.prog-lbl   { display:flex; justify-content:space-between; font-size:11px; color:#8A8A8A; margin-bottom:6px; }
.prog-track { height:5px; background:#F0EDE8; border-radius:99px; overflow:hidden; }
.prog-fill  { height:100%; border-radius:99px; background:#0D0D0D; }

/* MINI CAL */
.mini-cal { padding:13px 20px; }
.mcal-nav { display:flex; justify-content:space-between; align-items:center; margin-bottom:9px; }
.mcal-mon { font-size:12px; font-weight:500; color:#0D0D0D; }
.cal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:2px; }
.cal-dow  { font-size:9px; font-weight:600; color:#AAAAAA; text-align:center;
            padding:3px 0; letter-spacing:.04em; text-transform:uppercase; }
.cal-day  { font-size:11px; font-family:'DM Mono',monospace; text-align:center;
            padding:5px 2px; border-radius:5px; color:#0D0D0D; }
.cal-day.today { background:#0D0D0D; color:#fff; }
.cal-day.sel:not(.today) { background:#E8E5DF; }
.cal-day.out  { color:rgba(13,13,13,.18); }

/* DAY PULSE TIMELINE */
.dp-tl-wrap { padding:0 20px 14px; display:flex; flex-direction:column; gap:4px; }
.dp-tl-hd   { font-size:10px; font-weight:600; letter-spacing:.07em; text-transform:uppercase;
               color:#8A8A8A; margin-bottom:6px; margin-top:2px; }
.dp-blk     { display:flex; align-items:stretch; gap:10px; border-radius:8px;
               padding:8px 10px; transition:background .1s; }
.dp-blk-busy { background:#F0F3F8; }
.dp-blk-free { background:#F0F7F4; }
.dp-blk:hover { filter:brightness(.97); }
.dp-tms     { display:flex; flex-direction:column; align-items:flex-end;
               width:38px; flex-shrink:0; gap:2px; padding-top:1px; }
.dp-t       { font-family:'DM Mono',monospace; font-size:9.5px; color:#8A8A8A; line-height:1; }
.dp-t-free  { color:#AAAAAA; }
.dp-sep     { flex:1; width:1px; background:rgba(13,13,13,.10); align-self:center;
               min-height:10px; margin:2px 0; }
.dp-sep-free{ background:rgba(13,13,13,.06); }
.dp-bar     { width:3px; border-radius:2px; flex-shrink:0; align-self:stretch; min-height:32px; }
.dp-bar-busy{ background:#1A4F8A; }
.dp-bar-free{ background:#1C6C4E; opacity:.4; }
.dp-body    { flex:1; min-width:0; display:flex; flex-direction:column;
               justify-content:center; gap:2px; }
.dp-tag     { display:inline-flex; align-items:center; font-size:9px; font-weight:600;
               letter-spacing:.05em; text-transform:uppercase; padding:2px 6px;
               border-radius:4px; width:fit-content; }
.dp-tag-busy{ background:#D8E4F2; color:#1A4F8A; }
.dp-tag-free{ background:#C8E8DC; color:#1C6C4E; }
.dp-title   { font-size:11.5px; font-weight:500; color:#0D0D0D;
               white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

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

/* ── MOBILE BOTTOM NAV ── */
@media (max-width: 768px) {
  [data-testid="stSidebar"] { display: none !important; }
  [data-testid="stMainBlockContainer"] { padding-bottom: 80px !important; }

  /* Stack columns vertically on mobile */
  [data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
  }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    width: 100% !important; min-width: 100% !important;
  }

  .mobile-nav {
    display: flex !important;
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;
    background: #0D0D0D; border-top: 1px solid rgba(255,255,255,.08);
    height: 64px; align-items: center; justify-content: space-around;
    padding: 0 8px; padding-bottom: env(safe-area-inset-bottom, 0px);
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
}
@media (min-width: 769px) {
  .mobile-nav { display: none !important; }
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TELA DE LOGIN — usa components.html para evitar escape de HTML pelo Streamlit
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["logado_ms"]:

    auth_url = get_msal_app().get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    logo_b64 = get_logo_b64()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:26px;opacity:.55;">' if logo_b64 else "GestorHub"

    # Esconde sidebar e padding na tela de login
    st.markdown("""
    <style>
    [data-testid="stSidebar"]            { display:none !important; }
    [data-testid="stMainBlockContainer"] { padding:0 !important; max-width:100% !important; }
    [data-testid="stMain"]               { padding:0 !important; }
    .block-container                     { padding:0 !important; max-width:100% !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── HTML completo da tela de login renderizado como iframe ──
    login_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}
  html, body {{
    height:100%; background:#F5F3EF;
    font-family:'DM Sans',system-ui,sans-serif;
    display:flex; align-items:center; justify-content:center;
  }}
  .card {{
    display:flex; width:880px; max-width:97vw;
    border-radius:18px; overflow:hidden;
    box-shadow:0 20px 80px rgba(0,0,0,.13);
    min-height:500px;
  }}
  /* Esquerda */
  .left {{
    width:50%; background:#0D0D0D; padding:44px;
    display:flex; flex-direction:column; justify-content:space-between;
    position:relative; overflow:hidden;
  }}
  .left::before {{
    content:''; position:absolute;
    width:460px; height:460px; border-radius:50%;
    border:1px solid rgba(255,255,255,.05);
    top:-190px; left:-170px; pointer-events:none;
  }}
  .left::after {{
    content:''; position:absolute;
    width:320px; height:320px; border-radius:50%;
    border:1px solid rgba(255,255,255,.04);
    bottom:-110px; right:-60px; pointer-events:none;
  }}
  .wordmark {{
    font-size:11px; font-weight:500; letter-spacing:.10em;
    text-transform:uppercase; color:rgba(255,255,255,.24);
    position:relative; z-index:1;
  }}
  .hero {{ position:relative; z-index:1; }}
  .hero h1 {{
    font-size:34px; font-weight:300; line-height:1.18;
    color:#fff; letter-spacing:-.5px; margin-bottom:13px;
  }}
  .hero h1 em {{ font-style:italic; color:rgba(255,255,255,.36); }}
  .hero p {{ font-size:13px; color:rgba(255,255,255,.30); max-width:250px; line-height:1.7; }}
  .badges {{ display:flex; gap:6px; flex-wrap:wrap; position:relative; z-index:1; }}
  .badge {{
    font-size:10px; font-weight:500; padding:4px 11px;
    border-radius:999px; border:1px solid rgba(255,255,255,.10);
    color:rgba(255,255,255,.30);
  }}
  /* Direita */
  .right {{
    flex:1; background:#fff; padding:44px;
    display:flex; flex-direction:column; justify-content:center;
  }}
  .right h2 {{
    font-size:21px; font-weight:500; color:#0D0D0D;
    margin-bottom:6px; letter-spacing:-.3px;
  }}
  .right p {{
    font-size:13px; color:#8A8A8A;
    line-height:1.65; margin-bottom:28px;
  }}
  .ms-btn {{
    display:flex; align-items:center; justify-content:center; gap:12px;
    width:100%; padding:14px 20px;
    background:#0D0D0D; color:#fff;
    border:none; border-radius:10px;
    font-family:'DM Sans',sans-serif;
    font-size:14px; font-weight:500;
    cursor:pointer; text-decoration:none;
    transition:opacity .15s;
  }}
  .ms-btn:hover {{ opacity:.82; }}
  .ms-icon {{ width:20px; height:20px; flex-shrink:0; }}
  .terms {{
    font-size:11px; color:#BBBBBB;
    text-align:center; margin-top:16px; line-height:1.6;
  }}
  @media (max-width:640px) {{
    .left {{ display:none; }}
    .right {{ padding:36px 28px; }}
  }}
</style>
</head>
<body>
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

    <!-- O botão usa onclick + window.top.location.href para sair do sandbox do iframe -->
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
    // Navega no contexto pai (o navegador real), não dentro do iframe sandboxed
    try {{
      window.top.location.href = AUTH_URL;
    }} catch(e) {{
      // Fallback: abre numa nova aba se window.top for bloqueado por CSP
      window.open(AUTH_URL, '_blank');
    }}
  }}
</script>
</body>
</html>"""

    components.html(login_html, height=580, scrolling=False)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
usuario  = st.session_state.get("usuario", {})
nome     = usuario.get("displayName") or "Gestor"
iniciais = "".join([p[0].upper() for p in nome.split()[:2]]) if nome else "GH"
cargo    = usuario.get("jobTitle") or "Colaborador"
email    = usuario.get("mail") or usuario.get("userPrincipalName") or ""

with st.sidebar:
    st.markdown(f"""
    <span class="sb-wordmark">GestorHub</span>
    <span class="sb-label">Principal</span>
    """, unsafe_allow_html=True)

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

    nome_safe  = html_lib.escape(str(nome))
    cargo_safe = html_lib.escape(str(cargo))
    st.markdown(f"""
    <div class="user-chip">
        <div class="user-avatar">{iniciais}</div>
        <div style="overflow:hidden;">
            <div class="user-name">{nome_safe}</div>
            <div class="user-role">{cargo_safe}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sair da conta", use_container_width=True):
        st.session_state.clear(); st.rerun()

# ── MOBILE BOTTOM NAV ─────────────────────────────────────────────────────────
_mob_active = {"🏠  Início": 0, "🎥  Resumos tl;dv": 1, "📊  Chamados": 2}.get(opcao, 0)
_mob_nav_items = [("🏠", "Início", "inicio"), ("🎥", "Resumos", "resumos"), ("📊", "Chamados", "chamados")]

# Hidden Streamlit buttons that the mobile nav triggers via click simulation
_mob_pg_map = {"inicio": "🏠  Início", "resumos": "🎥  Resumos tl;dv", "chamados": "📊  Chamados"}

# Check if a mobile nav button was pressed via query param set by JS
_mob_nav_target = st.query_params.get("mob_nav", "")
if _mob_nav_target and _mob_nav_target in _mob_pg_map:
    # Map to selectbox value and clear the param
    _new_page_label = _mob_pg_map[_mob_nav_target]
    _page_index = {"🏠  Início": 0, "🎥  Resumos tl;dv": 1, "📊  Chamados": 2}[_new_page_label]
    st.query_params.clear()
    st.query_params["page"] = _mob_nav_target
    st.rerun()

_mob_btns = ""
for _i, (_ico, _lbl, _pg_key) in enumerate(_mob_nav_items):
    _cls = "mob-nav-btn active" if _i == _mob_active else "mob-nav-btn"
    _mob_btns += f'<button class="{_cls}" onclick="mobNav(\'{_pg_key}\')" aria-label="{_lbl}"><span class="mob-icon">{_ico}</span>{_lbl}</button>'

st.markdown(f"""
<div class="mobile-nav" id="mob-nav">
  {_mob_btns}
</div>
<script>
function mobNav(page){{
  // Update query param and reload — works in both iframe and top-level contexts
  var target = window.top || window.parent || window;
  try {{
    var url = new URL(target.location.href);
    url.searchParams.set("page", page);
    // Remove stale mob_nav param if present
    url.searchParams.delete("mob_nav");
    target.location.href = url.toString();
  }} catch(e) {{
    try {{
      window.parent.location.href = "?page=" + page;
    }} catch(e2) {{
      window.location.href = "?page=" + page;
    }}
  }}
}}
</script>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def topbar(titulo: str, subtitulo: str):
    hoje_sp = datetime.now(tz=TZ_SP)
    dias    = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
    dstr    = f"{dias[hoje_sp.weekday()]}, {hoje_sp.day} de {MESES_PT[hoje_sp.month-1]} de {hoje_sp.year}"
    t_safe  = html_lib.escape(str(titulo or ""))
    s_safe  = html_lib.escape(str(subtitulo or ""))
    st.markdown(f"""
    <div class="gh-topbar">
        <div>
            <h2>{t_safe}</h2>
            <p>{s_safe} · {dstr}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _mini_cal_html(data_sel: date) -> str:
    """Static mini-calendar used inside the sidebar card (desktop). Clicking navigates."""
    hoje  = datetime.now(tz=TZ_SP).date()
    y, m  = data_sel.year, data_sel.month
    first = (date(y, m, 1).weekday() + 1) % 7
    total = (date(y, m % 12 + 1, 1) - date(y, m, 1)).days if m < 12 \
            else (date(y+1, 1, 1) - date(y, m, 1)).days
    cells = '<div class="cal-day out"></div>' * first
    for d in range(1, total + 1):
        dt  = date(y, m, d)
        iso = dt.isoformat()
        cls = "cal-day" + (" today" if dt == hoje else " sel" if dt == data_sel else "")
        cells += f'<div class="{cls}" onclick="pickDate(\'{iso}\')" style="cursor:pointer">{d}</div>'

    # prev / next month
    if m == 1: prev_y, prev_m = y-1, 12
    else:      prev_y, prev_m = y,   m-1
    if m == 12: next_y, next_m = y+1, 1
    else:       next_y, next_m = y,   m+1

    return f"""
    <div class="mini-cal">
      <div class="mcal-nav">
        <span style="font-size:18px;color:#8A8A8A;cursor:pointer;padding:4px 8px;"
              onclick="navMonth('{date(prev_y,prev_m,1).isoformat()}')">&#8249;</span>
        <span class="mcal-mon">{MESES_PT[m-1]} {y}</span>
        <span style="font-size:18px;color:#8A8A8A;cursor:pointer;padding:4px 8px;"
              onclick="navMonth('{date(next_y,next_m,1).isoformat()}')">&#8250;</span>
      </div>
      <div class="cal-grid">
        <div class="cal-dow">D</div><div class="cal-dow">S</div>
        <div class="cal-dow">T</div><div class="cal-dow">Q</div>
        <div class="cal-dow">Q</div><div class="cal-dow">S</div>
        <div class="cal-dow">S</div>{cells}
      </div>
    </div>
    <script>
    function _sendDate(iso){{
      var p=iso.split("-"),fmt=p[1]+"/"+p[2]+"/"+p[0];
      var docs=[];
      try{{docs.push(window.parent.document)}}catch(e){{}}
      try{{if(window.top!==window.parent)docs.push(window.top.document)}}catch(e){{}}
      for(var i=0;i<docs.length;i++){{
        var inp=docs[i].querySelector('[data-testid="stDateInput"] input');
        if(inp){{
          var sv=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,"value");
          sv.set.call(inp,fmt);
          inp.dispatchEvent(new Event("input",{{bubbles:true}}));
          inp.dispatchEvent(new Event("change",{{bubbles:true}}));
          return;
        }}
      }}
    }}
    function pickDate(iso){{ _sendDate(iso); }}
    function navMonth(iso){{ _sendDate(iso); }}
    </script>"""


def _calendar_widget(label: str, hoje_iso: str, sel_iso: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:'DM Sans',system-ui,sans-serif}}
html,body{{background:transparent;padding:4px 0 6px}}
.bar{{display:flex;align-items:center;gap:10px;position:relative}}
.cal-btn{{background:#FFF;border:1px solid rgba(13,13,13,.10);border-radius:8px;
  padding:7px 14px 7px 10px;display:inline-flex;align-items:center;gap:8px;
  font-size:13px;font-weight:500;color:#0D0D0D;user-select:none;cursor:default}}
.sync-btn{{width:32px;height:32px;border-radius:7px;background:#FFF;
  border:1px solid rgba(13,13,13,.10);cursor:pointer;font-size:17px;
  display:inline-flex;align-items:center;justify-content:center;color:#8A8A8A;transition:background .12s}}
.sync-btn:hover{{background:#F5F3EF;color:#0D0D0D}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.spinning{{animation:spin .5s linear}}
.dot{{width:5px;height:5px;border-radius:50%;background:#1C6C4E;display:inline-block}}
</style></head><body>
<div class="bar">
  <div class="cal-btn" id="tog">
    <span class="dot"></span><span id="lbl">{label}</span>
  </div>
  <button class="sync-btn" id="sbtn" onclick="doSync()">&#8635;</button>
</div>
<script>
(function(){{
  window.doSync=function(){{
    var b=document.getElementById("sbtn");b.classList.add("spinning");
    setTimeout(function(){{b.classList.remove("spinning");}},500);
    var docs=[];
    try{{docs.push(window.parent.document)}}catch(e){{}}
    for(var i=0;i<docs.length;i++){{
      var inp=docs[i].querySelector('[data-testid="stDateInput"] input');
      if(inp){{inp.dispatchEvent(new Event("input",{{bubbles:true}}));inp.dispatchEvent(new Event("change",{{bubbles:true}}));return;}}
    }}
  }};
}})();
</script>
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
    if st.session_state["data_agenda"] is None:
        st.session_state["data_agenda"] = hoje_sp
    data_sel = st.session_state["data_agenda"]
    label    = "Hoje" if data_sel == hoje_sp else f"{data_sel.day} {MESES_ABR[data_sel.month-1]} {data_sel.year}"

    data_input = st.date_input("data_oculta", value=data_sel,
                               key="date_picker_hidden", label_visibility="collapsed")
    if data_input != data_sel:
        st.session_state["data_agenda"] = data_input; st.rerun()

    components.html(_calendar_widget(label, hoje_sp.isoformat(), data_sel.isoformat()),
                    height=52, scrolling=False)

    col_agenda, col_side = st.columns([1.5, 1], gap="medium")

    with col_agenda:
        with st.spinner("Carregando agenda..."):
            eventos = buscar_agenda(st.session_state["access_token"], data_sel)
        if eventos == "EXPIRADO":
            st.session_state.clear(); st.rerun()

        # ── Janela fixa ──────────────────────────────────────────────────────
        _TL_START = datetime(data_sel.year, data_sel.month, data_sel.day, 8,  0, tzinfo=TZ_SP)
        _TL_END   = datetime(data_sel.year, data_sel.month, data_sel.day, 18, 48, tzinfo=TZ_SP)

        # ── Coleta eventos válidos com metadados ─────────────────────────────
        _ev_data = []   # (s, e, subject, link, platform)
        for ev in eventos:
            if ev.get("_allday"):
                continue
            try:
                s = pd.to_datetime(ev["start"]["dateTime"])
                e = pd.to_datetime(ev["end"]["dateTime"])
                if s.tzinfo is None: s = s.tz_localize("UTC")
                if e.tzinfo is None: e = e.tz_localize("UTC")
                s = s.tz_convert(TZ_SP)
                e = e.tz_convert(TZ_SP)
                s = max(s, _TL_START)
                e = min(e, _TL_END)
                if s >= e:
                    continue
                lnk = (ev.get("onlineMeeting") or {}).get("joinUrl") or ev.get("onlineMeetingUrl","")
                u   = ev.get("onlineMeetingUrl","") or ""
                plt = "Teams" if "teams.microsoft" in u else "Zoom" if "zoom.us" in u else "Meet" if "meet.google" in u else ""
                _ev_data.append((s, e, str(ev.get("subject") or "Sem título"), lnk, plt))
            except Exception:
                continue

        _ev_data.sort(key=lambda x: x[0])

        # ── Mesclar sobrepostos (preserva primeiro subject/link) ─────────────
        _merged = []  # (s, e, subject, link, platform)
        for s, e, subj, lnk, plt in _ev_data:
            if _merged and s <= _merged[-1][1]:
                ps, pe, psubj, plnk, pplt = _merged[-1]
                _merged[-1] = (ps, max(pe, e), psubj, plnk, pplt)
            else:
                _merged.append((s, e, subj, lnk, plt))

        # ── Construir linha do tempo ─────────────────────────────────────────
        def _fmt_dur(a, b):
            d = int((b - a).total_seconds() / 60)
            if d <= 0: return ""
            h, m = divmod(d, 60)
            if h == 0:   return f"{m}min"
            if m == 0:   return f"{h}h"
            return f"{h}h{m:02d}"

        _timeline = []   # dicts: type, hi, hf, dur, subject, link, platform
        cursor = _TL_START
        for s, e, subj, lnk, plt in _merged:
            if s > cursor:
                _timeline.append({"type": "livre", "hi": cursor.strftime("%H:%M"),
                                   "hf": s.strftime("%H:%M"), "dur": _fmt_dur(cursor, s),
                                   "subject": "", "link": "", "platform": ""})
            _timeline.append({"type": "ocupado", "hi": s.strftime("%H:%M"),
                               "hf": e.strftime("%H:%M"), "dur": _fmt_dur(s, e),
                               "subject": subj, "link": lnk, "platform": plt})
            cursor = e
        if cursor < _TL_END:
            _timeline.append({"type": "livre", "hi": cursor.strftime("%H:%M"),
                               "hf": _TL_END.strftime("%H:%M"), "dur": _fmt_dur(cursor, _TL_END),
                               "subject": "", "link": "", "platform": ""})

        total_ev = len([t for t in _timeline if t["type"] == "ocupado"])

        # ── Gerar HTML dos blocos ────────────────────────────────────────────
        if not _timeline:
            tl_rows = '<div class="empty-box"><div class="ei">🎉</div><p>Nenhum evento neste dia.</p></div>'
        else:
            tl_rows = ""
            for blk in _timeline:
                if blk["type"] == "ocupado":
                    subj_safe = html_lib.escape(blk["subject"])
                    sub_parts = [p for p in [blk["platform"]] if p]
                    sub_html  = f'<div class="ev-sub">{" · ".join(sub_parts)}</div>' if sub_parts else ""
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
                        <div class="tl-title">{subj_safe}</div>
                        {sub_html}
                      </div>
                      {btn_html}
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
          </div>
          {tl_rows}
        </div>"""

        _tl_height = max(140, 56 + len(_timeline) * 72)
        components.html(f"""<!DOCTYPE html><html><head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
        *{{box-sizing:border-box;margin:0;padding:0}}
        html,body{{background:#F5F3EF;font-family:'DM Sans',system-ui,sans-serif}}
        .gh-card{{background:#FFF;border:1px solid rgba(13,13,13,.09);border-radius:14px;overflow:hidden;font-family:'DM Sans',sans-serif;margin-bottom:4px}}
        .card-hd{{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid rgba(13,13,13,.07)}}
        .card-title{{font-size:13px;font-weight:500;color:#0D0D0D}}
        .card-meta{{font-size:11px;color:#8A8A8A}}

        /* timeline rows */
        .tl-row{{display:flex;align-items:stretch;gap:12px;padding:10px 20px;border-bottom:1px solid rgba(13,13,13,.05);transition:background .1s;font-family:'DM Sans',sans-serif}}
        .tl-row:last-child{{border-bottom:none}}
        .tl-busy:hover{{background:#F9F8F6}}
        .tl-free{{background:#FAFAF8}}
        .tl-free:hover{{background:#F5F3EF}}

        /* time column */
        .tl-times{{display:flex;flex-direction:column;align-items:flex-end;width:44px;flex-shrink:0;padding-top:2px;gap:3px}}
        .tl-t{{font-family:'DM Mono',monospace;font-size:10px;color:#8A8A8A;line-height:1}}
        .tl-t-free{{color:#AAAAAA}}
        .tl-sep{{flex:1;width:1px;background:rgba(13,13,13,.10);align-self:center;min-height:14px;margin:3px 0}}
        .tl-sep-free{{background:rgba(13,13,13,.06)}}

        /* accent bar */
        .tl-bar{{width:3px;border-radius:2px;flex-shrink:0;align-self:stretch;min-height:40px}}
        .tl-bar-busy{{background:#1A4F8A}}
        .tl-bar-free{{background:#D6EDE5}}

        /* body */
        .tl-body{{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center;gap:3px}}
        .tl-label-tag{{display:inline-flex;align-items:center;font-size:10px;font-weight:500;letter-spacing:.04em;padding:2px 7px;border-radius:4px;width:fit-content}}
        .tl-tag-busy{{background:#E8EEF6;color:#1A4F8A}}
        .tl-tag-free{{background:#D6EDE5;color:#1C6C4E}}
        .tl-title{{font-size:13px;font-weight:500;color:#0D0D0D;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
        .tl-sub{{font-size:11px;color:#8A8A8A}}

        /* buttons */
        .btn-join{{font-size:11px;font-weight:500;padding:6px 13px;border-radius:6px;background:#0D0D0D;color:#fff!important;border:none;text-decoration:none!important;flex-shrink:0;transition:opacity .12s;font-family:'DM Sans',sans-serif;cursor:pointer;align-self:center}}
        .btn-join:hover{{opacity:.75}}
        .no-link{{font-size:11px;color:#CCC;flex-shrink:0;align-self:center}}

        /* empty */
        .empty-box{{text-align:center;padding:36px 20px}}
        .empty-box .ei{{font-size:26px}}
        .empty-box p{{font-size:13px;color:#8A8A8A;margin-top:8px}}
        </style></head><body>{agenda_html}</body></html>""",
        height=_tl_height, scrolling=False)

    with col_side:
        # ── DAY PULSE ── janela fixa 08:00–18:48 (648 min) ──────────────────
        BASE_MIN = 648
        WIN_START = datetime(data_sel.year, data_sel.month, data_sel.day, 8,  0, tzinfo=TZ_SP)
        WIN_END   = datetime(data_sel.year, data_sel.month, data_sel.day, 18, 48, tzinfo=TZ_SP)

        # 1. Filtrar e converter eventos válidos (ignorar _allday)
        _evs_raw = []
        for ev in eventos:
            if ev.get("_allday"):
                continue
            try:
                s = pd.to_datetime(ev["start"]["dateTime"])
                e = pd.to_datetime(ev["end"]["dateTime"])
                if s.tzinfo is None: s = s.tz_localize("UTC")
                if e.tzinfo is None: e = e.tz_localize("UTC")
                s = s.tz_convert(TZ_SP)
                e = e.tz_convert(TZ_SP)
                # Ajustar à janela
                s = max(s, WIN_START)
                e = min(e, WIN_END)
                if s >= e:
                    continue
                _evs_raw.append((s, e))
            except Exception:
                continue

        # 2. Ordenar por início
        _evs_raw.sort(key=lambda x: x[0])

        # 3. Mesclar sobrepostos
        merged = []
        for s, e in _evs_raw:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))

        # 4. Métricas
        total_eventos    = len([ev for ev in eventos if not ev.get("_allday")])
        tempo_ocupado_min = sum((e - s).total_seconds() / 60 for s, e in merged)
        tempo_livre_min   = max(0, BASE_MIN - tempo_ocupado_min)
        pct_raw           = tempo_ocupado_min / BASE_MIN * 100 if tempo_ocupado_min > 0 else 0
        pct               = min(100, int(pct_raw))
        fim_ultimo_evento = merged[-1][1].strftime("%H:%M") if merged else "--:--"

        # 5. Intervalos livres
        def _fmt_interval(a, b):
            return f"{a.strftime('%H:%M')} → {b.strftime('%H:%M')}"

        intervalos_livres = []
        cursor = WIN_START
        for s, e in merged:
            if s > cursor:
                intervalos_livres.append((cursor, s))
            cursor = e
        if cursor < WIN_END:
            intervalos_livres.append((cursor, WIN_END))

        def _dur_label(a, b):
            d = int((b - a).total_seconds() / 60)
            return f"{d//60}h {d%60}m" if d >= 60 else f"{d}m"

        proximo_livre = None
        agora_sp = datetime.now(tz=TZ_SP)
        for a, b in intervalos_livres:
            if b > agora_sp or data_sel != datetime.now(tz=TZ_SP).date():
                proximo_livre = (a, b)
                break
        if proximo_livre is None and intervalos_livres:
            proximo_livre = intervalos_livres[0]

        maior_intervalo = max(intervalos_livres, key=lambda x: (x[1]-x[0]).total_seconds()) if intervalos_livres else None

        prox_txt  = f"{_fmt_interval(*proximo_livre)} ({_dur_label(*proximo_livre)})"  if proximo_livre  else "–"
        maior_txt = f"{_fmt_interval(*maior_intervalo)} ({_dur_label(*maior_intervalo)})" if maior_intervalo else "–"

        # 6. Formatação de tempo
        h_oc  = int(tempo_ocupado_min // 60); m_oc  = int(tempo_ocupado_min % 60)
        h_liv = int(tempo_livre_min   // 60); m_liv = int(tempo_livre_min   % 60)

        # 7. Cor da barra
        if pct_raw < 50:
            bar_color = "#1C6C4E"   # verde
        elif pct_raw < 80:
            bar_color = "#8C5A00"   # amarelo
        else:
            bar_color = "#B83232"   # vermelho

        # ── Linha do tempo para o Day Pulse ─────────────────────────────────
        def _dp_fmt_dur(a, b):
            d = int((b - a).total_seconds() / 60)
            if d <= 0: return ""
            h2, m2 = divmod(d, 60)
            if h2 == 0:  return f"{m2}min"
            if m2 == 0:  return f"{h2}h"
            return f"{h2}h{m2:02d}"

        _dp_timeline = []
        _dp_cursor = WIN_START
        for s, e in merged:
            if s > _dp_cursor:
                _dp_timeline.append({"type": "livre",
                                     "hi": _dp_cursor.strftime("%H:%M"),
                                     "hf": s.strftime("%H:%M"),
                                     "dur": _dp_fmt_dur(_dp_cursor, s),
                                     "subject": ""})
            _dp_timeline.append({"type": "ocupado",
                                  "hi": s.strftime("%H:%M"),
                                  "hf": e.strftime("%H:%M"),
                                  "dur": _dp_fmt_dur(s, e),
                                  "subject": ""})
            _dp_cursor = e
        if _dp_cursor < WIN_END:
            _dp_timeline.append({"type": "livre",
                                  "hi": _dp_cursor.strftime("%H:%M"),
                                  "hf": WIN_END.strftime("%H:%M"),
                                  "dur": _dp_fmt_dur(_dp_cursor, WIN_END),
                                  "subject": ""})

        # Enriquecer blocos "ocupado" com o subject do evento correspondente
        _busy_blocks = [blk for blk in _dp_timeline if blk["type"] == "ocupado"]
        _busy_idx = 0
        for blk in _dp_timeline:
            if blk["type"] != "ocupado":
                continue
            for ev in eventos:
                if ev.get("_allday"): continue
                try:
                    _s = pd.to_datetime(ev["start"]["dateTime"])
                    if _s.tzinfo is None: _s = _s.tz_localize("UTC")
                    _s = _s.tz_convert(TZ_SP)
                    if max(_s, WIN_START).strftime("%H:%M") == blk["hi"]:
                        blk["subject"] = str(ev.get("subject") or "Reunião")
                        break
                except Exception:
                    pass
            if not blk["subject"]:
                blk["subject"] = "Reunião"

        # Gerar HTML dos blocos do Day Pulse timeline
        _dp_rows = ""
        for blk in _dp_timeline:
            if blk["type"] == "ocupado":
                _subj_safe = html_lib.escape(blk["subject"])
                _dp_rows += f"""
                <div class="dp-blk dp-blk-busy">
                  <div class="dp-tms">
                    <div class="dp-t">{blk["hi"]}</div>
                    <div class="dp-sep"></div>
                    <div class="dp-t">{blk["hf"]}</div>
                  </div>
                  <div class="dp-bar dp-bar-busy"></div>
                  <div class="dp-body">
                    <div class="dp-tag dp-tag-busy">Reunião · {blk["dur"]}</div>
                    <div class="dp-title">{_subj_safe}</div>
                  </div>
                </div>"""
            else:
                _dp_rows += f"""
                <div class="dp-blk dp-blk-free">
                  <div class="dp-tms">
                    <div class="dp-t dp-t-free">{blk["hi"]}</div>
                    <div class="dp-sep dp-sep-free"></div>
                    <div class="dp-t dp-t-free">{blk["hf"]}</div>
                  </div>
                  <div class="dp-bar dp-bar-free"></div>
                  <div class="dp-body">
                    <div class="dp-tag dp-tag-free">Disponível · {blk["dur"]}</div>
                  </div>
                </div>"""

        _dp_rows_or_empty = _dp_rows if _dp_rows else '<div style="padding:12px;font-size:12px;color:#8A8A8A;text-align:center;">Dia livre 🎉</div>'

        _day_pulse_html = (
            '<div class="gh-card">'
            '<div class="card-hd"><span class="card-title">Day Pulse</span><span class="card-meta">Resumo do dia</span></div>'
            '<div class="pulse-grid">'
            f'<div class="pulse-cell"><div class="pulse-lbl">Eventos</div><div class="pulse-val c-blue">{total_eventos}</div></div>'
            f'<div class="pulse-cell"><div class="pulse-lbl">Ocupado</div><div class="pulse-val">{h_oc}h {m_oc}m</div></div>'
            f'<div class="pulse-cell"><div class="pulse-lbl">Livre</div><div class="pulse-val c-green">{h_liv}h {m_liv}m</div></div>'
            f'<div class="pulse-cell"><div class="pulse-lbl">Término</div><div class="pulse-val c-red">{fim_ultimo_evento}</div></div>'
            '</div>'
            '<div class="prog-wrap">'
            f'<div class="prog-lbl"><span>Ocupação</span><span>{pct}%</span></div>'
            f'<div class="prog-track"><div class="prog-fill" style="width:{pct}%;background:{bar_color}"></div></div>'
            '</div>'
            '<div class="dp-tl-wrap">'
            '<div class="dp-tl-hd">Linha do tempo · 08:00 – 18:48</div>'
            + _dp_rows_or_empty +
            '</div>'
            '</div>'
        )
        st.markdown(_day_pulse_html, unsafe_allow_html=True)

        st.markdown("""
        <div class="gh-card">
          <div class="card-hd"><span class="card-title">Calendário</span></div>
        """, unsafe_allow_html=True)
        cal_inner = _mini_cal_html(data_sel)
        components.html(
            f"""<!DOCTYPE html><html><head>
            <meta charset="UTF-8">
            <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
            <style>
            *{{box-sizing:border-box;margin:0;padding:0;font-family:'DM Sans',system-ui,sans-serif}}
            html,body{{background:#fff;padding:0}}
            .mini-cal{{padding:13px 20px}}
            .mcal-nav{{display:flex;justify-content:space-between;align-items:center;margin-bottom:9px}}
            .mcal-mon{{font-size:12px;font-weight:500;color:#0D0D0D}}
            .cal-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}}
            .cal-dow{{font-size:9px;font-weight:600;color:#AAAAAA;text-align:center;padding:3px 0;letter-spacing:.04em;text-transform:uppercase}}
            .cal-day{{font-size:11px;font-family:'DM Mono',monospace;text-align:center;padding:5px 2px;border-radius:5px;color:#0D0D0D}}
            .cal-day:hover:not(.out){{background:#F5F3EF;cursor:pointer}}
            .cal-day.today{{background:#0D0D0D;color:#fff}}
            .cal-day.sel:not(.today){{background:#E8E5DF}}
            .cal-day.out{{color:rgba(13,13,13,.18);pointer-events:none}}
            </style></head><body>{cal_inner}</body></html>""",
            height=240, scrolling=False
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: RESUMOS
# ══════════════════════════════════════════════════════════════════════════════
def pagina_resumos():
    topbar("Resumos de Reuniões", "Insights extraídos via tl;dv · Últimas 2 semanas")
    st.markdown("""
    <div class="resumo-card">
      <div class="resumo-top">
        <div class="resumo-row">
          <div><div class="resumo-tit">Comitê de Mudanças (CAB)</div>
               <div class="resumo-when">Hoje, 10:30 · 45 min · 6 participantes</div></div>
          <div class="tags"><span class="tag tag-amber">🟡 CAB</span><span class="tag tag-gray">tl;dv</span></div>
        </div>
        <div class="resumo-body">A equipe aprovou a atualização do banco de dados do ERP para este domingo,
        com janela das 22h às 02h. Bernardo ficará de plantão. Foram discutidos riscos de rollback e o processo
        de comunicação para os usuários afetados.</div>
        <div class="actions-box">
          <div class="actions-lbl">Ações extraídas</div>
          <div class="act-row"><div class="act-chk done"></div><div>
            <div class="act-text">Agendar plantão para Bernardo no domingo</div>
            <div class="act-who">Ana M. · Prazo: 30 Abr</div></div></div>
          <div class="act-row"><div class="act-chk"></div><div>
            <div class="act-text">Preparar plano de rollback documentado</div>
            <div class="act-who">Equipe DBA · Prazo: 02 Mai</div></div></div>
          <div class="act-row"><div class="act-chk"></div><div>
            <div class="act-text">Enviar comunicado para usuários do ERP</div>
            <div class="act-who">Comunicação · Prazo: 03 Mai</div></div></div>
        </div>
      </div>
      <div class="resumo-footer">
        <a href="#" class="btn-sm-pri">🎬 Ver gravação</a>
        <a href="#" class="btn-sm">📋 Copiar resumo</a>
        <a href="#" class="btn-sm">📤 Compartilhar</a>
      </div>
    </div>
    <div class="resumo-card">
      <div class="resumo-top">
        <div class="resumo-row">
          <div><div class="resumo-tit">1:1 com Diretor de Tecnologia</div>
               <div class="resumo-when">28 Abr, 14:00 · 52 min · 2 participantes</div></div>
          <div class="tags"><span class="tag tag-blue">🔵 1:1</span><span class="tag tag-gray">tl;dv</span></div>
        </div>
        <div class="resumo-body">Revisão do roadmap do Q2. O diretor sinalizou que o projeto de migração
        para cloud deve ser prioridade máxima. Orçamento adicional pode ser aprovado até o final de maio.
        Discussão sobre headcount para o segundo semestre.</div>
      </div>
      <div class="resumo-footer">
        <a href="#" class="btn-sm-pri">🎬 Ver gravação</a>
        <a href="#" class="btn-sm">📋 Copiar resumo</a>
      </div>
    </div>
    <div class="resumo-card">
      <div class="resumo-top">
        <div class="resumo-row">
          <div><div class="resumo-tit">Reunião de Alinhamento — Squad</div>
               <div class="resumo-when">27 Abr, 09:00 · 60 min · 8 participantes</div></div>
          <div class="tags"><span class="tag tag-green">🟢 Squad</span><span class="tag tag-gray">tl;dv</span></div>
        </div>
        <div class="resumo-body">Sprint 24 revisada: 9 de 12 stories entregues. Dois impedimentos técnicos
        identificados na integração com o gateway de pagamentos. Próxima sprint planeja focar em estabilidade
        antes de novas funcionalidades.</div>
      </div>
      <div class="resumo-footer">
        <a href="#" class="btn-sm-pri">🎬 Ver gravação</a>
        <a href="#" class="btn-sm">📋 Copiar resumo</a>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: CHAMADOS (Power BI)
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
