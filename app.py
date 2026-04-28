import streamlit as st
import msal
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ==========================================
# 1. CONFIGURACAO
# ==========================================
st.set_page_config(page_title="GestorHub", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. CREDENCIAIS DA MICROSOFT
# ==========================================
CLIENT_ID     = "261febe1-b827-452e-8bc5-e5ae52a6340c"
CLIENT_SECRET = "~pQ8Q~ckiPJbeP~FOA0yTOySNzGCxbVTIfVmLcV_"
AUTHORITY     = "https://login.microsoftonline.com/common"
REDIRECT_URI  = "https://gestor-app.streamlit.app"
SCOPE         = ["User.Read", "Calendars.ReadWrite"]

TZ_SP  = ZoneInfo("America/Sao_Paulo")
TZ_UTC = ZoneInfo("UTC")

def get_msal_app():
    return msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)

def buscar_agenda_microsoft(token, data_alvo):
    """
    Busca eventos do calendário apenas para a data_alvo (fuso America/Sao_Paulo).
    Retorna lista de eventos ordenados por início.
    """
    inicio_sp  = datetime(data_alvo.year, data_alvo.month, data_alvo.day, 0,  0,  0,  tzinfo=TZ_SP)
    fim_sp     = datetime(data_alvo.year, data_alvo.month, data_alvo.day, 23, 59, 59, tzinfo=TZ_SP)
    inicio_utc = inicio_sp.astimezone(TZ_UTC).strftime('%Y-%m-%dT%H:%M:%S')
    fim_utc    = fim_sp.astimezone(TZ_UTC).strftime('%Y-%m-%dT%H:%M:%S')

    url = (
        f"https://graph.microsoft.com/v1.0/me/calendarView"
        f"?startDateTime={inicio_utc}Z&endDateTime={fim_utc}Z"
        f"&$orderby=start/dateTime&$top=50"
    )
    headers = {
        'Authorization': f'Bearer {token}',
        'Prefer': 'outlook.timezone="America/Sao_Paulo"'
    }
    resposta = requests.get(url, headers=headers)
    if resposta.status_code == 200:
        eventos = resposta.json().get('value', [])
        resultado = []
        for ev in eventos:
            dt_inicio = pd.to_datetime(ev['start']['dateTime'])
            if dt_inicio.tzinfo is None:
                dt_inicio = dt_inicio.replace(tzinfo=TZ_SP)
            else:
                dt_inicio = dt_inicio.astimezone(TZ_SP)
            if dt_inicio.date() == data_alvo:
                resultado.append(ev)
        return resultado
    return []

