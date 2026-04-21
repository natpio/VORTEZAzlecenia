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

st.title("🚛 Dyspozycja Floty - TARGI")
st.markdown("Zamówienie głównego transportu zbiorczego na wydarzenie.")

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
    
    st.markdown("**Dane Auta i Kierowcy:**")
    k1, k2, k3 = st.columns(3)
    nr_rej = k1.text_input("Nr rejestracyjny")
    kierowca = k2.text_input("Kierowca")
    tel_kierowcy = k3.text_input("Telefon")
    
    stawka = st.number_input("Koszt całkowity (Stawka)", min_value=0)
    nr_zlecenia = st.text_input("Numer Zlecenia", f"TARGI/{datetime.now().strftime('%Y/%m')}/")
    uwagi = st.text_area("Uwagi (Projekty na aucie, specyfikacja)")

    if st.form_submit_button("🚀 Zapisz Zlecenie"):
        dane_auta = f"{uwagi} | AUTO: {nr_rej}, KIER: {kierowca} ({tel_kierowcy})"
        # Zapisujemy "TARGI" w kolumnie Q
        nowy_wiersz = [
            datetime.now().strftime("%Y-%m-%d %H:%M"), nr_zlecenia, "Moja Firma", 
            przewoznik, skad, dokad, "", "", "Transport Zbiorczy", "", "", "", "", 
            dane_auta, "", wybrany_event, "TARGI", stawka
        ]
        get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
        st.success(f"Zlecenie główne na TARGI ({wybrany_event}) zapisane!")
