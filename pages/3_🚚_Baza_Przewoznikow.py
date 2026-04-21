import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Baza Przewoźników | Cargo")

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

# --- KONFIGURACJA BAZY DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_przewoznicy():
    """Pobiera wszystkie dane z zakładki Zleceniobiorcy"""
    try:
        client = get_gsheets_client()
        spreadsheet = client.open_by_url(SHEET_URL)
        ws = spreadsheet.worksheet("Zleceniobiorcy")
        return pd.DataFrame(ws.get_all_records())
    except Exception as e:
        st.error(f"Błąd łączenia z arkuszem Zleceniobiorcy: {e}")
        return pd.DataFrame()

def append_przewoznik(row_data):
    """Dopisuje nowy wiersz do bazy przewoźników"""
    client = get_gsheets_client()
    client.open_by_url(SHEET_URL).worksheet("Zleceniobiorcy").append_row(row_data)

# --- INTERFEJS APLIKACJI ---
st.title("🚚 Zarządzanie Bazą Przewoźników Cargo")
st.markdown("Słownik głównych firm transportowych obsługujących wyjazdy na eventy. Firmy dodane tutaj będą dostępne w Dyspozycji Floty oraz Terminalu CMR.")

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę z Google Sheets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# --- FORMULARZ DODAWANIA NOWEGO PRZEWOŹNIKA ---
with st.expander("➕ KLIKNIJ TUTAJ, ABY DODAĆ NOWEGO PRZEWOŹNIKA", expanded=False):
    with st.form("form_nowy_przewoznik"):
        st.info("Pamiętaj: Skrócona nazwa to ta, którą będziesz wybierać z listy w innych modułach. Pełna nazwa wydrukuje się na dokumentach oficjalnych.")
        col1, col2 = st.columns(2)
        with col1:
            skrot = st.text_input("Skrócona nazwa do listy (np. Trans-Pol)")
            pelna_nazwa = st.text_area("Pełna nazwa firmy i NIP (np. Trans-Pol Sp. z o.o., NIP: 123456)")
            nip = st.text_input("NIP (osobno)")
        with col2:
            ulica = st.text_input("Ulica i numer")
            miasto = st.text_input("Kod pocztowy i Miasto")
            kraj = st.text_input("Kraj", value="Polska")
            pojazd = st.text_input("Domyślny pojazd i kierowca (Opcjonalnie)")
            
        submit = st.form_submit_button("Zapisz Przewoźnika do Bazy (Google Sheets)")
        
        if submit:
            if skrot and pelna_nazwa:
                with st.spinner("Zapisywanie do chmury..."):
                    # Kolejność zapisu odpowiada domyślnym kolumnom w Twoim arkuszu "Zleceniobiorcy"
                    nowy_wiersz = [skrot, pelna_nazwa, ulica, miasto, kraj, nip, pojazd]
                    append_przewoznik(nowy_wiersz)
                    st.cache_data.clear() 
                    st.success(f"Sukces! Dodano firmę '{skrot}' do bazy.")
                    st.rerun()
            else:
                st.warning("⚠️ Skrócona nazwa oraz Pełna nazwa są wymagane!")

# --- WYŚWIETLANIE BAZY W TABELI ---
st.markdown("### 📋 Twoi Przewoźnicy Cargo")
df_przewoznicy = load_przewoznicy()

if not df_przewoznicy.empty:
    st.dataframe(
        df_przewoznicy, 
        use_container_width=True, 
        hide_index=True,
        height=500
    )
    st.caption(f"Łącznie przewoźników w bazie: {len(df_przewoznicy)}")
else:
    st.info("Baza przewoźników jest pusta. Dodaj pierwszą firmę korzystając z formularza powyżej.")
