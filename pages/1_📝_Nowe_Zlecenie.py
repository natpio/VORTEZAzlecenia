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

st.title("🚛 Dyspozycja Floty (Transport Główny na Event)")
st.markdown("Ten moduł służy do zamawiania transportu zbiorczego na całe targi/konferencję.")

with st.form("form_flota"):
    c1, c2 = st.columns(2)
    lista_eventow = sorted(df_projekty['Nazwa Eventu'].unique().tolist()) if not df_projekty.empty else []
    wybrany_event = c1.selectbox("Wybierz Event (Targi)", lista_eventow)
    opcje_trasy = c2.multiselect("Zakres operacji", ["Dostawa", "Postój", "Powrót"], default=["Dostawa"])
    
    st.divider()
    col1, col2, col3 = st.columns(3)
    przewoznik = col1.selectbox("Przewoźnik", df_p['Nazwa do listy'].tolist())
    skad = col2.selectbox("Załadunek", df_m['Nazwa do listy'].tolist())
    dokad = col3.selectbox("Rozładunek", df_m['Nazwa do listy'].tolist())
    
    stawka = st.number_input("Koszt całkowity transportu floty", min_value=0)
    nr_zlecenia = st.text_input("Numer Zlecenia", f"FLOTA/{datetime.now().strftime('%Y/%m')}/")
    uwagi = st.text_area("Lista projektów na naczepie / Dodatkowe uwagi")

    if st.form_submit_button("🚀 Zapisz Zlecenie Floty"):
        # P: ID Projektu (tutaj zapisujemy Nazwę Eventu), Q: Typ transportu, R: Stawka
        nowy_wiersz = [datetime.now().strftime("%Y-%m-%d %H:%M"), nr_zlecenia, "Moja Firma", przewoznik, skad, dokad, "", "", "Transport Zbiorczy", "", "", "", "", uwagi, "", wybrany_event, "FLOTA_MAIN", stawka]
        get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
        st.success(f"Zlecenie floty dla {wybrany_event} zostało zapisane.")
