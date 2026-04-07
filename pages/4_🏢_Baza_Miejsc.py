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
def load_miejsca():
    """Pobiera wszystkie dane z zakładki Miejsca"""
    try:
        client = get_gsheets_client()
        spreadsheet = client.open_by_url(SHEET_URL)
        ws = spreadsheet.worksheet("Miejsca")
        df = pd.DataFrame(ws.get_all_records())
        return df
    except Exception as e:
        st.error(f"Błąd łączenia z arkuszem Miejsca: {e}")
        return pd.DataFrame()

def append_miejsce(row_data):
    """Dopisuje nowy wiersz do bazy miejsc"""
    client = get_gsheets_client()
    client.open_by_url(SHEET_URL).worksheet("Miejsca").append_row(row_data)

# --- INTERFEJS APLIKACJI ---
st.set_page_config(layout="wide", page_title="Baza Miejsc")
st.title("🏢 Zarządzanie Bazą Załadunków i Rozładunków")
st.markdown("Tutaj znajduje się słownik wszystkich adresów używanych w zleceniach. Nowo dodane miejsca natychmiast pojawią się na listach rozwijanych w głównym module aplikacji.")

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę z Google Sheets"):
        st.cache_data.clear()

st.markdown("---")

# --- FORMULARZ DODAWANIA NOWEGO MIEJSCA ---
with st.expander("➕ KLIKNIJ TUTAJ, ABY DODAĆ NOWE MIEJSCE / ADRES", expanded=False):
    with st.form("form_nowe_miejsce"):
        st.info("Nazwa skrócona posłuży Ci do łatwego wyszukiwania na liście w formularzu Zlecenia.")
        col1, col2 = st.columns(2)
        with col1:
            skrot = st.text_input("Nazwa do listy (np. Magazyn Amazon WRO1)")
            firma = st.text_input("Pełna nazwa firmy (Odbiorcy/Nadawcy na miejscu)")
            ulica = st.text_input("Ulica i numer")
        with col2:
            kod_pocztowy = st.text_input("Kod pocztowy")
            miasto = st.text_input("Miasto")
            kraj = st.text_input("Kraj", value="Polska")
            kontakt = st.text_input("Osoba kontaktowa / Telefon (Opcjonalnie)")
            
        submit = st.form_submit_button("Zapisz Miejsce do Bazy (Google Sheets)")
        
        if submit:
            if skrot and miasto:
                with st.spinner("Zapisywanie adresu do chmury..."):
                    # Kolejność zapisu odpowiadająca kolumnom w Twojej zakładce "Miejsca"
                    nowy_wiersz = [skrot, firma, ulica, kod_pocztowy, miasto, kraj, kontakt]
                    append_miejsce(nowy_wiersz)
                    st.cache_data.clear() # Wymusza odświeżenie widoku
                    st.success(f"Sukces! Dodano lokalizację '{skrot}' do bazy.")
            else:
                st.warning("⚠️ Nazwa do listy oraz Miasto są polami obowiązkowymi!")

# --- WYŚWIETLANIE BAZY W TABELI ---
st.markdown("### 📋 Twoje zapisane lokalizacje")
df_miejsca = load_miejsca()

if not df_miejsca.empty:
    st.dataframe(
        df_miejsca, 
        use_container_width=True, 
        hide_index=True,
        height=500
    )
    st.caption(f"Łącznie zapisanych adresów: {len(df_miejsca)}")
else:
    st.info("Baza miejsc jest obecnie pusta. Dodaj pierwszy adres korzystając z panelu powyżej.")
