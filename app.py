import streamlit as st
import streamlit.components.v1 as components
import msal
import requests

# 1. Configuração da Página (Mobile-First)
st.set_page_config(page_title="GestorHub App", page_icon="📱", layout="centered")

# ==========================================
# 🔑 CREDENCIAIS REAIS DA MICROSOFT
# ==========================================
CLIENT_ID = "93bb2fa9-7fad-44fe-899f-2f8a143945bd"
CLIENT_SECRET = "PGS8Q~UJ0E3r_QNHb~lDgjbiyq2OGO5Swr3zGcXo"
TENANT_ID = "5476c56d-32fe-4aa3-b6cd-e04b8d5701bd"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# URL oficial do seu aplicativo na nuvem
REDIRECT_URI = "https://gestor-app.streamlit.app" 
SCOPE =["User.Read", "Calendars.Read"]

def get_msal_app():
    return msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)

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
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN CORPORATIVO (O Fluxo Real da Microsoft)
# ==========================================
if "logado_ms" not in st.session_state:
    st.session_state["logado_ms"] = False
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

# O app verifica se a Microsoft devolveu o código na URL
query_params = st.query_params
if "code" in query_params and not st.session_state["logado_ms"]:
    code = query_params["code"]
    msal_app = get_msal_app()
    result = msal_app.acquire_token_by_authorization_code(code, scopes=SCOPE, redirect_uri=REDIRECT_URI)
    
    if "access_token" in result:
        st.session_state["access_token"] = result["access_token"]
        st.session_state["logado_ms"] = True
        st.query_params.clear() # Limpa a barra de endereços para ficar bonito
        st.rerun()

# Se não estiver logado, mostra a tela de login
if not st.session_state["logado_ms"]:
    st.write("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>📱 GestorHub</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6b7280;'>Central de Gestão Inteligente</p>", unsafe_allow_html=True)
    st.write("")
    st.info("🔒 Sistema restrito. Autentique-se com seu e-mail corporativo Microsoft.")
    
    # Gera o link dinâmico e seguro da Microsoft
    msal_app = get_msal_app()
    auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    
    # ⚠️ A MUDANÇA ESTÁ AQUI: target="_top" em vez de "_self"
    st.markdown(f'''
        <a href="{auth_url}" target="_top" style="text-decoration: none;">
            <div style="background-color: #2F2F2F; color: white; padding: 12px; border-radius: 6px; text-align: center; font-weight: bold; border: 1px solid #000; font-family: sans-serif;">
                🟩 Entrar com conta Microsoft
            </div>
        </a>
    ''', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 📱 CABEÇALHO DO APLICATIVO
# ==========================================
st.markdown("""
<div class="app-header">
    <h3 style="margin:0;">GestorHub</h3>
    <span class="ms-badge">🟢 Conectado</span>
</div>
""", unsafe_allow_html=True)

aba_hoje, aba_chamados, aba_reunioes = st.tabs(["🏠 Início", "🎫 Chamados", "🎥 tl;dv"])

# ==========================================
# 🏠 ABA 1: TELA INICIAL
# ==========================================
with aba_hoje:
    st.markdown("#### 📅 Sua Agenda Hoje")
    st.caption("Acesso liberado via Microsoft Graph API")
    st.info("**Próximo Evento:** Comitê de Mudanças (10:00 - 10:45)")
    
    st.divider()
    st.markdown("#### 💓 Day Pulse")
    st.markdown("""
        <div class="pulse-grid">
            <div class="pulse-card"><div class="pulse-icon">💓</div><div class="pulse-title">RITMO</div><div class="pulse-value cor-verde">Leve</div></div>
            <div class="pulse-card"><div class="pulse-icon">📅</div><div class="pulse-title">EVENTOS</div><div class="pulse-value cor-azul">4</div></div>
            <div class="pulse-card"><div class="pulse-icon">🕒</div><div class="pulse-title">OCUPADO</div><div class="pulse-value cor-cinza">3h 30m</div></div>
            <div class="pulse-card"><div class="pulse-icon">☀️</div><div class="pulse-title">LIVRE</div><div class="pulse-value cor-verde">4h 30m</div></div>
            <div class="pulse-card"><div class="pulse-icon">🏁</div><div class="pulse-title">TÉRMINO</div><div class="pulse-value cor-vermelha">18:00</div></div>
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
    with st.container(border=True):
        st.markdown("**Comitê de Mudanças (CAB)**")
        st.markdown("<span style='font-size:12px; color:gray;'>Hoje, 10:00 • MS Teams</span>", unsafe_allow_html=True)
        cat1, cat2, cat3 = st.tabs(["📝 Resumo", "🎯 Decisões", "✅ Tarefas"])
        with cat1: st.write("A equipe aprovou a atualização do BD do ERP. Migração do e-mail rejeitada.")
        with cat2: st.success("✔️ Aprovado: Atualização BD ERP")
        with cat3: st.checkbox("Agendar janela do BD (Carlos)")

# Botão de Logout
st.write("<br><br>", unsafe_allow_html=True)
if st.button("Sair da Conta Microsoft", use_container_width=True):
    st.session_state["logado_ms"] = False
    st.session_state["access_token"] = None
    st.rerun()
