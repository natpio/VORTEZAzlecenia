import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(layout="wide", page_title="Kreator Zaopatrzenia V2")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_data(ttl=10) # Krótki cache dla szybkich aktualizacji
def load_data():
    sh = get_gsheets_client().open_by_url(SHEET_URL)
    return (pd.DataFrame(sh.worksheet("Zlecenia").get_all_records()), 
            pd.DataFrame(sh.worksheet("Miejsca").get_all_records()))

df_z, df_m = load_data()

st.title("📦 System Zarządzania Zaopatrzeniem")
tab1, tab2 = st.tabs(["➕ Zgłoś transport (Zaopatrzeniowiec)", "💰 Wycena i Zatwierdzenie (Logistyk)"])

with tab1:
    st.subheader("Nowe zapotrzebowanie na sprzęt")
    with st.form("form_request"):
        id_p = st.text_input("ID Projektu (5 cyfr)")
        skad = st.selectbox("Skąd pobieramy sprzęt? (Kontrahent)", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])
        data_zal = st.date_input("Kiedy gotowe do odbioru?")
        opis = st.text_area("Co jest do ściągnięcia?")
        
        if st.form_submit_button("Wyślij do Logistyka"):
            nr_ref = f"REQ/{id_p}/{datetime.now().strftime('%H%M%S')}"
            nowy_wiersz = [datetime.now().strftime("%Y-%m-%d %H:%M"), nr_ref, "ZAOPATRZENIE", "", skad, "MAGAZYN", str(data_zal), "", "Sprzęt Wypożyczony", "", "", "", "", opis, "", id_p, "ZAOP_DO_WYCENY", 0]
            get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
            st.success("Zgłoszenie wysłane!")
            st.cache_data.clear()

with tab2:
    st.subheader("Oczekujące wyceny i dane transportu")
    do_wyceny = df_z[df_z['Typ transportu'] == "ZAOP_DO_WYCENY"]
    
    if not do_wyceny.empty:
        for idx, row in do_wyceny.iterrows():
            with st.container(border=True):
                st.write(f"**Projekt:** {row['ID Projektu']} | **Zgłoszenie:** {row['Numer zlecenia']}")
                st.write(f"📍 {row['Miejsce Zaladunku']} | 📦 {row['Uwagi / Instrukcje']}")
                
                with st.expander("Wypełnij dane transportu i wyceń"):
                    with st.form(f"wycena_{row['Numer zlecenia']}"):
                        c1, c2 = st.columns(2)
                        stawka_log = c1.number_input("Stawka (PLN/EUR)", min_value=0)
                        przewoznik_log = c2.text_input("Firma transportowa")
                        
                        st.markdown("**Dane Kierowcy i Auta:**")
                        k1, k2, k3 = st.columns(3)
                        nr_rej = k1.text_input("Nr rejestracyjny")
                        kierowca = k2.text_input("Imię i Nazwisko kierowcy")
                        tel_kierowcy = k3.text_input("Telefon do kierowcy")
                        
                        typ_final = st.radio("Zmień status na:", ["Inbound (Zatwierdzony)", "Zwrot (Zatwierdzony)"])

                        if st.form_submit_button("Zatwierdź i zapisz"):
                            ws = get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia")
                            cell = ws.find(row['Numer zlecenia'])
                            
                            # Aktualizujemy kolumny: 
                            # D (Przewoźnik), Q (Status), R (Stawka)
                            # Dodatkowo w kolumnie N (Uwagi) dopiszemy dane auta dla historii
                            dane_auta = f"{row['Uwagi / Instrukcje']} | AUTO: {nr_rej}, KIER: {kierowca} ({tel_kierowcy})"
                            
                            ws.update_cell(cell.row, 4, przewoznik_log)
                            ws.update_cell(cell.row, 14, dane_auta) # Kolumna N - Uwagi/Instrukcje
                            ws.update_cell(cell.row, 17, typ_final)
                            ws.update_cell(cell.row, 18, stawka_log)
                            
                            st.success("Transport zatwierdzony!")
                            st.cache_data.clear()
                            st.rerun()
    else:
        st.info("Brak nowych zgłoszeń do wyceny.")
