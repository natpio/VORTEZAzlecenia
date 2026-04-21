import streamlit as st
from datetime import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Dyspozycja Floty | Cargo")

# --- UKRYCIE DOMYŚLNEGO MENU I DEDYKOWANY PASEK BOCZNY (CARGO) ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='color: #38bdf8;'>🚛 LOGISTYKA CARGO</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/1_🚛_Dyspozycja_Floty.py", label="Dyspozycja Floty (TARGI)")
    st.page_link("pages/8_🛠️_Obsluga_Zaopatrzenia.py", label="Obsługa Zaopatrzenia")
    st.page_link("pages/2_📄_Terminal_CMR.py", label="Terminal CMR")
    st.page_link("pages/3_🚚_Baza_Przewoznikow.py", label="Baza Przewoźników Cargo")
    st.page_link("pages/4_📊_Historia_Zlecen_Cargo.py", label="Historia Zleceń Cargo")

# --- KONFIGURACJA BAZY DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def get_next_daily_number():
    """Sprawdza ile zleceń wpisano dzisiaj do bazy i zwraca kolejny numer (1, 2, 3...)"""
    client = get_gsheets_client()
    ws = client.open_by_url(SHEET_URL).worksheet("Zlecenia")
    dzisiaj = datetime.now().strftime("%Y-%m-%d")
    
    # Pobieramy wszystkie dane, aby przeliczyć dzisiejsze wpisy
    df = pd.DataFrame(ws.get_all_records())
    
    if not df.empty and 'Data wystawienia' in df.columns:
        # Liczymy wiersze, które mają dzisiejszą datę w kolumnie 'Data wystawienia'
        dzisiejsze = df[df['Data wystawienia'].astype(str).str.startswith(dzisiaj)]
        return len(dzisiejsze) + 1
    return 1

@st.cache_data(ttl=60)
def load_data_dictionaries():
    """Pobiera listy przewoźników i projektów"""
    try:
        client = get_gsheets_client()
        sh = client.open_by_url(SHEET_URL)
        df_p = pd.DataFrame(sh.worksheet("Zleceniobiorcy").get_all_records())
        df_e = pd.DataFrame(sh.worksheet("Projekty").get_all_records())
        return df_p, df_e
    except Exception as e:
        st.error(f"Błąd ładowania słowników: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- INTERFEJS ---
st.title("🚛 Dyspozycja Floty - Transporty Targowe")
st.markdown("Zaplanuj wyjazd naczepy. Numer zlecenia zostanie wygenerowany automatycznie zgodnie z nowym standardem.")

df_p, df_e = load_data_dictionaries()

# Zabezpieczenie przed brakiem kolumn w Google Sheets (KeyError)
lista_przewoznikow = df_p['Skrócona Nazwa'].tolist() if not df_p.empty and 'Skrócona Nazwa' in df_p.columns else ["Brak danych w arkuszu"]
lista_eventow = df_e['Nazwa Eventu'].tolist() if not df_e.empty and 'Nazwa Eventu' in df_e.columns else ["Brak danych w arkuszu"]

with st.form("form_fleet_main", border=True):
    st.subheader("Opiekun i Projekt")
    logistyk = st.radio("Logistyk wystawiający:", ["PD", "PK"], horizontal=True)
    
    c1, c2, c3 = st.columns(3)
    wybrane_targi = c1.selectbox("Nazwa Targów / Eventu", lista_eventow)
    przewoznik = c2.selectbox("Przewoźnik", lista_przewoznikow)
    tabor = c3.selectbox("Rodzaj auta/naczepy", ["MEGA", "Standard", "Zestaw 120m3", "Solo", "Bus"])

    st.markdown("---")
    st.subheader("Harmonogram (Cykl 6 dat)")
    d1, d2, d3 = st.columns(3)
    z1 = d1.date_input("1. Załadunek Magazyn PL")
    r1 = d2.date_input("2. Rozładunek Targi")
    e1 = d3.date_input("3. Empties (Odbiór)")
    
    d4, d5, d6 = st.columns(3)
    e2 = d4.date_input("4. Empties (Zwrot)")
    z2 = d5.date_input("5. Załadunek Powrotny")
    r2 = d6.date_input("6. Rozładunek Magazyn PL")

    st.markdown("---")
    st.subheader("Szczegóły i Koszty")
    m1, m2 = st.columns(2)
    start = m1.text_input("Adres startu", "Magazyn Komorniki")
    cel = m2.text_input("Adres docelowy", f"Targi - {wybrane_targi}")
    
    k1, k2 = st.columns(2)
    stawka = k1.number_input("Stawka netto", min_value=0.0)
    auto_dane = k2.text_input("Dane auta / kierowcy")
    
    uwagi = st.text_area("Dodatkowe instrukcje")
    
    if st.form_submit_button("ZATWIERDŹ I WYGENERUJ NUMER", type="primary", use_container_width=True):
        if "Brak danych" in wybrane_targi:
            st.error("Błąd: Sprawdź nagłówki w Google Sheets (brak kolumny 'Nazwa Eventu')")
        else:
            with st.spinner("Generowanie zlecenia..."):
                try:
                    # LOGIKA GENEROWANIA NUMERU
                    pref = str(wybrane_targi)[:3].upper()
                    rok = datetime.now().strftime('%y')
                    data_kod = datetime.now().strftime('%m%d')
                    dzienny_nr = get_next_daily_number()
                    
                    # Wynik: np. IFA26/0421/PD01
                    final_nr = f"{pref}{rok}/{data_kod}/{logistyk}{dzienny_nr:02d}"
                    
                    harmonogram_tekst = f"CYKL: {z1} -> {r1} | EMP: {e1}/{e2} | POWRÓT: {z2} -> {r2}"
                    pelne_uwagi = f"Logistyk: {logistyk} | {uwagi} \nAUTO: {auto_dane} | {harmonogram_tekst}"
                    
                    nowy_wpis = [
                        datetime.now().strftime("%Y-%m-%d %H:%M"),
                        final_nr,
                        "LOGISTYKA CARGO",
                        przewoznik,
                        start,
                        cel,
                        str(z1),
                        str(r2),
                        "Elementy Zabudowy",
                        "", "", "", "",
                        pelne_uwagi,
                        "",
                        wybrane_targi,
                        "TARGI",
                        stawka
                    ]
                    
                    client = get_gsheets_client()
                    client.open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wpis)
                    
                    st.success(f"Zlecenie zapisane pomyślnie!")
                    st.info(f"WYGENEROWANY NUMER: **{final_nr}**")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")

st.caption("VORTEX NEXUS v2.1 | Moduł Cargo")
