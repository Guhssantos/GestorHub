import streamlit as st
import streamlit.components.v1 as components
import msal
import requests
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo

# ───────────────── CONFIG ─────────────────
st.set_page_config(page_title="GestorHub", layout="wide")

CLIENT_ID     = st.secrets.get("AZURE_CLIENT_ID", "")
CLIENT_SECRET = st.secrets.get("AZURE_CLIENT_SECRET", "")
AUTHORITY     = "https://login.microsoftonline.com/common"
REDIRECT_URI  = st.secrets.get("REDIRECT_URI", "")
SCOPE         = ["User.Read", "Calendars.Read"]

TZ_SP  = ZoneInfo("America/Sao_Paulo")
TZ_UTC = ZoneInfo("UTC")

# ───────────────── SESSION ─────────────────
if "logado" not in st.session_state:
    st.session_state.logado = False
if "token" not in st.session_state:
    st.session_state.token = None
if "data" not in st.session_state:
    st.session_state.data = datetime.now(TZ_SP).date()

# ───────────────── MSAL ─────────────────
def get_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

# ───────────────── LOGIN ─────────────────
qp = st.query_params
if "code" in qp and not st.session_state.logado:
    result = get_app().acquire_token_by_authorization_code(
        qp["code"],
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    if "access_token" in result:
        st.session_state.token = result["access_token"]
        st.session_state.logado = True
        st.query_params.clear()
        st.rerun()

if not st.session_state.logado:
    auth_url = get_app().get_authorization_request_url(
        SCOPE, redirect_uri=REDIRECT_URI
    )
    st.markdown("## GestorHub")
    if st.button("Entrar com Microsoft"):
        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
    st.stop()

# ───────────────── BUSCAR AGENDA ─────────────────
@st.cache_data(ttl=120)
def buscar_agenda(token, data):
    inicio = datetime(data.year, data.month, data.day, tzinfo=TZ_SP)
    fim    = inicio.replace(hour=23, minute=59)

    url = "https://graph.microsoft.com/v1.0/me/calendarView"
    params = {
        "startDateTime": inicio.astimezone(TZ_UTC).isoformat(),
        "endDateTime": fim.astimezone(TZ_UTC).isoformat(),
    }

    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)

    if r.status_code != 200:
        return []

    return r.json().get("value", [])

# ───────────────── CSS PREMIUM ─────────────────
st.markdown("""
<style>

/* MOBILE FIX SIDEBAR */
@media (max-width: 768px){
  [data-testid="stSidebar"] {
    width: 85% !important;
  }
}

/* EVENT CARD */
.event-card {
  background: #fff;
  padding: 14px;
  border-radius: 12px;
  margin-bottom: 10px;
  border: 1px solid #eee;
}

/* BOTTOM NAV */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 65px;
  background: #0D0D0D;
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 9999;
}
.bottom-item {
  color: rgba(255,255,255,.5);
  font-size: 11px;
}
.bottom-item.active {
  color: #fff;
}
@media (min-width:768px){
  .bottom-nav { display:none; }
}

</style>
""", unsafe_allow_html=True)

# ───────────────── CALENDÁRIO PREMIUM ─────────────────
def calendar_widget(data_sel):
    return f"""
    <script>
    function sendDate(d){{
        window.parent.postMessage({{type:"date",value:d}}, "*");
    }}
    </script>

    <div style="display:flex;gap:8px;">
        <button onclick="sendDate('{data_sel}')" style="padding:8px;border-radius:8px;">Hoje</button>
    </div>
    """

msg = components.html(calendar_widget(st.session_state.data), height=60)

if msg and isinstance(msg, dict):
    if msg.get("type") == "date":
        nova = datetime.fromisoformat(msg["value"]).date()
        st.session_state.data = nova
        st.cache_data.clear()
        st.rerun()

# ───────────────── SIDEBAR ─────────────────
with st.sidebar:
    pagina = st.radio("Menu", ["🏠 Início", "📊 Agenda"], label_visibility="collapsed")

# ───────────────── AGENDA ─────────────────
eventos = buscar_agenda(st.session_state.token, st.session_state.data)

st.title("Agenda")

if not eventos:
    st.info("Sem eventos")
else:
    for ev in eventos:
        inicio = pd.to_datetime(ev["start"]["dateTime"]).tz_localize("UTC").tz_convert(TZ_SP)
        fim    = pd.to_datetime(ev["end"]["dateTime"]).tz_localize("UTC").tz_convert(TZ_SP)

        st.html(f"""
        <div class="event-card">
            <b>{ev.get("subject","Sem título")}</b><br>
            {inicio.strftime("%H:%M")} - {fim.strftime("%H:%M")}
        </div>
        """)

# ───────────────── NAV MOBILE ─────────────────
st.markdown("""
<div class="bottom-nav">
  <div class="bottom-item active">🏠<br>Início</div>
  <div class="bottom-item">📊<br>Agenda</div>
</div>
""", unsafe_allow_html=True)
