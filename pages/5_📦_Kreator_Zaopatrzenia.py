import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(layout="wide", page_title="Kreator Zaopatrzenia")

# --- MENU BOCZNE (TYLKO ZAOPATRZENIE) ---
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none !important;}</style>""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("### 📦 ZAOPATRZENIE")
    st.page_link("app.py", label="⬅ Wróć do Głównego Menu")
    st.divider()
    st.page_link("pages/5_📦_Kreator_Zaopatrzenia.py", label="Kreator Zaopatrzenia")
    st.page_link("pages/6_💰_Finanse_Projektu.py", label="Finanse Projektów")
    st.page_link("pages/7_🏢_Baza_Kontrahentow.py", label="Baza Kontrahentów")

# --- LOGIKA BAZY ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"
def get_gsheets_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_data(ttl=10)
def load_data():
    sh = get_gsheets_client().open_by_url(SHEET_URL)
    return pd.DataFrame(sh.worksheet("Zlecenia").get_all_records()), pd.DataFrame(sh.worksheet("Miejsca").get_all_records())

df_z, df_m = load_data()

st.title("📦 Kreator Zaopatrzenia")

tab1, tab2 = st.tabs(["➕ Nowe Zgłoszenie", "💰 Wycena i Zatwierdzenie"])

with tab1:
    st.subheader("Zgłoszenie od Zaopatrzeniowca")
    with st.form("form_zaop"):
        id_p = st.text_input("ID Projektu (5 cyfr)")
        kontrahent = st.selectbox("Od kogo odbieramy?", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])
        co_to = st.text_area("Opis sprzętu / Co jest do odebrania?")
        data_gotowosci = st.date_input("Kiedy sprzęt będzie gotowy?")
        
        if st.form_submit_button("Wyślij zapotrzebowanie"):
            nowy = [datetime.now().strftime("%Y-%m-%d %H:%M"), f"REQ/{id_p}/{datetime.now().strftime('%H%M')}", "ZAOPATRZENIE", "", kontrahent, "MAGAZYN", str(data_gotowosci), "", "Wypożyczenie", "", "", "", "", co_to, "", id_p, "ZAOP_DO_WYCENY", 0]
            get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy)
            st.success("Zgłoszenie trafiło do kolejki logistyka.")

with tab2:
    st.subheader("Kolejka wycen (Logistyk)")
    oczekujace = df_z[df_z['Typ transportu'] == "ZAOP_DO_WYCENY"]
    
    if not oczekujace.empty:
        for _, row in oczekujace.iterrows():
            with st.expander(f"Projekt {row['ID Projektu']} - {row['Miejsce Zaladunku']}"):
                with st.form(f"wycena_{row['Numer zlecenia']}"):
                    c1, c2 = st.columns(2)
                    stawka = c1.number_input("Koszt", min_value=0)
                    przewoznik = c2.text_input("Przewoźnik (np. Kurier/Własny)")
                    dane_auta = st.text_input("Dane kierowcy / Nr auta")
                    typ = st.radio("Kierunek:", ["Inbound (Przywóz)", "Zwrot (Odesłanie)"])
                    
                    if st.form_submit_button("Zatwierdź koszt i transport"):
                        ws = get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia")
                        cell = ws.find(row['Numer zlecenia'])
                        ws.update_cell(cell.row, 4, przewoznik)
                        ws.update_cell(cell.row, 14, f"{row['Uwagi / Instrukcje']} | AUTO: {dane_auta}")
                        ws.update_cell(cell.row, 17, typ)
                        ws.update_cell(cell.row, 18, stawka)
                        st.success("Zlecenie rozliczone!")
                        st.rerun()
    else:
        st.info("Brak nowych zgłoszeń do wyceny.")
