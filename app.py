import streamlit as st
import msal
import requests
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="GestorHub", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

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
    resposta = requests.get(url, headers=headers)
    if resposta.status_code == 200:
        return resposta.json().get('value', [])
    return []

# ==========================================
# 3. CSS + BOTAO HAMBURGER FLUTUANTE
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    .stApp, [data-testid="stAppViewContainer"] { background-color: #F9FAFB !important; }

    header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
    .stAppDeployButton { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Esconde AMBOS os botoes nativos de toggle da sidebar */
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
        background-color: #7F1D1D !important;
        color: #FEE2E2 !important;
        border: 1px solid #991B1B !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] button:hover { background-color: #991B1B !important; }

    /* PILL HAMBURGER FLUTUANTE */
    #menu-pill {
        position: fixed;
        top: 16px;
        left: 16px;
        z-index: 99999;
        background-color: #111827;
        color: #FFFFFF;
        border: none;
        border-radius: 50px;
        padding: 10px 20px;
        font-size: 18px;
        line-height: 1;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.30);
        font-family: 'Inter', sans-serif;
        transition: background 0.2s, transform 0.1s;
        -webkit-tap-highlight-color: transparent;
        user-select: none;
    }
    #menu-pill:active { transform: scale(0.96); }
    #menu-pill .pill-label { font-size: 14px; font-weight: 700; letter-spacing: 0.02em; }

    /* Empurra o conteudo para nao ficar atras do pill */
    .dashboard-header { margin-top: 64px; margin-bottom: 30px; font-family: 'Inter', sans-serif; }
    .dashboard-header h1 { font-size: 28px; font-weight: 800; color: #111827; margin: 0; }
    .dashboard-header p { font-size: 15px; color: #6B7280; margin: 4px 0 0 0; }

    .nexuma-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid #E5E7EB;
        margin-bottom: 20px;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    .btn-primary {
        background-color: #111827;
        color: #FFFFFF !important;
        padding: 10px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
        text-align: center;
        border: none;
        cursor: pointer;
        white-space: nowrap;
        font-family: 'Inter', sans-serif;
    }
    .btn-primary:hover { background-color: #374151; }

    .pulse-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 15px;
        margin-top: 15px;
        font-family: 'Inter', sans-serif;
    }
    .pulse-box {
        background-color: #F9FAFB;
        border-radius: 12px;
        padding: 20px 10px;
        text-align: center;
        border: 1px solid #E5E7EB;
    }
    .p-title { font-size: 11px; color: #6B7280; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; }
    .p-val { font-size: 20px; font-weight: 800; margin-top: 8px; color: #111827; }
</style>

<!-- PILL HAMBURGER -->
<button id="menu-pill" onclick="toggleSidebar()">
    &#9776; <span class="pill-label">Menu</span>
</button>

<script>
function toggleSidebar() {
    var doc = window.parent.document;

    // Tenta o botao de colapso (sidebar aberta)
    var btnCollapse = doc.querySelector('[data-testid="stSidebarCollapseButton"] button');
    // Tenta o botao de expandir (sidebar fechada)
    var btnExpand = doc.querySelector('[data-testid="collapsedControl"]');

    if (btnCollapse) {
        btnCollapse.click();
    } else if (btnExpand) {
        btnExpand.click();
    }
}
</script>
""", unsafe_allow_html=True)

# ==========================================
# 4. AUTENTICACAO REAL MSAL
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

if not st.session_state["logado_ms"]:
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="nexuma-card" style="text-align: center; padding: 50px;">
            <h1 style="color: #111827; font-weight: 800; font-size: 32px; font-family: 'Inter', sans-serif;">GestorHub</h1>
            <p style="color: #6B7280; margin-bottom: 40px; font-family: 'Inter', sans-serif;">Centro de Comando Executivo</p>
        </div>
        """, unsafe_allow_html=True)
        msal_app = get_msal_app()
        auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.link_button("Entrar com Microsoft 365", auth_url, type="primary", use_container_width=True)
    st.stop()

# ==========================================
# 5. PROCESSAMENTO DE DADOS
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
minutos_livres = max(0, 480 - minutos_ocupados)

# ==========================================
# 6. SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="padding: 10px 0 20px 0;">
            <h2 style="margin:0; font-weight:800; font-size:24px; color:#FFFFFF; font-family: 'Inter', sans-serif;">GestorHub</h2>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:12px; color:#9CA3AF; margin-bottom:5px; letter-spacing:0.08em; text-transform:uppercase; font-family: Inter, sans-serif;'>Navegacao</p>",
        unsafe_allow_html=True
    )
    opcao = st.selectbox(
        "Navegacao",
        ["🏠 Inicio", "📊 Chamados", "🎥 Resumos tl;dv"],
        label_visibility="collapsed"
    )

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("Sair da Conta", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 7. TELAS
# ==========================================
if opcao == "🏠 Inicio":

    st.markdown("""
    <div class="dashboard-header">
        <h1>Ola, Gestor!</h1>
        <p>Visao geral da sua agenda sincronizada com a Microsoft</p>
    </div>
    """, unsafe_allow_html=True)

    col_titulo, col_botao = st.columns([8, 2])
    with col_titulo:
        st.markdown(
            "<h4 style='color:#111827; margin-bottom:15px; font-family: Inter, sans-serif;'>Sua Agenda Hoje</h4>",
            unsafe_allow_html=True
        )
    with col_botao:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()

    if total_eventos == 0:
        st.markdown("""
        <div class="nexuma-card" style="text-align: center; padding: 40px;">
            <span style="font-size: 30px;">🎉</span>
            <p style="color: #6B7280; font-size: 16px; margin-top: 10px; font-family: Inter, sans-serif;">Sua agenda esta livre hoje.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="nexuma-card">', unsafe_allow_html=True)
        for i, ev in enumerate(eventos_hoje):
            hora_ini = pd.to_datetime(ev['start']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            hora_fim = pd.to_datetime(ev['end']['dateTime']).replace(tzinfo=None).strftime("%H:%M")
            titulo = ev.get('subject', 'Sem titulo')

            link = ""
            if ev.get('onlineMeeting') and ev['onlineMeeting'].get('joinUrl'):
                link = ev['onlineMeeting']['joinUrl']
            elif ev.get('onlineMeetingUrl'):
                link = ev['onlineMeetingUrl']

            botao_html = f'<a href="{link}" target="_blank" class="btn-primary">Entrar na Reuniao</a>' if link else \
                         '<span style="color:#9CA3AF; font-size:13px; font-family: Inter, sans-serif;">Sem link online</span>'

            borda = "" if i == len(eventos_hoje) - 1 else "border-bottom: 1px solid #F3F4F6;"
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:16px 0; {borda} gap:16px;">
                <div style="flex:1;">
                    <h4 style="margin:0; font-size:16px; color:#111827; font-family:Inter,sans-serif;">{titulo}</h4>
                    <p style="margin:4px 0 0 0; font-size:14px; color:#6B7280; font-family:Inter,sans-serif;">🕒 {hora_ini} - {hora_fim}</p>
                </div>
                <div>{botao_html}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<h4 style='color:#111827; margin-top:30px; margin-bottom:5px; font-family: Inter, sans-serif;'>Day Pulse</h4>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="nexuma-card">
        <div class="pulse-grid">
            <div class="pulse-box"><div class="p-title">EVENTOS</div><div class="p-val" style="color:#3B82F6;">{total_eventos}</div></div>
            <div class="pulse-box"><div class="p-title">OCUPADO</div><div class="p-val">{horas_ocupadas}h {min_ocupados_rest}m</div></div>
            <div class="pulse-box"><div class="p-title">LIVRE</div><div class="p-val" style="color:#10B981;">{int(minutos_livres // 60)}h {int(minutos_livres % 60)}m</div></div>
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
    st.markdown('<div class="nexuma-card" style="padding: 10px;">', unsafe_allow_html=True)
    link_pbi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    st.components.v1.iframe(link_pbi, width=1400, height=800, scrolling=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif opcao == "🎥 Resumos tl;dv":
    st.markdown("""
    <div class="dashboard-header">
        <h1>Resumos de Reunioes</h1>
        <p>Insights extraidos das reunioes (tl;dv)</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="nexuma-card">
        <h3 style="color:#111827; margin:0; font-family: Inter, sans-serif;">Comite de Mudancas (CAB)</h3>
        <p style="color:#6B7280; font-size:14px; margin-top:4px; font-family: Inter, sans-serif;">Hoje, 10:00 &bull; Duracao: 45m</p>
        <div style="background-color:#F9FAFB; padding:15px; border-radius:8px; margin-top:20px;">
            <p style="color:#111827; font-size:14px; margin:0; font-family: Inter, sans-serif;"><b>📝 Resumo:</b> A equipe aprovou a atualizacao do BD do ERP para este domingo.</p>
        </div>
        <br>
        <a href="#" class="btn-primary" style="width: auto;">🔗 Assistir Gravacao no tl;dv</a>
    </div>
    """, unsafe_allow_html=True)
