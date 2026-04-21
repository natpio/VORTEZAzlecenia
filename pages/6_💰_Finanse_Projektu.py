import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Finanse Projektów | Zaopatrzenie")

# --- UKRYCIE DOMYŚLNEGO MENU I DEDYKOWANY PASEK BOCZNY (ZAOPATRZENIE) ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# ---> NAPRAWIONY PASEK BOCZNY (Z poprawionym linkiem do pliku nr 5) <---
with st.sidebar:
    st.markdown("<h2 style='color: #10b981;'>📦 ZAOPATRZENIE</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/5_📦_Zgloszenie_Zaopatrzenia.py", label="Zgłoś transport")
    st.page_link("pages/6_💰_Finanse_Projektu.py", label="Koszty Projektów")
    st.page_link("pages/7_🏢_Baza_Kontrahentow.py", label="Baza Kontrahentów / Miejsc")

# --- KONFIGURACJA BAZY DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=30)
def load_finance_data():
    try:
        client = get_gsheets_client()
        sh = client.open_by_url(SHEET_URL)
        zlecenia = pd.DataFrame(sh.worksheet("Zlecenia").get_all_records())
        projekty = pd.DataFrame(sh.worksheet("Projekty").get_all_records())
        return zlecenia, projekty
    except Exception as e:
        st.error(f"Błąd ładowania bazy danych: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- ŁADOWANIE DANYCH ---
df_zlecenia, df_projekty = load_finance_data()

# --- INTERFEJS APLIKACJI ---
st.title("💰 Budżety i Koszty Zaopatrzenia")
st.markdown("Monitorowanie wydatków na logistykę sprzętu wypożyczonego. Wpisz numer projektu, aby sprawdzić pełne zestawienie kosztów.")

# WYSZUKIWARKA
col_search, col_empty = st.columns([1, 2])
wyszukiwane_id = col_search.text_input("🔍 Wpisz 5-cyfrowe ID Projektu:", max_chars=5)

st.markdown("---")

if wyszukiwane_id:
    # Zabezpieczenie przed błędami pustej bazy
    if df_projekty.empty or df_zlecenia.empty:
        st.warning("Baza danych ładuje się lub jest pusta. Spróbuj za chwilę.")
    elif 'ID Projektu' not in df_projekty.columns:
        st.error("🚨 Błąd bazy: Brak kolumny 'ID Projektu' w zakładce Projekty w Google Sheets.")
    else:
        # 1. Identyfikacja Projektu
        projekt_info = df_projekty[df_projekty['ID Projektu'].astype(str) == str(wyszukiwane_id)]
        
        if not projekt_info.empty:
            nazwa_eventu = projekt_info.iloc[0].get('Nazwa Eventu', 'Brak przypisanej nazwy')
            st.success(f"**EVENT / LOKALIZACJA:** {nazwa_eventu} | **PROJEKT ID:** {wyszukiwane_id}")
            
            # 2. Filtrowanie Zleceń TYLKO dla tego projektu
            df_zlecenia_projektu = df_zlecenia[df_zlecenia['ID Projektu'].astype(str) == str(wyszukiwane_id)].copy()
            
            if not df_zlecenia_projektu.empty:
                # Oczyszczenie formatu kwot (zamiana błędnych na 0)
                df_zlecenia_projektu['Stawka'] = pd.to_numeric(df_zlecenia_projektu['Stawka'], errors='coerce').fillna(0)
                
                # Obliczenia sumaryczne
                koszt_inbound = df_zlecenia_projektu[df_zlecenia_projektu['Typ transportu'].str.contains("Inbound", na=False)]['Stawka'].sum()
                koszt_zwrotow = df_zlecenia_projektu[df_zlecenia_projektu['Typ transportu'].str.contains("Zwrot", na=False)]['Stawka'].sum()
                calkowity_koszt = koszt_inbound + koszt_zwrotow
                
                # Sprawdzenie, czy są jakieś zgłoszenia oczekujące na wycenę przez logistyka
                oczekujace = df_zlecenia_projektu[df_zlecenia_projektu['Typ transportu'] == "ZAOP_DO_WYCENY"]
                
                # 3. Wyświetlanie Metryk
                st.markdown("### 📊 Podsumowanie Kosztów Projektu")
                k1, k2, k3 = st.columns(3)
                k1.metric("Suma Kosztów Zaopatrzenia", f"{calkowity_koszt:,.2f} PLN")
                k2.metric("📦 Ściągnięcie (Inbound)", f"{koszt_inbound:,.2f}")
                k3.metric("🔄 Zwroty (Outbound)", f"{koszt_zwrotow:,.2f}")
                
                if not oczekujace.empty:
                    st.warning(f"⚠️ **Uwaga:** Ten projekt posiada {len(oczekujace)} transport(ów) oczekujących na wycenę u Logistyka. Całkowity koszt ulegnie zmianie!")
                
                # 4. Tabela ze szczegółami
                st.markdown("---")
                st.markdown("### 📋 Rejestr Operacji Logistycznych (Szczegóły)")
                
                # Wybieramy kluczowe kolumny do wyświetlenia
                kolumny_do_tabeli = ['Data wystawienia', 'Numer zlecenia', 'Miejsce Zaladunku', 'Miejsce Rozladunku', 'Typ transportu', 'Zleceniobiorca', 'Stawka']
                obecne_kolumny = [kol for kol in kolumny_do_tabeli if kol in df_zlecenia_projektu.columns]
                
                # Wyświetlamy tabelę, sortując od najnowszych
                st.dataframe(
                    df_zlecenia_projektu[obecne_kolumny].sort_values(by='Data wystawienia', ascending=False),
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("Brak przypisanych kosztów logistyki zaopatrzeniowej dla tego projektu.")
        else:
            st.error("Wprowadzone ID Projektu nie istnieje w głównej Bazie Projektów.")
