import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_miejsca():
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
    client = get_gsheets_client()
    client.open_by_url(SHEET_URL).worksheet("Miejsca").append_row(row_data)

# --- INTERFEJS APLIKACJI ---
st.set_page_config(layout="wide", page_title="Baza Miejsc V2")
st.title("🏢 Zarządzanie Bazą Kontrahentów i Miejsc")
st.markdown("V2.0: Dodano obsługę rampy i bezpośrednich kontaktów.")

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę"):
        st.cache_data.clear()

st.markdown("---")

# --- FORMULARZ DODAWANIA ---
with st.expander("➕ DODAĆ NOWE MIEJSCE / KONTRAHENTA", expanded=False):
    with st.form("form_nowe_miejsce"):
        col1, col2 = st.columns(2)
        with col1:
            skrot = st.text_input("Nazwa do listy (np. SQM Komorniki)")
            firma = st.text_input("Pełna nazwa firmy")
            ulica = st.text_input("Ulica i numer")
            rampa = st.selectbox("Czy na miejscu jest rampa?", ["TAK", "NIE", "BRAK DANYCH"])
        with col2:
            kod_pocztowy = st.text_input("Kod pocztowy")
            miasto = st.text_input("Miasto")
            kraj = st.text_input("Kraj", value="Polska")
            kontakt = st.text_input("Osoba kontaktowa / Tel (np. P.Dukiel +48...)")
            
        submit = st.form_submit_button("Zapisz do Google Sheets")
        
        if submit:
            if skrot and miasto:
                with st.spinner("Zapisywanie..."):
                    # Kolejność kolumn: Nazwa do listy, Nazwa pełna, Ulica, Kod, Miasto, Kraj, Osoba/Tel, Rampa
                    nowy_wiersz = [skrot, firma, ulica, kod_pocztowy, miasto, kraj, kontakt, rampa]
                    append_miejsce(nowy_wiersz)
                    st.cache_data.clear()
                    st.success(f"Dodano: {skrot}")
            else:
                st.warning("Nazwa i Miasto są wymagane!")

# --- TABELA ---
df_miejsca = load_miejsca()
if not df_miejsca.empty:
    st.dataframe(df_miejsca, use_container_width=True, hide_index=True)
