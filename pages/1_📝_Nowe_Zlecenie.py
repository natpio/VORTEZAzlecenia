import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA ---
st.set_page_config(layout="wide", page_title="Dyspozycja Floty")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_data():
    client = get_gsheets_client()
    sh = client.open_by_url(SHEET_URL)
    return (pd.DataFrame(sh.worksheet("Zleceniobiorcy").get_all_records()), 
            pd.DataFrame(sh.worksheet("Miejsca").get_all_records()), 
            pd.DataFrame(sh.worksheet("Projekty").get_all_records()))

df_p, df_m, df_projekty = load_data()

st.title("🚛 Dyspozycja Floty (Transport Główny)")
st.markdown("Ten moduł służy do zamawiania transportu zbiorczego na Event.")

with st.form("form_flota"):
    c1, c2 = st.columns(2)
    # Wybór Eventu (unikalne nazwy z bazy projektów)
    lista_eventow = sorted(df_projekty['Nazwa Eventu'].unique().tolist()) if not df_projekty.empty else []
    wybrany_event = c1.selectbox("Wybierz Event (Targi)", lista_eventow)
    
    # Szczegóły trasy
    opcje_trasy = c2.multiselect("Typ operacji", ["Dostawa", "Postój (Auto-Magazyn)", "Odbiór/Powrót"], default=["Dostawa"])
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    przewoznik = col1.selectbox("Przewoźnik", df_p['Nazwa do listy'].tolist() if not df_p.empty else [])
    skad = col2.selectbox("Załadunek", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])
    dokad = col3.selectbox("Rozładunek", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])
    
    stawka = st.number_input("Koszt całkowity transportu (Stawka)", min_value=0)
    nr_zlecenia = st.text_input("Numer Zlecenia", f"FLOTA/{datetime.now().strftime('%Y/%m')}/")
    uwagi = st.text_area("Co dokładnie jedzie? (Np. Projekty: 11112, 11115, 12001)")

    if st.form_submit_button("🚀 Zapisz Zlecenie Floty"):
        # Zapisujemy do Google Sheets (Kolumna Q: Typ transportu -> 'Główny/Flota', Kolumna P: ID Projektu -> Nazwa Eventu)
        nowy_wiersz = [datetime.now().strftime("%Y-%m-%d %H:%M"), nr_zlecenia, "Moja Firma", przewoznik, skad, dokad, "", "", "Transport Zbiorczy", "", "", "", "", uwagi, "", wybrany_event, "FLOTA_MAIN", stawka]
        get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
        st.success("Zlecenie transportu zbiorczego zapisane!")
