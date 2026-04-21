import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    """Autoryzacja w Google Sheets na podstawie st.secrets"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_zlecenia_history():
    """Pobiera historię wystawionych zleceń z bazy"""
    try:
        client = get_gsheets_client()
        spreadsheet = client.open_by_url(SHEET_URL)
        ws_zlecenia = spreadsheet.worksheet("Zlecenia")
        df_zlecenia = pd.DataFrame(ws_zlecenia.get_all_records())
        return df_zlecenia
    except Exception as e:
        st.error(f"Błąd łączenia z arkuszem Zleceń: {e}")
        return pd.DataFrame()

# --- INTERFEJS APLIKACJI ---
st.set_page_config(layout="wide", page_title="Historia Zleceń V2")
st.title("📊 Historia Zleceń i Projektów")
st.markdown("Archiwum wszystkich dokumentów. Zaktualizowano o widok ID Projektu i kosztów.")

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę z Google Sheets"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

df_zlecenia = load_zlecenia_history()

if not df_zlecenia.empty:
    # --- BEZPIECZEŃSTWO WSTECZNE (Dla starych zleceń) ---
    if 'ID Projektu' not in df_zlecenia.columns:
        df_zlecenia['ID Projektu'] = "Brak"
    if 'Typ transportu' not in df_zlecenia.columns:
        df_zlecenia['Typ transportu'] = "Brak"
    if 'Stawka' not in df_zlecenia.columns:
        df_zlecenia['Stawka'] = 0

    # --- STATYSTYKI ---
    st.markdown("### 📈 Podsumowanie")
    liczba_zlecen = len(df_zlecenia)
    
    # Odwracamy DataFrame, żeby najnowsze zlecenia były na samej górze
    df_zlecenia = df_zlecenia.iloc[::-1].reset_index(drop=True)
    
    ostatnie_zlecenie = df_zlecenia.iloc[0]['Numer zlecenia'] if 'Numer zlecenia' in df_zlecenia.columns else "Brak"
    ostatnia_data = df_zlecenia.iloc[0]['Data wystawienia'] if 'Data wystawienia' in df_zlecenia.columns else "Brak"

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric(label="Całkowita liczba zleceń", value=liczba_zlecen)
    kpi2.metric(label="Ostatni wygenerowany numer", value=ostatnie_zlecenie)
    kpi3.metric(label="Data ostatniego zlecenia", value=ostatnia_data)

    st.markdown("---")

    # --- WYSZUKIWARKA / FILTROWANIE ---
    st.markdown("### 🔎 Wyszukaj w archiwum")
    wyszukiwana_fraza = st.text_input("Wpisz ID Projektu, numer zlecenia lub przewoźnika:", "")

    if wyszukiwana_fraza:
        mask = df_zlecenia.apply(lambda row: row.astype(str).str.contains(wyszukiwana_fraza, case=False, na=False).any(), axis=1)
        df_wyswietlane = df_zlecenia[mask]
        st.success(f"Znaleziono wyników: {len(df_wyswietlane)}")
    else:
        df_wyswietlane = df_zlecenia

    # --- REORGANIZACJA KOLUMN ---
    # Układamy kolumny tak, by ID projektu i koszty były zaraz po numerze zlecenia
    kolumny_startowe = ['Data wystawienia', 'Numer zlecenia', 'ID Projektu', 'Typ transportu', 'Stawka', 'Zleceniobiorca', 'Miejsce Zaladunku', 'Miejsce Rozladunku']
    
    # Pobieramy resztę kolumn, które nie są w kolumnach startowych
    wszystkie_kolumny = df_wyswietlane.columns.tolist()
    pozostale_kolumny = [kol for kol in wszystkie_kolumny if kol not in kolumny_startowe]
    
    # Łączymy w nową, czytelną listę
    nowa_kolejnosc = kolumny_startowe + pozostale_kolumny
    
    df_wyswietlane = df_wyswietlane[nowa_kolejnosc]

    # --- TABELA DANYCH ---
    st.dataframe(
        df_wyswietlane,
        use_container_width=True,
        hide_index=True,
        height=600
    )

else:
    st.info("Baza zleceń jest pusta.")
