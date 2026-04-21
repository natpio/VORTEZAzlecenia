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

@st.cache_data(ttl=30)
def load_data():
    sh = get_gsheets_client().open_by_url(SHEET_URL)
    return (pd.DataFrame(sh.worksheet("Zlecenia").get_all_records()), 
            pd.DataFrame(sh.worksheet("Miejsca").get_all_records()), 
            pd.DataFrame(sh.worksheet("Projekty").get_all_records()))

df_z, df_m, df_p = load_data()

st.title("📦 System Zarządzania Zaopatrzeniem")
tab1, tab2 = st.tabs(["➕ Zgłoś transport (Zaopatrzenie)", "💰 Wycena i Zatwierdzenie (Logistyka)"])

# --- TAB 1: DLA ZAOPATRZENIOWCA ---
with tab1:
    st.subheader("Nowe zapotrzebowanie na sprzęt")
    with st.form("form_request"):
        id_p = st.text_input("ID Projektu (5 cyfr)")
        
        col1, col2 = st.columns(2)
        skad = col1.selectbox("Skąd pobieramy sprzęt? (Kontrahent)", df_m['Nazwa do listy'].tolist())
        data_zal = col2.date_input("Kiedy ma być gotowe do odbioru?")
        
        opis = st.text_area("Co jest do ściągnięcia? (Lista sprzętu, waga, wymiary)")
        
        if st.form_submit_button("Wyślij zgłoszenie do Logistyka"):
            if len(id_p) == 5:
                # Zapisujemy zlecenia ze stawką 0 i typem PENDING
                nr_ref = f"REQ/{id_p}/{datetime.now().strftime('%d%m%H%M')}"
                nowy_wiersz = [
                    datetime.now().strftime("%Y-%m-%d %H:%M"), nr_ref, "ZAOPATRZENIE", "", 
                    skad, "MAGAZYN", str(data_zal), "", "Sprzęt Wypożyczony", "", "", "", "", 
                    opis, "", id_p, "ZAOP_DO_WYCENY", 0
                ]
                get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
                st.success("Zgłoszenie wysłane! Logistyk wyceni transport.")
                st.cache_data.clear()
            else:
                st.error("Podaj poprawne 5-cyfrowe ID Projektu.")

# --- TAB 2: DLA LOGISTYKA ---
with tab2:
    st.subheader("Oczekujące wyceny")
    # Filtrujemy tylko zlecenia typu "ZAOP_DO_WYCENY"
    do_wyceny = df_z[df_z['Typ transportu'] == "ZAOP_DO_WYCENY"]
    
    if not do_wyceny.empty:
        for idx, row in do_wyceny.iterrows():
            with st.container(border=True):
                st.markdown(f"**Projekt:** {row['ID Projektu']} | **Zgłoszenie:** {row['Numer zlecenia']}")
                st.write(f"📍 Skąd: {row['Miejsce Zaladunku']} | 📅 Kiedy: {row['Data Zaladunku']}")
                st.write(f"📦 Co: {row['Uwagi / Instrukcje']}")
                
                # Formularz wyceny dla konkretnego wiersza
                with st.expander("Wycen i przypisz przewoźnika"):
                    with st.form(f"wycena_{row['Numer zlecenia']}"):
                        stawka_log = st.number_input("Stawka (EUR/PLN)", min_value=0)
                        przewoznik_log = st.text_input("Przewoźnik / Kurier")
                        
                        if st.form_submit_button("Zatwierdź transport"):
                            # Logika aktualizacji wiersza w Google Sheets
                            client = get_gsheets_client()
                            ws = client.open_by_url(SHEET_URL).worksheet("Zlecenia")
                            
                            # Znajdujemy wiersz w Sheets (Pandas index + 2, bo Sheets startuje od 1 i ma nagłówek)
                            # Ale bezpieczniej szukać po Numerze zlecenia
                            cell = ws.find(row['Numer zlecenia'])
                            ws.update_cell(cell.row, 17, "Inbound (Zatwierdzony)") # Kolumna Q
                            ws.update_cell(cell.row, 18, stawka_log)              # Kolumna R
                            ws.update_cell(cell.row, 4, przewoznik_log)            # Kolumna D
                            
                            st.success(f"Zatwierdzono transport dla {row['Numer zlecenia']}")
                            st.cache_data.clear()
                            st.rerun()
    else:
        st.info("Brak oczekujących zgłoszeń do wyceny.")
