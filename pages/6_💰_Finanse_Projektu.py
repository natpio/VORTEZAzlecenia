import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(layout="wide", page_title="Koszty Projektu")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_data(ttl=30)
def load_all():
    sh = get_gsheets_client().open_by_url(SHEET_URL)
    return pd.DataFrame(sh.worksheet("Zlecenia").get_all_records()), pd.DataFrame(sh.worksheet("Projekty").get_all_records())

df_z, df_p = load_all()

st.title("💰 Kalkulator Kosztów Zaopatrzenia")
id_search = st.text_input("Wpisz ID Projektu, aby sprawdzić koszty zaopatrzenia:")

if id_search:
    # 1. Filtrujemy tylko zaopatrzenie (Inbound/Zwrot) dla tego ID
    df_filtered = df_z[(df_z['ID Projektu'].astype(str) == str(id_search)) & (df_z['Typ transportu'].str.contains("Inbound|Zwrot", na=False))]
    
    if not df_filtered.empty:
        # Sumowanie
        df_filtered['Stawka'] = pd.to_numeric(df_filtered['Stawka'], errors='coerce').fillna(0)
        koszt_in = df_filtered[df_filtered['Typ transportu'].str.contains("Inbound")]['Stawka'].sum()
        koszt_out = df_filtered[df_filtered['Typ transportu'].str.contains("Zwrot")]['Stawka'].sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Suma Kosztów Logistyki", f"{koszt_in + koszt_out:,.2f}")
        k2.metric("📦 Ściągnięcie sprzętu", f"{koszt_in:,.2f}")
        k3.metric("🔄 Koszt zwrotów", f"{koszt_out:,.2f}")
        
        st.dataframe(df_filtered[['Data wystawienia', 'Numer zlecenia', 'Miejsce Zaladunku', 'Miejsce Rozladunku', 'Typ transportu', 'Stawka']], use_container_width=True, hide_index=True)
    else:
        st.info("Nie znaleziono kosztów zaopatrzenia dla tego ID.")
