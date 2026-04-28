import streamlit as st
import streamlit.components.v1 as components
import msal
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

st.set_page_config(page_title="GestorHub", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

# ── CREDENCIAIS DA MICROSOFT ──────────────────────────────────────────────────
CLIENT_ID     = "261febe1-b827-452e-8bc5-e5ae52a6340c"
CLIENT_SECRET = "~pQ8Q~ckiPJbeP~FOA0yTOySNzGCxbVTIfVmLcV_"
AUTHORITY     = "https://login.microsoftonline.com/common"
REDIRECT_URI  = "https://gestor-app.streamlit.app"
SCOPE         = ["User.Read", "Calendars.ReadWrite"]
TZ_SP         = ZoneInfo("America/Sao_Paulo")
TZ_UTC        = ZoneInfo("UTC")

def get_msal_app():
    return msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)

def buscar_agenda(token, data_alvo):
    inicio_sp  = datetime(data_alvo.year, data_alvo.month, data_alvo.day, 0,  0,  0,  tzinfo=TZ_SP)
    fim_sp     = datetime(data_alvo.year, data_alvo.month, data_alvo.day, 23, 59, 59, tzinfo=TZ_SP)
    inicio_utc = inicio_sp.astimezone(TZ_UTC).strftime('%Y-%m-%dT%H:%M:%S')
    fim_utc    = fim_sp.astimezone(TZ_UTC).strftime('%Y-%m-%dT%H:%M:%S')
    url = (f"https://graph.microsoft.com/v1.0/me/calendarView"
           f"?startDateTime={inicio_utc}Z&endDateTime={fim_utc}Z&$orderby=start/dateTime&$top=50")
    headers = {'Authorization': f'Bearer {token}',
               'Prefer': 'outlook.timezone="America/Sao_Paulo"'}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return[]
    resultado = []
    for ev in r.json().get('value',[]):
        dt = pd.to_datetime(ev['start']['dateTime'])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_SP)
        else:
            dt = dt.astimezone(TZ_SP)
        if dt.date() == data_alvo:
            resultado.append(ev)
    return resultado

# ── CSS GLOBAL (DESIGN PREMIUM CORRIGIDO) ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

