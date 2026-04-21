import streamlit as st
import streamlit.components.v1 as components
import msal
import requests
from datetime import datetime, timedelta

# 1. Configuração da Página
st.set_page_config(page_title="GestorHub App", page_icon="📱", layout="centered")

# ==========================================
# 🔑 CREDENCIAIS
# ==========================================
CLIENT_ID = "93bb2fa9-7fad-44fe-899f-2f8a143945bd"
CLIENT_SECRET = "PGS8Q~UJ0E3r_QNHb~lDgjbiyq2OGO5Swr3zGcXo"
TENANT_ID = "5476c56d-32fe-4aa3-b6cd-e04b8d5701bd"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = "https://gestor-app.streamlit.app" 
SCOPE = ["User.Read", "Calendars.Read"]

def get_msal_app():
    return msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)

# ==========================================
# 🔌 FUNÇÃO PARA BUSCAR EVENTOS REAIS
# ==========================================
def get_ms_calendar_events(token):
    headers = {'Authorization': f'Bearer {token}'}
    # Define o período de hoje (00:00 até 23:59)
    now = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now + timedelta(days=1)
    
    url = f"https://graph.microsoft.com/v1.0/me/calendarview?startDateTime={now.isoformat()}Z&endDateTime={end_of_day.isoformat()}Z&$orderby=start/dateTime"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('value', [])
    return []

# ==========================================
# 🎨 CSS RESPONSIVO (Mantido e Ajustado)
# ==========================================
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .pulse-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; margin-top: 10px; }
    .pulse-card { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 15px 5px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .pulse-icon { font-size: 20px; margin-bottom: 5px; }
    .pulse-title { font-size: 10px; color: #6b7280; text-transform: uppercase; font-weight: bold; }
    .pulse-value { font-size: 16px; font-weight: 800; margin-top: 5px; }
    .cor-verde { color: #10b981; } .cor-azul { color: #3b82f6; } .cor-cinza { color: #4b5563; } .cor-vermelha { color: #ef4444; }
    .app-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 0px; border-bottom: 1px solid #e5e7eb; margin-bottom: 20px; }
    .ms-badge { background-color: #eff6ff; color: #1d4ed8; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 LÓGICA DE AUTENTICAÇÃO
# ==========================================
if "logado_ms" not in st.session_state: st.session_state["logado_ms"] = False
if "access_token" not in st.session_state: st.session_state["access_token"] = None

query_params = st.query_params
if "code" in query_params and not st.session_state["logado_ms"]:
    code = query_params["code"]
    msal_app = get_msal_app()
    result = msal_app.acquire_token_by_authorization_code(code, scopes=SCOPE, redirect_uri=REDIRECT_URI)
    if "access_token" in result:
        st.session_state["access_token"] = result["access_token"]
        st.session_state["logado_ms"] = True
        st.query_params.clear()
        st.rerun()

if not st.session_state["logado_ms"]:
    st.write("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>📱 GestorHub</h1>", unsafe_allow_html=True)
    msal_app = get_msal_app()
    auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    st.link_button("🟩 Entrar com conta Microsoft", auth_url, type="primary", use_container_width=True)
    st.stop()

# ==========================================
# 📊 PROCESSAMENTO DE DADOS (DENTRO DO APP)
# ==========================================
eventos = get_ms_calendar_events(st.session_state["access_token"])

# Cálculos para o Day Pulse
total_eventos = len(eventos)
minutos_ocupados = 0
proximo_evento = "Nenhum evento hoje"
hora_termino = "18:00"

for i, ev in enumerate(eventos):
    start = datetime.fromisoformat(ev['start']['dateTime'][:19])
    end = datetime.fromisoformat(ev['end']['dateTime'][:19])
    duracao = (end - start).seconds / 60
    minutos_ocupados += duracao
    
    # Pega o próximo evento baseado na hora atual
    if start > datetime.now() and proximo_evento == "Nenhum evento hoje":
        proximo_evento = f"{ev['subject']} ({start.strftime('%H:%M')})"
    
    # Define a hora de término como o fim do último evento
    hora_termino = end.strftime('%H:%M')

horas_foco = round(minutos_ocupados / 60, 1)
horas_livres = round(8 - horas_foco, 1) # Baseado em jornada de 8h
ritmo = "Leve" if horas_foco < 3 else "Intenso" if horas_foco > 5 else "Moderado"
cor_ritmo = "cor-verde" if ritmo == "Leve" else "cor-vermelha" if ritmo == "Intenso" else "cor-azul"

# ==========================================
# 📱 INTERFACE DO APP
# ==========================================
st.markdown(f"""<div class="app-header"><h3 style="margin:0;">GestorHub</h3><span class="ms-badge">🟢 {st.session_state.get('user_name', 'Conectado')}</span></div>""", unsafe_allow_html=True)

aba_hoje, aba_chamados, aba_reunioes = st.tabs(["🏠 Início", "🎫 Chamados", "🎥 tl;dv"])

with aba_hoje:
    st.markdown("#### 📅 Sua Agenda Hoje")
    if total_eventos > 0:
        st.success(f"**Próximo:** {proximo_evento}")
        for ev in eventos[:3]: # Mostra os 3 primeiros
            st.write(f"• {ev['subject']} | {ev['start']['dateTime'][11:16]} - {ev['end']['dateTime'][11:16]}")
    else:
        st.info("Sua agenda está livre hoje!")
    
    st.divider()
    st.markdown("#### 💓 Day Pulse")
    st.markdown(f"""
        <div class="pulse-grid">
            <div class="pulse-card"><div class="pulse-icon">💓</div><div class="pulse-title">RITMO</div><div class="pulse-value {cor_ritmo}">{ritmo}</div></div>
            <div class="pulse-card"><div class="pulse-icon">📅</div><div class="pulse-title">EVENTOS</div><div class="pulse-value cor-azul">{total_eventos}</div></div>
            <div class="pulse-card"><div class="pulse-icon">🕒</div><div class="pulse-title">OCUPADO</div><div class="pulse-value cor-cinza">{horas_foco}h</div></div>
            <div class="pulse-card"><div class="pulse-icon">☀️</div><div class="pulse-title">LIVRE</div><div class="pulse-value cor-verde">{max(0, horas_livres)}h</div></div>
            <div class="pulse-card"><div class="pulse-icon">🏁</div><div class="pulse-title">TÉRMINO</div><div class="pulse-value cor-vermelha">{hora_termino}</div></div>
        </div>
    """, unsafe_allow_html=True)

# As outras abas (PowerBI e tl;dv) permanecem iguais
with aba_chamados:
    st.markdown("#### 🎫 Central de Chamados")
    components.iframe("https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14", width="100%", height=450)

with aba_reunioes:
    st.markdown("#### 🎥 Resumos Inteligentes")
    st.info("Integração tl;dv ativa: Buscando últimas gravações...")

# Botão Logout
if st.button("Sair", use_container_width=True):
    st.session_state.clear()
    st.rerun()
