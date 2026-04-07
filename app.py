import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="TMS Enterprise | Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- WSTRZYKNIĘCIE CUSTOM CSS (EFEKT PREMIUM) ---
st.markdown("""
    <style>
        /* Usunięcie domyślnego, wielkiego marginesu na górze */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        /* Stylizacja kafelków ze statystykami (Karty) */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: transform 0.2s ease-in-out;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        }
        /* Dedykowany kolor dla głównych wartości metryk */
        div[data-testid="stMetricValue"] {
            color: #0f52ba;
        }
        /* Stylizacja przycisków */
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }
        .stButton>button:hover {
            border-color: #0f52ba;
            color: #0f52ba;
        }
        /* Typografia nagłówków */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            color: #1e1e1e;
        }
    </style>
""", unsafe_allow_html=True)

# --- POŁĄCZENIE Z BAZĄ DANYCH DLA STATYSTYK ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

@st.cache_data(ttl=60)
def fetch_dashboard_stats():
    """Funkcja pobierająca statystyki do wyświetlenia na Dashboardzie"""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(SHEET_URL)
        
        zlecenia = spreadsheet.worksheet("Zlecenia").get_all_records()
        przewoznicy = spreadsheet.worksheet("Zleceniobiorcy").get_all_records()
        miejsca = spreadsheet.worksheet("Miejsca").get_all_records()
        
        ostatnie_zlecenie = zlecenia[-1] if zlecenia else None
        
        return len(zlecenia), len(przewoznicy), len(miejsca), ostatnie_zlecenie
    except Exception as e:
        # W razie błędu połączenia zwracamy zera, aby aplikacja się nie "wysypała"
        return 0, 0, 0, None

# Pobranie danych
stats_zlecenia, stats_przewoznicy, stats_miejsca, last_order = fetch_dashboard_stats()

# --- TOP BAR (NAGŁÓWEK) ---
col_logo, col_user = st.columns([4, 1])
with col_logo:
    st.markdown("<h1>🚛 System Zarządzania Transportem <span style='color: #0f52ba;'>PRO</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 1.1rem;'>Witaj w głównym panelu sterowania. Przeglądaj statystyki na żywo.</p>", unsafe_allow_html=True)
with col_user:
    st.markdown("<div style='text-align: right; padding-top: 20px; color: #888;'>Zalogowano jako:<br><b>Administrator TMS</b></div>", unsafe_allow_html=True)

st.markdown("---")

# --- SEKCJA KPI (METRYKI) ---
st.markdown("### 📊 Podsumowanie Operacyjne")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(label="📄 Wystawione Zlecenia", value=stats_zlecenia, delta="Wszystkie" if stats_zlecenia > 0 else None)
with kpi2:
    st.metric(label="🚚 Baza Przewoźników", value=stats_przewoznicy)
with kpi3:
    st.metric(label="🏢 Baza Miejsc", value=stats_miejsca)
with kpi4:
    ostatni_nr = last_order["Numer zlecenia"] if last_order else "Brak"
    st.metric(label="Ostatni dokument", value=ostatni_nr, delta="Najnowszy", delta_color="off")

st.markdown("<br>", unsafe_allow_html=True)

# --- SZYBKIE AKCJE (SKRÓTY DO MODUŁÓW) ---
st.markdown("### ⚡ Szybkie Akcje")
akcja1, akcja2, akcja3 = st.columns(3)

with akcja1:
    with st.container(border=True):
        st.markdown("#### 📝 Wystaw Nowe Zlecenie")
        st.caption("Wygeneruj oficjalny dokument zlecenia oraz 3 strony listu przewozowego CMR z kodem QR.")
        if st.button("Uruchom Moduł Zleceń ➔", use_container_width=True, type="primary"):
            st.switch_page("pages/1_📝_Nowe_Zlecenie.py")

with akcja2:
    with st.container(border=True):
        st.markdown("#### 📄 Szybki CMR")
        st.caption("Pobierz dane z poprzednich zleceń i wydrukuj sam dokument listu przewozowego.")
        if st.button("Uruchom Kreator CMR ➔", use_container_width=True):
            st.switch_page("pages/2_📄_Kreator_CMR.py")

with akcja3:
    with st.container(border=True):
        st.markdown("#### 🚚 Zarządzaj Przewoźnikami")
        st.caption("Dodaj nową firmę transportową do bazy, aby mieć ją zawsze pod ręką.")
        if st.button("Otwórz Bazę ➔", use_container_width=True):
            st.switch_page("pages/3_🚚_Baza_Przewoznikow.py")
