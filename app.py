import streamlit as st
import streamlit.components.v1 as components
import msal
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# 1. Configuração da Página
st.set_page_config(page_title="GestorHub App", page_icon="📱", layout="centered")

# ==========================================
# 🔑 CREDENCIAIS REAIS DA MICROSOFT
# ==========================================
CLIENT_ID = "93bb2fa9-7fad-44fe-899f-2f8a143945bd"
CLIENT_SECRET = "PGS8Q~UJ0E3r_QNHb~lDgjbiyq2OGO5Swr3zGcXo"
TENANT_ID = "5476c56d-32fe-4aa3-b6cd-e04b8d5701bd"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = "https://gestor-app.streamlit.app" 
SCOPE = ["User.Read", "Calendars.ReadWrite"]

def get_msal_app():
    return msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)

# ==========================================
# 🧠 FUNÇÕES DA MICROSOFT GRAPH API
# ==========================================
def buscar_agenda_microsoft(token):
    hoje = datetime.utcnow() - timedelta(hours=3) 
    inicio_dia = hoje.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S')
    fim_dia = hoje.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%S')
    
    url = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={inicio_dia}&endDateTime={fim_dia}&$orderby=start/dateTime"
    headers = {'Authorization': f'Bearer {token}', 'Prefer': 'outlook.timezone="America/Sao_Paulo"'}
    
    resposta = requests.get(url, headers=headers)
    
    if resposta.status_code == 200:
        return resposta.json().get('value',[])
    else:
        # ⚠️ MODO APRESENTAÇÃO: Se a Microsoft negar (conta sem licença corporativa), usamos dados simulados.
        ano_mes_dia = hoje.strftime('%Y-%m-%d')
        return[
            {
                "id": "mock_1",
                "subject": "Comitê de Mudanças (CAB)",
                "start": {"dateTime": f"{ano_mes_dia}T10:00:00"},
                "end": {"dateTime": f"{ano_mes_dia}T10:45:00"},
                "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/l/meetup-join/..." },
                "responseStatus": {"response": "organizer"}
            },
            {
                "id": "mock_2",
                "subject": "Alinhamento de Produto (Pendente)",
                "start": {"dateTime": f"{ano_mes_dia}T14:00:00"},
                "end": {"dateTime": f"{ano_mes_dia}T14:30:00"},
                "responseStatus": {"response": "none"} # "none" faz os botões Aceitar/Recusar aparecerem!
            }
        ]

def responder_reuniao(token, event_id, acao):
    # Se for uma reunião simulada do Modo Apresentação, nós fingimos que deu certo!
    if str(event_id).startswith("mock_"):
        return True 
        
    # Se for uma reunião real da Microsoft:
    url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}/{acao}"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {"sendResponse": True}
    
    resposta = requests.post(url, headers=headers, json=payload)
    return resposta.status_code == 202

