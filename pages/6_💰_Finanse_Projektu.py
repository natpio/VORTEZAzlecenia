import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA ---
st.set_page_config(layout="wide", page_title="Finanse Projektu | Vortex")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_data():
    client = get_gsheets_client()
    sh = client.open_by_url(SHEET_URL)
    zlecenia = pd.DataFrame(sh.worksheet("Zlecenia").get_all_records())
    projekty = pd.DataFrame(sh.worksheet("Projekty").get_all_records())
    return zlecenia, projekty

# --- INTERFEJS ---
st.markdown("<h1 style='text-align: center; color: #38bdf8;'>VORTEX FINANCIAL TRACKER</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8;'>Panel kontroli kosztów i logistyki zwrotnej sprzętu eventowego</p>", unsafe_allow_html=True)
st.markdown("---")

df_zlecenia, df_projekty = load_data()

# WYSZUKIWARKA
col_search, col_empty = st.columns([1, 2])
wyszukiwane_id = col_search.text_input("🔍 Wpisz 5-cyfrowe ID Projektu:")

if wyszukiwane_id:
    # Zabezpieczenie przed pustym arkuszem Google
    if 'ID Projektu' not in df_projekty.columns:
        st.error("🚨 Błąd bazy danych: Brak kolumny 'ID Projektu'. Upewnij się, że w arkuszu Google jest przynajmniej jeden wypełniony wiersz pod nagłówkami.")
    else:
        # 1. Sprawdzanie Projektu
        projekt_info = df_projekty[df_projekty['ID Projektu'].astype(str) == str(wyszukiwane_id)]
        
        if not projekt_info.empty:
            nazwa_eventu = projekt_info.iloc[0]['Nazwa Eventu']
            st.success(f"**EVENT:** {nazwa_eventu} | **PROJEKT ID:** {wyszukiwane_id}")
            
            # 2. Filtrowanie Zleceń dla tego projektu
            if not df_zlecenia.empty and 'ID Projektu' in df_zlecenia.columns:
                zlecenia_projektu = df_zlecenia[df_zlecenia['ID Projektu'].astype(str) == str(wyszukiwane_id)]
                
                if not zlecenia_projektu.empty:
                    zlecenia_projektu['Stawka'] = pd.to_numeric(zlecenia_projektu['Stawka'], errors='coerce').fillna(0)
                    
                    koszt_inbound = zlecenia_projektu[zlecenia_projektu['Typ transportu'].str.contains("Inbound", na=False)]['Stawka'].sum()
                    koszt_zwrotow = zlecenia_projektu[zlecenia_projektu['Typ transportu'].str.contains("Zwrot", na=False)]['Stawka'].sum()
                    koszt_outbound = zlecenia_projektu[zlecenia_projektu['Typ transportu'].str.contains("Outbound", na=False)]['Stawka'].sum()
                    koszt_calkowity = koszt_inbound + koszt_zwrotow + koszt_outbound

                    st.markdown("### 📊 Podsumowanie Kosztów")
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Całkowity Koszt", f"{koszt_calkowity:,.2f} PLN/EUR")
                    k2.metric("📦 Ściągnięcie (Inbound)", f"{koszt_inbound:,.2f}")
                    k3.metric("🚛 Wyjazd (Outbound)", f"{koszt_outbound:,.2f}")
                    k4.metric("🔄 Zwroty (Return)", f"{koszt_zwrotow:,.2f}")

                    st.markdown("---")
                    st.dataframe(
                        zlecenia_projektu[['Data wystawienia', 'Numer zlecenia', 'Zleceniobiorca', 'Typ transportu', 'Stawka']],
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.info("Brak wystawionych zleceń dla tego projektu.")
            else:
                st.info("Baza zleceń nie zawiera jeszcze powiązań z tym projektem.")
        else:
            st.error("Nie znaleziono projektu o tym ID w bazie.")
