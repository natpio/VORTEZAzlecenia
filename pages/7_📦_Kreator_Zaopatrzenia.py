import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(layout="wide", page_title="Kreator Zaopatrzenia")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_data(ttl=10)
def load_data():
    sh = get_gsheets_client().open_by_url(SHEET_URL)
    return pd.DataFrame(sh.worksheet("Zlecenia").get_all_records()), pd.DataFrame(sh.worksheet("Miejsca").get_all_records())

df_z, df_m = load_data()

st.title("📦 System Zarządzania Zaopatrzeniem")
tab1, tab2 = st.tabs(["➕ Zgłoś transport", "💰 Wycena i Dane Auta"])

with tab1:
    with st.form("form_request"):
        id_p = st.text_input("ID Projektu (5 cyfr)")
        skad = st.selectbox("Kontrahent", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])
        data_zal = st.date_input("Data odbioru")
        opis = st.text_area("Lista sprzętu")
        if st.form_submit_button("Wyślij zgłoszenie"):
            nowy_wiersz = [datetime.now().strftime("%Y-%m-%d %H:%M"), f"REQ/{id_p}/{datetime.now().strftime('%H%M')}", "ZAOPATRZENIE", "", skad, "NASZ MAGAZYN", str(data_zal), "", "Sprzęt Wypożyczony", "", "", "", "", opis, "", id_p, "ZAOP_DO_WYCENY", 0]
            get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
            st.success("Zgłoszenie wysłane!")
            st.cache_data.clear()

with tab2:
    do_wyceny = df_z[df_z['Typ transportu'] == "ZAOP_DO_WYCENY"]
    if not do_wyceny.empty:
        for idx, row in do_wyceny.iterrows():
            with st.container(border=True):
                st.write(f"**Projekt:** {row['ID Projektu']} | **Sprzęt:** {row['Uwagi / Instrukcje']}")
                with st.expander("Wyceń i podaj dane kierowcy"):
                    with st.form(f"f_{row['Numer zlecenia']}"):
                        stawka = st.number_input("Stawka", min_value=0)
                        auto = st.text_input("Nr rejestracyjny / Kierowca")
                        status = st.radio("Typ:", ["Inbound (Zatwierdzony)", "Zwrot (Zatwierdzony)"])
                        if st.form_submit_button("Zatwierdź"):
                            ws = get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia")
                            cell = ws.find(row['Numer zlecenia'])
                            ws.update_cell(cell.row, 14, f"{row['Uwagi / Instrukcje']} | {auto}")
                            ws.update_cell(cell.row, 17, status)
                            ws.update_cell(cell.row, 18, stawka)
                            st.success("Zatwierdzono!")
                            st.cache_data.clear()
                            st.rerun()
    else:
        st.info("Brak oczekujących zgłoszeń.")
