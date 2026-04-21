import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Historia Zleceń | Cargo")

# --- UKRYCIE DOMYŚLNEGO MENU I DEDYKOWANY PASEK BOCZNY (CARGO) ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# ---> ZAKTUALIZOWANY PASEK BOCZNY <---
with st.sidebar:
    st.markdown("<h2 style='color: #38bdf8;'>🚛 LOGISTYKA CARGO</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/1_🚛_Dyspozycja_Floty.py", label="Dyspozycja Floty (TARGI)")
    st.page_link("pages/8_🛠️_Obsluga_Zaopatrzenia.py", label="Obsługa Zaopatrzenia")
    st.page_link("pages/2_📄_Terminal_CMR.py", label="Terminal CMR")
    st.page_link("pages/3_🚚_Baza_Przewoznikow.py", label="Baza Przewoźników Cargo")
    # Ten link poniżej wyrzucał błąd - upewnij się, że nazwa na GitHubie to "4_📊_Historia_Zlecen_Cargo.py"
    st.page_link("pages/4_📊_Historia_Zlecen_Cargo.py", label="Historia Zleceń Cargo")

# --- KONFIGURACJA BAZY DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=30)
def load_cargo_history():
    """Pobiera zlecenia i filtruje TYLKO te dla Logistyki Cargo (TARGI)"""
    try:
        client = get_gsheets_client()
        sh = client.open_by_url(SHEET_URL)
        df = pd.DataFrame(sh.worksheet("Zlecenia").get_all_records())
        
        if not df.empty and 'Typ transportu' in df.columns:
            df_cargo = df[df['Typ transportu'] == "TARGI"]
            return df_cargo
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Błąd łączenia z arkuszem: {e}")
        return pd.DataFrame()

# --- INTERFEJS APLIKACJI ---
st.title("📊 Historia Zleceń Cargo")
st.markdown("Rejestr głównych transportów na wydarzenia. Baza odfiltrowana wyłącznie dla wyjazdów zbiorczych (TARGI).")

# Pobranie danych
df_history = load_cargo_history()

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę z chmury", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

if not df_history.empty:
    # --- STATYSTYKI SZYBKIE ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Wszystkich Zleceń Cargo", len(df_history))
    
    df_history['Stawka'] = pd.to_numeric(df_history['Stawka'], errors='coerce').fillna(0)
    suma_kosztow = df_history['Stawka'].sum()
    c2.metric("Suma Kosztów Transportu Cargo", f"{suma_kosztow:,.2f}")
    
    unikalne_eventy = df_history['ID Projektu'].nunique()
    c3.metric("Obsłużonych Eventów", unikalne_eventy)
    
    st.markdown("---")
    
    # --- FILTROWANIE BAZY ---
    st.markdown("### 🔍 Wyszukiwarka Zleceń")
    f1, f2, f3 = st.columns(3)
    
    lista_eventow = ["Wszystkie"] + sorted(df_history['ID Projektu'].astype(str).unique().tolist())
    lista_przewoznikow = ["Wszyscy"] + sorted(df_history['Zleceniobiorca'].astype(str).unique().tolist())
    
    filtr_event = f1.selectbox("Filtruj wg Eventu (Targów):", lista_eventow)
    filtr_przew = f2.selectbox("Filtruj wg Przewoźnika:", lista_przewoznikow)
    wyszukiwarka = f3.text_input("Szukaj w numerze zlecenia lub uwagach:")
    
    df_filtered = df_history.copy()
    
    if filtr_event != "Wszystkie":
        df_filtered = df_filtered[df_filtered['ID Projektu'] == filtr_event]
        
    if filtr_przew != "Wszyscy":
        df_filtered = df_filtered[df_filtered['Zleceniobiorca'] == filtr_przew]
        
    if wyszukiwarka:
        df_filtered = df_filtered[
            df_filtered['Numer zlecenia'].str.contains(wyszukiwarka, case=False, na=False) |
            df_filtered['Uwagi / Instrukcje'].str.contains(wyszukiwarka, case=False, na=False)
        ]
        
    # --- WYŚWIETLANIE TABELI ---
    kolumny_do_widoku = [
        'Data wystawienia', 'Numer zlecenia', 'ID Projektu', 
        'Zleceniobiorca', 'Miejsce Zaladunku', 'Miejsce Rozladunku', 
        'Stawka', 'Uwagi / Instrukcje'
    ]
    
    obecne_kolumny = [col for col in kolumny_do_widoku if col in df_filtered.columns]
    
    st.dataframe(
        df_filtered[obecne_kolumny].sort_values(by='Data wystawienia', ascending=False),
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    st.caption(f"Wyświetlam {len(df_filtered)} zleceń z bazy.")

else:
    st.info("Brak zarejestrowanych transportów Cargo (TARGI) w bazie. Wygeneruj pierwsze zlecenie w zakładce 'Dyspozycja Floty'.")
