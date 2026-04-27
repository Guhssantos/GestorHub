import streamlit as st
import msal
import requests
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURAÇÃO (WIDE = Fica perfeito no PC e no Celular)
# ==========================================
st.set_page_config(page_title="GestorHub", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 2. CREDENCIAIS DA MICROSOFT (DADOS REAIS)
# ==========================================
CLIENT_ID = "261febe1-b827-452e-8bc5-e5ae52a6340c"
CLIENT_SECRET = "~pQ8Q~ckiPJbeP~FOA0yTOySNzGCxbVTIfVmLcV_"

# Usando 'common' para aceitar o @outlook.com
AUTHORITY = "https://login.microsoftonline.com/common"
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
# 3. CSS PREMIUM (Obriga a ser Modo Claro / Nexuma)
# ==========================================
st.markdown("""
<style>
    /* Força Fundo Claro no App Inteiro */
    .stApp, [data-testid="stAppViewContainer"] { background-color: #F9FAFB !important; }
    
    /* Força Fundo Branco e Texto Escuro na Barra Lateral */[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E7EB !important; }
    [data-testid="stSidebar"] * { color: #111827 !important; }
    
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* Tipografia Limpa */
    * { font-family: 'Inter', 'Segoe UI', sans-serif !important; }
    
    /* Cards Modernos (Nexuma) */
    .nexuma-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        border: 1px solid #E5E7EB;
        margin-bottom: 20px;
    }
    
    /* Header do Dashboard */
    .dashboard-header { margin-top: 10px; margin-bottom: 30px; }
    .dashboard-header h1 { font-size: 28px; font-weight: 800; color: #111827; margin: 0;}
    .dashboard-header p { font-size: 15px; color: #6B7280; margin: 4px 0 0 0;}
    
    /* Botões elegantes */
    .btn-primary {
        background-color: #111827; color: #FFFFFF !important;
        padding: 12px 24px; border-radius: 8px; text-decoration: none;
        font-weight: 600; font-size: 14px; display: inline-block; text-align: center;
        border: none; cursor: pointer; width: 100%;
    }
    .btn-primary:hover { background-color: #374151; }
    
    /* Item da Agenda */
    .agenda-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 16px 0; border-bottom: 1px solid #F3F4F6;
    }
    .agenda-item:last-child { border-bottom: none; padding-bottom: 0; }
    
    /* Grid do Day Pulse */
    .pulse-grid {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 15px; margin-top: 15px;
    }
    .pulse-box {
        background-color: #F9FAFB; border-radius: 12px; padding: 20px 10px;
        text-align: center; border: 1px solid #E5E7EB;
    }
    .p-title { font-size: 11px; color: #6B7280; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px;}
    .p-val { font-size: 20px; font-weight: 800; margin-top: 8px; color: #111827; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. AUTENTICAÇÃO REAL MSAL
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
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="nexuma-card" style="text-align: center; padding: 50px;">
            <h1 style="color: #111827; font-weight: 800; font-size: 32px;">GestorHub</h1>
            <p style="color: #6B7280; margin-bottom: 40px;">Centro de Comando Executivo</p>
        </div>
        """, unsafe_allow_html=True)
        msal_app = get_msal_app()
        auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.link_button("Entrar com Microsoft 365", auth_url, type="primary", use_container_width=True)
    st.stop()

# ==========================================
# 5. PROCESSAMENTO DE DADOS (AGENDA E PULSE)
# ==========================================
eventos_hoje = buscar_agenda_microsoft(st.session_state["access_token"])
total_eventos = len(eventos_hoje)
minutos_ocupados = 0
termino_do_dia = "--:--"

if total_eventos > 0:
    for ev in eventos_hoje:
        inicio = pd.to_datetime(ev['start']['dateTime']).replace(tzinfo=None)
        fim = pd.to_datetime(ev['end']['dateTime']).replace(tzinfo=None)
        minutos_ocupados += (fim - inicio).total_seconds() / 60
    termino_do_dia = pd.to_datetime(eventos_hoje[-1]['end']['dateTime']).replace(tzinfo=None).strftime("%H:%M")

horas_ocupadas = int(minutos_ocupados // 60)
min_ocupados_rest = int(minutos_ocupados % 60)
minutos_livres = 480 - minutos_ocupados if (480 - minutos_ocupados) > 0 else 0

# ==========================================
# 6. MENU LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="padding: 10px 0 30px 0;">
            <h2 style="margin:0; font-weight:800; font-size:24px;">GestorHub</h2>
        </div>
    """, unsafe_allow_html=True)
    
    opcao = st.radio("Navegação", ["🏠 Início", "📊 Chamados", "🎥 tl;dv"], label_visibility="collapsed")
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("Sair da Conta", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 7. TELAS DO APLICATIVO
# ==========================================
if opcao == "🏠 Início":
    
    # Header
    st.markdown("""
    <div class="dashboard-header">
        <h1>Olá, Gestor!</h1>
        <p>Visão geral da sua agenda sincronizada com a Microsoft</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Bloco Principal: Agenda
    st.markdown("<h4 style='color:#111827; margin-bottom:15px;'>Sua Agenda Hoje</h4>", unsafe_allow_html=True)
    
    if total_eventos == 0:
        st.markdown("""
        <div class="nexuma-card" style="text-align: center; padding: 40px;">
            <span style="font-size: 30px;">🎉</span>
            <p style="color: #6B7280; font-size: 16px; margin-top: 10px;">Sua agenda está livre hoje.</p>
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
                
            botao_html = f"<a href='{link}' target='_blank' class='btn-primary' style='width:auto;'>Entrar na Reunião</a>" if link else "<span style='color:#9CA3AF; font-size:13px;'>Sem link online</span>"
            
            agenda_html += f"""
            <div class="agenda-item">
                <div style="flex:1;">
                    <h4 style="margin: 0; font-size: 16px; color:#111827;">{titulo}</h4>
                    <p style="margin: 4px 0 0 0; font-size: 14px; color:#6B7280;">🕒 {hora_ini} - {hora_fim}</p>
                </div>
                <div>{botao_html}</div>
            </div>
            """
        agenda_html += "</div>"
        st.markdown(agenda_html, unsafe_allow_html=True)

    # Bloco Inferior: Day Pulse (Como solicitado, posicionado no final)
    st.markdown("<h4 style='color:#111827; margin-top:30px; margin-bottom:5px;'>Day Pulse</h4>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="nexuma-card">
        <div class="pulse-grid">
            <div class="pulse-box"><div class="p-title">EVENTOS</div><div class="p-val" style="color:#3B82F6;">{total_eventos}</div></div>
            <div class="pulse-box"><div class="p-title">OCUPADO</div><div class="p-val">{horas_ocupadas}h {min_ocupados_rest}m</div></div>
            <div class="pulse-box"><div class="p-title">LIVRE</div><div class="p-val" style="color:#10B981;">{int(minutos_livres // 60)}h {int(minutos_livres % 60)}m</div></div>
            <div class="pulse-box"><div class="p-title">TÉRMINO</div><div class="p-val" style="color:#EF4444;">{termino_do_dia}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

elif opcao == "📊 Chamados":
    st.markdown("""
    <div class="dashboard-header">
        <h1>Chamados</h1>
        <p>Acompanhamento de SLAs em tempo real</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="nexuma-card" style="padding: 10px;">', unsafe_allow_html=True)
    link_pbi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    st.components.v1.iframe(link_pbi, width=1200, height=700, scrolling=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif opcao == "🎥 Resumos tl;dv":
    st.markdown("""
    <div class="dashboard-header">
        <h1>Resumos de Reuniões</h1>
        <p>Insights extraídos das reuniões (tl;dv)</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="nexuma-card">
        <h3 style="color:#111827; margin:0;">Comitê de Mudanças (CAB)</h3>
        <p style="color:#6B7280; font-size:14px; margin-top:4px;">Hoje, 10:00 • Duração: 45m</p>
        
        <div style="background-color:#F9FAFB; padding:15px; border-radius:8px; margin-top:20px;">
            <p style="color:#111827; font-size:14px; margin:0;"><b>📝 Resumo:</b> A equipe aprovou a atualização do BD do ERP para este domingo. A migração do servidor de e-mails foi rejeitada por falta de testes de segurança.</p>
        </div>
        
        <div style="margin-top: 15px;">
            <span style="background-color:#D1FAE5; color:#065F46; padding:5px 10px; border-radius:20px; font-size:12px; font-weight:bold; margin-right:10px;">✔️ Aprovado: BD ERP</span>
            <span style="background-color:#FEE2E2; color:#991B1B; padding:5px 10px; border-radius:20px; font-size:12px; font-weight:bold;">❌ Rejeitado: Migração E-mails</span>
        </div>
        
        <br>
        <a href="#" class="btn-primary" style="width: auto;">🔗 Assistir Gravação no tl;dv</a>
    </div>
    """, unsafe_allow_html=True)
