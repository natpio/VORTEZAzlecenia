import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# ==========================================
# ⚙️ VORTEX CORE ENGINE 
# ==========================================

SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

# --- 1. AUTORYZACJA GOOGLE SHEETS ---
@st.cache_resource
def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

# --- 2. POBIERANIE DANYCH ---
@st.cache_data(ttl=60)
def fetch_data(sheet_name):
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
        st.cache_data.clear()
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
        st.error("Nie znaleziono klucza API Gemini lub błąd inicjalizacji.")
        return None

# --- 5. GENERATOR NUMERÓW ---
def get_next_daily_number(prefix_date):
    df = fetch_data("Zlecenia")
    if not df.empty:
        kolumna = 'Data utworzenia' if 'Data utworzenia' in df.columns else df.columns[0]
        dzisiejsze = df[df[kolumna].astype(str).str.startswith(prefix_date)]
        return len(dzisiejsze) + 1
    return 1

# --- 6. ORYGINALNE FUNKCJE AKTUALIZACJI (np. dla Bazy Przewoźników) ---
def update_row(sheet_name, row_index, new_row_data):
    try:
        client = get_gsheets_client()
        sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
        sheet.update(f"A{row_index}", [new_row_data])
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Błąd aktualizacji: {e}")
        return False

def delete_row(sheet_name, row_index):
    try:
        client = get_gsheets_client()
        sheet = client.open_by_url(SHEET_URL).worksheet(sheet_name)
        sheet.delete_rows(row_index)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd usuwania: {e}")
        return False

# ==========================================
# NOWE FUNKCJE DLA NOWEJ HISTORII ZLECEŃ
# ==========================================
def update_data(worksheet_name, identifier_col, identifier_val, new_data_dict):
    try:
        client = get_gsheets_client()
        sheet = client.open_by_url(SHEET_URL).worksheet(worksheet_name)
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        
        if identifier_col not in df.columns: return False
        
        # Szukamy indeksu (+2 ponieważ gspread liczy od 1, a wiersz 1 to nagłówki)
        matching_idx = df.index[df[identifier_col].astype(str) == str(identifier_val)].tolist()
        if not matching_idx: return False
        row_idx = matching_idx[0] + 2
        
        current_row = sheet.row_values(row_idx)
        headers = sheet.row_values(1)
        
        while len(current_row) < len(headers): current_row.append("")
        
        for col, val in new_data_dict.items():
            if col in headers:
                col_idx = headers.index(col)
                current_row[col_idx] = val
                
        sheet.update(f"A{row_idx}", [current_row])
        st.cache_data.clear()
        return True
    except Exception as e:
        return False

def delete_data(worksheet_name, identifier_col, identifier_val):
    try:
        client = get_gsheets_client()
        sheet = client.open_by_url(SHEET_URL).worksheet(worksheet_name)
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        
        if identifier_col not in df.columns: return False
        
        matching_idx = df.index[df[identifier_col].astype(str) == str(identifier_val)].tolist()
        if not matching_idx: return False
        row_idx = matching_idx[0] + 2
        
        sheet.delete_rows(row_idx)
        st.cache_data.clear()
        return True
    except Exception as e:
        return False
