import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- KONFIGURACJA STRONY (ENTERPRISE LEVEL) ---
st.set_page_config(
    page_title="Vortex TMS | Enterprise Dashboard",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- WSTRZYKNIĘCIE ZAAWANSOWANEGO CSS (ANIMACJE, GLASSMORPHISM, UX) ---
st.markdown("""
    <style>
        /* Import luksusowego fontu */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #f8fafc;
        }
        
        /* Ukrycie domyślnego menu i stopki Streamlit dla czystego wyglądu SaaS */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        .block-container {
            padding-top: 2rem;
            padding-bottom: 4rem;
            max-width: 1600px;
        }

        /* Animacja wejścia (Fade In Up) */
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .animated-card {
            animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        /* Stylizacja kart / kontenerów */
        div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
            transition: all 0.3s ease;
        }
        
        div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"]:hover {
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025);
            transform: translateY(-2px);
        }

        /* Luksusowe KPI (Metryki) */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
            border: 1px solid #e2e8f0;
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            border-left: 5px solid #2563eb;
        }
        
        div[data-testid="stMetricValue"] {
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            color: #1e293b !important;
            letter-spacing: -1px;
        }

        /* Przyciski Akcji Premium */
        .stButton>button {
            border-radius: 12px;
            font-weight: 600;
            height: 3.5rem;
            transition: all 0.2s;
            border: none;
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            color: white;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
            color: white;
            border: none;
        }
        
        /* Gradientowe Nagłówki */
        .gradient-text {
            background: linear-gradient(135deg, #1e293b 0%, #2563eb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 2.5rem;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        
        /* Wskaźnik statusu */
        .status-dot {
            height: 10px;
            width: 10px;
            background-color: #10b981;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            box-shadow: 0 0 8px #10b981;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
    </style>
""", unsafe_allow_html=True)

# --- POŁĄCZENIE Z BAZĄ DANYCH DLA STATYSTYK ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

@st.cache_data(ttl=60)
def fetch_dashboard_data():
    """Pobiera i przetwarza dane analityczne na żywo z chmury"""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(SHEET_URL)
        
        zlecenia = spreadsheet.worksheet("Zlecenia").get_all_records()
        przewoznicy = spreadsheet.worksheet("Zleceniobiorcy").get_all_records()
        miejsca = spreadsheet.worksheet("Miejsca").get_all_records()
        
        df_zlecenia = pd.DataFrame(zlecenia)
        
        return df_zlecenia, len(przewoznicy), len(miejsca), True
    except Exception as e:
        return pd.DataFrame(), 0, 0, False

df_zlecenia, stats_przewoznicy, stats_miejsca, api_status = fetch_dashboard_data()

# --- HEADER (DYNAMICZNE POWITANIE) ---
current_hour = datetime.now().hour
if current_hour < 12: greeting = "Dzień dobry"
elif current_hour < 18: greeting = "Dzień dobry"
else: greeting = "Dobry wieczór"

data_dzis = datetime.now().strftime("%d.%m.%Y")

col_header, col_profile = st.columns([4, 1])
with col_header:
    st.markdown(f"<div class='animated-card'><p style='color: #64748b; font-size: 1.1rem; margin-bottom: -15px; font-weight: 600;'>{greeting}, Administratorze.</p></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='gradient-text animated-card'>Control Tower | TMS</h1>", unsafe_allow_html=True)
with col_profile:
    status_color = "#10b981" if api_status else "#ef4444"
    status_text = "API Operational" if api_status else "System Offline"
    st.markdown(f"""
        <div style='text-align: right; padding-top: 10px;' class='animated-card'>
            <div style='font-size: 0.9rem; color: #64748b;'>Dzisiaj jest {data_dzis}</div>
            <div style='margin-top: 10px; display: flex; align-items: center; justify-content: flex-end;'>
                <span class='status-dot' style='background-color: {status_color}; box-shadow: 0 0 8px {status_color};'></span>
                <span style='font-weight: 600; font-size: 0.9rem; color: #334155;'>{status_text}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- SEKCJA KPI (METRYKI OPERACYJNE) ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
liczba_zlecen = len(df_zlecenia) if not df_zlecenia.empty else 0

with kpi1:
    st.metric(label="Wystawione Dokumenty (YTD)", value=f"{liczba_zlecen:,}", delta="↑ Na żywo" if liczba_zlecen > 0 else None)
with kpi2:
    st.metric(label="Aktywni Przewoźnicy", value=stats_przewoznicy)
with kpi3:
    st.metric(label="Zapisane Lokalizacje", value=stats_miejsca)
with kpi4:
    ostatnie = df_zlecenia.iloc[-1]['Numer zlecenia'] if not df_zlecenia.empty and 'Numer zlecenia' in df_zlecenia.columns else "Brak Danych"
    st.metric(label="Ostatni Nr Referencyjny", value=ostatnie, delta="Zsynchronizowano", delta_color="off")

st.markdown("<br><br>", unsafe_allow_html=True)

# --- SEKCJA ŚRODKOWA: ANALITYKA I AKTYWNOŚĆ ---
col_chart, col_feed = st.columns([6, 4])

with col_chart:
    st.markdown("<h3 style='color: #1e293b;'>📈 Trend Wystawianych Zleceń</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        if not df_zlecenia.empty and 'Data wystawienia' in df_zlecenia.columns:
            # Agregacja danych do wykresu (grupowanie po dacie)
            df_wykres = df_zlecenia.groupby('Data wystawienia').size().reset_index(name='Ilość')
            
            # Nowoczesny wykres Plotly
            fig = px.area(df_wykres, x='Data wystawienia', y='Ilość', 
                          color_discrete_sequence=['#2563eb'],
                          line_shape='spline') # spline robi płynne zaokrąglone linie
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title=""),
                height=320,
                hovermode="x unified"
            )
            fig.update_traces(fillcolor='rgba(37, 99, 235, 0.1)', mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Zbyt mało danych do wygenerowania wykresu analitycznego. Wystaw pierwsze zlecenia!")

with col_feed:
    st.markdown("<h3 style='color: #1e293b;'>⚡ Ostatnia Aktywność</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        if not df_zlecenia.empty:
            # Pobieramy 4 ostatnie zlecenia (odwrócona kolejność)
            ostatnie_operacje = df_zlecenia.tail(4).iloc[::-1]
            for _, row in ostatnie_operacje.iterrows():
                nr = row.get('Numer zlecenia', 'Brak')
                przewoznik = row.get('Zleceniobiorca', 'Nieznany')
                data_dod = row.get('Data wystawienia', '')
                
                # Renderowanie pięknego elementu listy (Activity Feed)
                st.markdown(f"""
                <div style='padding: 12px 15px; border-left: 3px solid #3b82f6; background-color: #f8fafc; margin-bottom: 10px; border-radius: 0 8px 8px 0;'>
                    <div style='font-weight: 700; color: #1e293b; font-size: 1rem;'>{nr}</div>
                    <div style='color: #64748b; font-size: 0.85rem; margin-top: 4px;'>
                        🚚 {przewoznik[:25]}... <span style='float: right;'>🕒 {data_dod}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("Brak niedawnej aktywności w systemie.")

st.markdown("<br><br>", unsafe_allow_html=True)

# --- SZYBKIE AKCJE (NAWIGACJA MODUŁOWA) ---
st.markdown("<h3 style='color: #1e293b;'>🚀 Zarządzanie Systemem</h3>", unsafe_allow_html=True)
nav1, nav2, nav3, nav4 = st.columns(4)

with nav1:
    with st.container(border=True):
        st.markdown("<div style='font-size: 2.5rem; margin-bottom: 10px;'>📝</div>", unsafe_allow_html=True)
        st.markdown("#### Generator Dokumentów")
        st.caption("Pełny proces: Zlecenie Transportowe + 3x Oficjalny CMR z Hash QR.")
        if st.button("Uruchom Moduł", key="btn1", use_container_width=True):
            st.switch_page("pages/1_📝_Nowe_Zlecenie.py")

with nav2:
    with st.container(border=True):
        st.markdown("<div style='font-size: 2.5rem; margin-bottom: 10px;'>📄</div>", unsafe_allow_html=True)
        st.markdown("#### Szybki CMR")
        st.caption("Klonuj dane z historii i generuj wyłącznie list przewozowy.")
        if st.button("Kreator CMR", key="btn2", use_container_width=True):
            st.switch_page("pages/2_📄_Kreator_CMR.py")

with nav3:
    with st.container(border=True):
        st.markdown("<div style='font-size: 2.5rem; margin-bottom: 10px;'>🚚</div>", unsafe_allow_html=True)
        st.markdown("#### Flota i Podwykonawcy")
        st.caption("Zarządzaj słownikiem przewoźników używanych w zleceniach.")
        if st.button("Baza Przewoźników", key="btn3", use_container_width=True):
            st.switch_page("pages/3_🚚_Baza_Przewoznikow.py")

with nav4:
    with st.container(border=True):
        st.markdown("<div style='font-size: 2.5rem; margin-bottom: 10px;'>📊</div>", unsafe_allow_html=True)
        st.markdown("#### Archiwum Operacji")
        st.caption("Przeszukuj historię, analizuj koszty i sprawdzaj numery referencyjne.")
        if st.button("Historia Zleceń", key="btn4", use_container_width=True):
            st.switch_page("pages/5_📊_Historia_Zlecen.py")
