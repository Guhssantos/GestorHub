import streamlit as st
import pandas as pd
import time 
import streamlit.components.v1 as components 

st.set_page_config(page_title="GestorHub", page_icon="🧠", layout="wide")

# ==========================================
# 🔐 SISTEMA DE LOGIN
# ==========================================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write(""); st.write(""); st.write("")
        st.title("🧠 Bem-vindo ao GestorHub")
        st.write("Faça login para acessar o seu centro de comando.")
        st.divider()
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar no Sistema", type="primary", use_container_width=True):
            if usuario == "gestor" and senha == "hub2024":
                st.session_state["logado"] = True
                st.rerun()
            else:
                st.error("⚠️ Usuário ou senha incorretos.")
    st.stop()

# ==========================================
# 🚀 O SISTEMA GESTORHUB
# ==========================================

url_google_sheets = "https://docs.google.com/spreadsheets/d/18zJTm9sVvZLYqyUicQHl8R5-UWmM3qLOoE0vPAZU6_g/export?format=csv"

st.markdown("""
<style>
    .pulse-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); color: #333333; }
    .pulse-icon { font-size: 20px; margin-bottom: 5px; }
    .pulse-title { font-size: 11px; color: #888888; text-transform: uppercase; font-weight: bold; margin-bottom: 5px;}
    .pulse-value { font-size: 18px; font-weight: bold; }
    .agenda-card { background-color: #f8fafc; border-left: 5px solid #3b82f6; padding: 15px; margin-bottom: 10px; border-radius: 0 8px 8px 0; }
    .agenda-card.urgente { border-left-color: #ef4444; background-color: #fef2f2; }
    .cor-verde { color: #10b981; } .cor-azul { color: #3b82f6; } .cor-cinza { color: #6b7280; } .cor-vermelha { color: #ef4444; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🧠 GestorHub")
    st.write("Bem-vindo, Gestor!")
    st.divider()
    opcao_escolhida = st.radio("Navegação:",["📊 Dashboard", "📅 Agenda", "🎥 Reuniões", "🎫 Chamados", "⚙️ Day Pulse", "📝 Carga de Trabalho"])
    st.divider()
    if st.button("Sair (Logout)", use_container_width=True):
        st.session_state["logado"] = False
        st.rerun()

# ---------------------------------------------------------
# 3. LÓGICA DE TELAS
# ---------------------------------------------------------

if opcao_escolhida == "📊 Dashboard":
    st.title("📊 Visão Geral do Dia")
    st.write("O que você precisa focar agora.")
    st.info("🕒 **Próxima Reunião em 15 min:** Alinhamento de Produto | [🎥 Entrar no Teams](#)")
    try:
        df_tarefas = pd.read_csv(url_google_sheets)
        tarefas_pendentes = len(df_tarefas[df_tarefas['Concluido'] == 'FALSO'])
    except:
        tarefas_pendentes = "Erro"

    col1, col2, col3 = st.columns(3)
    col1.metric("Reuniões Restantes", "2", "-2 concluídas", delta_color="normal")
    col2.metric("SLA de Chamados", "98%", "Atenção", delta_color="off")
    col3.metric("Tarefas Pendentes", tarefas_pendentes, "Base atualizada", delta_color="normal")
    
    st.divider()
    col_alertas, col_resumo = st.columns(2)
    with col_alertas:
        st.subheader("⚠️ Alertas Prioritários")
        st.error("🚨 **Atraso Crítico:** Chamado #1042 rompeu o SLA.")
        st.warning("👤 **Sobrecarga:** A analista 'Ana' possui 3 tarefas de Alta Prioridade acumuladas.")
    with col_resumo:
        st.subheader("💡 Último Insight da IA")
        st.success("**CAB (Comitê de Mudanças):** Atualização do BD do ERP Aprovada para Domingo às 02h. Risco baixo.")

elif opcao_escolhida == "📅 Agenda":
    st.title("📅 Sua Agenda")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Tempo em Reuniões", "4h 30m", "50% do dia", delta_color="inverse")
    col_kpi2.metric("Tempo de Foco (Livre)", "3h 30m")
    col_kpi3.metric("Convites Pendentes", "1")
    st.divider()
    st.markdown('<div class="agenda-card urgente"><h4 style="margin:0; color:#ef4444;">14:00 - 15:30 | Alinhamento de Produto</h4></div>', unsafe_allow_html=True)

elif opcao_escolhida == "🎥 Reuniões":
    st.title("🎥 Inteligência de Reuniões")
    texto_reuniao = st.text_area("Cole aqui a transcrição bruta do Comitê de Mudanças (CAB):", height=150)
    if st.button("✨ Analisar Comitê com IA", type="primary"):
        if texto_reuniao != "":
            with st.spinner("Analisando impactos, aprovações e janelas... ⏳"):
                time.sleep(2)
                st.success("✨ Análise do Comitê de Mudanças concluída!")
                aba1, aba2, aba3 = st.tabs(["📝 Resumo", "⚖️ GMUDs", "✅ Plano de Ação"])
                with aba1: st.write("Foram avaliadas 2 requisições de mudança (GMUDs)...")
                with aba2: st.success("✔️ **APROVADO: Atualização do BD do ERP**")
                with aba3: st.checkbox("Agendar janela de manutenção para Domingo às 02h")

elif opcao_escolhida == "🎫 Chamados":
    st.title("🎫 Chamados")
    st.divider()
    seu_link_power_bi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    
    # ⚠️ AQUI ESTÁ A MUDANÇA DO TAMANHO
    # Aumentei a largura (width) para 1400 e a altura (height) para 850
    components.iframe(seu_link_power_bi, width=1400, height=850, scrolling=True)

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
    try:
        dados_da_planilha = pd.read_csv(url_google_sheets)
        if 'Concluido' in dados_da_planilha.columns:
            dados_da_planilha['Concluido'] = dados_da_planilha['Concluido'].replace({'FALSO': False, 'VERDADEIRO': True})
        st.data_editor(dados_da_planilha, hide_index=True, use_container_width=True, column_config={"Concluido": st.column_config.CheckboxColumn("Concluído?")})
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha.")
