import streamlit as st
import pandas as pd
from datetime import datetime
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
    st.page_link("pages/2_📄_Terminal_CMR.py", label="Terminal CMR")
    st.page_link("pages/3_🚚_Baza_Przewoznikow.py", label="Baza Przewoźników Cargo")
    st.page_link("pages/4_📊_Historia_Zlecen_Cargo.py", label="Historia Zleceń Cargo")

# --- POŁĄCZENIE Z BAZĄ DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_all_cargo_data():
    client = get_gsheets_client()
    sh = client.open_by_url(SHEET_URL)
    
    # Pobieranie danych z arkuszy
    przewoznicy = pd.DataFrame(sh.worksheet("Zleceniobiorcy").get_all_records())
    miejsca = pd.DataFrame(sh.worksheet("Miejsca").get_all_records())
    projekty = pd.DataFrame(sh.worksheet("Projekty").get_all_records())
    
    return przewoznicy, miejsca, projekty

# --- ŁADOWANIE DANYCH ---
df_p, df_m, df_projekty = load_all_cargo_data()

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("🚛 Dyspozycja Floty - TARGI")
st.markdown("Planowanie transportu zbiorczego z pełnym harmonogramem operacyjnym.")

with st.form("form_targi_cargo", border=True):
    
    # SEKCJA 1: INFORMACJE OGÓLNE
    st.markdown("### 🎯 1. Identyfikacja Wydarzenia")
    c1, c2 = st.columns(2)
    
    lista_eventow = sorted(df_projekty['Nazwa Eventu'].unique().tolist()) if not df_projekty.empty else []
    wybrany_event = c1.selectbox("Wybierz Event (Targi)", lista_eventow)
    nr_zlecenia = c2.text_input("Numer Zlecenia", f"TARGI/{datetime.now().strftime('%Y/%m')}/")
    
    st.divider()

    # SEKCJA 2: STRONY I TRASA
    st.markdown("### 🏢 2. Strony i Trasa Główna")
    col1, col2, col3 = st.columns(3)
    
    przewoznik = col1.selectbox("Przewoźnik", df_p['Nazwa do listy'].tolist() if not df_p.empty else [])
    zaladunek_skrot = col2.selectbox("Miejsce Załadunku (Start)", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])
    rozladunek_skrot = col3.selectbox("Miejsce Rozładunku (Targi)", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])

    st.divider()

    # SEKCJA 3: HARMONOGRAM OPERACYJNY (6 DAT)
    st.markdown("### 📅 3. Harmonogram Operacyjny (Full Cycle)")
    
    h1, h2, h3 = st.columns(3)
    d_zal_magazyn = h1.date_input("1. Data Załadunku (Magazyn własny)")
    d_roz_montaz = h2.date_input("2. Data Rozładunku (Montaż na Targach)")
    d_empties_odbior = h3.date_input("3. Odbiór Empties (Odbiór pustych opakowań)")
    
    h4, h5, h6 = st.columns(3)
    d_empties_dostawa = h4.date_input("4. Dostawa Empties (Dostarczenie na demontaż)")
    d_zal_powrot = h5.date_input("5. Załadunek Pełnych Casów (Koniec demontażu)")
    d_roz_magazyn_final = h6.date_input("6. Rozładunek po powrocie (Magazyn)")

    st.divider()

    # SEKCJA 4: DANE TECHNICZNE I FINANSE
    st.markdown("### 🛠️ 4. Szczegóły Transportu")
    k1, k2, k3, k4 = st.columns(4)
    
    nr_rej = k1.text_input("Nr rejestracyjny auta")
    kierowca = k2.text_input("Imię i Nazwisko kierowcy")
    telefon = k3.text_input("Telefon do kierowcy")
    stawka = k4.number_input("Stawka całkowita (PLN/EUR)", min_value=0)

    uwagi = st.text_area("Uwagi dodatkowe (Specyfikacja naczepy, lista projektów itp.)")

    # PRZYCISK ZAPISU
    submit = st.form_submit_button("🚀 ZAPISZ ZLECENIE I HARMONOGRAM")

if submit:
    # Przygotowanie tekstu harmonogramu do kolumny UWAGI (Kolumna N)
    harmonogram_txt = (
        f"HARMONOGRAM: [1] Zal: {d_zal_magazyn} | [2] Roz(Mont): {d_roz_montaz} | "
        f"[3] Emp_Out: {d_empties_odbior} | [4] Emp_In: {d_empties_dostawa} | "
        f"[5] Zal(Demont): {d_zal_powrot} | [6] Roz(Mag): {d_roz_magazyn_final}"
    )
    
    kompletne_uwagi = f"{uwagi} || AUTO: {nr_rej}, KIER: {kierowca} ({telefon}) || {harmonogram_txt}"
    
    # Przygotowanie wiersza do Google Sheets (zgodnie ze strukturą Twojego arkusza)
    nowy_wiersz = [
        datetime.now().strftime("%Y-%m-%d %H:%M"), # A: Data wystawienia
        nr_zlecenia,             # B: Numer zlecenia
        "VORTEX_CARGO",          # C: Zleceniodawca (Dział)
        przewoznik,              # D: Zleceniobiorca
        zaladunek_skrot,         # E: Miejsce Zaladunku
        rozladunek_skrot,        # F: Miejsce Rozladunku
        str(d_zal_magazyn),      # G: Data Zaladunku (Pierwsza data)
        str(d_roz_magazyn_final),# H: Data Rozladunku (Ostatnia data)
        "Transport Zbiorczy TARGI", # I: Rodzaj towaru
        "",                      # J: Ilosc opakowan
        "",                      # K: Rodzaj opakowania
        "",                      # L: Waga brutto
        "",                      # M: Wartosc towaru
        kompletne_uwagi,         # N: Uwagi / Instrukcje (Tu ląduje harmonogram i auto)
        "",                      # O: Hash QR
        wybrany_event,           # P: ID PROJEKTU (W Cargo używamy Nazwy Eventu)
        "TARGI",                 # Q: TYP TRANSPORTU (Kluczowy filtr)
        stawka                   # R: STAWKA
    ]
    
    try:
        with st.spinner("Zapisywanie zlecenia w systemie..."):
            get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
            st.success(f"Zlecenie {nr_zlecenia} dla {wybrany_event} zostało pomyślnie zapisane!")
            st.balloons()
            st.cache_data.clear() # Odświeżamy dane
    except Exception as e:
        st.error(f"Wystąpił błąd podczas zapisu: {e}")
