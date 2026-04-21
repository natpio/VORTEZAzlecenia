import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Baza Kontrahentów | Zaopatrzenie")

# --- UKRYCIE DOMYŚLNEGO MENU I DEDYKOWANY PASEK BOCZNY (ZAOPATRZENIE) ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='color: #10b981;'>📦 ZAOPATRZENIE</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/5_📦_Kreator_Zaopatrzenia.py", label="Kreator Zaopatrzenia")
    st.page_link("pages/6_💰_Finanse_Projektu.py", label="Finanse Projektów (Koszty)")
    st.page_link("pages/7_🏢_Baza_Kontrahentow.py", label="Baza Kontrahentów / Miejsc")

# --- KONFIGURACJA BAZY DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_kontrahenci():
    try:
        client = get_gsheets_client()
        sh = client.open_by_url(SHEET_URL)
        return pd.DataFrame(sh.worksheet("Miejsca").get_all_records())
    except Exception as e:
        st.error(f"Błąd ładowania bazy kontrahentów: {e}")
        return pd.DataFrame()

# --- INTERFEJS APLIKACJI ---
st.title("🏢 Baza Kontrahentów i Lokalizacji")
st.markdown("Słownik miejsc, z których najczęściej wypożyczany jest sprzęt lub do których realizowane są zwroty.")

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę z chmury", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# --- FORMULARZ DODAWANIA KONTRAHENTA ---
with st.expander("➕ KLIKNIJ TUTAJ, ABY DODAĆ NOWEGO KONTRAHENTA/MIEJSCE", expanded=False):
    with st.form("form_add_kontrahent"):
        st.info("Dodanie kontrahenta tutaj sprawi, że będzie on od razu dostępny na rozwijanych listach w 'Kreatorze Zaopatrzenia'.")
        
        c1, c2 = st.columns(2)
        nazwa_skrocona = c1.text_input("Nazwa do listy (np. Rental-Pro Poznań) *Wymagane")
        pelna_nazwa = c2.text_input("Pełna nazwa firmy (Opcjonalnie)")
        
        d1, d2, d3 = st.columns(3)
        ulica = d1.text_input("Ulica")
        miasto = d2.text_input("Miasto")
        kraj = d3.text_input("Kraj", value="Polska")
        
        uwagi = st.text_input("Dodatkowe informacje (np. godziny otwarcia magazynu, telefon do handlowca)")
        
        submit_k = st.form_submit_button("Zapisz Kontrahenta do Bazy")
        
        if submit_k:
            if nazwa_skrocona:
                with st.spinner("Zapisywanie w systemie..."):
                    try:
                        # Dopasowanie do domyślnych 7 kolumn, które zwykle masz w zakładce 'Miejsca'
                        nowy_wiersz = [nazwa_skrocona, pelna_nazwa, ulica, miasto, kraj, uwagi, ""]
                        get_gsheets_client().open_by_url(SHEET_URL).worksheet("Miejsca").append_row(nowy_wiersz)
                        st.success(f"Dodano firmę '{nazwa_skrocona}' do słownika!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Nie udało się zapisać: {e}")
            else:
                st.warning("⚠️ Pole 'Nazwa do listy' jest wymagane!")

# --- WYŚWIETLANIE TABELI ---
st.markdown("### 📋 Lista Twoich Kontrahentów")
df_miejsca = load_kontrahenci()

if not df_miejsca.empty:
    st.dataframe(
        df_miejsca, 
        use_container_width=True, 
        hide_index=True,
        height=500
    )
    st.caption(f"Łącznie wpisów w bazie: {len(df_miejsca)}")
else:
    st.info("Baza kontrahentów jest pusta.")
