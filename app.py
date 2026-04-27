import streamlit as st
import msal
import requests
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA (WIDE PARA DASHBOARD)
# ==========================================
st.set_page_config(page_title="GestorHub", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

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
        return resposta.json().get('value', [])
    return[] # RETORNA VAZIO SE NÃO TIVER DADOS. ZERO MOCKS.

# ==========================================
# 3. CSS PREMIUM (ESTILO NEXUMA / REFERENCE)
# ==========================================
st.markdown("""
<style>
    /* Força o fundo claro e esconde elementos padrão do Streamlit */
    .stApp { background-color: #F8F9FA; }
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* Tipografia e Cores Base */
    h1, h2, h3, h4, p, span, div { font-family: 'Inter', 'Segoe UI', sans-serif !important; }
    .text-dark { color: #111827 !important; }
    .text-gray { color: #6B7280 !important; }
    
    /* Cards Modernos (Estilo Nexuma) */
    .nexuma-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
        border: 1px solid #F3F4F6;
        margin-bottom: 20px;
        transition: transform 0.2s ease;
    }
    .nexuma-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 0, 0, 0.06); }
    
    /* Métricas do Dashboard */
    .metric-title { font-size: 14px; font-weight: 600; color: #6B7280; display: flex; align-items: center; gap: 8px;}
    .metric-value { font-size: 32px; font-weight: 700; color: #111827; margin-top: 8px; }
    
    /* Botoes Elegantes */
    .btn-primary {
        background-color: #111827; color: #FFFFFF !important;
        padding: 10px 20px; border-radius: 8px; text-decoration: none;
        font-weight: 600; font-size: 14px; display: inline-block; text-align: center;
    }
    .btn-outline {
        background-color: #FFFFFF; color: #111827 !important;
        border: 1px solid #E5E7EB; padding: 10px 20px; border-radius: 8px; 
        text-decoration: none; font-weight: 600; font-size: 14px; display: inline-block;
    }
    
    /* Tabela / Lista de Agenda */
    .agenda-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 16px 0; border-bottom: 1px solid #F3F4F6;
    }
    .agenda-item:last-child { border-bottom: none; padding-bottom: 0; }
    
    /* Saudação Topo */
    .greeting-header { margin-top: 20px; margin-bottom: 30px; }
    .greeting-header h1 { font-size: 28px; font-weight: 700; color: #111827; margin: 0;}
    .greeting-header p { font-size: 16px; color: #6B7280; margin: 5px 0 0 0;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. AUTENTICAÇÃO REAL (SEM ENROLAÇÃO)
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
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="nexuma-card" style="text-align: center; padding: 40px;">
            <h2 class="text-dark">GestorHub</h2>
            <p class="text-gray" style="margin-bottom: 30px;">Faça login para acessar seu centro de comando.</p>
        </div>
        """, unsafe_allow_html=True)
        msal_app = get_msal_app()
        auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.link_button("Entrar com Microsoft 365", auth_url, type="primary", use_container_width=True)
    st.stop()

# ==========================================
# 5. PROCESSAMENTO DE DADOS (100% REAIS)
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
# 6. SIDEBAR (MENU LIMPO)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color:#111827; margin-bottom: 30px;'>GestorHub</h2>", unsafe_allow_html=True)
    
    # Navegação usando botões radio limpos
    opcao = st.radio("", ["🏠 Home", "📊 Chamados", "🎥 Resumos tl;dv"], label_visibility="collapsed")
    
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    if st.button("Sair da Conta", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 7. INTERFACE PRINCIPAL (DASHBOARD)
# ==========================================
if opcao == "🏠 Home":
    
    # Cabeçalho Estilo Nexuma
    st.markdown("""
    <div class="greeting-header">
        <h1>Olá, Gestor!</h1>
        <p>Seu centro de comando está pronto 🚀</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ------------------------------------------
    # LINHA 1: MÉTRICAS (Day Pulse Redesenhado)
    # ------------------------------------------
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="nexuma-card">
            <div class="metric-title">📅 Eventos Hoje</div>
            <div class="metric-value">{total_eventos} <span style="font-size:14px; color:#6B7280; font-weight:normal;">reuniões</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="nexuma-card">
            <div class="metric-title">🕒 Tempo Ocupado</div>
            <div class="metric-value">{horas_ocupadas}h {min_ocupados_rest}m</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="nexuma-card">
            <div class="metric-title">🔥 Status SLA</div>
            <div class="metric-value" style="color: #10B981;">Estável</div>
        </div>
        """, unsafe_allow_html=True)

    # ------------------------------------------
    # LINHA 2: AGENDA (Totalmente Clean e Funcional)
    # ------------------------------------------
    st.markdown("<h3 class='text-dark' style='margin-top: 20px; margin-bottom: 15px;'>Agenda do Dia</h3>", unsafe_allow_html=True)
    
    if total_eventos == 0:
        st.markdown("""
        <div class="nexuma-card" style="text-align: center; padding: 40px;">
            <p class="text-gray" style="font-size: 16px;">Sua agenda está livre hoje.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Construindo a lista de agenda com HTML/CSS dentro do Card
        agenda_html = "<div class='nexuma-card'>"
        
        for ev in eventos_hoje:
            hora_ini = pd.to_datetime(ev['start']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            hora_fim = pd.to_datetime(ev['end']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            titulo = ev['subject']
            
            # Pega link se tiver
            link = ""
            if 'onlineMeeting' in ev and ev['onlineMeeting'] and 'joinUrl' in ev['onlineMeeting']:
                link = ev['onlineMeeting']['joinUrl']
            elif 'onlineMeetingUrl' in ev and ev['onlineMeetingUrl']:
                link = ev['onlineMeetingUrl']
                
            botao_html = f"<a href='{link}' target='_blank' class='btn-primary'>Entrar</a>" if link else "<span class='text-gray' style='font-size:12px;'>Presencial / Sem Link</span>"
            
            agenda_html += f"""
            <div class="agenda-item">
                <div>
                    <h4 class="text-dark" style="margin: 0; font-size: 16px;">{titulo}</h4>
                    <p class="text-gray" style="margin: 0; font-size: 14px; margin-top: 4px;">{hora_ini} - {hora_fim}</p>
                </div>
                <div>{botao_html}</div>
            </div>
            """
            
        agenda_html += "</div>"
        st.markdown(agenda_html, unsafe_allow_html=True)

# ==========================================
# TELA 2: CHAMADOS (POWER BI LIMPO)
# ==========================================
elif opcao == "📊 Chamados":
    st.markdown("""
    <div class="greeting-header">
        <h1>Chamados</h1>
        <p>Painel de SLAs via Power BI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Embutindo Power BI dentro de um card com bordas redondas
    st.markdown('<div class="nexuma-card" style="padding: 10px;">', unsafe_allow_html=True)
    link_pbi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    st.components.v1.iframe(link_pbi, width=1200, height=700, scrolling=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TELA 3: RESUMOS TL;DV
# ==========================================
elif opcao == "🎥 Resumos tl;dv":
    st.markdown("""
    <div class="greeting-header">
        <h1>Resumos de Reuniões</h1>
        <p>Insights extraídos das suas reuniões corporativas.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="nexuma-card">
        <h4 class="text-dark" style="margin:0;">Comitê de Mudanças (CAB)</h4>
        <p class="text-gray" style="font-size: 14px; margin-top: 5px;">Data: 24 de Abril</p>
        <hr style="border: 0; border-top: 1px solid #F3F4F6; margin: 15px 0;">
        <p class="text-dark"><b>Resumo:</b> A equipe aprovou a atualização do BD do ERP. Migração do e-mail rejeitada.</p>
        <p class="text-dark"><b>Decisões:</b> <span style="color: #10B981;">Aprovado: BD ERP</span> | <span style="color: #EF4444;">Rejeitado: E-mails</span></p>
        <br>
        <a href="#" class="btn-outline">Ver Vídeo Completo (tl;dv)</a>
    </div>
    """, unsafe_allow_html=True)
