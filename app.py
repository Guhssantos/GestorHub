import streamlit as st
import streamlit.components.v1 as components
import msal
import requests
import pandas as pd
import html
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

# ── CONFIGURAÇÕES (use st.secrets em produção) ────────────────────────────────
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
def get_logo_tag(path: str = "logo.png") -> str:
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{b64}" class="gh-logo">'
    return ""


# ── MSAL ──────────────────────────────────────────────────────────────────────
def get_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )


# ── GRAPH API ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def buscar_agenda(token: str, data_alvo: date):
    """Busca eventos do calendário para um dia específico (cache 5 min)."""
    inicio_sp = datetime(data_alvo.year, data_alvo.month, data_alvo.day,  0,  0,  0, tzinfo=TZ_SP)
    fim_sp    = datetime(data_alvo.year, data_alvo.month, data_alvo.day, 23, 59, 59, tzinfo=TZ_SP)
    ini_utc   = inicio_sp.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S")
    fim_utc   = fim_sp.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S")

    url    = "https://graph.microsoft.com/v1.0/me/calendarView"
    params = {
        "startDateTime": f"{ini_utc}Z",
        "endDateTime":   f"{fim_utc}Z",
        "$orderby":      "start/dateTime",
        "$top":          50,
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 401:
            return "EXPIRADO"
        if r.status_code != 200:
            st.error(f"Erro ao buscar eventos ({r.status_code}): {r.text}")
            return []

        resultado = []
        for ev in r.json().get("value", []):
            # Trata eventos de dia inteiro (sem dateTime)
            start_raw = ev["start"]
            if "dateTime" not in start_raw:
                resultado.append({**ev, "_allday": True})
                continue

            dt_utc = pd.to_datetime(start_raw["dateTime"])
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.tz_localize("UTC")
            dt_sp = dt_utc.tz_convert(TZ_SP)
            if dt_sp.date() == data_alvo:
                resultado.append({**ev, "_allday": False})

        return resultado
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_usuario(token: str) -> dict:
    """Busca nome e email do usuário autenticado."""
    try:
        r = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def _parse_horario(ev: dict, campo: str) -> str:
    raw = ev[campo]
    if "dateTime" not in raw:
        return "Dia todo"
    dt = pd.to_datetime(raw["dateTime"])
    if dt.tzinfo is None:
        dt = dt.tz_localize("UTC")
    return dt.tz_convert(TZ_SP).strftime("%H:%M")


def _duracao_min(ev: dict) -> float:
    if ev.get("_allday"):
        return 0
    try:
        s = pd.to_datetime(ev["start"]["dateTime"])
        e = pd.to_datetime(ev["end"]["dateTime"])
        if s.tzinfo is None: s = s.tz_localize("UTC")
        if e.tzinfo is None: e = e.tz_localize("UTC")
        return (e - s).total_seconds() / 60
    except Exception:
        return 0


# ── SESSION STATE ─────────────────────────────────────────────────────────────
_defaults = {
    "logado_ms":    False,
    "access_token": None,
    "data_agenda":  None,
    "usuario":      {},
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── OAUTH CALLBACK ────────────────────────────────────────────────────────────
qp = st.query_params
if "code" in qp and not st.session_state["logado_ms"]:
    app = get_msal_app()
    res = app.acquire_token_by_authorization_code(
        qp["code"], scopes=SCOPE, redirect_uri=REDIRECT_URI
    )
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

/* ── RESET / BASE ── */
*, *::before, *::after { box-sizing: border-box; }
html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background-color: #F5F3EF !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Esconde elementos padrão do Streamlit */
header[data-testid="stHeader"]       { background: transparent !important; height: 0 !important; }
.stAppDeployButton                   { display: none !important; }
#MainMenu, footer                    { visibility: hidden; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
button[data-testid="collapsedControl"]  { display: none !important; }
div[data-testid="stDateInput"]       { position: absolute !important; opacity: 0 !important;
                                       pointer-events: none !important; height: 0 !important;
                                       overflow: hidden !important; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background-color: #0D0D0D !important;
    width: 220px !important;
}
[data-testid="stSidebar"] * {
    font-family: 'DM Sans', sans-serif !important;
}

/* ── LOGO FIXO ── */
.gh-logo {
    position: fixed; top: 16px; right: 20px;
    width: 150px; z-index: 999998; pointer-events: none;
}
@media (max-width: 768px) { .gh-logo { width: 120px; right: 12px; } }

/* ── SIDEBAR COMPONENTS ── */
.sb-wordmark {
    font-size: 12px; font-weight: 500; letter-spacing: .10em;
    text-transform: uppercase; color: rgba(255,255,255,.30);
    padding: 0 10px; margin-bottom: 28px;
}
.sb-section-label {
    font-size: 10px; font-weight: 500; letter-spacing: .09em;
    text-transform: uppercase; color: rgba(255,255,255,.25);
    padding: 0 10px; margin: 20px 0 6px;
}
.nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 10px; border-radius: 8px; cursor: pointer;
    color: rgba(255,255,255,.40); font-size: 13px; font-weight: 400;
    margin-bottom: 1px; border: 1px solid transparent;
    transition: all .12s;
}
.nav-item:hover   { background: rgba(255,255,255,.06); color: rgba(255,255,255,.75); }
.nav-item.active  { background: rgba(255,255,255,.10); color: #fff;
                    border-color: rgba(255,255,255,.08); }
.nav-icon         { font-size: 15px; width: 20px; text-align: center; }

.user-chip {
    display: flex; align-items: center; gap: 10px;
    padding: 10px; border-radius: 8px; cursor: pointer;
    transition: background .12s; margin-top: 16px;
    border-top: 1px solid rgba(255,255,255,.06); padding-top: 16px;
}
.user-chip:hover { background: rgba(255,255,255,.06); }
.user-avatar {
    width: 30px; height: 30px; border-radius: 50%;
    background: rgba(255,255,255,.12);
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 600; color: rgba(255,255,255,.6);
    flex-shrink: 0;
}
.user-name  { font-size: 12px; font-weight: 500; color: rgba(255,255,255,.75);
              white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-role  { font-size: 10px; color: rgba(255,255,255,.30); }

/* ── TOPBAR ── */
.gh-topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 32px; background: #FFFFFF;
    border-bottom: 1px solid rgba(13,13,13,.08);
    margin-bottom: 28px;
}
.gh-topbar h2  { font-size: 16px; font-weight: 500; letter-spacing: -.2px; color: #0D0D0D; margin: 0; }
.gh-topbar p   { font-size: 12px; color: #8A8A8A; margin: 2px 0 0; }
.topbar-actions { display: flex; gap: 8px; }
.icon-btn {
    width: 34px; height: 34px; border-radius: 8px;
    border: 1px solid rgba(13,13,13,.10); background: #fff;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; font-size: 15px; transition: background .12s;
}
.icon-btn:hover { background: #F5F3EF; }

/* ── PAGE HEADER ── */
.page-header { margin: 0 0 24px; font-family: 'DM Sans', sans-serif; }
.page-header h1 { font-size: 22px; font-weight: 500; color: #0D0D0D; margin: 0; letter-spacing: -.3px; }
.page-header p  { font-size: 13px; color: #8A8A8A; margin: 3px 0 0; }

/* ── CARDS ── */
.gh-card {
    background: #FFFFFF; border: 1px solid rgba(13,13,13,.09);
    border-radius: 14px; overflow: hidden;
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 16px;
}
.card-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 20px; border-bottom: 1px solid rgba(13,13,13,.07);
}
.card-title { font-size: 13px; font-weight: 500; color: #0D0D0D; }
.card-meta  { font-size: 11px; color: #8A8A8A; }

/* ── AGENDA ── */
.event-item {
    display: flex; align-items: center; gap: 14px;
    padding: 12px 20px; border-bottom: 1px solid rgba(13,13,13,.06);
    transition: background .10s; cursor: pointer;
    font-family: 'DM Sans', sans-serif;
}
.event-item:last-child { border-bottom: none; }
.event-item:hover { background: #F5F3EF; }
.event-time-col { width: 48px; flex-shrink: 0; text-align: right; }
.event-time { font-family: 'DM Mono', monospace; font-size: 11px; color: #8A8A8A; line-height: 1.5; }
.event-bar { width: 3px; border-radius: 2px; flex-shrink: 0; align-self: stretch; min-height: 36px; }
.event-body { flex: 1; min-width: 0; }
.event-title {
    font-size: 13px; font-weight: 500; color: #0D0D0D;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.event-sub  { font-size: 11px; color: #8A8A8A; margin-top: 2px; }
.btn-join {
    font-size: 11px; font-weight: 500; padding: 6px 14px; border-radius: 6px;
    background: #0D0D0D; color: #fff; border: none; cursor: pointer;
    flex-shrink: 0; text-decoration: none; transition: opacity .12s;
    font-family: 'DM Sans', sans-serif;
}
.btn-join:hover { opacity: .75; }
.no-link { font-size: 11px; color: #CCCCCC; flex-shrink: 0; }
.allday-badge {
    font-size: 10px; font-weight: 500; padding: 3px 8px; border-radius: 4px;
    background: #F0EDE8; color: #8A8A8A; flex-shrink: 0;
}

/* ── DAY PULSE ── */
.pulse-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 1px; background: rgba(13,13,13,.07);
}
.pulse-cell { background: #fff; padding: 18px 16px; }
.pulse-label {
    font-size: 9px; font-weight: 500; letter-spacing: .08em;
    text-transform: uppercase; color: #8A8A8A;
}
.pulse-val { font-size: 22px; font-weight: 300; letter-spacing: -.5px; margin-top: 6px; color: #0D0D0D; }
.pulse-blue  { color: #1A4F8A; }
.pulse-green { color: #1C6C4E; }
.pulse-red   { color: #B83232; }

.progress-wrap { padding: 14px 20px; }
.progress-lbl  { display: flex; justify-content: space-between; font-size: 11px; color: #8A8A8A; margin-bottom: 7px; }
.progress-track { height: 5px; background: #F0EDE8; border-radius: 99px; overflow: hidden; }
.progress-fill  { height: 100%; border-radius: 99px; background: #0D0D0D; transition: width .4s; }

/* ── MINI CALENDÁRIO ── */
.mini-cal { padding: 14px 20px; }
.cal-month-nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.cal-month { font-size: 12px; font-weight: 500; color: #0D0D0D; }
.cal-grid  { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.cal-dow   { font-size: 9px; font-weight: 600; text-transform: uppercase; color: #AAAAAA;
             text-align: center; padding: 3px 0; letter-spacing: .04em; }
.cal-day   { font-size: 11px; font-family: 'DM Mono', monospace; text-align: center;
             padding: 5px 2px; border-radius: 5px; cursor: pointer;
             transition: background .1s; color: #0D0D0D; }
.cal-day:hover { background: #F0EDE8; }
.cal-day.today { background: #0D0D0D; color: #fff; }
.cal-day.out   { color: rgba(13,13,13,.18); pointer-events: none; }
.cal-day.sel:not(.today) { background: #E8E5DF; }

/* ── DATE NAV STRIP ── */
.date-strip { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }
.date-nav-btn {
    width: 30px; height: 30px; border-radius: 6px;
    border: 1px solid rgba(13,13,13,.10); background: #fff;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; font-size: 14px; color: #8A8A8A;
    transition: all .12s; font-family: 'DM Sans', sans-serif;
}
.date-nav-btn:hover { background: #F5F3EF; color: #0D0D0D; }
.date-current-btn {
    display: flex; align-items: center; gap: 8px; padding: 6px 14px;
    border-radius: 8px; border: 1px solid rgba(13,13,13,.10);
    background: #fff; font-size: 13px; font-weight: 500;
    cursor: pointer; transition: background .12s;
    font-family: 'DM Sans', sans-serif; color: #0D0D0D;
}
.date-current-btn:hover { background: #F5F3EF; }
.date-dot { width: 6px; height: 6px; border-radius: 50%; background: #1C6C4E; }

/* ── POWER BI WRAPPER ── */
.pbi-container {
    background: #fff; border: 1px solid rgba(13,13,13,.09);
    border-radius: 14px; padding: 4px; overflow: hidden;
}
.pbi-wrapper { position: relative; width: 100%; padding-bottom: 60%; height: 0; overflow: hidden; border-radius: 10px; }
.pbi-wrapper iframe { position: absolute; top: 0; left: 0; width: 100% !important; height: 100% !important; border: none; }

/* ── RESUMOS ── */
.resumo-card {
    background: #fff; border: 1px solid rgba(13,13,13,.09);
    border-radius: 14px; overflow: hidden; margin-bottom: 14px;
    transition: box-shadow .15s; font-family: 'DM Sans', sans-serif;
}
.resumo-card:hover { box-shadow: 0 8px 40px rgba(0,0,0,.08); }
.resumo-top { padding: 18px 20px; }
.resumo-title { font-size: 14px; font-weight: 500; color: #0D0D0D; letter-spacing: -.2px; }
.resumo-when  { font-size: 11px; color: #8A8A8A; margin-top: 3px; }
.resumo-body  { font-size: 13px; color: #3A3A3A; line-height: 1.65; margin: 12px 0; }
.tag {
    display: inline-flex; align-items: center; font-size: 10px; font-weight: 500;
    letter-spacing: .04em; padding: 3px 8px; border-radius: 4px;
}
.tag-blue  { background: #D8E8F8; color: #1A4F8A; }
.tag-amber { background: #FFF0CC; color: #8C5A00; }
.tag-gray  { background: #F0EDE8; color: #8A8A8A; }
.tag-green { background: #D6EDE5; color: #1C6C4E; }
.resumo-actions {
    display: flex; align-items: center; gap: 8px;
    padding: 12px 20px; border-top: 1px solid rgba(13,13,13,.07);
    background: #FAFAF8;
}
.btn-sm {
    font-size: 11px; font-weight: 500; padding: 6px 14px; border-radius: 6px;
    border: 1px solid rgba(13,13,13,.10); background: #fff; cursor: pointer;
    color: #0D0D0D; display: inline-flex; align-items: center; gap: 5px;
    transition: all .12s; text-decoration: none;
    font-family: 'DM Sans', sans-serif;
}
.btn-sm:hover { background: #0D0D0D; color: #fff; border-color: #0D0D0D; }
.btn-primary-sm {
    font-size: 11px; font-weight: 500; padding: 6px 14px; border-radius: 6px;
    border: none; background: #0D0D0D; cursor: pointer; color: #fff;
    display: inline-flex; align-items: center; gap: 5px;
    transition: opacity .12s; text-decoration: none;
    font-family: 'DM Sans', sans-serif;
}
.btn-primary-sm:hover { opacity: .75; }
.actions-box {
    background: #F5F3EF; border-radius: 8px; padding: 12px 14px; margin-top: 12px;
}
.actions-label {
    font-size: 10px; font-weight: 600; letter-spacing: .06em;
    text-transform: uppercase; color: #8A8A8A; margin-bottom: 8px;
}
.action-row {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 8px 0; border-bottom: 1px solid rgba(13,13,13,.06);
}
.action-row:last-child { border-bottom: none; padding-bottom: 0; }
.action-chk {
    width: 15px; height: 15px; border-radius: 4px;
    border: 1.5px solid rgba(13,13,13,.20); flex-shrink: 0; margin-top: 2px;
}
.action-chk.done { background: #0D0D0D; border-color: #0D0D0D; }
.action-text     { font-size: 12.5px; line-height: 1.5; color: #0D0D0D; }
.action-who      { font-size: 11px; color: #8A8A8A; margin-top: 1px; }

/* ── MISC ── */
.empty-state {
    text-align: center; padding: 40px 20px;
    font-family: 'DM Sans', sans-serif;
}
.empty-state .icon { font-size: 28px; }
.empty-state p { font-size: 14px; color: #8A8A8A; margin-top: 10px; }

div[data-testid="stHtml"]   { overflow: visible !important; }
iframe { position: relative; z-index: 99999 !important; }

/* Streamlit selectbox na sidebar */
[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: #1A1A1A !important; color: #F5F3EF !important;
    border: 1px solid rgba(255,255,255,.12) !important; border-radius: 8px !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] span,
[data-testid="stSidebar"] div[data-baseweb="select"] div { color: #F5F3EF !important; }
[data-testid="stSidebar"] div[data-baseweb="select"] svg { fill: #8A8A8A !important; }
ul[data-baseweb="menu"] { background: #1A1A1A !important; border: 1px solid rgba(255,255,255,.12) !important; border-radius: 8px !important; }
ul[data-baseweb="menu"] li { color: #F5F3EF !important; font-family: 'DM Sans', sans-serif !important; }
ul[data-baseweb="menu"] li:hover { background: #2A2A2A !important; }

/* Botão de sair */
[data-testid="stSidebar"] button {
    background: rgba(184,50,50,.15) !important; color: #F5C6C6 !important;
    border: 1px solid rgba(184,50,50,.25) !important;
    font-weight: 500 !important; border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSidebar"] button:hover { background: rgba(184,50,50,.28) !important; }
</style>
""", unsafe_allow_html=True)

# Logo
st.markdown(get_logo_tag(), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TELA DE LOGIN
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["logado_ms"]:
    st.markdown("""
    <style>
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {
        background-color: #F5F3EF !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown("""
        <div style="display:flex;min-height:72vh;border-radius:20px;overflow:hidden;
                    box-shadow:0 20px 80px rgba(0,0,0,.12);font-family:'DM Sans',sans-serif;">
            <!-- Painel esquerdo escuro -->
            <div style="width:52%;background:#0D0D0D;padding:40px;display:flex;
                        flex-direction:column;justify-content:space-between;position:relative;overflow:hidden;">
                <div style="position:absolute;width:500px;height:500px;border-radius:50%;
                            border:1px solid rgba(255,255,255,.05);top:-200px;left:-180px;"></div>
                <div style="position:absolute;width:350px;height:350px;border-radius:50%;
                            border:1px solid rgba(255,255,255,.04);bottom:-120px;right:-80px;"></div>

                <div style="font-size:11px;font-weight:500;letter-spacing:.10em;
                            text-transform:uppercase;color:rgba(255,255,255,.25);position:relative;">
                    GestorHub
                </div>

                <div style="position:relative;">
                    <h1 style="font-size:34px;font-weight:300;line-height:1.18;color:#fff;
                               letter-spacing:-.5px;margin:0 0 14px;">
                        Centro de<br>Comando<br><em style="font-style:italic;color:rgba(255,255,255,.4);">Executivo</em>
                    </h1>
                    <p style="font-size:12.5px;color:rgba(255,255,255,.35);max-width:240px;line-height:1.7;margin:0;">
                        Agenda, reuniões e chamados integrados em um único painel.
                    </p>
                </div>

                <div style="display:flex;gap:6px;flex-wrap:wrap;position:relative;">
                    <span style="font-size:10px;font-weight:500;padding:4px 10px;border-radius:999px;
                                 border:1px solid rgba(255,255,255,.10);color:rgba(255,255,255,.35);">📅 MS Calendar</span>
                    <span style="font-size:10px;font-weight:500;padding:4px 10px;border-radius:999px;
                                 border:1px solid rgba(255,255,255,.10);color:rgba(255,255,255,.35);">🎥 tl;dv</span>
                    <span style="font-size:10px;font-weight:500;padding:4px 10px;border-radius:999px;
                                 border:1px solid rgba(255,255,255,.10);color:rgba(255,255,255,.35);">📊 Power BI</span>
                </div>
            </div>

            <!-- Painel direito claro -->
            <div style="flex:1;background:#fff;padding:40px;display:flex;
                        flex-direction:column;justify-content:center;">
                <h2 style="font-size:20px;font-weight:500;color:#0D0D0D;margin:0 0 6px;letter-spacing:-.3px;">
                    Bom dia, Gestor.
                </h2>
                <p style="font-size:12.5px;color:#8A8A8A;margin:0 0 32px;line-height:1.6;">
                    Acesse com sua conta corporativa Microsoft para carregar sua agenda e seus painéis.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        auth_url = get_msal_app().get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.link_button("🪟  Entrar com Microsoft 365", auth_url, type="primary", use_container_width=True)
        st.markdown("""
        <p style="font-size:11px;color:#AAAAAA;text-align:center;margin-top:12px;
                  font-family:'DM Sans',sans-serif;line-height:1.6;">
            Seus dados são sincronizados apenas com sua conta corporativa.<br>
            Nenhuma informação é armazenada em servidores externos.
        </p>
        """, unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
usuario  = st.session_state.get("usuario", {})
nome     = usuario.get("displayName", "Gestor")
iniciais = "".join([p[0].upper() for p in nome.split()[:2]]) if nome else "GH"
cargo    = usuario.get("jobTitle", "Colaborador")

with st.sidebar:
    st.markdown(f"""
    <div style="padding:4px 0 0;">
        <div class="sb-wordmark">GestorHub</div>
        <div class="sb-section-label">Principal</div>
    </div>
    """, unsafe_allow_html=True)

    opcao = st.selectbox(
        "nav",
        ["🏠  Início", "🎥  Resumos tl;dv", "📊  Chamados"],
        label_visibility="collapsed",
    )

    # Realça o item ativo com HTML espelhando a seleção
    _ativo = {
        "🏠  Início":        0,
        "🎥  Resumos tl;dv": 1,
        "📊  Chamados":      2,
    }[opcao]
    _labels = [
        ("🏠", "Início"),
        ("🎥", "Resumos"),
        ("📊", "Chamados"),
    ]
    nav_html = ""
    for i, (icon, lbl) in enumerate(_labels):
        cls = "nav-item active" if i == _ativo else "nav-item"
        nav_html += f'<div class="{cls}"><span class="nav-icon">{icon}</span> {lbl}</div>'

    st.markdown(nav_html, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="user-chip">
        <div class="user-avatar">{iniciais}</div>
        <div style="overflow:hidden;">
            <div class="user-name">{html.escape(nome)}</div>
            <div class="user-role">{html.escape(cargo)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sair da conta", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE TOPBAR
# ══════════════════════════════════════════════════════════════════════════════
def topbar(titulo: str, subtitulo: str):
    hoje_sp  = datetime.now(tz=TZ_SP)
    dia_sem  = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"][hoje_sp.weekday()]
    data_str = f"{dia_sem}, {hoje_sp.day} de {MESES_PT[hoje_sp.month-1]} de {hoje_sp.year}"
    st.markdown(f"""
    <div class="gh-topbar">
        <div>
            <h2>{html.escape(titulo)}</h2>
            <p>{html.escape(subtitulo)} · {data_str}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: INÍCIO
# ══════════════════════════════════════════════════════════════════════════════
def pagina_inicio():
    saudacao = "Bom dia" if datetime.now(tz=TZ_SP).hour < 12 else \
               "Boa tarde" if datetime.now(tz=TZ_SP).hour < 18 else "Boa noite"
    primeiro = nome.split()[0] if nome else "Gestor"
    topbar(f"{saudacao}, {primeiro} 👋", "Agenda sincronizada com a Microsoft")

    hoje_sp = datetime.now(tz=TZ_SP).date()
    if st.session_state["data_agenda"] is None:
        st.session_state["data_agenda"] = hoje_sp
    data_sel = st.session_state["data_agenda"]

    # ── Date strip ──────────────────────────────────────────────────────────
    label = "Hoje" if data_sel == hoje_sp else \
            f"{data_sel.day} {MESES_ABR[data_sel.month-1]} {data_sel.year}"
    hoje_iso = hoje_sp.isoformat()
    sel_iso  = data_sel.isoformat()

    # Input oculto para o calendário customizado
    data_input = st.date_input(
        "data_oculta", value=data_sel,
        key="date_picker_hidden", label_visibility="collapsed",
    )
    if data_input != data_sel:
        st.session_state["data_agenda"] = data_input
        st.rerun()

    # Calendário customizado
    components.html(_make_calendar_html(label, hoje_iso, sel_iso), height=52, scrolling=False)

    # ── Layout 2 colunas ────────────────────────────────────────────────────
    col_agenda, col_side = st.columns([1.5, 1], gap="medium")

    with col_agenda:
        with st.spinner("Carregando agenda..."):
            eventos = buscar_agenda(st.session_state["access_token"], data_sel)

        if eventos == "EXPIRADO":
            st.session_state.clear()
            st.rerun()

        total = len(eventos)
        cores = ["#1A4F8A", "#1C6C4E", "#8C5A00", "#B83232", "#6B3A8C"]

        st.markdown(f"""
        <div class="gh-card">
            <div class="card-header">
                <span class="card-title">Agenda do dia</span>
                <span class="card-meta">{total} evento{'s' if total != 1 else ''}</span>
            </div>
        """, unsafe_allow_html=True)

        if total == 0:
            st.markdown("""
            <div class="empty-state">
                <div class="icon">🎉</div>
                <p>Nenhum evento neste dia.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for i, ev in enumerate(eventos):
                cor  = cores[i % len(cores)]
                safe_titulo = html.escape(ev.get("subject", "Sem título"))

                if ev.get("_allday"):
                    btn_html = '<span class="allday-badge">Dia todo</span>'
                    hi = hf = "–"
                else:
                    hi  = _parse_horario(ev, "start")
                    hf  = _parse_horario(ev, "end")
                    link = (ev.get("onlineMeeting") or {}).get("joinUrl") or \
                           ev.get("onlineMeetingUrl", "")
                    btn_html = f'<a href="{link}" target="_blank" class="btn-join">Entrar</a>' \
                               if link else '<span class="no-link">Sem link</span>'

                # Plataforma
                plataforma = ""
                if "teams.microsoft" in (ev.get("onlineMeetingUrl") or ""):
                    plataforma = "Microsoft Teams"
                elif "zoom.us" in (ev.get("onlineMeetingUrl") or ""):
                    plataforma = "Zoom"
                elif "meet.google" in (ev.get("onlineMeetingUrl") or ""):
                    plataforma = "Google Meet"

                dur_min = int(_duracao_min(ev))
                dur_str = f"{dur_min//60}h {dur_min%60}m" if dur_min >= 60 else f"{dur_min}m"
                sub_str = f"{plataforma} · {dur_str}" if plataforma else dur_str if dur_min > 0 else ""

                st.markdown(f"""
                <div class="event-item">
                    <div class="event-time-col">
                        <div class="event-time">{hi}</div>
                        <div class="event-time">{hf}</div>
                    </div>
                    <div class="event-bar" style="background:{cor};"></div>
                    <div class="event-body">
                        <div class="event-title">{safe_titulo}</div>
                        {'<div class="event-sub">'+sub_str+'</div>' if sub_str else ''}
                    </div>
                    {btn_html}
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with col_side:
        # Day Pulse
        total_min = sum(_duracao_min(ev) for ev in eventos if not ev.get("_allday"))
        h_oc = int(total_min // 60)
        m_oc = int(total_min % 60)
        liv  = max(0, 480 - total_min)
        h_liv = int(liv // 60); m_liv = int(liv % 60)
        pct  = min(100, int(total_min / 480 * 100))

        fim_str = "--:--"
        if eventos:
            last = [ev for ev in eventos if not ev.get("_allday")]
            if last:
                dt_fim = pd.to_datetime(last[-1]["end"]["dateTime"])
                if dt_fim.tzinfo is None: dt_fim = dt_fim.tz_localize("UTC")
                fim_str = dt_fim.tz_convert(TZ_SP).strftime("%H:%M")

        st.markdown(f"""
        <div class="gh-card">
            <div class="card-header">
                <span class="card-title">Day Pulse</span>
                <span class="card-meta">Resumo do dia</span>
            </div>
            <div class="pulse-grid">
                <div class="pulse-cell">
                    <div class="pulse-label">Eventos</div>
                    <div class="pulse-val pulse-blue">{total}</div>
                </div>
                <div class="pulse-cell">
                    <div class="pulse-label">Ocupado</div>
                    <div class="pulse-val">{h_oc}h {m_oc}m</div>
                </div>
                <div class="pulse-cell">
                    <div class="pulse-label">Livre</div>
                    <div class="pulse-val pulse-green">{h_liv}h {m_liv}m</div>
                </div>
                <div class="pulse-cell">
                    <div class="pulse-label">Término</div>
                    <div class="pulse-val pulse-red">{fim_str}</div>
                </div>
            </div>
            <div class="progress-wrap">
                <div class="progress-lbl">
                    <span>Ocupação</span><span>{pct}%</span>
                </div>
                <div class="progress-track">
                    <div class="progress-fill" style="width:{pct}%"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Mini calendário
        st.markdown(f"""
        <div class="gh-card">
            <div class="card-header">
                <span class="card-title">Calendário</span>
            </div>
            {_mini_cal_html(data_sel)}
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: RESUMOS
# ══════════════════════════════════════════════════════════════════════════════
def pagina_resumos():
    topbar("Resumos de Reuniões", "Insights extraídos via tl;dv")

    st.markdown("""
    <div class="resumo-card">
        <div class="resumo-top">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
                <div>
                    <div class="resumo-title">Comitê de Mudanças (CAB)</div>
                    <div class="resumo-when">Hoje, 10:30 · 45 min · 6 participantes</div>
                </div>
                <div style="display:flex;gap:5px;flex-wrap:wrap;">
                    <span class="tag tag-amber">🟡 CAB</span>
                    <span class="tag tag-gray">tl;dv</span>
                </div>
            </div>
            <div class="resumo-body">
                A equipe aprovou a atualização do banco de dados do ERP para este domingo,
                com janela das 22h às 02h. Bernardo ficará de plantão. Foram discutidos riscos
                de rollback e o processo de comunicação para os usuários afetados.
            </div>
            <div class="actions-box">
                <div class="actions-label">Ações extraídas</div>
                <div class="action-row">
                    <div class="action-chk done"></div>
                    <div>
                        <div class="action-text">Agendar plantão para Bernardo no domingo</div>
                        <div class="action-who">Ana M. · Prazo: 30 Abr</div>
                    </div>
                </div>
                <div class="action-row">
                    <div class="action-chk"></div>
                    <div>
                        <div class="action-text">Preparar plano de rollback documentado</div>
                        <div class="action-who">Equipe DBA · Prazo: 02 Mai</div>
                    </div>
                </div>
                <div class="action-row">
                    <div class="action-chk"></div>
                    <div>
                        <div class="action-text">Enviar comunicado para usuários do ERP</div>
                        <div class="action-who">Comunicação · Prazo: 03 Mai</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="resumo-actions">
            <a href="#" class="btn-primary-sm">🎬 Ver gravação</a>
            <a href="#" class="btn-sm">📋 Copiar resumo</a>
            <a href="#" class="btn-sm">📤 Compartilhar</a>
        </div>
    </div>

    <div class="resumo-card">
        <div class="resumo-top">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
                <div>
                    <div class="resumo-title">1:1 com Diretor de Tecnologia</div>
                    <div class="resumo-when">28 Abr, 14:00 · 52 min · 2 participantes</div>
                </div>
                <div style="display:flex;gap:5px;flex-wrap:wrap;">
                    <span class="tag tag-blue">🔵 1:1</span>
                    <span class="tag tag-gray">tl;dv</span>
                </div>
            </div>
            <div class="resumo-body">
                Revisão do roadmap do Q2. O diretor sinalizou que o projeto de migração para cloud
                deve ser prioridade máxima. Orçamento adicional pode ser aprovado até o final de maio.
                Discussão sobre headcount para o segundo semestre.
            </div>
        </div>
        <div class="resumo-actions">
            <a href="#" class="btn-primary-sm">🎬 Ver gravação</a>
            <a href="#" class="btn-sm">📋 Copiar resumo</a>
        </div>
    </div>

    <div class="resumo-card">
        <div class="resumo-top">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
                <div>
                    <div class="resumo-title">Reunião de Alinhamento — Squad</div>
                    <div class="resumo-when">27 Abr, 09:00 · 60 min · 8 participantes</div>
                </div>
                <div style="display:flex;gap:5px;flex-wrap:wrap;">
                    <span class="tag tag-green">🟢 Squad</span>
                    <span class="tag tag-gray">tl;dv</span>
                </div>
            </div>
            <div class="resumo-body">
                Sprint 24 revisada: 9 de 12 stories entregues. Dois impedimentos técnicos
                identificados na integração com o gateway de pagamentos. Próxima sprint planeja
                focar na estabilidade antes de novas funcionalidades.
            </div>
        </div>
        <div class="resumo-actions">
            <a href="#" class="btn-primary-sm">🎬 Ver gravação</a>
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
    <div class="pbi-container">
        <div class="pbi-wrapper">
            <iframe src="{POWER_BI_URL}" allowFullScreen="true"></iframe>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CALENDÁRIO CUSTOMIZADO (iframe)
# ══════════════════════════════════════════════════════════════════════════════
def _make_calendar_html(label_exib: str, hoje_iso: str, sel_iso: str) -> str:
    return f"""<!DOCTYPE html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:'DM Sans',system-ui,sans-serif}}
html,body{{background:transparent;padding:4px 0 6px}}
.bar{{display:flex;align-items:center;gap:10px;position:relative}}
.cal-btn{{
    background:#FFF;border:1px solid rgba(13,13,13,.10);border-radius:8px;
    padding:7px 14px 7px 10px;display:inline-flex;align-items:center;gap:8px;
    cursor:pointer;font-size:13px;font-weight:500;color:#0D0D0D;
    box-shadow:none;user-select:none;-webkit-tap-highlight-color:transparent;
    touch-action:manipulation;transition:background .12s}}
.cal-btn:hover{{background:#F5F3EF}}
.sync-btn{{
    width:32px;height:32px;border-radius:7px;background:#FFF;
    border:1px solid rgba(13,13,13,.10);cursor:pointer;font-size:16px;line-height:1;
    display:inline-flex;align-items:center;justify-content:center;
    -webkit-tap-highlight-color:transparent;touch-action:manipulation;
    color:#8A8A8A;transition:background .12s}}
.sync-btn:hover{{background:#F5F3EF}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.spinning{{animation:spin .5s linear}}
#popup{{
    display:none;position:absolute;top:44px;left:0;z-index:999999;
    background:#FFF;border-radius:12px;width:268px;padding:16px;
    box-shadow:0 8px 40px rgba(0,0,0,.14);border:1px solid rgba(13,13,13,.08)}}
.ph{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}}
.ph-title{{font-size:13px;font-weight:500;color:#0D0D0D}}
.nav{{background:none;border:none;cursor:pointer;font-size:22px;color:#8A8A8A;padding:0 8px;line-height:1}}
.nav:hover{{color:#0D0D0D}}
.grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center}}
.dow{{font-size:9px;font-weight:600;color:#AAAAAA;text-transform:uppercase;padding:3px 0;letter-spacing:.04em}}
.day{{font-size:11px;font-family:'DM Mono',monospace;color:#0D0D0D;padding:6px 2px;
    border-radius:5px;cursor:pointer;border:none;background:none;width:100%;
    touch-action:manipulation;-webkit-tap-highlight-color:transparent}}
.day:hover{{background:#F5F3EF}}
.today{{background:#0D0D0D!important;color:#FFF!important;border-radius:5px!important}}
.sel:not(.today){{background:#E8E5DF!important;border-radius:5px!important}}
.out{{color:rgba(13,13,13,.18)!important;pointer-events:none!important}}
.date-dot{{width:5px;height:5px;border-radius:50%;background:#1C6C4E;display:inline-block}}
</style></head><body>
<div class="bar">
  <div class="cal-btn" id="tog" onclick="toggleCal()">
    <span class="date-dot"></span>
    <span id="lbl">{label_exib}</span>
  </div>
  <button class="sync-btn" id="sbtn" title="Sincronizar" onclick="doSync()">↻</button>
</div>
<div id="popup">
  <div class="ph">
    <button class="nav" onclick="chgMonth(-1)">&#8249;</button>
    <span class="ph-title" id="mlbl"></span>
    <button class="nav" onclick="chgMonth(1)">&#8250;</button>
  </div>
  <div class="grid">
    <div class="dow">D</div><div class="dow">S</div><div class="dow">T</div>
    <div class="dow">Q</div><div class="dow">Q</div><div class="dow">S</div><div class="dow">S</div>
  </div>
  <div class="grid" id="days"></div>
</div>
<script>
(function(){{
  var MESES=["Janeiro","Fevereiro","Marco","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
  var MS=["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
  var hoje=new Date("{hoje_iso}T12:00:00");
  var sel=new Date("{sel_iso}T12:00:00");
  var cur=new Date(sel.getFullYear(),sel.getMonth(),1);
  var open=false;

  function pad(n){{return n<10?"0"+n:n}}
  function iso(d){{return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())}}

  function resize(h,isOpen){{
    try{{
      var fr=window.parent.document.querySelectorAll("iframe");
      for(var i=0;i<fr.length;i++){{
        if(fr[i].contentWindow===window){{
          fr[i].height=h;fr[i].style.height=h+"px";fr[i].style.minHeight=h+"px";
          var c=fr[i].closest('div[data-testid="element-container"]');
          if(c){{c.style.position="relative";c.style.zIndex=isOpen?"99999":"1";}}
          var p=fr[i].parentElement;
          while(p&&p.tagName!=="BODY"){{p.style.overflow="visible";p=p.parentElement;}}
          break;
        }}
      }}
    }}catch(e){{}}
  }}

  function render(){{
    var y=cur.getFullYear(),m=cur.getMonth();
    document.getElementById("mlbl").textContent=MESES[m]+" "+y;
    var g=document.getElementById("days");g.innerHTML="";
    var first=new Date(y,m,1).getDay();
    var days=new Date(y,m+1,0).getDate();
    var prev=new Date(y,m,0).getDate();
    for(var i=0;i<first;i++) mk(g,prev-first+1+i,true,null,false,false);
    for(var d=1;d<=days;d++){{
      var dt=new Date(y,m,d);
      mk(g,d,false,dt,iso(dt)===iso(hoje),iso(dt)===iso(sel));
    }}
    var rem=(first+days)%7;
    if(rem) for(var i=1;i<=7-rem;i++) mk(g,i,true,null,false,false);
  }}

  function mk(g,txt,out,dt,isT,isS){{
    var b=document.createElement("button");
    b.className="day"+(out?" out":"")+(isS?" sel":"")+(isT?" today":"");
    b.textContent=txt;
    if(dt){{(function(d){{b.onclick=function(){{pick(d)}};}})(dt);}}
    g.appendChild(b);
  }}

  function pick(dt){{
    sel=dt;
    var s=iso(dt);
    document.getElementById("lbl").textContent=(s===iso(hoje))?"Hoje":dt.getDate()+" "+MS[dt.getMonth()]+" "+dt.getFullYear();
    closePopup();send(s);
  }}

  function send(s){{
    var p=s.split("-");
    var fmt=p[0]+"/"+p[1]+"/"+p[2];
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

  window.toggleCal=function(){{
    open=!open;
    var p=document.getElementById("popup");
    if(open){{cur=new Date(sel.getFullYear(),sel.getMonth(),1);render();p.style.display="block";resize(420,true);}}
    else{{closePopup();}}
  }};

  window.chgMonth=function(d){{cur.setMonth(cur.getMonth()+d);render();}};

  function closePopup(){{
    open=false;
    document.getElementById("popup").style.display="none";
    resize(52,false);
  }}

  window.doSync=function(){{
    var b=document.getElementById("sbtn");
    b.classList.add("spinning");
    setTimeout(function(){{b.classList.remove("spinning");}},500);
    var docs=[];
    try{{docs.push(window.parent.document)}}catch(e){{}}
    try{{if(window.top!==window.parent)docs.push(window.top.document)}}catch(e){{}}
    for(var i=0;i<docs.length;i++){{
      var inp=docs[i].querySelector('[data-testid="stDateInput"] input');
      if(inp){{
        inp.dispatchEvent(new Event("input",{{bubbles:true}}));
        inp.dispatchEvent(new Event("change",{{bubbles:true}}));
        return;
      }}
    }}
  }};

  document.addEventListener("click",function(e){{
    if(!open)return;
    var p=document.getElementById("popup");
    var t=document.getElementById("tog");
    if(p&&t&&!p.contains(e.target)&&!t.contains(e.target))closePopup();
  }});

  resize(52,false);
}})();
</script>
</body></html>"""


# ══════════════════════════════════════════════════════════════════════════════
# MINI CALENDÁRIO (HTML estático — sem interação)
# ══════════════════════════════════════════════════════════════════════════════
def _mini_cal_html(data_sel: date) -> str:
    hoje = datetime.now(tz=TZ_SP).date()
    y, m = data_sel.year, data_sel.month
    primeiro_dia = date(y, m, 1).weekday()  # 0=seg, ..., 6=dom
    # Ajusta para domingo=0
    primeiro_dia = (primeiro_dia + 1) % 7
    dias_mes = (date(y, m % 12 + 1, 1) - date(y, m, 1)).days if m < 12 else \
               (date(y + 1, 1, 1) - date(y, m, 1)).days
    mes_nome = MESES_PT[m - 1]

    cells = ""
    for _ in range(primeiro_dia):
        cells += '<div class="cal-day out"></div>'
    for d in range(1, dias_mes + 1):
        dt = date(y, m, d)
        cls = "cal-day"
        if dt == hoje:    cls += " today"
        elif dt == data_sel: cls += " sel"
        cells += f'<div class="{cls}">{d}</div>'

    return f"""
    <div class="mini-cal">
        <div class="cal-month-nav">
            <span style="font-size:16px;color:#8A8A8A;cursor:pointer;">‹</span>
            <span class="cal-month">{mes_nome} {y}</span>
            <span style="font-size:16px;color:#8A8A8A;cursor:pointer;">›</span>
        </div>
        <div class="cal-grid">
            <div class="cal-dow">D</div><div class="cal-dow">S</div>
            <div class="cal-dow">T</div><div class="cal-dow">Q</div>
            <div class="cal-dow">Q</div><div class="cal-dow">S</div>
            <div class="cal-dow">S</div>
            {cells}
        </div>
    </div>"""


# ══════════════════════════════════════════════════════════════════════════════
# ROTEADOR DE PÁGINAS
# ══════════════════════════════════════════════════════════════════════════════
if opcao == "🏠  Início":
    pagina_inicio()
elif opcao == "🎥  Resumos tl;dv":
    pagina_resumos()
elif opcao == "📊  Chamados":
    pagina_chamados()