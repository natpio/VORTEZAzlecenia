import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(layout="wide", page_title="Logistyka Zaopatrzenia")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_gsheets_client()
sh = client.open_by_url(SHEET_URL)
df_projekty = pd.DataFrame(sh.worksheet("Projekty").get_all_records())
df_m = pd.DataFrame(sh.worksheet("Miejsca").get_all_records())

st.title("📦 Logistyka Zaopatrzenia (Sprzęt Wypożyczony)")
st.markdown("Śledzenie kosztów sprowadzenia i zwrotu sprzętu pod konkretne ID Projektu.")

with st.form("form_zaopatrzenie"):
    id_projektu = st.text_input("Wpisz ID Projektu (5 cyfr)")
    
    c1, c2 = st.columns(2)
    kontrahent = c1.selectbox("Od kogo sprzęt?", df_m['Nazwa do listy'].tolist())
    typ_ruchu = c2.selectbox("Kierunek", ["Inbound (Do nas)", "Zwrot (Do kontrahenta)"])
    
    stawka = st.number_input("Koszt transportu (np. kurier, bus)", min_value=0)
    opis = st.text_area("Co wypożyczono? (Np. 4x Moving Head, Kratownica 3m)")
    
    if st.form_submit_button("✅ Zapisz Koszt Zaopatrzenia"):
        # Zapis do zakładki Zlecenia z oznaczeniem ZAOPATRZENIE
        nr_ref = f"ZAOP/{id_projektu}/{datetime.now().strftime('%d%m')}"
        nowy_wiersz = [datetime.now().strftime("%Y-%m-%d %H:%M"), nr_ref, "ZAOPATRZENIE", "", kontrahent if "Zwrot" not in typ_ruchu else "MAGAZYN", "MAGAZYN" if "Zwrot" not in typ_ruchu else kontrahent, "", "", "Sprzęt Wypożyczony", "", "", "", "", opis, "", id_projektu, typ_ruchu, stawka]
        sh.worksheet("Zlecenia").append_row(nowy_wiersz)
        st.success(f"Zapisano koszt {typ_ruchu} dla projektu {id_projektu}")
