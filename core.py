import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Stały adres URL bazy danych Google Sheets
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit#gid=0"

def get_connection():
    """Inicjalizuje i zwraca połączenie z Google Sheets."""
    return st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def fetch_data(worksheet_name):
    """Pobiera dane z określonego arkusza."""
    try:
        conn = get_connection()
        # Jawne wskazanie spreadsheet=SPREADSHEET_URL eliminuje błędy konfiguracji połączenia
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name)
        return df.dropna(how="all") 
    except Exception as e:
        st.error(f"Błąd podczas pobierania danych z arkusza '{worksheet_name}': {e}")
        return pd.DataFrame()

def append_data(worksheet_name, new_row_list):
    """Dodaje nowy wiersz na końcu arkusza."""
    try:
        conn = get_connection()
        # Pobieramy najświeższe dane (ttl=0), aby zachować ciągłość wierszy
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name, ttl=0).dropna(how="all")
        
        # Walidacja długości wiersza względem liczby kolumn
        if len(new_row_list) != len(df.columns):
            if len(new_row_list) < len(df.columns):
                new_row_list.extend([""] * (len(df.columns) - len(new_row_list)))
            else:
                new_row_list = new_row_list[:len(df.columns)]

        new_row_df = pd.DataFrame([new_row_list], columns=df.columns)
        updated_df = pd.concat([df, new_row_df], ignore_index=True)
        
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name, data=updated_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd podczas dodawania danych do arkusza: {e}")
        return False

def get_next_daily_number(date_str):
    """Oblicza kolejny numer zlecenia dla danego dnia."""
    try:
        conn = get_connection()
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Zlecenia", ttl=0)
        if df.empty:
            return 1
        
        # Zakładamy, że data utworzenia jest w pierwszej kolumnie
        kolumna_daty = 'Data utworzenia' if 'Data utworzenia' in df.columns else df.columns[0]
        dzisiejsze = df[df[kolumna_daty].astype(str).str.startswith(date_str)]
        return len(dzisiejsze) + 1
    except:
        return 1

def update_data(worksheet_name, identifier_col, identifier_val, new_data_dict):
    """Aktualizuje istniejący wiersz na podstawie identyfikatora."""
    try:
        conn = get_connection()
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name, ttl=0).dropna(how="all")
        
        if identifier_col not in df.columns:
            st.error(f"Kolumna '{identifier_col}' nie została znaleziona.")
            return False
            
        mask = df[identifier_col].astype(str) == str(identifier_val)
        if not mask.any():
            st.error(f"Nie znaleziono rekordu o numerze: {identifier_val}")
            return False
            
        # Mapowanie i aktualizacja pól w DataFrame
        for col, val in new_data_dict.items():
            if col in df.columns:
                df.loc[mask, col] = val
        
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd podczas aktualizacji rekordu: {e}")
        return False

def delete_data(worksheet_name, identifier_col, identifier_val):
    """Trwale usuwa wiersz z arkusza."""
    try:
        conn = get_connection()
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name, ttl=0).dropna(how="all")
        
        if identifier_col not in df.columns:
            st.error(f"Kolumna '{identifier_col}' nie istnieje.")
            return False
            
        # Filtrowanie - usunięcie rekordu o podanym ID
        df_updated = df[df[identifier_col].astype(str) != str(identifier_val)]
        
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name, data=df_updated)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd podczas usuwania rekordu: {e}")
        return False
