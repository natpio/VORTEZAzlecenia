import streamlit as st
import pandas as pd
import qrcode
import hashlib
from datetime import datetime
import io
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials
import os
import time

# --- KONFIGURACJA ---
st.set_page_config(layout="wide", page_title="Nowe Zlecenie V2")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_all_data():
    client = get_gsheets_client()
    sh = client.open_by_url(SHEET_URL)
    
    przewoznicy = pd.DataFrame(sh.worksheet("Zleceniobiorcy").get_all_records())
    miejsca = pd.DataFrame(sh.worksheet("Miejsca").get_all_records())
    projekty = pd.DataFrame(sh.worksheet("Projekty").get_all_records())
    
    return przewoznicy, miejsca, projekty

def append_to_gsheets(worksheet_name, row_data):
    client = get_gsheets_client()
    client.open_by_url(SHEET_URL).worksheet(worksheet_name).append_row(row_data)

# --- START UI ---
st.title("📝 Formularz Nowego Zlecenia V2.0")
df_p, df_m, df_projekty = load_all_data()

with st.form("form_zlecenie_v2"):
    
    # SEKCJA 1: PROJEKT I EVENT
    st.markdown("### 🎯 1. Powiązanie z Projektem")
    col_id, col_ev = st.columns([1, 2])
    id_projektu = col_id.text_input("ID Projektu (5 cyfr)", help="Wpisz 5-cyfrowy numer projektu, aby zaciągnąć nazwę targów.")
    
    nazwa_eventu = ""
    if id_projektu and not df_projekty.empty:
        proj_match = df_projekty[df_projekty['ID Projektu'].astype(str) == str(id_projektu)]
        if not proj_match.empty:
            nazwa_eventu = proj_match.iloc[0]['Nazwa Eventu']
            col_ev.info(f"📍 Powiązany Event: **{nazwa_eventu}**")
        else:
            col_ev.warning("Nie znaleziono takiego ID projektu.")

    # SEKCJA 2: KONTRAHENCI I TRASA
    st.markdown("### 🏢 2. Trasa i Kontrahenci")
    c1, c2, c3 = st.columns(3)
    
    wybrany_przewoznik = c1.selectbox("Przewoźnik", df_p['Nazwa do listy'].tolist() if not df_p.empty else [])
    zaladunek_skrot = c2.selectbox("Miejsce Załadunku", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])
    rozladunek_skrot = c3.selectbox("Miejsce Rozładunku", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])

    # Sprawdzanie rampy
    if zaladunek_skrot:
        info_z = df_m[df_m['Nazwa do listy'] == zaladunek_skrot].iloc[0]
        if str(info_z.get('Rampa (TAK/NIE)', '')).upper() == "NIE":
            st.error(f"⚠️ UWAGA: {zaladunek_skrot} NIE POSIADA RAMPY! Zamów auto z windą.")
            st.caption(f"📞 Kontakt: {info_z.get('Osoba / Tel', 'Brak danych')}")

    # SEKCJA 3: FINANSE I TYP
    st.markdown("### 💰 3. Koszty i Typ Ruchu")
    f1, f2, f3 = st.columns(3)
    stawka = f1.number_input("Stawka transportu (EUR/PLN)", min_value=0)
    typ_transportu = f2.selectbox("Typ ruchu", ["Outbound (Na Event)", "Inbound (Od kontrahenta)", "Zwrot (Do kontrahenta)", "Inne"])
    nr_ref = f3.text_input("Nr referencyjny", f"ZLEC/{datetime.now().strftime('%Y/%m')}/")

    # Reszta standardowych pól
    st.markdown("### 📦 4. Towar")
    t1, t2, t3, t4 = st.columns(4)
    towar = t1.text_input("Rodzaj towaru", "Sprzęt Eventowy")
    ilosc = t2.text_input("Ilość", "33")
    opakowanie = t3.selectbox("Opakowanie", ["EUR-paleta", "Case", "Sztuka"])
    waga = t4.text_input("Waga (kg)", "24000")
    
    uwagi = st.text_area("Uwagi / Instrukcje dla kierowcy")

    submit = st.form_submit_button("🚀 ZAPISZ I GENERUJ DOKUMENTY")

if submit:
    # Generowanie Hasha (uproszczone dla przykładu)
    hash_qr = hashlib.sha256(f"{nr_ref}{stawka}".encode()).hexdigest()
    
    # Tworzenie wiersza (A-R, 18 kolumn)
    nowy_wiersz = [
        datetime.now().strftime("%Y-%m-%d %H:%M"), # A: Data wystawienia
        nr_ref,             # B: Numer zlecenia
        "Moja Firma Sp. z o.o.", # C: Zleceniodawca (na sztywno lub z inputu)
        wybrany_przewoznik, # D: Zleceniobiorca
        zaladunek_skrot,    # E: Miejsce Zaladunku
        rozladunek_skrot,   # F: Miejsce Rozladunku
        datetime.now().strftime("%Y-%m-%d"), # G: Data Zaladunku
        datetime.now().strftime("%Y-%m-%d"), # H: Data Rozladunku
        towar,              # I: Rodzaj towaru
        ilosc,              # J: Ilosc opakowan
        opakowanie,         # K: Rodzaj opakowania
        waga,               # L: Waga brutto
        "",                 # M: Wartosc towaru (puste jeśli nie używasz)
        uwagi,              # N: Uwagi
        hash_qr,            # O: Hash QR
        id_projektu,        # P: ID PROJEKTU (Nowe!)
        typ_transportu,     # Q: TYP TRANSPORTU (Nowe!)
        stawka              # R: STAWKA (Nowe!)
    ]
    
    with st.spinner("Zapisywanie w systemie..."):
        append_to_gsheets("Zlecenia", nowy_wiersz)
        st.success(f"Zlecenie {nr_ref} zostało poprawnie powiązane z projektem {id_projektu}!")
        st.balloons()
