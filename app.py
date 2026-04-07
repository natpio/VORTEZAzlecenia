import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# --- KONFIGURACJA STRONY (ULTIMATE ENTERPRISE) ---
st.set_page_config(
    page_title="Vortex TMS | Ultimate",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="collapsed" # Zwinięty pasek boczny dla maksymalnego efektu WOW na start
)

# --- WSTRZYKNIĘCIE CSS ZA 1 MILION EURO (DARK GLASSMORPHISM) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;700;900&display=swap');
        
        /* Główne tło aplikacji - Głęboki, luksusowy ciemny motyw */
        .stApp {
            background: radial-gradient(circle at 50% 0%, #1e293b 0%, #020617 100%);
            color: #f8fafc;
            font-family: 'Outfit', sans-serif;
        }
        
        /* Ukrycie domyślnych śmieci Streamlita */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Marginesy i szerokość kontenera */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 4rem;
            max-width: 1700px;
        }

        /* Szklane Karty (Glassmorphism) */
        div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"], 
        div.stMetric {
            background: rgba(30, 41, 59, 0.4) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 20px !important;
            padding: 1.5rem !important;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        }
        
        div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"]:hover {
            transform: translateY(-5px);
            box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.7), 0 0 20px rgba(56, 189, 248, 0.1) !important;
            border-color: rgba(56, 189, 248, 0.3) !important;
        }

        /* Stylizacja napisów w Metrykach KPI */
        div[data-testid="stMetricLabel"] > div > div > p {
            color: #94a3b8 !important;
            font-size: 1.1rem !important;
            font-weight: 500 !important;
        }
        div[data-testid="stMetricValue"] > div {
            color: #f8fafc !important;
            font-size: 2.8rem !important;
            font-weight: 800 !important;
            text-shadow: 0 0 20px rgba(255,255,255,0.1);
        }
        div[data-testid="stMetricDelta"] > div > div > p {
            color: #38bdf8 !important;
        }

        /* Przyciski jak z filmów Sci-Fi (Holograficzny blask) */
        .stButton>button {
            background: linear-gradient(135deg, rgba(56,189,248,0.1) 0%, rgba(14,165,233,0.2) 100%) !important;
            border: 1px solid rgba(56,189,248,0.3) !important;
            color: #e0f2fe !important;
            border-radius: 12px !important;
            height: 4rem !important;
            font-size: 1.2rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s ease !important;
            box-shadow: inset 0 0 20px rgba(56,189,248,0.05) !important;
        }
        
        .stButton>button:hover {
            background: linear-gradient(135deg, rgba(56,189,248,0.3) 0%, rgba(14,165,233,0.5) 100%) !important;
            border-color: rgba(56,189,248,0.8) !important;
            color: #ffffff !important;
            box-shadow: 0 0 25px rgba(56,189,248,0.4), inset 0 0 15px rgba(255,255,255,0.2) !important;
            transform: translateY(-2px) scale(1.02) !important;
        }

        /* Tekst Gradientowy do Głównego Logo */
        .ultimate-title {
            background: linear-gradient(to right, #e0f2fe, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 900;
            letter-spacing: -1px;
            margin: 0;
            padding: 0;
            text-shadow: 0 0 40px rgba(56,189,248,0.3);
        }

        /* Pasek statusu online */
        .cyber-status {
            display: inline-flex;
            align-items: center;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            color: #34d399;
            font-weight: 600;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.1);
        }
        .pulse-dot {
            height: 8px; width: 8px;
            background-color: #10b981;
            border-radius: 50%;
            margin-right: 8px;
            box-shadow: 0 0 10px #10b981;
            animation: cyberPulse 2s infinite;
        }
        @keyframes cyberPulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        
        /* Styl dla czcionek białych wymuszony */
        h1, h2, h3, h4, p { color: #f8fafc; }
    </style>
""", unsafe_allow_html=True)

# --- POŁĄCZENIE Z CHMURĄ ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

@st.cache_data(ttl=60)
def fetch_enterprise_data():
    """Silnik danych dla Dashboardu"""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(SHEET_URL)
        
        zlecenia = spreadsheet.worksheet("Zlecenia").get_all_records()
        przewoznicy = spreadsheet.worksheet("Zleceniobiorcy").get_all_records()
        miejsca = spreadsheet.worksheet("Miejsca").get_all_records()
        
        return pd.DataFrame(zlecenia), len(przewoznicy), len(miejsca), True
    except Exception as e:
        return pd.DataFrame(), 0, 0, False

df_zlecenia, stats_przewoznicy, stats_miejsca, api_status = fetch_enterprise_data()

# --- HEADER (TOP BAR) ---
col_logo, col_space, col_profile = st.columns([5, 1, 2])

with col_logo:
    st.markdown("<h1 class='ultimate-title'>VORTEX NEXUS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 1.2rem; margin-top: -10px; font-weight: 300;'>Enterprise Transport Management System</p>", unsafe_allow_html=True)

with col_profile:
    status_color = "#34d399" if api_status else "#f87171"
    status_text = "NEXUS Core Online" if api_status else "Connection Lost"
    
    st.markdown(f"""
        <div style='text-align: right; padding-top: 15px;'>
            <div class='cyber-status'>
                <div class='pulse-dot' style='background-color: {status_color}; box-shadow: 0 0 10px {status_color};'></div>
                {status_text}
            </div>
            <div style='margin-top: 12px; display: flex; align-items: center; justify-content: flex-end;'>
                <div style='text-align: right; margin-right: 15px;'>
                    <div style='font-size: 0.9rem; color: #cbd5e1; font-weight: 600;'>Admin Terminal</div>
                    <div style='font-size: 0.75rem; color: #64748b;'>{datetime.now().strftime("%d %B %Y | %H:%M")}</div>
                </div>
                <div style='height: 45px; width: 45px; border-radius: 50%; background: linear-gradient(135deg, #38bdf8, #818cf8); display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.2rem; box-shadow: 0 0 15px rgba(56,189,248,0.5); border: 2px solid rgba(255,255,255,0.2);'>
                    A
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- KPI METRICS (HOLOGRAM CARDS) ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
liczba_zlecen = len(df_zlecenia) if not df_zlecenia.empty else 0
ostatnie = df_zlecenia.iloc[-1]['Numer zlecenia'] if not df_zlecenia.empty and 'Numer zlecenia' in df_zlecenia.columns else "BRAK"

with kpi1:
    st.metric(label="DOKUMENTY WYSTAWIONE", value=f"{liczba_zlecen:,}", delta="↑ ODCZYT NA ŻYWO" if liczba_zlecen > 0 else None)
with kpi2:
    st.metric(label="ZWIERYFIKOWANI PRZEWOŹNICY", value=stats_przewoznicy)
with kpi3:
    st.metric(label="ZAPISANE WĘZŁY LOKALIZACYJNE", value=stats_miejsca)
with kpi4:
    st.metric(label="OSTATNI IDENTYFIKATOR", value=ostatnie, delta="SYNCHRONIZACJA ZAKOŃCZONA", delta_color="off")

st.markdown("<br><br>", unsafe_allow_html=True)

# --- ZAAWANSOWANE WYKRESY (PLOTLY GRAPH OBJECTS Z TRYBEM CIEMNYM) ---
col_chart, col_feed = st.columns([7, 3])

with col_chart:
    st.markdown("<h3 style='color: #e2e8f0; font-weight: 300; letter-spacing: 1px;'>WIZUALIZACJA PRZEPŁYWU ZLECEŃ</h3>", unsafe_allow_html=True)
    with st.container(border=False): # Używamy CSS dla obramowania
        if not df_zlecenia.empty and 'Data wystawienia' in df_zlecenia.columns:
            df_wykres = df_zlecenia.groupby('Data wystawienia').size().reset_index(name='Ilość')
            
            # Własny wykres Plotly zaprojektowany dla trybu ciemnego
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_wykres['Data wystawienia'], 
                y=df_wykres['Ilość'],
                mode='lines+markers',
                line=dict(color='#38bdf8', width=3, shape='spline'),
                marker=dict(size=8, color='#818cf8', line=dict(width=2, color='#ffffff')),
                fill='tozeroy',
                fillcolor='rgba(56, 189, 248, 0.1)'
            ))
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(showgrid=False, color='#94a3b8', tickfont=dict(family='Outfit')),
                yaxis=dict(showgrid=True, gridcolor='rgba(148, 163, 184, 0.1)', color='#94a3b8', tickfont=dict(family='Outfit')),
                height=350,
                hovermode="x unified",
                hoverlabel=dict(bgcolor="rgba(15, 23, 42, 0.9)", font_size=14, font_family="Outfit", bordercolor="#38bdf8")
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Oczekuję na dane z sieci w celu wygenerowania wizualizacji...")

