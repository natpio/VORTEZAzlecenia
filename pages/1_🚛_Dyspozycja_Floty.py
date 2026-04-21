import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA ---
st.set_page_config(layout="wide", page_title="Dyspozycja Floty | Cargo")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

# --- MENU BOCZNE (TYLKO CARGO) ---
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none !important;}</style>""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("### 🚛 LOGISTYKA CARGO")
    st.page_link("app.py", label="⬅ Wróć do Głównego Menu")
    st.divider()
    st.page_link("pages/1_🚛_Dyspozycja_Floty.py", label="Dyspozycja Floty")
    st.page_link("pages/2_📄_Terminal_CMR.py", label="Terminal CMR")
    st.page_link("pages/3_🚚_Baza_Przewoznikow.py", label="Baza Przewoźników")
    st.page_link("pages/4_📊_Historia_Zlecen_Cargo.py", label="Historia Zleceń")

def get_gsheets_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_data():
    client = get_gsheets_client()
    sh = client.open_by_url(SHEET_URL)
    return (pd.DataFrame(sh.worksheet("Zleceniobiorcy").get_all_records()), 
            pd.DataFrame(sh.worksheet("Miejsca").get_all_records()), 
            pd.DataFrame(sh.worksheet("Projekty").get_all_records()))

df_p, df_m, df_projekty = load_data()

st.title("🚛 Dyspozycja Floty - TARGI")
st.info("Formularz planowania pełnego cyklu transportowego na wydarzenie.")

with st.form("form_cargo_full"):
    # Sekcja 1: Nagłówek i Strony
    c1, c2 = st.columns(2)
    lista_eventow = sorted(df_projekty['Nazwa Eventu'].unique().tolist()) if not df_projekty.empty else []
    wybrany_event = c1.selectbox("Wybierz Event (Targi)", lista_eventow)
    nr_zlecenia = c2.text_input("Numer Zlecenia", f"TARGI/{datetime.now().strftime('%Y/%m')}/")
    
    st.divider()
    
    # Sekcja 2: Przewoźnik i Trasa
    col1, col2, col3 = st.columns(3)
    przewoznik = col1.selectbox("Przewoźnik", df_p['Nazwa do listy'].tolist())
    skad = col2.selectbox("Załadunek (Start)", df_m['Nazwa do listy'].tolist())
    dokad = col3.selectbox("Rozładunek (Targi)", df_m['Nazwa do listy'].tolist())

    # Sekcja 3: HARMONOGRAM TARGOWY (Twoje nowe daty)
    st.markdown("### 📅 Harmonogram Operacyjny")
    d1, d2, d3 = st.columns(3)
    data_zal = d1.date_input("1. Data Załadunku (Magazyn)")
    data_roz_montaz = d2.date_input("2. Data Rozładunku (Montaż)")
    data_empties_odbior = d3.date_input("3. Odbiór Empties (od Kontrahenta)")
    
    d4, d5, d6 = st.columns(3)
    data_empties_dostawa = d4.date_input("4. Dostawa Empties (na stoisko)")
    data_zal_powrot = d5.date_input("5. Załadunek po demontażu")
    data_roz_magazyn = d6.date_input("6. Rozładunek (Magazyn własny)")

    st.divider()

    # Sekcja 4: Dane techniczne
    st.markdown("### 🚛 Dane Auta i Kierowcy")
    k1, k2, k3, k4 = st.columns(4)
    nr_rej = k1.text_input("Nr rejestracyjny")
    kierowca = k2.text_input("Imię i Nazwisko")
    tel_kierowcy = k3.text_input("Telefon")
    stawka = k4.number_input("Stawka Całkowita", min_value=0)
    
    uwagi = st.text_area("Uwagi dodatkowe i specyfikacja ładunku")

    if st.form_submit_button("🚀 Zapisz Pełne Zlecenie"):
        # Przygotowanie opisu z datami do kolumny N (Uwagi)
        harmonogram_txt = (
            f"ZAL: {data_zal} | ROZ(MONT): {data_roz_montaz} | "
            f"EMP_OUT: {data_empties_odbior} | EMP_IN: {data_empties_dostawa} | "
            f"POWR_ZAL: {data_zal_powrot} | POWR_ROZ: {data_roz_magazyn}"
        )
        kompletne_uwagi = f"{uwagi} || AUTO: {nr_rej}, KIER: {kierowca} ({tel_kierowcy}) || HARMONOGRAM: {harmonogram_txt}"
        
        nowy_wiersz = [
            datetime.now().strftime("%Y-%m-%d %H:%M"), nr_zlecenia, "VORTEX_CARGO", 
            przewoznik, skad, dokad, str(data_zal), str(data_roz_magazyn), 
            "Transport Targowy", "", "", "", "", 
            kompletne_uwagi, "", wybrany_event, "TARGI", stawka
        ]
        
        get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
        st.success("Zlecenie TARGI zostało poprawnie zarchiwizowane w systemie!")
        st.balloons()
