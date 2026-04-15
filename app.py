import streamlit as st
import pandas as pd
import altair as alt

# 1. Configuração da Página (Sempre tem que ser a primeira linha do Streamlit)
st.set_page_config(page_title="GestorHub", page_icon="🧠", layout="wide")

# ==========================================
# 🔐 SISTEMA DE LOGIN (A Mágica da Memória)
# ==========================================

# Cria a "memória" para saber se o usuário está logado
if "logado" not in st.session_state:
    st.session_state["logado"] = False

# Se NÃO estiver logado, mostra apenas a tela de Login
if not st.session_state["logado"]:
    # Criando colunas para centralizar a caixa de login no meio da tela
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.write("")
        st.write("")
        st.write("")
        st.title("🧠 Bem-vindo ao GestorHub")
        st.write("Faça login para acessar o seu centro de comando.")
        
        st.divider()
        
        # Campos de texto
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password") # type="password" esconde as letras!
        
        if st.button("Entrar no Sistema", type="primary", use_container_width=True):
            # AQUI DEFINIMOS A SENHA OFICIAL (Exemplo simples)
            if usuario == "gestor" and senha == "hub2024":
                st.session_state["logado"] = True
                st.rerun() # Faz a página recarregar para sumir o login e aparecer o sistema
            else:
                st.error("⚠️ Usuário ou senha incorretos. Tente novamente.")
                
    # O comando st.stop() impede que o resto do código abaixo seja lido se não estiver logado
    st.stop()

# ==========================================
# 🚀 O SISTEMA GESTORHUB (Só aparece se logado)
# ==========================================

# ESTILOS VISUAIS (CSS)
st.markdown("""
<style>
    .pulse-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); color: #333333; }
    .pulse-icon { font-size: 20px; margin-bottom: 5px; }
    .pulse-title { font-size: 11px; color: #888888; text-transform: uppercase; font-weight: bold; margin-bottom: 5px;}
    .pulse-value { font-size: 18px; font-weight: bold; }
    .agenda-card { background-color: #f8fafc; border-left: 5px solid #3b82f6; padding: 15px; margin-bottom: 10px; border-radius: 0 8px 8px 0; }
    .agenda-card.urgente { border-left-color: #ef4444; background-color: #fef2f2; }
    .agenda-card.foco { border-left-color: #10b981; background-color: #f0fdf4; }
    .cor-verde { color: #10b981; } .cor-azul { color: #3b82f6; } .cor-cinza { color: #6b7280; } .cor-vermelha { color: #ef4444; }
</style>
""", unsafe_allow_html=True)

# 2. Menu Lateral
with st.sidebar:
    st.title("🧠 GestorHub")
    st.write("Bem-vindo, Gestor!")
    st.divider()
    
    opcao_escolhida = st.radio("Navegação:", [
        "📊 Dashboard", "📅 Agenda", "🎥 Reuniões", "🎫 Chamados", "⚙️ Day Pulse", "📝 Carga de Trabalho" 
    ])
    
    st.divider()
    # Botão de Sair (Logout)
    if st.button("Sair (Logout)", use_container_width=True):
        st.session_state["logado"] = False
        st.rerun()

# ---------------------------------------------------------
# 3. LÓGICA DE TELAS
# ---------------------------------------------------------

if opcao_escolhida == "📊 Dashboard":
    st.title("📊 Visão Geral do Dia")
    col1, col2, col3 = st.columns(3)
    col1.metric("Reuniões Hoje", "4", "1 cancelada")
    col2.metric("Chamados Críticos", "2", "-3 resolvidos", delta_color="inverse")
    col3.metric("Tarefas Pendentes", "12")
    st.divider()
    st.warning("**Chamado #1042 em atraso:** Sistema fora do ar na filial Sul.")

elif opcao_escolhida == "📅 Agenda":
    st.title("📅 Sua Agenda")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Tempo em Reuniões", "4h 30m", "50% do dia", delta_color="inverse")
    col_kpi2.metric("Tempo de Foco (Livre)", "3h 30m", "Tempo para trabalhar")
    col_kpi3.metric("Convites Pendentes", "1", "Ação necessária", delta_color="off")
    st.divider()
    st.markdown('<div class="agenda-card urgente"><h4 style="margin:0; color:#ef4444;">14:00 - 15:30 | Alinhamento de Produto</h4></div>', unsafe_allow_html=True)

elif opcao_escolhida == "🎥 Reuniões":
    st.title("🎥 Inteligência de Reuniões")
    aba1, aba2, aba3 = st.tabs(["📝 Resumo", "🎯 Decisões", "✅ Tarefas"])
    with aba1: st.write("A equipe discutiu atrasos na nova funcionalidade...")

elif opcao_escolhida == "🎫 Chamados":
    st.title("🎫 Central de Chamados")
    st.write("Visão do Power BI em breve.")

elif opcao_escolhida == "⚙️ Day Pulse":
    st.title("💓 Day Pulse")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.markdown('<div class="pulse-card"><div class="pulse-icon">💓</div><div class="pulse-title">RITMO</div><div class="pulse-value cor-verde">Leve</div></div>', unsafe_allow_html=True)
    with col2: st.markdown('<div class="pulse-card"><div class="pulse-icon">📅</div><div class="pulse-title">EVENTOS</div><div class="pulse-value cor-azul">3</div></div>', unsafe_allow_html=True)
    with col3: st.markdown('<div class="pulse-card"><div class="pulse-icon">🕒</div><div class="pulse-title">OCUPADO</div><div class="pulse-value cor-cinza">2h 30m</div></div>', unsafe_allow_html=True)
    with col4: st.markdown('<div class="pulse-card"><div class="pulse-icon">☀️</div><div class="pulse-title">LIVRE</div><div class="pulse-value cor-verde">5h 30m</div></div>', unsafe_allow_html=True)
    with col5: st.markdown('<div class="pulse-card"><div class="pulse-icon">🏁</div><div class="pulse-title">TÉRMINO</div><div class="pulse-value cor-vermelha">18:00</div></div>', unsafe_allow_html=True)

elif opcao_escolhida == "📝 Carga de Trabalho":
    st.title("📝 Tarefas da Equipe")
    url_google_sheets = "https://docs.google.com/spreadsheets/d/18zJTm9sVvZLYqyUicQHl8R5-UWmM3qLOoE0vPAZU6_g/export?format=csv"
    try:
        dados_da_planilha = pd.read_csv(url_google_sheets)
        if 'Concluido' in dados_da_planilha.columns:
            dados_da_planilha['Concluido'] = dados_da_planilha['Concluido'].replace({'FALSO': False, 'VERDADEIRO': True})
        st.data_editor(dados_da_planilha, hide_index=True, use_container_width=True, column_config={"Concluido": st.column_config.CheckboxColumn("Concluído?")})
        st.success("Conexão com Banco de Dados realizada com sucesso! 🟢")
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha. Verifique se ela não está vazia. Erro técnico: {e}")
