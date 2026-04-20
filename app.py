import streamlit as st
import streamlit.components.v1 as components
import time

# 1. Configuração da Página (Mobile-First)
st.set_page_config(page_title="GestorHub App", page_icon="📱", layout="centered")

# ==========================================
# 🎨 CSS RESPONSIVO & PROFISSIONAL
# ==========================================
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Estilo do Botão Microsoft */
    .ms-btn {
        display: flex; align-items: center; justify-content: center;
        background-color: #2F2F2F; color: white; padding: 12px;
        border-radius: 6px; font-weight: bold; cursor: pointer;
        border: 1px solid #000; margin-top: 20px;
    }
    
    /* Grid Responsivo para o Day Pulse */
    .pulse-grid {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 10px; margin-top: 10px;
    }
    .pulse-card {
        background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px;
        padding: 15px 5px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .pulse-icon { font-size: 20px; margin-bottom: 5px; }
    .pulse-title { font-size: 10px; color: #6b7280; text-transform: uppercase; font-weight: bold; }
    .pulse-value { font-size: 16px; font-weight: 800; margin-top: 5px; }
    
    .cor-verde { color: #10b981; } .cor-azul { color: #3b82f6; } 
    .cor-cinza { color: #4b5563; } .cor-vermelha { color: #ef4444; }
    
    /* Cabeçalho do App */
    .app-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 0px; border-bottom: 1px solid #e5e7eb; margin-bottom: 20px;
    }
    .ms-badge {
        background-color: #eff6ff; color: #1d4ed8; padding: 4px 8px;
        border-radius: 4px; font-size: 10px; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN CORPORATIVO (Integração Microsoft)
# ==========================================
if "logado_ms" not in st.session_state:
    st.session_state["logado_ms"] = False

if not st.session_state["logado_ms"]:
    st.write("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>📱 GestorHub</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6b7280;'>Central de Gestão Inteligente</p>", unsafe_allow_html=True)
    
    st.write("")
    st.info("🔒 Sistema restrito. Autentique-se com seu e-mail corporativo.")
    
    # Botão simulando o SSO da Microsoft
    if st.button("🟩 Entrar com conta Microsoft", type="primary", use_container_width=True):
        with st.spinner("Autenticando via Microsoft Entra ID..."):
            time.sleep(2)
            st.session_state["logado_ms"] = True
            st.rerun()
    st.stop()

# ==========================================
# 📱 CABEÇALHO DO APLICATIVO
# ==========================================
st.markdown("""
<div class="app-header">
    <h3 style="margin:0;">GestorHub</h3>
    <span class="ms-badge">🟢 Conta Microsoft Vinculada</span>
</div>
""", unsafe_allow_html=True)

# NAVEGAÇÃO NATIVA MOBILE (Abas Superiores)
aba_hoje, aba_chamados, aba_reunioes = st.tabs(["🏠 Início", "🎫 Chamados", "🎥 tl;dv"])

# ==========================================
# 🏠 ABA 1: TELA INICIAL (Agenda MS + Pulse)
# ==========================================
with aba_hoje:
    st.markdown("#### 📅 Sua Agenda Hoje")
    st.caption("Sincronizado via Microsoft Graph API")
    
    st.info("**Próximo Evento:** Comitê de Mudanças (10:00 - 10:45)")
    st.success("**Reuniões Restantes:** 3 reuniões no MS Teams.")
    
    st.divider()
    
    st.markdown("#### 💓 Day Pulse")
    st.caption("Baseado no seu calendário do Outlook")
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
# 🎫 ABA 2: POWER BI (Chamados)
# ==========================================
with aba_chamados:
    st.markdown("#### 🎫 Central de Chamados")
    st.caption("Acesso unificado via Power BI SSO")
    
    # URL do Power BI
    seu_link_power_bi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    
    # Renderização Mobile-Friendly (100% da tela)
    components.iframe(seu_link_power_bi, width="100%", height=450, scrolling=True)
    
    st.button("🔄 Sincronizar Dados", use_container_width=True)

# ==========================================
# 🎥 ABA 3: RESUMOS TL;DV (Categorizados)
# ==========================================
with aba_reunioes:
    st.markdown("#### 🎥 Resumos Inteligentes")
    st.caption("Extraído automaticamente das reuniões do MS Teams via tl;dv")
    
    # Card de Reunião 1
    with st.container(border=True):
        st.markdown("**Comitê de Mudanças (CAB)**")
        st.markdown("<span style='font-size:12px; color:gray;'>Hoje, 10:00 • MS Teams</span>", unsafe_allow_html=True)
        
        # Categorias como você pediu!
        cat1, cat2, cat3 = st.tabs(["📝 Resumo", "🎯 Decisões", "✅ Tarefas"])
        with cat1:
            st.write("A equipe aprovou a atualização do BD do ERP. A migração do servidor de e-mails foi rejeitada por falta de testes de segurança.")
        with cat2:
            st.success("✔️ Aprovado: Atualização BD ERP")
            st.error("❌ Rejeitado: Migração E-mails")
        with cat3:
            st.checkbox("Agendar janela do BD (Carlos)")
            st.checkbox("Refazer testes de segurança (João)")
            
        st.button("🔗 Ver Vídeo Completo (tl;dv)", key="btn_tldv1", use_container_width=True)

    st.write("")
    
    # Card de Reunião 2
    with st.container(border=True):
        st.markdown("**Alinhamento de Produto**")
        st.markdown("<span style='font-size:12px; color:gray;'>Ontem, 14:00 • MS Teams</span>", unsafe_allow_html=True)
        
        cat4, cat5, cat6 = st.tabs(["📝 Resumo", "🎯 Decisões", "✅ Tarefas"])
        with cat4:
            st.write("Definição das prioridades da sprint atual com foco em correções.")
        with cat5:
            st.info("Prioridade: Correção de Bugs de Login")
        with cat6:
            st.checkbox("Atualizar repositório mobile (Ana)")
            
        st.button("🔗 Ver Vídeo Completo (tl;dv)", key="btn_tldv2", use_container_width=True)

# Botão de Logout no rodapé
st.write("<br><br>", unsafe_allow_html=True)
if st.button("Sair da Conta Microsoft", use_container_width=True):
    st.session_state["logado_ms"] = False
    st.rerun()
