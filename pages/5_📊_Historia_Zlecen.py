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
st.set_page_config(layout="wide", page_title="Historia Zleceń")
st.title("📊 Historia Wystawionych Zleceń i CMR")
st.markdown("Archiwum wszystkich dokumentów wygenerowanych przez aplikację. Dane są synchronizowane z arkuszem Google Sheets.")

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę z Google Sheets"):
        st.cache_data.clear()

st.markdown("---")

df_zlecenia = load_zlecenia_history()

if not df_zlecenia.empty:
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
    wyszukiwana_fraza = st.text_input("Wpisz numer zlecenia, nazwę przewoźnika lub miejscowość, aby przefiltrować tabelę:", "")

    if wyszukiwana_fraza:
        # Filtrowanie po wszystkich kolumnach (zamieniamy na tekst małą literą dla łatwego szukania)
        mask = df_zlecenia.apply(lambda row: row.astype(str).str.contains(wyszukiwana_fraza, case=False, na=False).any(), axis=1)
        df_wyswietlane = df_zlecenia[mask]
        st.success(f"Znaleziono wyników: {len(df_wyswietlane)}")
    else:
        df_wyswietlane = df_zlecenia

    # --- TABELA DANYCH ---
    st.dataframe(
        df_wyswietlane,
        use_container_width=True,
        hide_index=True,
        height=600
    )

else:
    st.info("Baza zleceń jest jeszcze pusta. Przejdź do modułu 'Nowe Zlecenie', aby wystawić swój pierwszy dokument!")
