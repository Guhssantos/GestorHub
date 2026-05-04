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
  // Tenta postMessage para o contexto pai (sem restrição cross-origin)
  try{{window.parent.postMessage({{type:"gh_nav",page:page}},"*");}}catch(e){{}}
  try{{window.top.postMessage({{type:"gh_nav",page:page}},"*");}}catch(e){{}}
  // Fallback direto neste contexto
  try{{
    var u=new URL(window.location.href);
    u.searchParams.set("page",page);
    window.location.href=u.toString();
  }}catch(e2){{window.location.href="?page="+page;}}
}}
// Listener para navegação mobile vinda de iframe interno
window.addEventListener("message",function(e){{
  if(!e.data||typeof e.data!=="object")return;
  if(e.data.type==="gh_nav"&&e.data.page){{
    try{{
      var u=new URL(window.location.href);
      u.searchParams.set("page",e.data.page);
      window.location.href=u.toString();
    }}catch(ex){{window.location.href="?page="+e.data.page;}}
  }}
}},false);
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
    hoje_iso = datetime.now(tz=TZ_SP).date().isoformat()
    sel_iso  = data_sel.isoformat()
    meses_js = '["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]'
    # Monta o HTML+JS como string pura (sem f-string no JS para evitar conflito de chaves/aspas)
    html = '<div id="ghcal"></div>\n'
    html += '<script>\n'
    html += '(function(){\n'
    html += '  var MESES=' + meses_js + ';\n'
    html += '  var HOJE="' + hoje_iso + '", SEL="' + sel_iso + '";\n'
    html += '  var hY=+HOJE.slice(0,4),hM=+HOJE.slice(5,7)-1,hD=+HOJE.slice(8,10);\n'
    html += '  var sY=+SEL.slice(0,4), sM=+SEL.slice(5,7)-1, sD=+SEL.slice(8,10);\n'
    html += '  var cy=sY,cm=sM;\n'
    html += '  function z(n){return n<10?"0"+n:""+n;}\n'
    html += '  function mkiso(y,m,d){return y+"-"+z(m+1)+"-"+z(d);}\n'
    html += '  function render(){\n'
    html += '    var first=new Date(cy,cm,1).getDay();\n'
    html += '    var days=new Date(cy,cm+1,0).getDate();\n'
    html += '    var py=cm===0?cy-1:cy, pm=cm===0?11:cm-1;\n'
    html += '    var ny=cm===11?cy+1:cy, nm=cm===11?0:cm+1;\n'
    html += '    var h="";\n'
    html += '    h+=\'<div class="mcal-nav">\';\n'
    html += '    h+=\'<span class="nav-arr" onclick="navM(\'+py+\',\'+pm+\')">&#8249;</span>\';\n'
    html += '    h+=\'<span class="mcal-mon">\'+MESES[cm]+\' \'+cy+\'</span>\';\n'
    html += '    h+=\'<span class="nav-arr" onclick="navM(\'+ny+\',\'+nm+\')">&#8250;</span>\';\n'
    html += '    h+=\'</div><div class="cal-grid">\';\n'
    html += '    h+=\'<div class="cal-dow">D</div><div class="cal-dow">S</div><div class="cal-dow">T</div><div class="cal-dow">Q</div><div class="cal-dow">Q</div><div class="cal-dow">S</div><div class="cal-dow">S</div>\';\n'
    html += '    for(var i=0;i<first;i++) h+=\'<div class="cal-day out">&nbsp;</div>\';\n'
    html += '    for(var d=1;d<=days;d++){\n'
    html += '      var iso=mkiso(cy,cm,d);\n'
    html += '      var isH=(cy===hY&&cm===hM&&d===hD);\n'
    html += '      var isS=(cy===sY&&cm===sM&&d===sD);\n'
    html += '      var cls="cal-day"+(isH?" today":isS?" sel":"");\n'
    html += '      h+=\'<div class="\'+cls+\'" onclick="pickDay(\\"\'+iso+\'\\")">\'+d+\'</div>\';\n'
    html += '    }\n'
    html += '    h+=\'</div>\';\n'
    html += '    document.getElementById("ghcal").innerHTML=h;\n'
    html += '  }\n'
    html += '  window.navM=function(y,m){cy=+y;cm=+m;render();};\n'
    html += '  window.pickDay=function(iso){\n'
    html += '    var go=function(ctx){try{var u=new URL(ctx.location.href);u.searchParams.set("date",iso);ctx.location.href=u.toString();return true;}catch(e){return false;}};\n'
    html += '    if(!go(window))if(!go(window.parent))go(window.top);\n'
    html += '  };\n'
    html += '  render();\n'
    html += '})();\n'
    html += '</script>\n'
    return html


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
def _render_mini_cal(data_sel):
    """Calendário visual 100% nativo Streamlit — usa st.button para cada dia."""
    import calendar as _cal
    from datetime import date, timedelta

    hoje = datetime.now(tz=TZ_SP).date()

    # Estado do mês exibido no calendário
    if "cal_view_y" not in st.session_state:
        st.session_state["cal_view_y"] = data_sel.year
    if "cal_view_m" not in st.session_state:
        st.session_state["cal_view_m"] = data_sel.month

    vy = st.session_state["cal_view_y"]
    vm = st.session_state["cal_view_m"]

    # CSS do mini-cal
    st.markdown("""
    <style>
    .gh-card-cal{background:#fff;border:1px solid rgba(13,13,13,.09);
                 border-radius:14px;overflow:hidden;margin-bottom:16px;}
    .cal-header{display:flex;align-items:center;justify-content:space-between;
                padding:14px 20px;border-bottom:1px solid rgba(13,13,13,.07);}
    .cal-title{font-size:13px;font-weight:500;color:#0D0D0D;
               font-family:'DM Sans',sans-serif;}
    /* Botões de dia */
    div[data-testid="stColumns"] button[kind="secondary"] {
        background:transparent!important;border:none!important;
        color:#0D0D0D!important;font-family:'DM Mono',monospace!important;
        font-size:11px!important;padding:4px 2px!important;
        border-radius:6px!important;width:100%!important;
        min-height:28px!important;line-height:1!important;
    }
    div[data-testid="stColumns"] button[kind="secondary"]:hover {
        background:#F5F3EF!important;
    }
    /* Botão nav mês */
    .cal-nav-btn button {
        background:transparent!important;border:none!important;
        color:#8A8A8A!important;font-size:16px!important;
        padding:2px 8px!important;border-radius:6px!important;
        min-height:28px!important;
    }
    .cal-nav-btn button:hover {background:#F5F3EF!important;}
    /* Esconder label de columns */
    div[data-testid="stColumns"] > div { padding:1px!important; }
    </style>
    <div class="gh-card-cal">
      <div class="cal-header"><span class="cal-title">Calendário</span></div>
    </div>
    """, unsafe_allow_html=True)

    # Navegação de mês
    prev_m = vm - 1 if vm > 1 else 12
    prev_y = vy if vm > 1 else vy - 1
    next_m = vm + 1 if vm < 12 else 1
    next_y = vy if vm < 12 else vy + 1

    nav_cols = st.columns([1, 3, 1])
    with nav_cols[0]:
        if st.button("‹", key="cal_prev", help="Mês anterior"):
            st.session_state["cal_view_m"] = prev_m
            st.session_state["cal_view_y"] = prev_y
            st.rerun()
    with nav_cols[1]:
        st.markdown(
            f"<p style='text-align:center;font-size:12px;font-weight:500;"
            f"color:#0D0D0D;font-family:DM Sans,sans-serif;margin:4px 0'>"
            f"{MESES_PT[vm-1]} {vy}</p>",
            unsafe_allow_html=True
        )
    with nav_cols[2]:
        if st.button("›", key="cal_next", help="Próximo mês"):
            st.session_state["cal_view_m"] = next_m
            st.session_state["cal_view_y"] = next_y
            st.rerun()

    # Cabeçalho dias da semana
    dow_labels = ["D","S","T","Q","Q","S","S"]
    dow_cols = st.columns(7)
    for i, lbl in enumerate(dow_labels):
        with dow_cols[i]:
            st.markdown(
                f"<p style='text-align:center;font-size:9px;font-weight:600;"
                f"color:#AAAAAA;letter-spacing:.04em;margin:2px 0'>{lbl}</p>",
                unsafe_allow_html=True
            )

    # Calcular primeiro dia do mês (0=seg..6=dom) → converter para dom=0
    first_weekday = (date(vy, vm, 1).weekday() + 1) % 7  # 0=dom
    days_in_month = _cal.monthrange(vy, vm)[1]

    # Montar grade de 6 semanas × 7 dias
    cells = [None] * first_weekday
    for d in range(1, days_in_month + 1):
        cells.append(date(vy, vm, d))
    # Preencher até múltiplo de 7
    while len(cells) % 7 != 0:
        cells.append(None)

    weeks = [cells[i:i+7] for i in range(0, len(cells), 7)]

    for week in weeks:
        week_cols = st.columns(7)
        for ci, dt in enumerate(week):
            with week_cols[ci]:
                if dt is None:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                else:
                    is_today = (dt == hoje)
                    is_sel   = (dt == data_sel)
                    # Estilo inline para hoje e selecionado
                    if is_today:
                        style = ("background:#0D0D0D!important;"
                                 "color:#fff!important;border-radius:6px!important;")
                    elif is_sel:
                        style = ("background:#E8E5DF!important;"
                                 "color:#0D0D0D!important;border-radius:6px!important;")
                    else:
                        style = ""

                    btn_key = f"cal_day_{vy}_{vm}_{dt.day}"
                    if style:
                        st.markdown(
                            f"<style>div[data-testid='stColumns'] "
                            f"[data-testid='stButton'] button[aria-label='{dt.day}']"
                            f"{{{style}}}</style>",
                            unsafe_allow_html=True
                        )
                    clicked = st.button(
                        str(dt.day),
                        key=btn_key,
                        help=dt.strftime("%d/%m/%Y"),
                    )
                    if clicked:
                        st.session_state["data_agenda"] = dt
                        st.session_state["cal_view_y"]  = vy
                        st.session_state["cal_view_m"]  = vm
                        st.rerun()


