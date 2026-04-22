import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Baza Kontrahentów | Zaopatrzenie")
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none !important;}</style>""", unsafe_allow_html=True)

# ---> PASEK BOCZNY <---
with st.sidebar:
    st.markdown("<h2 style='color: #10b981;'>📦 ZAOPATRZENIE</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/5_📦_Zgloszenie_Zaopatrzenia.py", label="Zgłoś transport")
    st.page_link("pages/6_💰_Finanse_Projektu.py", label="Koszty Projektów")
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
        return pd.DataFrame(get_gsheets_client().open_by_url(SHEET_URL).worksheet("Miejsca").get_all_records())
    except Exception as e:
        st.error(f"Błąd ładowania bazy kontrahentów: {e}")
        return pd.DataFrame()

# --- INTERFEJS APLIKACJI ---
st.title("🏢 Baza Kontrahentów i Lokalizacji")
st.markdown("Słownik miejsc, z których najczęściej wypożyczany jest sprzęt lub realizowane są zwroty.")

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# --- FORMULARZ DODAWANIA NOWEGO KONTRAHENTA ---
with st.expander("➕ KLIKNIJ TUTAJ, ABY DODAĆ NOWE MIEJSCE", expanded=False):
    with st.form("form_add_kontrahent"):
        st.info("Pamiętaj: Nazwa krótka (do listy) to ta, która będzie wyświetlać się w rozwijanym menu podczas zgłaszania zapotrzebowania.")
        
        # Wiersz 1: Nazwy
        c1, c2 = st.columns(2)
        nazwa_skrocona = c1.text_input("Nazwa krótka (do listy) *Wymagane")
        pelna_nazwa = c2.text_input("Pełna nazwa firmy / Magazynu")
        
        # Wiersz 2: Adres (Rozdzielony kod i miasto!)
        d1, d2, d3, d4 = st.columns([2, 1, 1.5, 1.5])
        ulica = d1.text_input("Ulica i numer")
        kod_pocztowy = d2.text_input("Kod pocztowy")
        miasto = d3.text_input("Miasto")
        kraj = d4.text_input("Kraj", value="Polska")
        
        # Wiersz 3: Nowe pola z Google Sheets
        o1, o2 = st.columns([3, 1])
        osoba_tel = o1.text_input("Osoba / Tel (np. P.Kowalski +48...)")
        rampa = o2.selectbox("Rampa (TAK/NIE)", ["TAK", "NIE", "BRAK DANYCH"])
        
        if st.form_submit_button("Zapisz Kontrahenta do Bazy", type="primary"):
            if nazwa_skrocona:
                with st.spinner("Zapisywanie danych..."):
                    try:
                        # IDEALNE DOPASOWANIE DO 8 KOLUMN W GOOGLE SHEETS
                        nowy_wiersz = [
                            nazwa_skrocona, 
                            pelna_nazwa, 
                            ulica, 
                            kod_pocztowy, 
                            miasto, 
                            kraj, 
                            osoba_tel, 
                            rampa
                        ]
                        get_gsheets_client().open_by_url(SHEET_URL).worksheet("Miejsca").append_row(nowy_wiersz)
                        
                        st.success(f"Dodano kontrahenta: '{nazwa_skrocona}'!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Wystąpił błąd podczas zapisu: {e}")
            else:
                st.warning("⚠️ Pole 'Nazwa krótka (do listy)' jest absolutnie wymagane!")

# --- WYŚWIETLANIE BAZY W TABELI ---
st.markdown("### 📋 Aktualna Lista Kontrahentów")
df_miejsca = load_kontrahenci()

if not df_miejsca.empty:
    st.dataframe(
        df_miejsca, 
        use_container_width=True, 
        hide_index=True,
        height=500
    )
    st.caption(f"Łącznie miejsc w słowniku: {len(df_miejsca)}")
else:
    st.info("Baza kontrahentów jest w tej chwili pusta. Dodaj pierwsze miejsce, aby ułatwić pracę zaopatrzeniowcom.")
