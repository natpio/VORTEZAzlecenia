import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

def get_connection():
    """Zwraca połączenie z Google Sheets."""
    return st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def fetch_data(worksheet_name):
    """Pobiera dane z określonego arkusza (z użyciem pamięci podręcznej)."""
    try:
        conn = get_connection()
        df = conn.read(worksheet=worksheet_name)
        # Odrzucamy całkowicie puste wiersze, które Google Sheets czasami dodaje
        return df.dropna(how="all") 
    except Exception as e:
        st.error(f"Błąd podczas pobierania danych z arkusza '{worksheet_name}': {e}")
        return pd.DataFrame()

def append_data(worksheet_name, new_row_list):
    """Dodaje nowy wiersz na końcu określonego arkusza."""
    try:
        conn = get_connection()
        # Pobieramy obecne dane bez cache'u (ttl=0), żeby mieć najświeższą wersję i uniknąć nadpisania
        df = conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
        
        # Zabezpieczenie przed niezgodnością liczby kolumn
        if len(new_row_list) != len(df.columns):
            # Jeśli lista ma mniej elementów, dopelniamy ją pustymi stringami
            if len(new_row_list) < len(df.columns):
                new_row_list.extend([""] * (len(df.columns) - len(new_row_list)))
            else:
                new_row_list = new_row_list[:len(df.columns)]

        # Tworzymy jednowierszowy DataFrame z nowymi danymi
        new_row_df = pd.DataFrame([new_row_list], columns=df.columns)
        
        # Łączymy stary DataFrame z nowym wierszem
        updated_df = pd.concat([df, new_row_df], ignore_index=True)
        
        # Wysyłamy do Google Sheets
        conn.update(worksheet=worksheet_name, data=updated_df)
        
        # Czyścimy cache, aby aplikacja od razu widziała nowe dane we wszystkich modułach
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd podczas dodawania danych do arkusza '{worksheet_name}': {e}")
        return False

def get_next_daily_number(date_str):
    """
    Oblicza kolejny numer zlecenia w danym dniu (dla inkrementacji np. P01, P02).
    """
    try:
        df = fetch_data("Zlecenia")
        if df.empty:
            return 1
            
        # Szukamy kolumny przechowującej datę (zazwyczaj to pierwsza kolumna w logach)
        kolumna_daty = 'Data utworzenia' if 'Data utworzenia' in df.columns else df.columns[0]

        # Filtrujemy zlecenia utworzone dzisiejszego dnia
        dzisiejsze_zlecenia = df[df[kolumna_daty].astype(str).str.startswith(date_str)]
        return len(dzisiejsze_zlecenia) + 1
    except Exception as e:
        st.warning(f"Błąd przy obliczaniu numeru zlecenia (fallback do 1): {e}")
        return 1

def update_data(worksheet_name, identifier_col, identifier_val, new_data_dict):
    """Aktualizuje wiersz w arkuszu na podstawie unikalnego identyfikatora."""
    try:
        conn = get_connection()
        df = conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
        
        if identifier_col not in df.columns:
            st.error(f"Kolumna '{identifier_col}' nie istnieje w arkuszu '{worksheet_name}'")
            return False
            
        # Znalezienie wiersza do aktualizacji
        mask = df[identifier_col].astype(str) == str(identifier_val)
        if not mask.any():
            st.error(f"Nie znaleziono rekordu o ID: {identifier_val}")
            return False
            
        # Aktualizacja wartości w DataFrame na podstawie słownika zmian
        for col, val in new_data_dict.items():
            if col in df.columns:
                df.loc[mask, col] = val
        
        # Zapisanie całego DataFrame do arkusza
        conn.update(worksheet=worksheet_name, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd podczas aktualizacji rekordu: {e}")
        return False

def delete_data(worksheet_name, identifier_col, identifier_val):
    """Usuwa wiersz z arkusza na podstawie unikalnego identyfikatora."""
    try:
        conn = get_connection()
        df = conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
        
        if identifier_col not in df.columns:
            st.error(f"Kolumna '{identifier_col}' nie istnieje.")
            return False
            
        # Filtrowanie - zostawiamy wszystko OPRÓCZ usuwanego rekordu
        df_updated = df[df[identifier_col].astype(str) != str(identifier_val)]
        
        # Nadpisanie arkusza bez tego wiersza
        conn.update(worksheet=worksheet_name, data=df_updated)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd podczas usuwania rekordu: {e}")
        return False
