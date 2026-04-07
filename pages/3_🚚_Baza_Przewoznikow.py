import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    """Autoryzacja w Google Sheets na podstawie st.secrets"""
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
        # Pobieranie wszystkich rekordów jako DataFrame
        df = pd.DataFrame(ws.get_all_records())
        return df
    except Exception as e:
        st.error(f"Błąd łączenia z arkuszem Zleceniobiorcy: {e}")
        return pd.DataFrame()

def append_przewoznik(row_data):
    """Dopisuje nowy wiersz do bazy przewoźników"""
    client = get_gsheets_client()
    client.open_by_url(SHEET_URL).worksheet("Zleceniobiorcy").append_row(row_data)

# --- INTERFEJS APLIKACJI ---
st.set_page_config(layout="wide", page_title="Baza Przewoźników")
st.title("🚚 Zarządzanie Bazą Przewoźników")
st.markdown("Tutaj znajduje się słownik Twoich podwykonawców. Firmy dodane w tym miejscu będą dostępne na liście rozwijanej podczas generowania nowych Zleceń i CMR.")

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę z Google Sheets"):
        st.cache_data.clear()

st.markdown("---")

# --- FORMULARZ DODAWANIA NOWEGO PRZEWOŹNIKA ---
# Expander to zwijany panel - oszczędza miejsce na ekranie
with st.expander("➕ KLIKNIJ TUTAJ, ABY DODAĆ NOWEGO PRZEWOŹNIKA", expanded=False):
    with st.form("form_nowy_przewoznik"):
        st.info("Pamiętaj: Skrócona nazwa to ta, którą będziesz wybierać z listy. Pełna nazwa wydrukuje się na dokumentach.")
        col1, col2 = st.columns(2)
        with col1:
            skrot = st.text_input("Skrócona nazwa (np. Trans-Pol)")
            pelna_nazwa = st.text_area("Pełna nazwa firmy i NIP (np. Trans-Pol Sp. z o.o., NIP 123456789)")
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
                    # Ważne: Kolejność zapisu odpowiada domyślnym kolumnom w Twoim arkuszu
                    nowy_wiersz = [skrot, pelna_nazwa, ulica, miasto, kraj, nip, pojazd]
                    append_przewoznik(nowy_wiersz)
                    # Wymuszamy wyczyszczenie pamięci podręcznej, żeby tabela poniżej od razu pokazała nową firmę
                    st.cache_data.clear() 
                    st.success(f"Sukces! Dodano firmę {skrot} do bazy.")
            else:
                st.warning("⚠️ Skrócona nazwa oraz Pełna nazwa są wymagane!")

# --- WYŚWIETLANIE BAZY W TABELI ---
st.markdown("### 📋 Twoi Przewoźnicy")
df_przewoznicy = load_przewoznicy()

if not df_przewoznicy.empty:
    # Wyświetlamy ładną tabelę. use_container_width dopasuje ją do szerokości monitora
    st.dataframe(
        df_przewoznicy, 
        use_container_width=True, 
        hide_index=True,
        height=500
    )
    st.caption(f"Łącznie przewoźników w bazie: {len(df_przewoznicy)}")
else:
    st.info("Baza przewoźników jest pusta. Dodaj pierwszą firmę korzystając z formularza powyżej lub wpisując ją bezpośrednio w Google Sheets.")
