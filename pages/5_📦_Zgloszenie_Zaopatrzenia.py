import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Zgłoszenie Zaopatrzenia")

# --- UKRYCIE DOMYŚLNEGO MENU ---
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none !important;}</style>""", unsafe_allow_html=True)

# --- PASEK BOCZNY (ZAOPATRZENIE) ---
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

def get_next_daily_number():
    """Sprawdza łączną liczbę wpisów z dzisiaj, aby nadać kolejny numer (01, 02...)"""
    client = get_client()
    ws = client.open_by_url(SHEET_URL).worksheet("Zlecenia")
    dzisiaj = datetime.now().strftime("%Y-%m-%d")
    df = pd.DataFrame(ws.get_all_records())
    
    if not df.empty and 'Data wystawienia' in df.columns:
        dzisiejsze = df[df['Data wystawienia'].astype(str).str.startswith(dzisiaj)]
        return len(dzisiejsze) + 1
    return 1

@st.cache_data(ttl=30)
def load_miejsca():
    try:
        return pd.DataFrame(get_client().open_by_url(SHEET_URL).worksheet("Miejsca").get_all_records())
    except Exception as e:
        st.error(f"Błąd łączenia z bazą miejsc: {e}")
        return pd.DataFrame()

miejsca = load_miejsca()

# --- INTERFEJS APLIKACJI ---
st.title("➕ Nowe Zgłoszenie Transportu (CRG)")
st.markdown("Wypełnij dane, aby przesłać zapotrzebowanie do działu logistyki.")

with st.form("form_req", border=True):
    # NOWOŚĆ: Wybór opiekuna zlecenia
    st.subheader("Opiekun zlecenia")
    logistyk = st.radio("Kto zajmuje się tym zgłoszeniem?", ["PD", "PK"], horizontal=True)
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    id_p = c1.text_input("ID Projektu (5 cyfr)", max_chars=5)
    
    lista_miejsc = miejsca['Nazwa do listy'].tolist() if not miejsca.empty else []
    kontrahent = c2.selectbox("Miejsce (Skąd/Dokąd)", lista_miejsc)
    
    d1, d2 = st.columns(2)
    data_gotowosci = d1.date_input("Data gotowości sprzętu")
    kierunek = d2.radio("Typ operacji:", ["Inbound (Do nas)", "Zwrot (Do kontrahenta)"])
    
    opis = st.text_area("Szczegóły (Co transportujemy?)")
    
    submit_btn = st.form_submit_button("🚀 Wyślij do Wyceny i Realizacji", type="primary")
    
    if submit_btn:
        if len(id_p) >= 4 and kontrahent:
            with st.spinner("Generowanie unikalnego numeru CRG..."):
                try:
                    # 1. Pobranie numeru dnia
                    kolejny = get_next_daily_number()
                    
                    # 2. Budowa numeru według Twojego nowego standardu:
                    # CRG + ROK / MIESIĄC_DZIEŃ / INICJAŁY_NUMER
                    rok = datetime.now().strftime('%y')
                    mc_dzien = datetime.now().strftime('%m%d')
                    seq = f"{kolejny:02d}"
                    
                    # Przykład: CRG26/0421/PD01
                    nr_zlecenia = f"CRG{rok}/{mc_dzien}/{logistyk}{seq}"
                    
                    # 3. Ustalanie trasy
                    m_zal = kontrahent if "Inbound" in kierunek else "MAGAZYN WŁASNY"
                    m_roz = "MAGAZYN WŁASNY" if "Inbound" in kierunek else kontrahent
                    
                    # 4. Zapis wiersza
                    nowy_wiersz = [
                        datetime.now().strftime("%Y-%m-%d %H:%M"), 
                        nr_zlecenia, 
                        "ZAOPATRZENIE", 
                        "", # Przewoźnik (puste do wyceny)
                        m_zal, 
                        m_roz, 
                        str(data_gotowosci), 
                        "", 
                        "Sprzęt Wypożyczony", 
                        "", "", "", "", 
                        f"Opiekun: {logistyk} | {opis}", 
                        "", 
                        id_p, 
                        "ZAOP_DO_WYCENY", 
                        0
                    ]
                    
                    get_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
                    st.success(f"Zgłoszenie zarejestrowane! Numer: **{nr_zlecenia}**")
                    st.cache_data.clear()
                    
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")
        else:
            st.warning("Uzupełnij ID Projektu i wybierz Miejsce!")