# ==========================================
# 3. CSS GLOBAL
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    .stApp, [data-testid="stAppViewContainer"] { background-color: #F9FAFB !important; }

    header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
    .stAppDeployButton { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Esconde botoes nativos de toggle */
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
    button[data-testid="collapsedControl"]  { display: none !important; }

    /* SIDEBAR PRETA */
    [data-testid="stSidebar"] { background-color: #111827 !important; }
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #F9FAFB !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="select"] > div:focus,
    [data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
        background-color: #1F2937 !important;
        color: #F9FAFB !important;
        border: 1.5px solid #374151 !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] span,
    [data-testid="stSidebar"] div[data-baseweb="select"] div { color: #F9FAFB !important; }
    [data-testid="stSidebar"] div[data-baseweb="select"] svg { fill: #9CA3AF !important; }
    ul[data-baseweb="menu"] { background-color: #1F2937 !important; border: 1px solid #374151 !important; border-radius: 8px !important; }
    ul[data-baseweb="menu"] li { color: #F9FAFB !important; font-family: 'Inter', sans-serif !important; }
    ul[data-baseweb="menu"] li:hover { background-color: #374151 !important; }
    [data-testid="stSidebar"] button {
        background-color: #7F1D1D !important; color: #FEE2E2 !important;
        border: 1px solid #991B1B !important; font-weight: 600 !important; border-radius: 8px !important;
    }
    [data-testid="stSidebar"] button:hover { background-color: #991B1B !important; }

    /* PILL HAMBURGER — fixo no topo, funciona em mobile e desktop */
    #menu-pill {
        position: fixed;
        top: 14px;
        left: 14px;
        z-index: 999999;
        background-color: #111827;
        color: #FFFFFF;
        border: none;
        border-radius: 999px;
        padding: 9px 18px 9px 14px;
        font-size: 16px;
        line-height: 1.2;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 7px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.35);
        font-family: 'Inter', sans-serif;
        transition: background 0.2s, transform 0.12s;
        -webkit-tap-highlight-color: transparent;
        user-select: none;
        touch-action: manipulation;
    }
    #menu-pill:active { transform: scale(0.93); background-color: #374151; }
    #menu-pill .pill-icon { font-size: 17px; line-height: 1; }
    #menu-pill .pill-label { font-size: 13px; font-weight: 700; letter-spacing: 0.03em; }

    /* Espacamento para nao esconder conteudo atras do pill */
    .dashboard-header { margin-top: 68px; margin-bottom: 24px; font-family: 'Inter', sans-serif; }
    .dashboard-header h1 { font-size: 26px; font-weight: 800; color: #111827; margin: 0; }
    .dashboard-header p  { font-size: 14px; color: #6B7280; margin: 4px 0 0 0; }

    /* CARDS */
    .nexuma-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        border: 1px solid #E5E7EB;
        margin-bottom: 18px;
        font-family: 'Inter', sans-serif;
    }

    /* BOTAO PRIMARIO */
    .btn-primary {
        background-color: #111827;
        color: #FFFFFF !important;
        padding: 9px 16px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 13px;
        display: inline-block;
        text-align: center;
        border: none;
        cursor: pointer;
        white-space: nowrap;
        font-family: 'Inter', sans-serif;
    }
    .btn-primary:hover { background-color: #374151; }

    /* DAY PULSE */
    .pulse-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 12px;
        margin-top: 12px;
        font-family: 'Inter', sans-serif;
    }
    .pulse-box {
        background-color: #F9FAFB;
        border-radius: 12px;
        padding: 16px 8px;
        text-align: center;
        border: 1px solid #E5E7EB;
    }
    .p-title { font-size: 10px; color: #6B7280; text-transform: uppercase; font-weight: 700; letter-spacing: 0.6px; }
    .p-val   { font-size: 19px; font-weight: 800; margin-top: 6px; color: #111827; }

    /* POWER BI RESPONSIVO */
    .pbi-wrapper {
        position: relative;
        width: 100%;
        padding-bottom: 62%;   /* razao 16:10 aproximada */
        height: 0;
        overflow: hidden;
        border-radius: 12px;
    }
    .pbi-wrapper iframe {
        position: absolute;
        top: 0; left: 0;
        width: 100% !important;
        height: 100% !important;
        border: none;
    }

    /* DATE PICKER ESTILIZADO */
    [data-testid="stDateInput"] input {
        border-radius: 8px !important;
        border: 1px solid #E5E7EB !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        padding: 8px 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. AUTENTICACAO MSAL
# ==========================================
if "logado_ms" not in st.session_state:
    st.session_state["logado_ms"] = False
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

query_params = st.query_params
if "code" in query_params and not st.session_state["logado_ms"]:
    msal_app = get_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        query_params["code"], scopes=SCOPE, redirect_uri=REDIRECT_URI
    )
    if "access_token" in result:
        st.session_state["access_token"] = result["access_token"]
        st.session_state["logado_ms"] = True
        st.query_params.clear()
        st.rerun()

# TELA DE LOGIN
if not st.session_state["logado_ms"]:
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="nexuma-card" style="text-align:center; padding:50px;">
            <h1 style="color:#111827; font-weight:800; font-size:32px; font-family:'Inter',sans-serif;">GestorHub</h1>
            <p style="color:#6B7280; margin-bottom:40px; font-family:'Inter',sans-serif;">Centro de Comando Executivo</p>
        </div>
        """, unsafe_allow_html=True)
        msal_app = get_msal_app()
        auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.link_button("Entrar com Microsoft 365", auth_url, type="primary", use_container_width=True)
    st.stop()

# ==========================================
# PILL HAMBURGER — so apos login
# ==========================================
st.markdown("""
<button id="menu-pill" onclick="toggleSidebar()">
    <span class="pill-icon">&#9776;</span>
    <span class="pill-label">Menu</span>
</button>
<script>
(function() {
    function toggleSidebar() {
        var doc = window.parent.document;
        // botao collapse (sidebar expandida)
        var c = doc.querySelector('[data-testid="stSidebarCollapseButton"] button');
        // botao expand (sidebar colapsada)
        var e = doc.querySelector('[data-testid="collapsedControl"]');
        if (c) { c.click(); }
        else if (e) { e.click(); }
    }
    // expoe no escopo global do iframe para o onclick funcionar
    window.toggleSidebar = toggleSidebar;
})();
</script>
""", unsafe_allow_html=True)

# ==========================================
# 5. SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="padding:10px 0 20px 0;">
            <h2 style="margin:0; font-weight:800; font-size:22px; color:#FFFFFF; font-family:'Inter',sans-serif;">GestorHub</h2>
        </div>
    """, unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:11px; color:#9CA3AF; margin-bottom:5px; letter-spacing:0.08em; text-transform:uppercase;'>Navegacao</p>",
        unsafe_allow_html=True
    )
    opcao = st.selectbox("nav", ["🏠 Inicio", "📊 Chamados", "🎥 Resumos tl;dv"], label_visibility="collapsed")
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("Sair da Conta", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 6. TELAS
# ==========================================
if opcao == "🏠 Inicio":

    st.markdown("""
    <div class="dashboard-header">
        <h1>Ola, Gestor!</h1>
        <p>Agenda sincronizada com a Microsoft</p>
    </div>
    """, unsafe_allow_html=True)

    # Seletor de data + botao atualizar
    hoje_sp = datetime.now(tz=TZ_SP).date()
    col_data, col_btn = st.columns([3, 1])
    with col_data:
        data_selecionada = st.date_input(
            "Data",
            value=hoje_sp,
            max_value=hoje_sp + timedelta(days=30),
            min_value=hoje_sp - timedelta(days=90),
            label_visibility="collapsed",
            format="DD/MM/YYYY"
        )
    with col_btn:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()

    # Indicador se e hoje ou outra data
    if data_selecionada == hoje_sp:
        label_data = "📅 Hoje"
    else:
        label_data = f"📅 {data_selecionada.strftime('%d/%m/%Y')}"
    st.markdown(
        f"<p style='color:#6B7280; font-size:13px; margin:-8px 0 16px 2px; font-family:Inter,sans-serif;'>{label_data}</p>",
        unsafe_allow_html=True
    )

    # Busca eventos para a data selecionada
    eventos = buscar_agenda_microsoft(st.session_state["access_token"], data_selecionada)
    total_eventos = len(eventos)

    # Cabecalho da agenda
    st.markdown(
        "<h4 style='color:#111827; margin-bottom:12px; font-family:Inter,sans-serif;'>Sua Agenda</h4>",
        unsafe_allow_html=True
    )

    if total_eventos == 0:
        st.markdown("""
        <div class="nexuma-card" style="text-align:center; padding:36px;">
            <span style="font-size:28px;">🎉</span>
            <p style="color:#6B7280; font-size:15px; margin-top:10px; font-family:Inter,sans-serif;">Nenhum evento neste dia.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="nexuma-card">', unsafe_allow_html=True)
        for i, ev in enumerate(eventos):
            hora_ini = pd.to_datetime(ev['start']['dateTime']).strftime("%H:%M")
            hora_fim = pd.to_datetime(ev['end']['dateTime']).strftime("%H:%M")
            titulo   = ev.get('subject', 'Sem titulo')

            link = ""
            if ev.get('onlineMeeting') and ev['onlineMeeting'].get('joinUrl'):
                link = ev['onlineMeeting']['joinUrl']
            elif ev.get('onlineMeetingUrl'):
                link = ev['onlineMeetingUrl']

            botao_html = (
                f'<a href="{link}" target="_blank" class="btn-primary">Entrar</a>'
                if link else
                '<span style="color:#9CA3AF; font-size:12px; font-family:Inter,sans-serif;">Sem link</span>'
            )
            borda = "" if i == len(eventos) - 1 else "border-bottom:1px solid #F3F4F6;"
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:14px 0; {borda} gap:12px; flex-wrap:wrap;">
                <div style="flex:1; min-width:0;">
                    <h4 style="margin:0; font-size:15px; color:#111827; font-family:Inter,sans-serif; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{titulo}</h4>
                    <p style="margin:3px 0 0 0; font-size:13px; color:#6B7280; font-family:Inter,sans-serif;">🕒 {hora_ini} - {hora_fim}</p>
                </div>
                <div style="flex-shrink:0;">{botao_html}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- DAY PULSE — calcula com os eventos da data selecionada ----
    minutos_ocupados = 0
    termino_do_dia   = "--:--"
    if total_eventos > 0:
        for ev in eventos:
            ini = pd.to_datetime(ev['start']['dateTime'])
            fim = pd.to_datetime(ev['end']['dateTime'])
            minutos_ocupados += (fim - ini).total_seconds() / 60
        termino_do_dia = pd.to_datetime(eventos[-1]['end']['dateTime']).strftime("%H:%M")

    horas_ocup    = int(minutos_ocupados // 60)
    min_ocup_rest = int(minutos_ocupados % 60)
    min_livres    = max(0, 480 - minutos_ocupados)

    st.markdown("<h4 style='color:#111827; margin-top:24px; margin-bottom:4px; font-family:Inter,sans-serif;'>Day Pulse</h4>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="nexuma-card">
        <div class="pulse-grid">
            <div class="pulse-box"><div class="p-title">EVENTOS</div><div class="p-val" style="color:#3B82F6;">{total_eventos}</div></div>
            <div class="pulse-box"><div class="p-title">OCUPADO</div><div class="p-val">{horas_ocup}h {min_ocup_rest}m</div></div>
            <div class="pulse-box"><div class="p-title">LIVRE</div><div class="p-val" style="color:#10B981;">{int(min_livres//60)}h {int(min_livres%60)}m</div></div>
            <div class="pulse-box"><div class="p-title">TERMINO</div><div class="p-val" style="color:#EF4444;">{termino_do_dia}</div></div>
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

    # Power BI 100% responsivo via CSS padding-bottom trick
    link_pbi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    st.markdown(f"""
    <div class="nexuma-card" style="padding:12px;">
        <div class="pbi-wrapper">
            <iframe src="{link_pbi}" allowFullScreen="true"></iframe>
        </div>
    </div>
    """, unsafe_allow_html=True)

elif opcao == "🎥 Resumos tl;dv":
    st.markdown("""
    <div class="dashboard-header">
        <h1>Resumos de Reunioes</h1>
        <p>Insights extraidos das reunioes (tl;dv)</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="nexuma-card">
        <h3 style="color:#111827; margin:0; font-family:Inter,sans-serif;">Comite de Mudancas (CAB)</h3>
        <p style="color:#6B7280; font-size:14px; margin-top:4px; font-family:Inter,sans-serif;">Hoje, 10:00 &bull; Duracao: 45m</p>
        <div style="background-color:#F9FAFB; padding:14px; border-radius:8px; margin-top:18px;">
            <p style="color:#111827; font-size:14px; margin:0; font-family:Inter,sans-serif;"><b>📝 Resumo:</b> A equipe aprovou a atualizacao do BD do ERP para este domingo.</p>
        </div>
        <br>
        <a href="#" class="btn-primary">🔗 Assistir Gravacao no tl;dv</a>
    </div>
    """, unsafe_allow_html=True)