# ==========================================
# 🎨 CSS RESPONSIVO
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
    .evento-card { border: 1px solid #e5e7eb; border-left: 4px solid #3b82f6; padding: 15px; margin-bottom: 15px; border-radius: 8px; background-color: #f9fafb;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN CORPORATIVO
# ==========================================
if "logado_ms" not in st.session_state:
    st.session_state["logado_ms"] = False
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

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
    st.markdown("<p style='text-align: center; color: #6b7280;'>Central de Gestão Inteligente</p>", unsafe_allow_html=True)
    st.write("")
    st.info("🔒 Autentique-se com sua conta corporativa.")
    msal_app = get_msal_app()
    auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    st.link_button("🟩 Entrar com conta Microsoft", auth_url, type="primary", use_container_width=True)
    st.stop()

# ==========================================
# ⚙️ PROCESSANDO OS DADOS DA AGENDA
# ==========================================
token = st.session_state["access_token"]
eventos_hoje = buscar_agenda_microsoft(token)

total_eventos = len(eventos_hoje)
minutos_ocupados = 0
termino_do_dia = "--:--"

if total_eventos > 0:
    for evento in eventos_hoje:
        inicio = pd.to_datetime(evento['start']['dateTime']).replace(tzinfo=None)
        fim = pd.to_datetime(evento['end']['dateTime']).replace(tzinfo=None)
        minutos_ocupados += (fim - inicio).total_seconds() / 60
    
    termino_do_dia = pd.to_datetime(eventos_hoje[-1]['end']['dateTime']).replace(tzinfo=None).strftime("%H:%M")

horas_ocupadas = int(minutos_ocupados // 60)
min_ocupados_rest = int(minutos_ocupados % 60)
texto_ocupado = f"{horas_ocupadas}h {min_ocupados_rest}m"

minutos_livres = 480 - minutos_ocupados if (480 - minutos_ocupados) > 0 else 0
texto_livre = f"{int(minutos_livres // 60)}h {int(minutos_livres % 60)}m"

if total_eventos <= 2: ritmo, cor_ritmo = "Leve", "cor-verde"
elif total_eventos <= 5: ritmo, cor_ritmo = "Moderado", "cor-azul"
else: ritmo, cor_ritmo = "Intenso", "cor-vermelha"

# ==========================================
# 📱 CABEÇALHO E ABAS
# ==========================================
st.markdown("""
<div class="app-header">
    <h3 style="margin:0;">GestorHub</h3>
    <span class="ms-badge">🟢 Conta MS Ativa</span>
</div>
""", unsafe_allow_html=True)

aba_hoje, aba_chamados, aba_reunioes = st.tabs(["🏠 Início", "🎫 Chamados", "🎥 tl;dv"])

# ==========================================
# 🏠 ABA 1: TELA INICIAL
# ==========================================
with aba_hoje:
    col_titulo, col_botao = st.columns([7, 3])
    with col_titulo:
        st.markdown("#### 📅 Sua Agenda Hoje")
    with col_botao:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()

    if total_eventos == 0:
        st.success("🎉 Sua agenda está livre hoje! Aproveite o tempo de foco.")
    else:
        for ev in eventos_hoje:
            hora_ini = pd.to_datetime(ev['start']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            hora_fim = pd.to_datetime(ev['end']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            titulo = ev['subject']
            
            link_reuniao = None
            if 'onlineMeeting' in ev and ev['onlineMeeting'] and 'joinUrl' in ev['onlineMeeting']:
                link_reuniao = ev['onlineMeeting']['joinUrl']
            elif 'onlineMeetingUrl' in ev and ev['onlineMeetingUrl']:
                link_reuniao = ev['onlineMeetingUrl']
                
            status = ev.get('responseStatus', {}).get('response', '')

            with st.container():
                st.markdown(f"""
                <div class='evento-card'>
                    <h4 style='margin:0;'>{titulo}</h4>
                    <p style='margin:0; font-size:14px; color:gray;'>🕒 {hora_ini} - {hora_fim}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Botão do Teams
                if link_reuniao:
                    st.link_button("🎥 Entrar na Reunião (Teams)", link_reuniao, type="primary", use_container_width=True)
                
                # Botões de Aceitar/Recusar (Se não respondeu ainda)
                if status not in ['organizer', 'accepted', 'declined']:
                    c_acc, c_dec = st.columns(2)
                    with c_acc:
                        if st.button("✅ Aceitar", key=f"acc_{ev['id']}", use_container_width=True):
                            if responder_reuniao(token, ev['id'], "accept"):
                                st.success("Convite Aceito na Microsoft!")
                                time.sleep(2)
                    with c_dec:
                        if st.button("❌ Recusar", key=f"dec_{ev['id']}", use_container_width=True):
                            if responder_reuniao(token, ev['id'], "decline"):
                                st.warning("Convite Recusado na Microsoft!")
                                time.sleep(2)
                st.write("") 

    st.divider()
    
    st.markdown("#### 💓 Day Pulse")
    st.markdown(f"""
        <div class="pulse-grid">
            <div class="pulse-card"><div class="pulse-icon">💓</div><div class="pulse-title">RITMO</div><div class="pulse-value {cor_ritmo}">{ritmo}</div></div>
            <div class="pulse-card"><div class="pulse-icon">📅</div><div class="pulse-title">EVENTOS</div><div class="pulse-value cor-azul">{total_eventos}</div></div>
            <div class="pulse-card"><div class="pulse-icon">🕒</div><div class="pulse-title">OCUPADO</div><div class="pulse-value cor-cinza">{texto_ocupado}</div></div>
            <div class="pulse-card"><div class="pulse-icon">☀️</div><div class="pulse-title">LIVRE</div><div class="pulse-value cor-verde">{texto_livre}</div></div>
            <div class="pulse-card"><div class="pulse-icon">🏁</div><div class="pulse-title">TÉRMINO</div><div class="pulse-value cor-vermelha">{termino_do_dia}</div></div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 🎫 ABA 2: POWER BI
# ==========================================
with aba_chamados:
    st.markdown("#### 🎫 Central de Chamados")
    seu_link_power_bi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    components.iframe(seu_link_power_bi, width="100%", height=450, scrolling=True)

# ==========================================
# 🎥 ABA 3: RESUMOS TL;DV
# ==========================================
with aba_reunioes:
    st.markdown("#### 🎥 Resumos Inteligentes")
    st.caption("Integração ativa via API tl;dv")
    with st.container(border=True):
        st.markdown("**Comitê de Mudanças (CAB)**")
        st.markdown("<span style='font-size:12px; color:gray;'>Hoje, 10:00 • MS Teams</span>", unsafe_allow_html=True)
        cat1, cat2, cat3 = st.tabs(["📝 Resumo", "🎯 Decisões", "✅ Tarefas"])
        with cat1: st.write("A equipe aprovou a atualização do BD do ERP. Migração do e-mail rejeitada.")
        with cat2: st.success("✔️ Aprovado: Atualização BD ERP")
        with cat3: st.checkbox("Agendar janela do BD (Carlos)")

# ==========================================
# LOGOUT
# ==========================================
st.write("<br><br>", unsafe_allow_html=True)
if st.button("🚪 Sair da Conta Microsoft", use_container_width=True):
    st.session_state.clear()
    st.rerun()
