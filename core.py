import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# ==========================================
# ⚙️ VORTEX CORE ENGINE v3.0
# Serce systemu: Baza danych, Cache i AI
# ==========================================

SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

# --- 1. AUTORYZACJA GOOGLE SHEETS (SINGLETON) ---
@st.cache_resource
def get_gsheets_client():
    """Nawiązuje jedno, stałe połączenie z bazą danych, zamiast logować się co kliknięcie."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

# --- 2. INTELIGENTNE POBIERANIE DANYCH (CACHE) ---
@st.cache_data(ttl=60)
def fetch_data(sheet_name):
    """Pobiera dane z zakładki i trzyma je w pamięci RAM przez 60 sekund. Aplikacja przyspieszy 10-krotnie."""
    try:
        client = get_gsheets_client()
        sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df.dropna(how="all")
    except Exception as e:
        st.error(f"Błąd pobierania danych: {e}")
        return pd.DataFrame()

# --- 3. DODAWANIE DANYCH ---
def append_data(sheet_name, new_row_list):
    try:
        client = get_gsheets_client()
        sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
        sheet.append_row(new_row_list)
        fetch_data.clear() 
        return True
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
        return False

# --- 4. INICJALIZACJA AI (GEMINI) ---
def init_ai_model():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model
    except Exception as e:
        st.error("Nie znaleziono klucza API Gemini lub błąd inicjalizacji. Upewnij się, że masz poprawny klucz Gemini w st.secrets.")
        return None

# --- 5. LOGIKA BIZNESOWA (GENERATORY NUMERÓW) ---
def get_next_daily_number(prefix_date):
    """Oblicza kolejny numer zlecenia w danym dniu dla logistyków."""
    df = fetch_data("Zlecenia")
    if not df.empty and 'Data wystawienia' in df.columns:
        dzisiejsze = df[df['Data wystawienia'].astype(str).str.startswith(prefix_date)]
        return len(dzisiejsze) + 1
    return 1

# --- 6. AKTUALIZACJA ISTNIEJĄCYCH DANYCH ---
def update_row(sheet_name, row_index, new_row_data):
    """Aktualizuje konkretny wiersz w Google Sheets. row_index musi być numerem wiersza w arkuszu."""
    try:
        client = get_gsheets_client()
        sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
        # row_index w gspread odpowiada fizycznemu numerowi wiersza (1, 2, 3...)
        sheet.update(f"A{row_index}", [new_row_data])
        fetch_data.clear() # Czyścimy cache, żeby zmiany były widoczne od razu
        return True
    except Exception as e:
        st.error(f"⚠️ Błąd silnika (Update - {sheet_name}): {e}")
        return False

def delete_row(sheet_name, row_index):
    try:
        client = get_gsheets_client()
        sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
        sheet.delete_rows(row_index)
        fetch_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd usuwania: {e}")
        return False