def pagina_inicio():
    h = datetime.now(tz=TZ_SP).hour
    saudacao = "Bom dia" if h < 12 else "Boa tarde" if h < 18 else "Boa noite"
    topbar(f"{saudacao}, {nome.split()[0] if nome else 'Gestor'} 👋",
           "Agenda sincronizada com a Microsoft")

    hoje_sp = datetime.now(tz=TZ_SP).date()
    # Lê ?date=YYYY-MM-DD enviado pelo clique no calendário JS
    _qdate = st.query_params.get("date", "")
    if _qdate:
        try:
            _parsed = date.fromisoformat(_qdate)
            st.session_state["data_agenda"] = _parsed
        except ValueError:
            pass
        # Remove o param para não ficar em loop
        _qp = dict(st.query_params)
        _qp.pop("date", None)
        st.query_params.clear()
        for _k,_v in _qp.items(): st.query_params[_k] = _v
    if st.session_state["data_agenda"] is None:
        st.session_state["data_agenda"] = hoje_sp
    data_sel = st.session_state["data_agenda"]
    label    = "Hoje" if data_sel == hoje_sp else f"{data_sel.day} {MESES_ABR[data_sel.month-1]} {data_sel.year}"

    # date_input principal agora é o cal_date_picker dentro do card Calendário

    components.html(_calendar_widget(label, hoje_sp.isoformat(), data_sel.isoformat()),
                    height=52, scrolling=False)

    col_agenda, col_side = st.columns([1.5, 1], gap="medium")

    with col_agenda:
        with st.spinner("Carregando agenda..."):
            eventos = buscar_agenda(st.session_state["access_token"], data_sel)
        if eventos == "EXPIRADO":
            st.session_state.clear(); st.rerun()

        total = len(eventos)
        cores = ["#1A4F8A","#1C6C4E","#8C5A00","#B83232","#6B3A8C"]
        rows  = ""
        if total == 0:
            rows = '<div class="empty-box"><div class="ei">🎉</div><p>Nenhum evento neste dia.</p></div>'
        else:
            for i, ev in enumerate(eventos):
                cor   = cores[i % len(cores)]
                titre = html_lib.escape(str(ev.get("subject") or "Sem título"))
                if ev.get("_allday"):
                    btn = '<span class="allday-badge">Dia todo</span>'; hi = hf = "–"
                else:
                    hi  = _parse_horario(ev,"start"); hf = _parse_horario(ev,"end")
                    lnk = (ev.get("onlineMeeting") or {}).get("joinUrl") or ev.get("onlineMeetingUrl","")
                    btn = f'<a href="{lnk}" target="_blank" class="btn-join">Entrar</a>' if lnk else '<span class="no-link">Sem link</span>'
                u   = ev.get("onlineMeetingUrl","") or ""
                plt = "Microsoft Teams" if "teams.microsoft" in u else "Zoom" if "zoom.us" in u else "Google Meet" if "meet.google" in u else ""
                dm  = int(_duracao_min(ev))
                dur = (f"{dm//60}h {dm%60}m" if dm>=60 else f"{dm}m") if dm>0 else ""
                sub = f"{plt} · {dur}" if plt and dur else plt or dur
                rows += f"""
                <div class="event-row">
                  <div class="ev-times"><div class="ev-time">{hi}</div><div class="ev-time">{hf}</div></div>
                  <div class="ev-bar" style="background:{cor}"></div>
                  <div class="ev-body">
                    <div class="ev-title">{titre}</div>
                    {'<div class="ev-sub">'+sub+'</div>' if sub else ''}
                  </div>
                  {btn}
                </div>"""

        agenda_html = f"""
        <div class="gh-card">
          <div class="card-hd">
            <span class="card-title">Agenda do dia</span>
            <span class="card-meta">{total} evento{'s' if total!=1 else ''}</span>
          </div>
          {rows}
        </div>"""
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
        .event-row{{display:flex;align-items:center;gap:14px;padding:12px 20px;border-bottom:1px solid rgba(13,13,13,.06);transition:background .1s;font-family:'DM Sans',sans-serif}}
        .event-row:last-child{{border-bottom:none}}
        .event-row:hover{{background:#F5F3EF}}
        .ev-times{{width:48px;flex-shrink:0;text-align:right}}
        .ev-time{{font-family:'DM Mono',monospace;font-size:11px;color:#8A8A8A;line-height:1.5}}
        .ev-bar{{width:3px;border-radius:2px;flex-shrink:0;align-self:stretch;min-height:36px}}
        .ev-body{{flex:1;min-width:0}}
        .ev-title{{font-size:13px;font-weight:500;color:#0D0D0D;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
        .ev-sub{{font-size:11px;color:#8A8A8A;margin-top:2px}}
        .btn-join{{font-size:11px;font-weight:500;padding:6px 13px;border-radius:6px;background:#0D0D0D;color:#fff!important;border:none;text-decoration:none!important;flex-shrink:0;transition:opacity .12s;font-family:'DM Sans',sans-serif;cursor:pointer}}
        .btn-join:hover{{opacity:.75}}
        .no-link{{font-size:11px;color:#CCC;flex-shrink:0}}
        .allday-badge{{font-size:10px;font-weight:500;padding:3px 8px;border-radius:4px;background:#F0EDE8;color:#8A8A8A;flex-shrink:0}}
        .empty-box{{text-align:center;padding:36px 20px}}
        .empty-box .ei{{font-size:26px}}
        .empty-box p{{font-size:13px;color:#8A8A8A;margin-top:8px}}
        </style></head><body>{agenda_html}</body></html>""",
        height=max(120, 68 + total * 70), scrolling=False)

    with col_side:
        total_min = sum(_duracao_min(ev) for ev in eventos if not ev.get("_allday"))
        h_oc = int(total_min//60); m_oc = int(total_min%60)
        liv   = max(0,480-total_min)
        h_liv = int(liv//60); m_liv = int(liv%60)
        pct   = min(100,int(total_min/480*100)) if total_min>0 else 0
        fim   = "--:--"
        validos = [ev for ev in eventos if not ev.get("_allday")]
        if validos:
            try:
                dt = pd.to_datetime(validos[-1]["end"]["dateTime"])
                if dt.tzinfo is None: dt = dt.tz_localize("UTC")
                fim = dt.tz_convert(TZ_SP).strftime("%H:%M")
            except Exception: pass

        st.markdown(f"""
        <div class="gh-card">
          <div class="card-hd"><span class="card-title">Day Pulse</span><span class="card-meta">Resumo do dia</span></div>
          <div class="pulse-grid">
            <div class="pulse-cell"><div class="pulse-lbl">Eventos</div><div class="pulse-val c-blue">{total}</div></div>
            <div class="pulse-cell"><div class="pulse-lbl">Ocupado</div><div class="pulse-val">{h_oc}h {m_oc}m</div></div>
            <div class="pulse-cell"><div class="pulse-lbl">Livre</div><div class="pulse-val c-green">{h_liv}h {m_liv}m</div></div>
            <div class="pulse-cell"><div class="pulse-lbl">Término</div><div class="pulse-val c-red">{fim}</div></div>
          </div>
          <div class="prog-wrap">
            <div class="prog-lbl"><span>Ocupação</span><span>{pct}%</span></div>
            <div class="prog-track"><div class="prog-fill" style="width:{pct}%"></div></div>
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Calendário visual com st.button (100% nativo, funciona no Streamlit Cloud) ──
        _render_mini_cal(data_sel)


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
