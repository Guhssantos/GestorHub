import streamlit as st
import msal
import requests
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURAÇÃO MOBILE-FIRST
# ==========================================
# layout="centered" é fundamental para celulares
st.set_page_config(page_title="GestorHub", page_icon="📱", layout="centered", initial_sidebar_state="collapsed")

# ==========================================
# 2. CREDENCIAIS DA MICROSOFT (DADOS REAIS)
# ==========================================
CLIENT_ID = "93bb2fa9-7fad-44fe-899f-2f8a143945bd"
CLIENT_SECRET = "PGS8Q~UJ0E3r_QNHb~lDgjbiyq2OGO5Swr3zGcXo"
TENANT_ID = "5476c56d-32fe-4aa3-b6cd-e04b8d5701bd"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = "https://gestor-app.streamlit.app" 
SCOPE =["User.Read", "Calendars.ReadWrite"]

def get_msal_app():
    return msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)

def buscar_agenda_microsoft(token):
    hoje = datetime.utcnow() - timedelta(hours=3) 
    inicio_dia = hoje.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S')
    fim_dia = hoje.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%S')
    
    url = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={inicio_dia}&endDateTime={fim_dia}&$orderby=start/dateTime"
    headers = {'Authorization': f'Bearer {token}', 'Prefer': 'outlook.timezone="America/Sao_Paulo"'}
    
    resposta = requests.get(url, headers=headers)
    if resposta.status_code == 200:
        return resposta.json().get('value',[])
    return[]

