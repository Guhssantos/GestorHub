import streamlit as st
import streamlit.components.v1 as components
import msal
import requests
import pandas as pd
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="GestorHub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CONSTANTES ────────────────────────────────────────────────────────────────
CLIENT_ID     = "261febe1-b827-452e-8bc5-e5ae52a6340c"
CLIENT_SECRET = "~pQ8Q~ckiPJbeP~FOA0yTOySNzGCxbVTIfVmLcV_"
AUTHORITY     = "https://login.microsoftonline.com/common"
REDIRECT_URI  = "https://gestor-app.streamlit.app"
SCOPE         = ["User.Read", "Calendars.ReadWrite"]
TZ_SP         = ZoneInfo("America/Sao_Paulo")
TZ_UTC        = ZoneInfo("UTC")

# ── FUNÇÕES ───────────────────────────────────────────────────────────────────
def get_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )

def buscar_agenda(token, data_alvo):
    inicio_sp  = datetime(data_alvo.year, data_alvo.month, data_alvo.day,  0,  0,  0, tzinfo=TZ_SP)
    fim_sp     = datetime(data_alvo.year, data_alvo.month, data_alvo.day, 23, 59, 59, tzinfo=TZ_SP)
    ini_utc    = inicio_sp.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S")
    fim_utc    = fim_sp.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S")
    url = (
        "https://graph.microsoft.com/v1.0/me/calendarView"
        f"?startDateTime={ini_utc}Z&endDateTime={fim_utc}Z"
        "&$orderby=start/dateTime&$top=50"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Prefer": 'outlook.timezone="America/Sao_Paulo"',
    }
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []
    resultado = []
    for ev in r.json().get("value", []):
        dt = pd.to_datetime(ev["start"]["dateTime"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_SP)
        else:
            dt = dt.astimezone(TZ_SP)
        if dt.date() == data_alvo:
            resultado.append(ev)
    return resultado

# ── CSS GLOBAL ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

.stApp, [data-testid="stAppViewContainer"] { background: #F9FAFB !important; }
header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
.stAppDeployButton { display: none !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

[data-testid="stSidebarCollapseButton"] { display: none !important; }
button[data-testid="collapsedControl"]  { display: none !important; }

[data-testid="stSidebar"] { background: #111827 !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color: #F9FAFB !important; font-family: 'Inter', sans-serif !important; }

[data-testid="stSidebar"] div[data-baseweb="select"] > div { background: #1F2937 !important; color: #F9FAFB !important; border: 1.5px solid #374151 !important; border-radius: 8px !important; }
[data-testid="stSidebar"] div[data-baseweb="select"] span,
[data-testid="stSidebar"] div[data-baseweb="select"] div { color: #F9FAFB !important; }
[data-testid="stSidebar"] div[data-baseweb="select"] svg { fill: #9CA3AF !important; }
ul[data-baseweb="menu"] { background: #1F2937 !important; border: 1px solid #374151 !important; border-radius: 8px !important; }
ul[data-baseweb="menu"] li { color: #F9FAFB !important; font-family: 'Inter', sans-serif !important; }
ul[data-baseweb="menu"] li:hover { background: #374151 !important; }
[data-testid="stSidebar"] button { background: #7F1D1D !important; color: #FEE2E2 !important; border: 1px solid #991B1B !important; font-weight: 600 !important; border-radius: 8px !important; }
[data-testid="stSidebar"] button:hover { background: #991B1B !important; }

.dashboard-header { margin-top: 10px; margin-bottom: 20px; font-family: 'Inter', sans-serif; }
.dashboard-header h1 { font-size: 26px; font-weight: 800; color: #111827; margin: 0; }
.dashboard-header p  { font-size: 14px; color: #6B7280; margin: 4px 0 0; }

.nexuma-card {
    background: #FFF; border-radius: 16px; padding: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,.04); border: 1px solid #E5E7EB;
    margin-bottom: 18px; font-family: 'Inter', sans-serif;
}
.btn-primary {
    background: #111827; color: #FFF !important; padding: 9px 16px;
    border-radius: 8px; text-decoration: none; font-weight: 600;
    font-size: 13px; display: inline-block; text-align: center;
    border: none; cursor: pointer; white-space: nowrap; font-family: 'Inter', sans-serif;
}
.btn-primary:hover { background: #374151; }

.pulse-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 12px; margin-top: 12px; font-family: 'Inter', sans-serif;
}
.pulse-box { background: #F9FAFB; border-radius: 12px; padding: 16px 8px; text-align: center; border: 1px solid #E5E7EB; }
.p-title { font-size: 10px; color: #6B7280; text-transform: uppercase; font-weight: 700; letter-spacing: .6px; }
.p-val   { font-size: 19px; font-weight: 800; margin-top: 6px; color: #111827; }

.pbi-wrapper { position: relative; width: 100%; padding-bottom: 62%; height: 0; overflow: hidden; border-radius: 12px; }
.pbi-wrapper iframe { position: absolute; top: 0; left: 0; width: 100% !important; height: 100% !important; border: none; }

div[data-testid="stDateInput"] { position: absolute !important; opacity: 0 !important; pointer-events: none !important; height: 0 !important; overflow: hidden !important; }

/* Permite que o iframe do componente extravase para mostrar o popup do calendario */
iframe[title="streamlit_components.html"] { overflow: visible !important; }
[data-testid="stCustomComponentV1"] { overflow: visible !important; }
.element-container:has(iframe) { overflow: visible !important; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k, v in [("logado_ms", False), ("access_token", None), ("data_agenda", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── AUTENTICAÇÃO ──────────────────────────────────────────────────────────────
qp = st.query_params
if "code" in qp and not st.session_state["logado_ms"]:
    app = get_msal_app()
    res = app.acquire_token_by_authorization_code(
        qp["code"], scopes=SCOPE, redirect_uri=REDIRECT_URI
    )
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
        <div class="nexuma-card" style="text-align:center; padding:50px;">
            <h1 style="color:#111827; font-weight:800; font-size:32px; font-family:'Inter',sans-serif;">GestorHub</h1>
            <p style="color:#6B7280; margin-bottom:40px; font-family:'Inter',sans-serif;">Centro de Comando Executivo</p>
        </div>
        """, unsafe_allow_html=True)
        auth_url = get_msal_app().get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.link_button("Entrar com Microsoft 365", auth_url, type="primary", use_container_width=True)
    st.stop()

# ── BOTÃO MENU FLUTUANTE ──────────────────────────────────────────────────────
components.html("""
<style>
#pill {
    position: fixed; top: 14px; left: 14px; z-index: 999999;
    background: #111827; color: #FFF; border: none; border-radius: 999px;
    padding: 9px 18px 9px 14px; font-size: 16px; line-height: 1;
    cursor: pointer; display: flex; align-items: center; gap: 7px;
    box-shadow: 0 4px 20px rgba(0,0,0,.35); font-family: 'Inter', sans-serif;
    -webkit-tap-highlight-color: transparent; touch-action: manipulation;
    transition: transform .12s, background .15s;
}
#pill:active { transform: scale(.93); background: #374151; }
</style>
<button id="pill" onclick="toggleMenu()">
    &#9776;&nbsp;<b style="font-size:13px; letter-spacing:.03em;">Menu</b>
</button>
<script>
function toggleMenu() {
    var docs = [];
    try { docs.push(window.parent.document); } catch(e) {}
    try { if (window.top !== window.parent) docs.push(window.top.document); } catch(e) {}
    for (var i = 0; i < docs.length; i++) {
        var d = docs[i];
        var c = d.querySelector('[data-testid="stSidebarCollapseButton"] button');
        var e = d.querySelector('[data-testid="collapsedControl"]');
        if (c) { c.click(); return; }
        if (e) { e.click(); return; }
    }
}
</script>
""", height=55, scrolling=False)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:10px 0 20px 0;">
        <h2 style="margin:0; font-weight:800; font-size:22px; color:#FFF; font-family:'Inter',sans-serif;">GestorHub</h2>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:11px; color:#9CA3AF; margin-bottom:5px; letter-spacing:.08em; text-transform:uppercase;'>Navegacao</p>",
        unsafe_allow_html=True
    )
    opcao = st.selectbox(
        "nav",
        ["🏠 Inicio", "📊 Chamados", "🎥 Resumos tl;dv"],
        label_visibility="collapsed"
    )
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("Sair da Conta", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ── TELA: INÍCIO ──────────────────────────────────────────────────────────────
if opcao == "🏠 Inicio":

    st.markdown("""
    <div class="dashboard-header">
        <h1>Ola, Gestor!</h1>
        <p>Agenda sincronizada com a Microsoft</p>
    </div>
    """, unsafe_allow_html=True)

    hoje_sp = datetime.now(tz=TZ_SP).date()
    if st.session_state["data_agenda"] is None:
        st.session_state["data_agenda"] = hoje_sp
    data_sel = st.session_state["data_agenda"]

    MESES_S = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    label_exib = "Hoje" if data_sel == hoje_sp else f"{data_sel.day} {MESES_S[data_sel.month-1]} {data_sel.year}"
    hoje_iso = hoje_sp.isoformat()
    sel_iso  = data_sel.isoformat()

    # date_input oculto — o JS do calendário o aciona para mudar a data
    data_input = st.date_input(
        "data_oculta",
        value=data_sel,
        key="date_picker_hidden",
        label_visibility="collapsed"
    )
    if data_input != data_sel:
        st.session_state["data_agenda"] = data_input
        st.rerun()

    # ── CALENDÁRIO VISUAL ─────────────────────────────────────────────────────
    # Renderizado via st.markdown no DOM principal (sem iframe),
    # assim o popup não fica cortado e o sync não navega para fora.
    st.markdown(f"""
<div id="cal-bar" style="display:flex;align-items:center;gap:10px;margin-bottom:20px;position:relative;">

  <div id="cal-toggle" onclick="ghToggleCal()" style="
      background:#FFF;border:1.5px solid #E5E7EB;border-radius:50px;
      padding:8px 16px 8px 12px;display:flex;align-items:center;gap:8px;
      cursor:pointer;font-size:14px;font-weight:600;color:#111827;
      box-shadow:0 1px 6px rgba(0,0,0,.08);user-select:none;
      -webkit-tap-highlight-color:transparent;touch-action:manipulation;">
    <svg width="16" height="16" fill="none" stroke="#111827" stroke-width="2.2"
         stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
      <rect x="3" y="4" width="18" height="18" rx="3"/>
      <line x1="16" y1="2" x2="16" y2="6"/>
      <line x1="8"  y1="2" x2="8"  y2="6"/>
      <line x1="3"  y1="10" x2="21" y2="10"/>
    </svg>
    <span id="gh-lbl">{label_exib}</span>
  </div>

  <button onclick="ghSync()" title="Sincronizar" style="
      width:36px;height:36px;border-radius:50%;background:#F3F4F6;
      border:1.5px solid #E5E7EB;cursor:pointer;font-size:17px;
      display:flex;align-items:center;justify-content:center;
      -webkit-tap-highlight-color:transparent;touch-action:manipulation;
      transition:background .15s;" id="gh-sync">&#x21bb;</button>

  <div id="gh-popup" style="
      display:none;position:absolute;top:48px;left:0;z-index:99999;
      background:#FFF;border-radius:16px;width:280px;padding:18px 16px;
      box-shadow:0 8px 40px rgba(0,0,0,.18);border:1px solid #E5E7EB;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
      <button onclick="ghChgMonth(-1)" style="background:none;border:none;cursor:pointer;font-size:22px;color:#6B7280;padding:2px 10px;border-radius:8px;line-height:1;">&#8249;</button>
      <span id="gh-mlbl" style="font-size:15px;font-weight:700;color:#111827;font-family:Inter,sans-serif;"></span>
      <button onclick="ghChgMonth(1)"  style="background:none;border:none;cursor:pointer;font-size:22px;color:#6B7280;padding:2px 10px;border-radius:8px;line-height:1;">&#8250;</button>
    </div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center;" id="gh-dows">
      <div style="font-size:10px;font-weight:700;color:#9CA3AF;padding:4px 0;">D</div>
      <div style="font-size:10px;font-weight:700;color:#9CA3AF;padding:4px 0;">S</div>
      <div style="font-size:10px;font-weight:700;color:#9CA3AF;padding:4px 0;">T</div>
      <div style="font-size:10px;font-weight:700;color:#9CA3AF;padding:4px 0;">Q</div>
      <div style="font-size:10px;font-weight:700;color:#9CA3AF;padding:4px 0;">Q</div>
      <div style="font-size:10px;font-weight:700;color:#9CA3AF;padding:4px 0;">S</div>
      <div style="font-size:10px;font-weight:700;color:#9CA3AF;padding:4px 0;">S</div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;" id="gh-days"></div>
  </div>
</div>

<script>
(function(){{
  var MESES   = ["Janeiro","Fevereiro","Marco","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
  var MESES_S = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
  var hoje    = new Date("{hoje_iso}T12:00:00");
  var sel     = new Date("{sel_iso}T12:00:00");
  var cur     = new Date(sel.getFullYear(), sel.getMonth(), 1);
  var open    = false;

  function pad(n){{ return n<10?"0"+n:n; }}
  function iso(d){{ return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate()); }}

  function render(){{
    var y=cur.getFullYear(), m=cur.getMonth();
    document.getElementById("gh-mlbl").textContent = MESES[m]+" "+y;
    var g=document.getElementById("gh-days");
    g.innerHTML="";
    var first=new Date(y,m,1).getDay();
    var days =new Date(y,m+1,0).getDate();
    var prev =new Date(y,m,0).getDate();
    for(var i=0;i<first;i++) addDay(g,prev-first+1+i,true,null);
    for(var d=1;d<=days;d++){{
      var dt=new Date(y,m,d);
      addDay(g,d,false,dt,iso(dt)===iso(hoje),iso(dt)===iso(sel));
    }}
    var rem=(first+days)%7;
    if(rem) for(var i=1;i<=7-rem;i++) addDay(g,i,true,null);
  }}

  function addDay(g,txt,out,dt,isT,isS){{
    var b=document.createElement("div");
    var base="font-size:13px;font-weight:500;padding:7px 2px;border-radius:8px;text-align:center;cursor:pointer;";
    if(out)   b.style.cssText=base+"color:#D1D5DB;pointer-events:none;";
    else if(isS) b.style.cssText=base+"background:#111827;color:#FFF;border-radius:50%;font-weight:700;";
    else if(isT) b.style.cssText=base+"border:2px solid #111827;border-radius:50%;font-weight:700;color:#111827;";
    else         b.style.cssText=base+"color:#111827;";
    b.textContent=txt;
    if(dt){{
      (function(d){{
        b.onmouseenter=function(){{if(!isS&&!isT)b.style.background="#F3F4F6";}};
        b.onmouseleave=function(){{if(!isS&&!isT)b.style.background="";}};
        b.onclick=function(){{pick(d);}};
      }})(dt);
    }}
    g.appendChild(b);
  }}

  function pick(dt){{
    sel=dt;
    var s=iso(dt);
    var label=(s===iso(hoje))?"Hoje":dt.getDate()+" "+MESES_S[dt.getMonth()]+" "+dt.getFullYear();
    document.getElementById("gh-lbl").textContent=label;
    ghCloseCal();
    // Atualiza o date_input oculto do Streamlit
    var inp=document.querySelector('[data-testid="stDateInput"] input');
    if(inp){{
      var parts=s.split("-");
      var fmt=parts[2]+"/"+parts[1]+"/"+parts[0];
      var setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,"value");
      setter.set.call(inp,fmt);
      inp.dispatchEvent(new Event("input",{{bubbles:true}}));
      inp.dispatchEvent(new Event("change",{{bubbles:true}}));
    }}
  }}

  window.ghToggleCal=function(){{
    open=!open;
    document.getElementById("gh-popup").style.display=open?"block":"none";
    if(open){{cur=new Date(sel.getFullYear(),sel.getMonth(),1);render();}}
  }};
  window.ghChgMonth=function(d){{cur.setMonth(cur.getMonth()+d);render();}};
  window.ghCloseCal=function(){{open=false;document.getElementById("gh-popup").style.display="none";}};
  window.ghSync=function(){{
    var btn=document.getElementById("gh-sync");
    btn.style.transform="rotate(360deg)";
    btn.style.transition="transform 0.5s";
    setTimeout(function(){{btn.style.transform="";btn.style.transition="";}},500);
    // Força rerun do Streamlit re-disparando o date input sem mudar valor
    var inp=document.querySelector('[data-testid="stDateInput"] input');
    if(inp){{
      inp.dispatchEvent(new Event("input",{{bubbles:true}}));
      inp.dispatchEvent(new Event("change",{{bubbles:true}}));
    }}
  }};

  // Fecha ao clicar fora
  document.addEventListener("click",function(e){{
    var p=document.getElementById("gh-popup");
    var t=document.getElementById("cal-toggle");
    if(p&&t&&open&&!p.contains(e.target)&&!t.contains(e.target)) ghCloseCal();
  }});

  render();
}})();
</script>
""", unsafe_allow_html=True)

    # ── AGENDA ────────────────────────────────────────────────────────────────
    eventos = buscar_agenda(st.session_state["access_token"], data_sel)
    total   = len(eventos)

    st.markdown(
        "<h4 style='color:#111827; margin-bottom:12px; font-family:Inter,sans-serif;'>Sua Agenda</h4>",
        unsafe_allow_html=True
    )

    if total == 0:
        st.markdown("""
        <div class="nexuma-card" style="text-align:center; padding:36px;">
            <span style="font-size:28px;">🎉</span>
            <p style="color:#6B7280; font-size:15px; margin-top:10px; font-family:Inter,sans-serif;">Nenhum evento neste dia.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="nexuma-card">', unsafe_allow_html=True)
        for i, ev in enumerate(eventos):
            hi    = pd.to_datetime(ev["start"]["dateTime"]).strftime("%H:%M")
            hf    = pd.to_datetime(ev["end"]["dateTime"]).strftime("%H:%M")
            titulo = ev.get("subject", "Sem titulo")
            link  = (ev.get("onlineMeeting") or {}).get("joinUrl") or ev.get("onlineMeetingUrl", "")
            btn   = f'<a href="{link}" target="_blank" class="btn-primary">Entrar</a>' if link else \
                    '<span style="color:#9CA3AF; font-size:12px;">Sem link</span>'
            borda = "" if i == total - 1 else "border-bottom: 1px solid #F3F4F6;"
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:14px 0; {borda} gap:12px; flex-wrap:wrap;">
                <div style="flex:1; min-width:0;">
                    <h4 style="margin:0; font-size:15px; color:#111827; font-family:Inter,sans-serif; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{titulo}</h4>
                    <p style="margin:3px 0 0; font-size:13px; color:#6B7280; font-family:Inter,sans-serif;">🕒 {hi} - {hf}</p>
                </div>
                <div style="flex-shrink:0;">{btn}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── DAY PULSE ─────────────────────────────────────────────────────────────
    mins    = 0
    fim_str = "--:--"
    for ev in eventos:
        mins += (
            pd.to_datetime(ev["end"]["dateTime"]) - pd.to_datetime(ev["start"]["dateTime"])
        ).total_seconds() / 60
    if eventos:
        fim_str = pd.to_datetime(eventos[-1]["end"]["dateTime"]).strftime("%H:%M")
    h   = int(mins // 60)
    m   = int(mins % 60)
    liv = max(0, 480 - mins)

    st.markdown(
        "<h4 style='color:#111827; margin-top:24px; margin-bottom:4px; font-family:Inter,sans-serif;'>Day Pulse</h4>",
        unsafe_allow_html=True
    )
    st.markdown(f"""
    <div class="nexuma-card">
        <div class="pulse-grid">
            <div class="pulse-box"><div class="p-title">EVENTOS</div><div class="p-val" style="color:#3B82F6;">{total}</div></div>
            <div class="pulse-box"><div class="p-title">OCUPADO</div><div class="p-val">{h}h {m}m</div></div>
            <div class="pulse-box"><div class="p-title">LIVRE</div><div class="p-val" style="color:#10B981;">{int(liv//60)}h {int(liv%60)}m</div></div>
            <div class="pulse-box"><div class="p-title">TERMINO</div><div class="p-val" style="color:#EF4444;">{fim_str}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── TELA: CHAMADOS ────────────────────────────────────────────────────────────
elif opcao == "📊 Chamados":
    st.markdown("""
    <div class="dashboard-header">
        <h1>Chamados</h1>
        <p>Acompanhamento de SLAs em tempo real</p>
    </div>
    """, unsafe_allow_html=True)
    link_pbi = "https://app.powerbi.com/reportEmbed?reportId=15bea8e3-da1f-403a-a495-4f459f849c93&autoAuth=true&ctid=a94d3a29-8a64-40c2-966f-e9001602ae14"
    st.markdown(f"""
    <div class="nexuma-card" style="padding:12px;">
        <div class="pbi-wrapper">
            <iframe src="{link_pbi}" allowFullScreen="true"></iframe>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── TELA: RESUMOS ─────────────────────────────────────────────────────────────
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
        <div style="background:#F9FAFB; padding:14px; border-radius:8px; margin-top:18px;">
            <p style="color:#111827; font-size:14px; margin:0; font-family:Inter,sans-serif;"><b>📝 Resumo:</b> A equipe aprovou a atualizacao do BD do ERP para este domingo.</p>
        </div>
        <br>
        <a href="#" class="btn-primary">🔗 Assistir Gravacao no tl;dv</a>
    </div>
    """, unsafe_allow_html=True)
