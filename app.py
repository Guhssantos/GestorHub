import streamlit as st
import msal
import requests
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="GestorHub", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 2. CREDENCIAIS DA MICROSOFT
# ==========================================
CLIENT_ID = "261febe1-b827-452e-8bc5-e5ae52a6340c"
CLIENT_SECRET = "~pQ8Q~ckiPJbeP~FOA0yTOySNzGCxbVTIfVmLcV_"
AUTHORITY = "https://login.microsoftonline.com/common"
REDIRECT_URI = "https://gestor-app.streamlit.app" 
SCOPE = ["User.Read", "Calendars.ReadWrite"]

def get_msal_app():
    return msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)

def buscar_agenda_microsoft(token):
    hoje = datetime.utcnow() - timedelta(hours=3) 
    inicio_dia = hoje.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S')
    fim_dia = hoje.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%S')
    
    url = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={inicio_dia}&endDateTime={fim_dia}&$orderby=start/dateTime"
    headers = {'Authorization': f'Bearer {token}', 'Prefer': 'outlook.timezone="America/Sao_Paulo"'}
    
    try:
        resposta = requests.get(url, headers=headers)
        if resposta.status_code == 200:
            return resposta.json().get('value', [])
    except:
        return []
    return []

# ==========================================
# 3. CSS PREMIUM (Correção total de visibilidade)
# ==========================================
st.markdown("""
<style>
    /* Fundo Claro Geral */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] { 
        background-color: #F9FAFB !important; 
    }
    
    /* CORREÇÃO DO BOTÃO DO MENU (Hambúrguer) */
    button[data-testid="baseButton-headerNoPadding"] {
        color: #111827 !important;
    }
    svg[viewBox="0 0 24 24"] {
        fill: #111827 !important;
    }

    /* Estilização da Sidebar */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { 
        color: #111827 !important; 
        font-weight: 600; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Selectbox na Sidebar */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #E5E7EB !important;
    }

    /* Botão Sair */
    [data-testid="stSidebar"] button {
        background-color: #FEE2E2 !important;
        color: #991B1B !important;
        border: 1px solid #FCA5A5 !important;
        border-radius: 8px !important;
    }

    /* Cards e Dashboard */
    .nexuma-card {
        background-color: #FFFFFF; border-radius: 16px; padding: 24px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03); border: 1px solid #E5E7EB; margin-bottom: 20px;
    }
    
    .btn-primary {
        background-color: #111827; color: #FFFFFF !important; padding: 10px 20px; 
        border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 13px; 
        display: inline-block; transition: 0.3s;
    }
    .btn-primary:hover { background-color: #374151; }

    .agenda-item { 
        display: flex; justify-content: space-between; align-items: center; 
        padding: 16px 0; border-bottom: 1px solid #F3F4F6; 
    }
    .agenda-item:last-child { border-bottom: none; }

    .pulse-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; }
    .pulse-box { background-color: #F9FAFB; border-radius: 12px; padding: 15px; text-align: center; border: 1px solid #E5E7EB; }
    .p-title { font-size: 11px; color: #6B7280; font-weight: bold; }
    .p-val { font-size: 18px; font-weight: 800; color: #111827; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. AUTENTICAÇÃO
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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="nexuma-card" style="text-align: center; margin-top: 100px;">', unsafe_allow_html=True)
        st.title("GestorHub")
        st.write("Centro de Comando Executivo")
        msal_app = get_msal_app()
        auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.link_button("Entrar com Microsoft 365", auth_url, type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 5. PROCESSAMENTO
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
min_restantes = int(minutos_ocupados % 60)
minutos_livres = max(0, 480 - minutos_ocupados)

# ==========================================
# 6. SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("## GestorHub")
    st.markdown("---")
    opcao = st.selectbox("Navegação", ["🏠 Início", "📊 Chamados", "🎥 Resumos tl;dv"])
    st.markdown("<br>" * 10, unsafe_allow_html=True)
    if st.button("Sair da Conta", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 7. TELAS
# ==========================================
if opcao == "🏠 Início":
    st.markdown('<h1>Olá, Gestor!</h1><p style="color:#6B7280;">Sua agenda sincronizada</p>', unsafe_allow_html=True)
    
    col_t, col_b = st.columns([8, 2])
    with col_t: st.subheader("Sua Agenda Hoje")
    with col_b: 
        if st.button("🔄 Atualizar"): st.rerun()

    if total_eventos == 0:
        st.info("Agenda livre para hoje!")
    else:
        # CONSTRUÇÃO DO HTML DA AGENDA
        html_agenda = '<div class="nexuma-card">'
        for ev in eventos_hoje:
            ini = pd.to_datetime(ev['start']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            fim = pd.to_datetime(ev['end']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            link = ev.get('onlineMeeting', {}).get('joinUrl') or ev.get('onlineMeetingUrl', '')
            
            botao = f'<a href="{link}" target="_blank" class="btn-primary">Entrar</a>' if link else '<span style="color:#9CA3AF;">Presencial</span>'
            
            html_agenda += f'''
            <div class="agenda-item">
                <div style="flex:1;">
                    <div style="font-weight:700; color:#111827;">{ev["subject"]}</div>
                    <div style="font-size:13px; color:#6B7280;">🕒 {ini} - {fim}</div>
                </div>
                {botao}
            </div>
            '''
        html_agenda += '</div>'
        st.markdown(html_agenda, unsafe_allow_html=True)

    # DAY PULSE
    st.subheader("Day Pulse")
    st.markdown(f"""
    <div class="nexuma-card">
        <div class="pulse-grid">
            <div class="pulse-box"><div class="p-title">EVENTOS</div><div class="p-val" style="color:#3B82F6;">{total_eventos}</div></div>
            <div class="pulse-box"><div class="p-title">OCUPADO</div><div class="p-val">{horas_ocupadas}h {min_restantes}m</div></div>
            <div class="pulse-box"><div class="p-title">LIVRE</div><div class="p-val" style="color:#10B981;">{int(minutos_livres//60)}h {int(minutos_livres%60)}m</div></div>
            <div class="pulse-box"><div class="p-title">TÉRMINO</div><div class="p-val" style="color:#EF4444;">{termino_do_dia}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

elif opcao == "📊 Chamados":
    st.title("Chamados")
    st.components.v1.iframe("https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14", height=800)

elif opcao == "🎥 Resumos tl;dv":
    st.title("Resumos tl;dv")
    st.markdown('<div class="nexuma-card"><h3>Comitê de Mudanças</h3><p>Resumo da IA: Aprovado deploy de domingo.</p></div>', unsafe_allow_html=True)
