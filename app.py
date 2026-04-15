import streamlit as st
import pandas as pd
import altair as alt

# 1. Configuração da Página
st.set_page_config(page_title="GestorHub", page_icon="🧠", layout="wide")

# ESTILOS VISUAIS (CSS)
st.markdown("""
<style>
    .pulse-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); color: #333333; }
    .pulse-icon { font-size: 20px; margin-bottom: 5px; }
    .pulse-title { font-size: 11px; color: #888888; text-transform: uppercase; font-weight: bold; margin-bottom: 5px;}
    .pulse-value { font-size: 18px; font-weight: bold; }
    .cor-verde { color: #10b981; } .cor-azul { color: #3b82f6; } .cor-cinza { color: #6b7280; } .cor-vermelha { color: #ef4444; }
</style>
""", unsafe_allow_html=True)

# 2. Menu Lateral
with st.sidebar:
    st.title("🧠 GestorHub")
    st.write("Bem-vindo, Gestor!")
    st.divider()
    opcao_escolhida = st.radio("Navegação do Sistema:", ["📊 Dashboard", "📅 Agenda", "🎥 Reuniões", "🎫 Chamados", "⚙️ Day Pulse"])

# ---------------------------------------------------------
# 3. LÓGICA DE TELAS
# ---------------------------------------------------------

if opcao_escolhida == "📊 Dashboard":
    st.title("📊 Visão Geral do Dia")
    st.write("O que você precisa saber hoje para tomar decisões rápidas.")
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Reuniões Hoje", value="4", delta="1 cancelada")
    col2.metric(label="Chamados Críticos", value="2", delta="-3 resolvidos", delta_color="inverse")
    col3.metric(label="Tarefas Pendentes", value="12")
    st.divider()
    st.subheader("⚠️ Requer Atenção Imediata")
    st.warning("**Chamado #1042 em atraso:** Sistema fora do ar na filial Sul.")
    st.info("**Próxima Reunião:** Alinhamento de Produto em 15 minutos.")

elif opcao_escolhida == "📅 Agenda":
    st.title("📅 Sua Agenda")
    st.info("Em breve: Integração com Microsoft Outlook.")

elif opcao_escolhida == "🎥 Reuniões":
    st.title("🎥 Inteligência de Reuniões")
    st.write("Acesse os resumos automáticos gerados pela IA para economizar seu tempo.")
    reuniao_selecionada = st.selectbox("Selecione uma reunião recente:", ["Alinhamento de Produto (Hoje, 10:00)", "Kickoff do Projeto Alpha (Ontem)"])
    st.divider()
    st.subheader(f"📌 {reuniao_selecionada}")
    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.write("**Duração:** 45 minutos")
    col_info2.write("**Participantes:** 5 pessoas")
    col_info3.write("**Status IA:** ✨ Resumo Concluído")
    st.write("")
    aba1, aba2, aba3 = st.tabs(["📝 Resumo da IA", "🎯 Decisões Tomadas", "✅ Tarefas e Pendências"])
    with aba1:
        st.write("### O que foi discutido (TL;DR)")
        st.write("A equipe discutiu os atrasos na entrega da nova funcionalidade do sistema...")
    with aba2:
        st.success("✔️ **Decisão 1:** O prazo de lançamento foi adiado para o dia 15.")
    with aba3:
        st.checkbox("Design: Enviar telas finais para aprovação (Responsável: Ana)")
        st.button("Mover tarefas pendentes para o 'Day Pulse'", type="primary")

