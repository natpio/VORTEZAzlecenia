import os
import string
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# ==========================================
# 🏛️ STYL MUZEALNY (WSTRZYKIWANIE CSS)
# ==========================================
def inject_custom_css():
    """Wstrzykuje muzealny styl CSS do każdej podstrony i widoku."""
    css_file = "style.css"
    # Szukamy pliku w głównym katalogu, niezależnie z którego poziomu odpalamy
    path = css_file if os.path.exists(css_file) else f"../{css_file}"
    
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Brak pliku stylów: {path}")

# ==========================================
# ⚙️ KONFIGURACJA GŁÓWNA
# ==========================================
# Link do bazy danych Google Sheets (najlepiej trzymać w st.secrets)
SHEET_URL = st.secrets.get("SHEET_URL", "WSTAW_SWOJ_LINK_DO_ARKUSZA_GOOGLE")

# ==========================================
# 🔐 AUTORYZACJA GOOGLE SHEETS
# ==========================================
@st.cache_resource
def get_gsheets_client():
    """Zwraca autoryzowanego klienta gspread na bazie Streamlit Secrets."""
    if "gcp_service_account" in st.secrets:
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scope
        )
        return gspread.authorize(creds)
    else:
        st.error("⚠️ Brak danych logowania GCP w st.secrets['gcp_service_account'].")
        return None

# ==========================================
# 📊 BAZA DANYCH (CRUD DLA GOOGLE SHEETS)
# ==========================================
@st.cache_data(ttl=60)
def fetch_data(sheet_name):
    """Pobiera dane z podanej zakładki arkusza i zwraca Pandas DataFrame."""
    client = get_gsheets_client()
    if client:
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
            records = sheet.get_all_records()
            return pd.DataFrame(records)
        except Exception as e:
            st.error(f"Błąd pobierania danych z arkusza {sheet_name}: {e}")
    return pd.DataFrame()

def append_data(sheet_name, row_data):
    """Dodaje nowy wiersz na końcu tabeli (Zlecenia, Miejsca, Przewoźnicy itp.)."""
    client = get_gsheets_client()
    if client:
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
            sheet.append_row(row_data)
            fetch_data.clear() # Czyścimy cache, by apka od razu pobrała nowe dane
            return True
        except Exception as e:
            st.error(f"Błąd zapisywania danych: {e}")
    return False

def update_row(sheet_name, row_index, row_data):
    """Nadpisuje istniejący wiersz (używane w trybie edycji)."""
    client = get_gsheets_client()
    if client:
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
            
            # Mapowanie kolumn od A do ZZ dla Google Sheets
            letters = list(string.ascii_uppercase) + [f"A{l}" for l in string.ascii_uppercase]
            col_end = letters[len(row_data) - 1]
            range_str = f"A{row_index}:{col_end}{row_index}"
            
            sheet.update(values=[row_data], range_name=range_str)
            fetch_data.clear()
            return True
        except Exception as e:
            st.error(f"Błąd aktualizacji wiersza {row_index}: {e}")
    return False

def delete_row(sheet_name, row_index):
    """Trwale usuwa wybrany wiersz z bazy (Zarządzanie kontrahentami)."""
    client = get_gsheets_client()
    if client:
        try:
            sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
            sheet.delete_rows(row_index)
            fetch_data.clear()
            return True
        except Exception as e:
            st.error(f"Błąd usuwania wiersza {row_index}: {e}")
    return False

# ==========================================
# 🔢 NUMERATOR ZLECEŃ
# ==========================================
def get_next_daily_number(date_str):
    """Zwraca kolejny, dynamiczny numer porządkowy zlecenia dla danego dnia."""
    df = fetch_data("Zlecenia")
    if not df.empty and 'Data wystawienia' in df.columns:
        # Filtrujemy zlecenia, które w dacie wystawienia mają dzisiejszy ciąg znaków
        dzisiejsze = df[df['Data wystawienia'].astype(str).str.startswith(date_str)]
        return len(dzisiejsze) + 1
    return 1

# ==========================================
# 🤖 SILNIK GOOGLE GEMINI AI
# ==========================================
@st.cache_resource
def init_ai_model():
    """Inicjalizuje model AI wykorzystywany w Skanerze Projektów."""
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Inicjalizujemy lekki i szybki model pod OCR i formatowanie JSON
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model
    else:
        st.error("⚠️ Brak klucza 'GEMINI_API_KEY' w pliku st.secrets.")
        return None
