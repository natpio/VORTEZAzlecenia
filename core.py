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
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"⚠️ Błąd silnika (Odczyt - {sheet_name}): {e}")
        return pd.DataFrame()

# --- 3. ZAPISYWANIE DANYCH ---
def append_data(sheet_name, row_data):
    """Bezpiecznie wysyła wiersz do bazy i wymusza odświeżenie pamięci (żeby listy od razu widziały zmianę)."""
    try:
        client = get_gsheets_client()
        sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
        sheet.append_row(row_data)
        fetch_data.clear() # Czyści stary cache, wymuszając pobranie nowych danych
        return True
    except Exception as e:
        st.error(f"⚠️ Błąd silnika (Zapis - {sheet_name}): {e}")
        return False

# --- 4. AUTORYZACJA SZTUCZNEJ INTELIGENCJI ---
@st.cache_resource
def init_ai_model():
    """Uruchamia najnowszy model Google Gemini."""
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return genai.GenerativeModel('models/gemini-2.5-flash')
    except Exception as e:
        st.error(f"⚠️ Błąd silnika (AI): Brak lub niepoprawny klucz Gemini w st.secrets.")
        return None

# --- 5. LOGIKA BIZNESOWA (GENERATORY NUMERÓW) ---
def get_next_daily_number(prefix_date):
    """Oblicza kolejny numer zlecenia w danym dniu dla logistyków."""
    df = fetch_data("Zlecenia")
    if not df.empty and 'Data wystawienia' in df.columns:
        dzisiejsze = df[df['Data wystawienia'].astype(str).str.startswith(prefix_date)]
        return len(dzisiejsze) + 1
    return 1
