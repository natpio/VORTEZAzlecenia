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
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_przewoznicy_i_projekty():
    """Pobiera listy przewoźników i projektów do menu rozwijanych"""
    try:
        client = get_gsheets_client()
        spreadsheet = client.open_by_url(SHEET_URL)
        df_przewoznicy = pd.DataFrame(spreadsheet.worksheet("Zleceniobiorcy").get_all_records())
        df_projekty = pd.DataFrame(spreadsheet.worksheet("Projekty").get_all_records())
        return df_przewoznicy, df_projekty
    except Exception as e:
        st.error(f"Błąd ładowania danych słownikowych: {e}")
        return pd.DataFrame(), pd.DataFrame()

def append_to_zlecenia(row_data):
    """Zapisuje nowy wiersz w głównej zakładce Zlecenia"""
    client = get_gsheets_client()
    spreadsheet = client.open_by_url(SHEET_URL)
    worksheet = spreadsheet.worksheet("Zlecenia")
    worksheet.append_row(row_data)

# --- INTERFEJS APLIKACJI ---
st.title("🚛 Dyspozycja Floty - Główne Wyjazdy (TARGI)")
st.markdown("Planowanie transportów naczepowych na wydarzenia. System automatycznie zapisuje zlecenie jako typ **TARGI**.")

# Ładowanie słowników
df_przewoznicy, df_projekty = load_przewoznicy_i_projekty()

# ZABEZPIECZENIE: Sprawdzamy czy kolumny fizycznie istnieją, żeby uniknąć błędu KeyError
if not df_przewoznicy.empty and 'Skrócona Nazwa' in df_przewoznicy.columns:
    lista_przewoznikow = df_przewoznicy['Skrócona Nazwa'].tolist()
else:
    lista_przewoznikow = ["Brak kolumny 'Skrócona Nazwa' w arkuszu Zleceniobiorcy!"]

if not df_projekty.empty and 'Nazwa Eventu' in df_projekty.columns:
    lista_eventow = df_projekty['Nazwa Eventu'].tolist()
else:
    lista_eventow = ["Brak kolumny 'Nazwa Eventu' w arkuszu Projekty!"]

# --- FORMULARZ DYSPOZYCJI ---
with st.form("form_cargo_fleet"):
    st.subheader("1. Podstawowe dane transportu")
    c1, c2, c3 = st.columns(3)
    event_nazwa = c1.selectbox("Projekt / Targi (Miejsce docelowe)", lista_eventow)
    przewoznik = c2.selectbox("Wybierz Przewoźnika", lista_przewoznikow)
    rodzaj_naczepy = c3.selectbox("Rodzaj taboru", ["MEGA 13.6m", "Standard 13.6m", "Zestaw 120m3", "Solo 7.5t", "Bus", "Inne"])
    
    st.markdown("---")
    st.subheader("2. Harmonogram Operacji (6 Etapów Cyklu)")
    st.info("Zaplanuj pełną drogę naczepy – od wyjazdu z magazynu do powrotu po targach.")
    
    # Podział na etapy (3 kolumny x 2 rzędy)
    d1, d2, d3 = st.columns(3)
    data_zaladunek_pl = d1.date_input("1. Załadunek Magazyn (PL)")
    data_rozladunek_eu = d2.date_input("2. Rozładunek na Targach")
    data_puste_skrzynie = d3.date_input("3. Odbiór opakowań (Empties)")
    
    d4, d5, d6 = st.columns(3)
    data_zwrot_skrzyn = d4.date_input("4. Zwrot opakowań na stoisko")
    data_zaladunek_eu = d5.date_input("5. Załadunek powrotny")
    data_rozladunek_pl = d6.date_input("6. Rozładunek Magazyn (PL)")
    
    st.markdown("---")
    st.subheader("3. Logistyka i Finanse")
    m1, m2 = st.columns(2)
    miejsce_zal = m1.text_input("Punkt startowy", value="Magazyn Komorniki")
    miejsce_roz = m2.text_input("Punkt docelowy", value=f"Teren Targów - {event_nazwa}")
    
    k1, k2 = st.columns(2)
    stawka = k1.number_input("Całkowita stawka za kółko (PLN/EUR)", min_value=0.0, step=100.0)
    dane_auta = k2.text_input("Numer rejestracyjny i telefon kierowcy")
    
    uwagi = st.text_area("Uwagi dla magazynu / instrukcje dla spedycji")
    
    submit_cargo = st.form_submit_button("Zatwierdź i Wyślij Dyspozycję do Bazy", type="primary", use_container_width=True)
    
    if submit_cargo:
        if "Brak kolumny" in event_nazwa or "Brak kolumny" in przewoznik:
            st.error("Nie możesz zapisać zlecenia, dopóki nie naprawisz nagłówków w Google Sheets!")
        elif event_nazwa and przewoznik:
            # Generowanie numeru zlecenia
            nr_zlecenia = f"CRG/{datetime.now().strftime('%m%H%M')}"
            
            # Formatowanie rozszerzonych uwag
            harmonogram_str = (
                f"CYKL TARGOWY: Zal. PL: {data_zaladunek_pl} | "
                f"Roz. EU: {data_rozladunek_eu} | "
                f"Empties: {data_puste_skrzynie} -> {data_zwrot_skrzyn} | "
                f"Powrót: {data_zaladunek_eu} -> {data_rozladunek_pl}"
            )
            
            pelne_uwagi = f"{uwagi} \n\nAUTO: {dane_auta} | TABOR: {rodzaj_naczepy} \n{harmonogram_str}"
            
            # Przygotowanie wiersza
            nowy_wiersz = [
                datetime.now().strftime("%Y-%m-%d %H:%M"), # A: Data wystawienia
                nr_zlecenia,                                # B: Numer zlecenia
                "LOGISTYKA CARGO",                         # C: Dział
                przewoznik,                                # D: Zleceniobiorca
                miejsce_zal,                               # E: Załadunek
                miejsce_roz,                               # F: Rozładunek
                str(data_zaladunek_pl),                    # G: Data załadunku
                str(data_rozladunek_pl),                   # H: Data rozładunku (finalna)
                "Elementy Zabudowy Targowej",              # I: Rodzaj towaru
                "", "", "", "",                            # J, K, L, M: Dane CMR
                pelne_uwagi,                               # N: Uwagi
                "",                                        # O: Hash
                event_nazwa,                               # P: ID Projektu
                "TARGI",                                   # Q: Typ transportu
                stawka                                     # R: Stawka
            ]
            
            with st.spinner("Zapisywanie danych w chmurze..."):
                try:
                    append_to_zlecenia(nowy_wiersz)
                    st.success(f"Zlecenie {nr_zlecenia} zostało pomyślnie zarejestrowane!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Wystąpił błąd podczas zapisu: {e}")
        else:
            st.warning("Uzupełnij nazwę eventu oraz przewoźnika!")

st.markdown("---")
st.caption("System VORTEX NEXUS v2.1 | Dział Logistyki Ciężkiej")