/* Fundo Geral */
.stApp, [data-testid="stAppViewContainer"] { background:#F9FAFB!important; }

/* Esconde Header mas deixa o botão de menu (hambúrguer) visível */
header[data-testid="stHeader"] { background:transparent!important; }
.stAppDeployButton { display:none!important; }
#MainMenu { visibility:hidden; }
footer { visibility:hidden; }

/* Menu da Barra Lateral Premium */
[data-testid="stSidebar"] { background:#111827!important; }
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span { color:#F9FAFB!important; font-family:'Inter',sans-serif!important; }
[data-testid="stSidebar"] div[data-baseweb="select"]>div { background:#1F2937!important; color:#F9FAFB!important; border:1.5px solid #374151!important; border-radius:8px!important; }[data-testid="stSidebar"] div[data-baseweb="select"] svg { fill:#9CA3AF!important; }
ul[data-baseweb="menu"] { background:#1F2937!important; border:1px solid #374151!important; border-radius:8px!important; }
ul[data-baseweb="menu"] li { color:#F9FAFB!important; font-family:'Inter',sans-serif!important; }
ul[data-baseweb="menu"] li:hover { background:#374151!important; }
[data-testid="stSidebar"] button { background:#7F1D1D!important; color:#FEE2E2!important; border:1px solid #991B1B!important; font-weight:600!important; border-radius:8px!important; }
[data-testid="stSidebar"] button:hover { background:#991B1B!important; }

/* Cards e Textos */
.dashboard-header { margin-top:20px; margin-bottom:20px; font-family:'Inter',sans-serif; }
.dashboard-header h1 { font-size:26px; font-weight:800; color:#111827; margin:0; }
.dashboard-header p { font-size:14px; color:#6B7280; margin:4px 0 0; }
.nexuma-card { background:#FFF; border-radius:16px; padding:20px; box-shadow:0 2px 12px rgba(0,0,0,.04); border:1px solid #E5E7EB; margin-bottom:18px; font-family:'Inter',sans-serif; }

/* Botões Nativos Estilizados */
.btn-primary { background:#111827; color:#FFF!important; padding:9px 16px; border-radius:8px; text-decoration:none; font-weight:600; font-size:13px; display:inline-block; text-align:center; border:none; cursor:pointer; white-space:nowrap; font-family:'Inter',sans-serif; }
.btn-primary:hover { background:#374151; }

/* Botão Secundário Nativo do Streamlit (Para o botão de Atualizar e Input de Data) */
div[data-testid="stDateInput"] > div { border-radius: 8px !important; border: 1.5px solid #E5E7EB !important; }
button[kind="secondary"] { border-radius: 8px !important; border: 1px solid #E5E7EB !important; font-weight: 600 !important; color: #111827 !important; background: white !important; }
button[kind="secondary"]:hover { background: #F3F4F6 !important; border: 1px solid #111827 !important; }

/* Day Pulse */
.pulse-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(100px,1fr)); gap:12px; margin-top:12px; }
.pulse-box { background:#F9FAFB; border-radius:12px; padding:16px 8px; text-align:center; border:1px solid #E5E7EB; }
.p-title { font-size:10px; color:#6B7280; text-transform:uppercase; font-weight:700; letter-spacing:.6px; }
.p-val { font-size:19px; font-weight:800; margin-top:6px; color:#111827; }

/* Frame do Power BI */
.pbi-wrapper { position:relative; width:100%; padding-bottom:62%; height:0; overflow:hidden; border-radius:12px; }
.pbi-wrapper iframe { position:absolute; top:0; left:0; width:100%!important; height:100%!important; border:none; }
</style>
""", unsafe_allow_html=True)

# ── AUTENTICAÇÃO E SESSÃO ─────────────────────────────────────────────────────
for k, v in[("logado_ms", False), ("access_token", None), ("data_agenda", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

qp = st.query_params
if "code" in qp and not st.session_state["logado_ms"]:
    app = get_msal_app()
    res = app.acquire_token_by_authorization_code(qp["code"], scopes=SCOPE, redirect_uri=REDIRECT_URI)
    if "access_token" in res:
        st.session_state["access_token"] = res["access_token"]
        st.session_state["logado_ms"] = True
        st.query_params.clear()
        st.rerun()

# ── TELA DE LOGIN ─────────────────────────────────────────────────────────────
if not st.session_state["logado_ms"]:
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div class="nexuma-card" style="text-align:center;padding:50px">
            <h1 style="color:#111827;font-weight:800;font-size:32px;font-family:'Inter',sans-serif">GestorHub</h1>
            <p style="color:#6B7280;margin-bottom:40px;font-family:'Inter',sans-serif">Centro de Comando Executivo</p>
        </div>""", unsafe_allow_html=True)
        auth_url = get_msal_app().get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.link_button("Entrar com Microsoft 365", auth_url, type="primary", use_container_width=True)
    st.stop()

# ── SIDEBAR (MENU SUSPENSO CORRIGIDO) ──────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style="padding:10px 0 20px 0">
        <h2 style="margin:0;font-weight:800;font-size:22px;color:#FFF;font-family:'Inter',sans-serif">GestorHub</h2>
    </div>""", unsafe_allow_html=True)
    st.markdown("<p style='font-size:11px;color:#9CA3AF;margin-bottom:5px;letter-spacing:.08em;text-transform:uppercase'>Navegacao</p>", unsafe_allow_html=True)
    
    opcao = st.selectbox("Menu",["🏠 Inicio", "📊 Chamados", "🎥 Resumos tl;dv"], label_visibility="collapsed")
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("Sair da Conta", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ── TELA: INÍCIO (AGENDA E DAY PULSE) ─────────────────────────────────────────
if opcao == "🏠 Inicio":

    st.markdown("""
    <div class="dashboard-header">
        <h1>Olá, Gestor!</h1>
        <p>Agenda sincronizada com a Microsoft</p>
    </div>""", unsafe_allow_html=True)

    hoje_sp = datetime.now(tz=TZ_SP).date()
    if st.session_state["data_agenda"] is None:
        st.session_state["data_agenda"] = hoje_sp

    # Controles Nativos e Seguros (Sem Hacks de HTML)
    col_data, col_btn = st.columns([7, 3])
    with col_data:
        data_sel = st.date_input("📅 Selecione a Data:", value=st.session_state["data_agenda"])
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()

    # Se mudar a data no calendário, salva e atualiza a página
    if data_sel != st.session_state["data_agenda"]:
        st.session_state["data_agenda"] = data_sel
        st.rerun()

    # ── Renderiza Agenda ──────────────────────────────────────────────────────
    eventos = buscar_agenda(st.session_state["access_token"], data_sel)
    total   = len(eventos)

    st.markdown("<h4 style='color:#111827;margin-top:20px;margin-bottom:12px;font-family:Inter,sans-serif'>Sua Agenda</h4>", unsafe_allow_html=True)

    if total == 0:
        st.markdown("""
        <div class="nexuma-card" style="text-align:center;padding:36px">
            <span style="font-size:28px">🎉</span>
            <p style="color:#6B7280;font-size:15px;margin-top:10px;font-family:Inter,sans-serif">Nenhum evento neste dia.</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="nexuma-card">', unsafe_allow_html=True)
        for i, ev in enumerate(eventos):
            hi = pd.to_datetime(ev['start']['dateTime']).strftime("%H:%M")
            hf = pd.to_datetime(ev['end']['dateTime']).strftime("%H:%M")
            titulo = ev.get('subject', 'Sem titulo')
            link = (ev.get('onlineMeeting') or {}).get('joinUrl') or ev.get('onlineMeetingUrl', '')
            btn  = f'<a href="{link}" target="_blank" class="btn-primary">Entrar</a>' if link else \
                   '<span style="color:#9CA3AF;font-size:12px">Sem link online</span>'
            borda = "" if i == total-1 else "border-bottom:1px solid #F3F4F6;"
            
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:14px 0;{borda}gap:12px;flex-wrap:wrap">
                <div style="flex:1;min-width:0">
                    <h4 style="margin:0;font-size:15px;color:#111827;font-family:Inter,sans-serif;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{titulo}</h4>
                    <p style="margin:3px 0 0;font-size:13px;color:#6B7280;font-family:Inter,sans-serif">🕒 {hi} - {hf}</p>
                </div>
                <div style="flex-shrink:0">{btn}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Day Pulse ─────────────────────────────────────────────────────────────
    mins = 0
    fim_str = "--:--"
    for ev in eventos:
        ini = pd.to_datetime(ev['start']['dateTime'])
        fim = pd.to_datetime(ev['end']['dateTime'])
        mins += (fim - ini).total_seconds() / 60
    if eventos:
        fim_str = pd.to_datetime(eventos[-1]['end']['dateTime']).strftime("%H:%M")
    
    h = int(mins//60)
    m = int(mins%60)
    liv = max(0, 480-mins)

    st.markdown("<h4 style='color:#111827;margin-top:24px;margin-bottom:4px;font-family:Inter,sans-serif'>Day Pulse</h4>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="nexuma-card">
      <div class="pulse-grid">
        <div class="pulse-box"><div class="p-title">EVENTOS</div><div class="p-val" style="color:#3B82F6">{total}</div></div>
        <div class="pulse-box"><div class="p-title">OCUPADO</div><div class="p-val">{h}h {m}m</div></div>
        <div class="pulse-box"><div class="p-title">LIVRE</div><div class="p-val" style="color:#10B981">{int(liv//60)}h {int(liv%60)}m</div></div>
        <div class="pulse-box"><div class="p-title">TÉRMINO</div><div class="p-val" style="color:#EF4444">{fim_str}</div></div>
      </div>
    </div>""", unsafe_allow_html=True)

# ── TELA: CHAMADOS ────────────────────────────────────────────────────────────
elif opcao == "📊 Chamados":
    st.markdown("""
    <div class="dashboard-header">
        <h1>Chamados</h1>
        <p>Acompanhamento de SLAs em tempo real</p>
    </div>""", unsafe_allow_html=True)
    link_pbi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    st.markdown(f"""
    <div class="nexuma-card" style="padding:12px">
        <div class="pbi-wrapper">
            <iframe src="{link_pbi}" allowFullScreen="true"></iframe>
        </div>
    </div>""", unsafe_allow_html=True)

# ── TELA: RESUMOS ─────────────────────────────────────────────────────────────
elif opcao == "🎥 Resumos tl;dv":
    st.markdown("""
    <div class="dashboard-header">
        <h1>Resumos de Reuniões</h1>
        <p>Insights extraídos das reuniões (tl;dv)</p>
    </div>""", unsafe_allow_html=True)
    st.markdown("""
    <div class="nexuma-card">
        <h3 style="color:#111827;margin:0;font-family:Inter,sans-serif">Comitê de Mudanças (CAB)</h3>
        <p style="color:#6B7280;font-size:14px;margin-top:4px;font-family:Inter,sans-serif">Hoje, 10:00 &bull; Duração: 45m</p>
        <div style="background:#F9FAFB;padding:14px;border-radius:8px;margin-top:18px">
            <p style="color:#111827;font-size:14px;margin:0;font-family:Inter,sans-serif"><b>📝 Resumo:</b> A equipe aprovou a atualização do BD do ERP para este domingo.</p>
        </div>
        <br>
        <a href="#" class="btn-primary">🔗 Assistir Gravação no tl;dv</a>
    </div>""", unsafe_allow_html=True)