with col_feed:
    st.markdown("<h3 style='color: #e2e8f0; font-weight: 300; letter-spacing: 1px;'>LOGI SYSTEMOWE</h3>", unsafe_allow_html=True)
    with st.container(border=False):
        if not df_zlecenia.empty:
            ostatnie_operacje = df_zlecenia.tail(5).iloc[::-1]
            for _, row in ostatnie_operacje.iterrows():
                nr = row.get('Numer zlecenia', 'Brak')
                przewoznik = row.get('Zleceniobiorca', 'Nieznany')
                data_dod = row.get('Data wystawienia', '')
                
                # Cyber-design dla listy aktywności
                st.markdown(f"""
                <div style='padding: 15px; border-left: 4px solid #38bdf8; background: linear-gradient(90deg, rgba(56, 189, 248, 0.05) 0%, rgba(0,0,0,0) 100%); margin-bottom: 12px; border-radius: 0 10px 10px 0; transition: all 0.3s; cursor: default;' onmouseover="this.style.background='rgba(56, 189, 248, 0.1)'" onmouseout="this.style.background='linear-gradient(90deg, rgba(56, 189, 248, 0.05) 0%, rgba(0,0,0,0) 100%)'">
                    <div style='font-weight: 700; color: #f8fafc; font-size: 1rem; letter-spacing: 1px;'>{nr}</div>
                    <div style='color: #94a3b8; font-size: 0.85rem; margin-top: 6px; display: flex; justify-content: space-between;'>
                        <span>🛰️ {przewoznik[:20]}</span>
                        <span style='color: #38bdf8;'>{data_dod}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("Brak wpisów w dzienniku zdarzeń.")

st.markdown("<br><br>", unsafe_allow_html=True)

# --- PORTAL NAWIGACYJNY (GŁÓWNE MODUŁY) ---
st.markdown("<h3 style='color: #e2e8f0; font-weight: 300; letter-spacing: 1px; text-align: center; margin-bottom: 20px;'>URUCHOM MODUŁY OPERACYJNE</h3>", unsafe_allow_html=True)

nav1, nav2, nav3, nav4 = st.columns(4)

with nav1:
    if st.button("🌐 INICJUJ ZLECENIE", key="btn1", use_container_width=True):
        st.switch_page("pages/1_📝_Nowe_Zlecenie.py")

with nav2:
    if st.button("📄 TERMINAL CMR", key="btn2", use_container_width=True):
        st.switch_page("pages/2_📄_Kreator_CMR.py")

with nav3:
    if st.button("🚛 FLOTA I KONTRAHENCI", key="btn3", use_container_width=True):
        st.switch_page("pages/3_🚚_Baza_Przewoznikow.py")

with nav4:
    if st.button("🔐 BAZA DANYCH ARCHIWUM", key="btn4", use_container_width=True):
        st.switch_page("pages/5_📊_Historia_Zlecen.py")