# --- NOVA TELA: CHAMADOS (Indicadores e Gráficos) ---
elif opcao_escolhida == "🎫 Chamados":
    st.title("🎫 Central de Chamados")
    st.write("Acompanhe os SLAs e a fila de atendimento da sua equipe.")
    
    # Linha 1: Indicadores rápidos (KPIs) com cores!
    st.markdown("### 🚨 Visão Rápida (SLA)")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(label="Abertos", value="45", delta="5 novos hoje", delta_color="off")
    kpi2.metric(label="Em Andamento", value="18")
    kpi3.metric(label="Resolvidos Hoje", value="12", delta="Acima da média")
    kpi4.metric(label="🚨 Em Atraso", value="3", delta="-2 resolvidos", delta_color="inverse")
    
    st.divider()
    
    # Criando Dados "Fake" para os gráficos
    dados_grafico = pd.DataFrame({
        "Categoria": ["Erro de Sistema", "Dúvida", "Acesso/Senha", "Equipamento", "Outros"],
        "Quantidade": [15, 12, 20, 5, 3]
    })
    
    # Dividindo a tela em duas colunas para os gráficos/tabelas
    col_grafico, col_tabela = st.columns([6, 4]) # 60% pro gráfico, 40% pra tabela
    
    with col_grafico:
        st.markdown("### 📊 Chamados por Categoria")
        # Criando um gráfico de barras bem bonito com Altair
        grafico_barras = alt.Chart(dados_grafico).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("Categoria", sort="-y", title=""),
            y=alt.Y("Quantidade", title="Nº de Chamados"),
            color=alt.condition(
                alt.datum.Quantidade > 15,  # Se tiver mais de 15 chamados, fica vermelho!
                alt.value("#ef4444"),     # Vermelho
                alt.value("#3b82f6")      # Azul normal
            )
        ).properties(height=300)
        
        st.altair_chart(grafico_barras, use_container_width=True)
        
    with col_tabela:
        st.markdown("### 🔥 Top 3 Mais Críticos")
        st.write("Estes chamados estão prestes a romper o SLA e precisam de atenção.")
        
        # Lista simples para foco na ação rápida
        st.error("**#1042** - Sistema de Vendas Fora do Ar (Faltam 10 min)")
        st.warning("**#1055** - Falha na integração de pagamentos (Faltam 45 min)")
        st.warning("**#1061** - Dúvida sobre novo processo de devolução (Faltam 2 horas)")
        
        st.button("Ver fila completa de chamados", use_container_width=True)

elif opcao_escolhida == "⚙️ Day Pulse":
    st.title("💓 Day Pulse")
    st.write("Medição de carga mental e ocupação baseada na sua agenda de hoje.")
    st.write("") 
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.markdown('<div class="pulse-card"><div class="pulse-icon">💓</div><div class="pulse-title">RITMO</div><div class="pulse-value cor-verde">Leve</div></div>', unsafe_allow_html=True)
    with col2: st.markdown('<div class="pulse-card"><div class="pulse-icon">📅</div><div class="pulse-title">EVENTOS</div><div class="pulse-value cor-azul">3</div></div>', unsafe_allow_html=True)
    with col3: st.markdown('<div class="pulse-card"><div class="pulse-icon">🕒</div><div class="pulse-title">OCUPADO</div><div class="pulse-value cor-cinza">2h 30m</div></div>', unsafe_allow_html=True)
    with col4: st.markdown('<div class="pulse-card"><div class="pulse-icon">☀️</div><div class="pulse-title">LIVRE</div><div class="pulse-value cor-verde">5h 30m</div></div>', unsafe_allow_html=True)
    with col5: st.markdown('<div class="pulse-card"><div class="pulse-icon">🏁</div><div class="pulse-title">TÉRMINO</div><div class="pulse-value cor-vermelha">18:00</div></div>', unsafe_allow_html=True)

    st.write("")
    st.write("**Próximo Evento:** Reunião de Alinhamento (Restam 45 min)")
    col_inicio, col_barra, col_fim = st.columns([1, 8, 1])
    with col_inicio: st.write("09:00")
    with col_barra: st.progress(50)
    with col_fim: st.write("19:00")
    st.markdown("<span style='color: #10b981;'>● Dia leve</span>", unsafe_allow_html=True)