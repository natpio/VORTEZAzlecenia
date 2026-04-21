import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Zgłoszenie Zaopatrzenia")

# --- UKRYCIE DOMYŚLNEGO MENU ---
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none !important;}</style>""", unsafe_allow_html=True)

# --- POPRAWIONY PASEK BOCZNY (ZAOPATRZENIE) ---
with st.sidebar:
    st.markdown("<h2 style='color: #10b981;'>📦 ZAOPATRZENIE</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/5_📦_Zgloszenie_Zaopatrzenia.py", label="Zgłoś transport")
    st.page_link("pages/6_💰_Finanse_Projektu.py", label="Koszty Projektów")
    st.page_link("pages/7_🏢_Baza_Kontrahentow.py", label="Baza Kontrahentów / Miejsc")

# --- BAZA DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=30)
def load_miejsca():
    try:
        return pd.DataFrame(get_client().open_by_url(SHEET_URL).worksheet("Miejsca").get_all_records())
    except Exception as e:
        st.error(f"Błąd łączenia z bazą miejsc: {e}")
        return pd.DataFrame()

miejsca = load_miejsca()

# --- INTERFEJS APLIKACJI ---
st.title("➕ Nowe Zgłoszenie Transportu")
st.markdown("Wypełnij poniższe dane. Twoje zgłoszenie trafi do działu logistyki w celu wyceny i organizacji przewoźnika.")

with st.form("form_req", border=True):
    id_p = st.text_input("ID Projektu (5 cyfr)", max_chars=5)
    
    lista_miejsc = miejsca['Nazwa do listy'].tolist() if not miejsca.empty else []
    kontrahent = st.selectbox("Skąd lub dokąd transportujemy?", lista_miejsc)
    
    d1, d2 = st.columns(2)
    data = d1.date_input("Data gotowości sprzętu")
    kierunek = d2.radio("Kierunek:", ["Inbound (Przywóz do nas)", "Zwrot (Odesłanie do kontrahenta)"])
    
    opis = st.text_area("Co dokładnie jedzie? (Opis sprzętu, ilość, uwagi)")
    
    submit_btn = st.form_submit_button("🚀 Wyślij do Logistyka")
    
    if submit_btn:
        if len(id_p) >= 4 and kontrahent:
            # Generowanie unikalnego numeru referencyjnego
            nr = f"REQ/{id_p}/{datetime.now().strftime('%d%H%M')}"
            
            # Ustalanie trasy na podstawie kierunku
            m_zal = kontrahent if "Inbound" in kierunek else "MAGAZYN WŁASNY"
            m_roz = "MAGAZYN WŁASNY" if "Inbound" in kierunek else kontrahent
            
            # Tworzenie wiersza danych do wysłania
            nowy_wiersz = [
                datetime.now().strftime("%Y-%m-%d %H:%M"), # A: Data wystawienia
                nr,                                        # B: Numer zlecenia
                "ZAOPATRZENIE",                            # C: Dział Zgłaszający
                "",                                        # D: Przewoźnik (zostawiamy puste dla logistyka)
                m_zal,                                     # E: Załadunek
                m_roz,                                     # F: Rozładunek
                str(data),                                 # G: Data gotowości
                "",                                        # H: Puste
                "Sprzęt Wypożyczony",                      # I: Rodzaj
                "", "", "", "",                            # J, K, L, M
                opis,                                      # N: Uwagi
                "",                                        # O: Hash
                id_p,                                      # P: ID Projektu
                "ZAOP_DO_WYCENY",                          # Q: Status (Kluczowe dla logistyka!)
                0                                          # R: Koszt (początkowo 0)
            ]
            
            with st.spinner("Wysyłanie zgłoszenia do bazy..."):
                try:
                    get_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
                    st.success(f"Sukces! Zgłoszenie {nr} zostało wysłane do logistyka.")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Nie udało się wysłać zgłoszenia: {e}")
        else:
            st.warning("⚠️ Uzupełnij poprawnie ID Projektu (min. 4 znaki) oraz miejsce!")