# ==========================================
# 3. CSS OTIMIZADO PARA CELULAR
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; }
    #MainMenu {visibility: hidden;} header {visibility: visible;} footer {visibility: hidden;}
    
    /* Tipografia Limpa */
    * { font-family: 'Inter', -apple-system, sans-serif !important; }
    .text-dark { color: #111827 !important; }
    .text-gray { color: #6B7280 !important; }
    
    /* Cards Mobile */
    .nexuma-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 16px; /* Menos padding para caber no celular */
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
        border: 1px solid #F3F4F6;
        margin-bottom: 16px;
    }
    
    /* Métricas Mobile */
    .metric-title { font-size: 12px; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px;}
    .metric-value { font-size: 24px; font-weight: 800; color: #111827; margin-top: 4px; }
    
    /* Botões Mobile (Largura Total para facilitar o toque) */
    .btn-mobile {
        background-color: #111827; color: #FFFFFF !important;
        padding: 12px 16px; border-radius: 8px; text-decoration: none;
        font-weight: 600; font-size: 14px; display: block; text-align: center;
        width: 100%; margin-top: 10px;
    }
    
    .btn-outline-mobile {
        background-color: #FFFFFF; color: #111827 !important;
        border: 1px solid #E5E7EB; padding: 12px 16px; border-radius: 8px; 
        text-decoration: none; font-weight: 600; font-size: 14px; display: block; text-align: center;
        width: 100%; margin-top: 10px;
    }
    
    /* Item da Agenda com quebra para celular */
    .agenda-item {
        padding: 12px 0; border-bottom: 1px solid #F3F4F6;
    }
    .agenda-item:last-child { border-bottom: none; padding-bottom: 0; }
    
    .greeting-header { margin-top: 10px; margin-bottom: 20px; }
    .greeting-header h1 { font-size: 24px; font-weight: 800; color: #111827; margin: 0;}
    .greeting-header p { font-size: 14px; color: #6B7280; margin: 5px 0 0 0;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. AUTENTICAÇÃO REAL
# ==========================================
if "logado_ms" not in st.session_state: st.session_state["logado_ms"] = False
if "access_token" not in st.session_state: st.session_state["access_token"] = None

query_params = st.query_params
if "code" in query_params and not st.session_state["logado_ms"]:
    msal_app = get_msal_app()
    result = msal_app.acquire_token_by_authorization_code(query_params["code"], scopes=SCOPE, redirect_uri=REDIRECT_URI)
    if "access_token" in result:
        st.session_state["access_token"] = result["access_token"]
        st.session_state["logado_ms"] = True
        st.query_params.clear()
        st.rerun()

if not st.session_state["logado_ms"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="nexuma-card" style="text-align: center; padding: 30px 20px;">
        <h2 class="text-dark">GestorHub</h2>
        <p class="text-gray" style="margin-bottom: 30px;">Acesso Corporativo</p>
    </div>
    """, unsafe_allow_html=True)
    msal_app = get_msal_app()
    auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    st.link_button("Entrar com Microsoft 365", auth_url, type="primary", use_container_width=True)
    st.stop()

# ==========================================
# 5. PROCESSAMENTO DA AGENDA REAL
# ==========================================
eventos_hoje = buscar_agenda_microsoft(st.session_state["access_token"])
total_eventos = len(eventos_hoje)
minutos_ocupados = 0

for evento in eventos_hoje:
    inicio = pd.to_datetime(evento['start']['dateTime']).replace(tzinfo=None)
    fim = pd.to_datetime(evento['end']['dateTime']).replace(tzinfo=None)
    minutos_ocupados += (fim - inicio).total_seconds() / 60

horas_ocupadas = int(minutos_ocupados // 60)
min_ocupados_rest = int(minutos_ocupados % 60)

# ==========================================
# 6. MENU LATERAL (HAMBÚRGUER NO CELULAR)
# ==========================================
with st.sidebar:
    st.markdown("<h3 class='text-dark'>📱 Navegação</h3>", unsafe_allow_html=True)
    opcao = st.radio("",["🏠 Início", "📊 Chamados", "🎥 tl;dv"], label_visibility="collapsed")
    st.divider()
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 7. TELAS DO APLICATIVO
# ==========================================
if opcao == "🏠 Início":
    
    st.markdown("""
    <div class="greeting-header">
        <h1>Olá, Gestor!</h1>
        <p>Resumo do seu dia</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Métricas adaptadas para celular (empilhadas)
    st.markdown(f"""
    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
        <div class="nexuma-card" style="flex: 1; margin-bottom: 0;">
            <div class="metric-title">Eventos</div>
            <div class="metric-value">{total_eventos}</div>
        </div>
        <div class="nexuma-card" style="flex: 1; margin-bottom: 0;">
            <div class="metric-title">Ocupado</div>
            <div class="metric-value">{horas_ocupadas}h {min_ocupados_rest}m</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Lista da Agenda
    st.markdown("<h4 class='text-dark' style='margin-bottom: 10px;'>Sua Agenda</h4>", unsafe_allow_html=True)
    
    if total_eventos == 0:
        st.markdown("""
        <div class="nexuma-card" style="text-align: center;">
            <p class="text-gray" style="margin: 0;">Sua agenda está livre hoje.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        agenda_html = "<div class='nexuma-card'>"
        for ev in eventos_hoje:
            hora_ini = pd.to_datetime(ev['start']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            hora_fim = pd.to_datetime(ev['end']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            titulo = ev['subject']
            
            link = ""
            if 'onlineMeeting' in ev and ev['onlineMeeting'] and 'joinUrl' in ev['onlineMeeting']:
                link = ev['onlineMeeting']['joinUrl']
            elif 'onlineMeetingUrl' in ev and ev['onlineMeetingUrl']:
                link = ev['onlineMeetingUrl']
                
            botao_html = f"<a href='{link}' target='_blank' class='btn-mobile'>Entrar na Reunião</a>" if link else "<p class='text-gray' style='font-size:12px; margin-top:5px;'><i>Sem link de reunião</i></p>"
            
            agenda_html += f"""
            <div class="agenda-item">
                <h4 class="text-dark" style="margin: 0; font-size: 15px;">{titulo}</h4>
                <p class="text-gray" style="margin: 0; font-size: 13px; margin-top: 2px;">🕒 {hora_ini} - {hora_fim}</p>
                {botao_html}
            </div>
            """
        agenda_html += "</div>"
        st.markdown(agenda_html, unsafe_allow_html=True)

elif opcao == "📊 Chamados":
    st.markdown("""
    <div class="greeting-header">
        <h1>Chamados</h1>
        <p>SLA Power BI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Iframe com width 100% e altura para celular
    st.markdown('<div class="nexuma-card" style="padding: 5px;">', unsafe_allow_html=True)
    link_pbi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    st.components.v1.iframe(link_pbi, width="100%", height=500, scrolling=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif opcao == "🎥 Resumos tl;dv":
    st.markdown("""
    <div class="greeting-header">
        <h1>tl;dv</h1>
        <p>Resumos das reuniões</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="nexuma-card">
        <h4 class="text-dark" style="margin:0;">Comitê de Mudanças</h4>
        <p class="text-gray" style="font-size: 12px; margin-top: 2px;">24 de Abril • MS Teams</p>
        <hr style="border: 0; border-top: 1px solid #F3F4F6; margin: 10px 0;">
        <p class="text-dark" style="font-size: 14px;"><b>Resumo:</b> Aprovação da atualização do BD do ERP. Migração de e-mail rejeitada.</p>
        <p class="text-dark" style="font-size: 14px; margin-top:5px;"><b>Decisões:</b><br><span style="color: #10B981;">• Aprovado: BD ERP</span><br><span style="color: #EF4444;">• Rejeitado: E-mails</span></p>
        <a href="#" class="btn-outline-mobile">Assistir no tl;dv</a>
    </div>
    """, unsafe_allow_html=True)
