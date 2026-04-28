import streamlit as st
import msal
import requests
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="GestorHub", page_icon="🚀", layout="wide")

# CONFIG
CLIENT_ID     = "SEU_CLIENT_ID"
CLIENT_SECRET = "SEU_CLIENT_SECRET"
AUTHORITY     = "https://login.microsoftonline.com/common"
REDIRECT_URI  = "https://gestor-app.streamlit.app"
SCOPE         = ["User.Read", "Calendars.Read"]

TZ_SP = ZoneInfo("America/Sao_Paulo")
TZ_UTC = ZoneInfo("UTC")

# SESSION STATE
for k, v in {
    "logado": False,
    "token": None,
    "data": datetime.now(TZ_SP).date()
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# MSAL
def get_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

# LOGIN
params = st.query_params
if "code" in params and not st.session_state["logado"]:
    result = get_app().acquire_token_by_authorization_code(
        params["code"],
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    if "access_token" in result:
        st.session_state["token"] = result["access_token"]
        st.session_state["logado"] = True
        st.query_params.clear()
        st.rerun()

# TELA LOGIN
if not st.session_state["logado"]:
    st.title("GestorHub")
    auth_url = get_app().get_authorization_request_url(
        SCOPE,
        redirect_uri=REDIRECT_URI
    )
    st.link_button("Entrar com Microsoft", auth_url)
    st.stop()

# BUSCAR AGENDA
def buscar_agenda(token, data):
    inicio = datetime(data.year, data.month, data.day, 0, 0, 0, tzinfo=TZ_SP)
    fim    = datetime(data.year, data.month, data.day, 23, 59, 59, tzinfo=TZ_SP)

    url = f"https://graph.microsoft.com/v1.0/me/calendarView"
    params = {
        "startDateTime": inicio.astimezone(TZ_UTC).isoformat(),
        "endDateTime": fim.astimezone(TZ_UTC).isoformat()
    }

    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        return []

    return r.json().get("value", [])

# HEADER
st.title("Olá, Gestor 👋")

# CONTROLES
col1, col2, col3 = st.columns([2,1,1])

with col1:
    nova_data = st.date_input(
        "Selecionar data",
        value=st.session_state["data"]
    )

with col2:
    if st.button("Hoje"):
        st.session_state["data"] = datetime.now(TZ_SP).date()
        st.rerun()

with col3:
    if st.button("Atualizar"):
        st.rerun()

if nova_data != st.session_state["data"]:
    st.session_state["data"] = nova_data
    st.rerun()

# BUSCA EVENTOS
eventos = buscar_agenda(st.session_state["token"], st.session_state["data"])

st.subheader("Sua Agenda")

if not eventos:
    st.info("Nenhum evento nesse dia.")
else:
    for ev in eventos:
        inicio = pd.to_datetime(ev['start']['dateTime']).strftime("%H:%M")
        fim    = pd.to_datetime(ev['end']['dateTime']).strftime("%H:%M")
        titulo = ev.get("subject", "Sem título")

        link = (
            (ev.get('onlineMeeting') or {}).get('joinUrl')
            or ev.get('onlineMeetingUrl')
        )

        with st.container():
            colA, colB = st.columns([4,1])

            with colA:
                st.markdown(f"**{titulo}**")
                st.caption(f"{inicio} - {fim}")

            with colB:
                if link:
                    st.link_button("Entrar", link)

# DAY PULSE
st.subheader("Day Pulse")

total = len(eventos)
mins = 0

for ev in eventos:
    ini = pd.to_datetime(ev['start']['dateTime'])
    fim = pd.to_datetime(ev['end']['dateTime'])
    mins += (fim - ini).total_seconds() / 60

h = int(mins // 60)
m = int(mins % 60)

st.metric("Eventos", total)
st.metric("Tempo ocupado", f"{h}h {m}m")

# LOGOUT
if st.button("Sair"):
    st.session_state.clear()
    st.rerun()
