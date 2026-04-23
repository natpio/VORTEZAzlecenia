import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# Importujemy silnik
from core import fetch_data, get_gsheets_client

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #10b981;'>🛠️ WYCENIARKA ZAOPATRZENIA</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Panel Logistyka: Akceptacja, wycena i przypisywanie opiekuna.</p>", unsafe_allow_html=True)

def generate_transport_order_pdf(dane):
    def sanitize(text):
        replacements = {'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z',
                        'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S', 'Ź':'Z', 'Ż':'Z'}
        for pl, eng in replacements.items():
            text = str(text).replace(pl, eng)
        return text

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, sanitize(f"ZLECENIE TRANSPORTOWE NR: {dane['nr']}"), ln=True, align="C")
    
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 10, sanitize(f"Data wygenerowania: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True, align="R")
    pdf.line(10, 35, 200, 35)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, sanitize("SZCZEGOLY OPERACYJNE:"), ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, sanitize(f"Zleceniobiorca (Przewoznik): {dane['przewoznik']}"), ln=True)
    pdf.cell(0, 8, sanitize(f"Miejsce Zaladunku: {dane['zaladunek']}"), ln=True)
    pdf.cell(0, 8, sanitize(f"Miejsce Rozladunku: {dane['rozladunek']}"), ln=True)
    pdf.cell(0, 8, sanitize(f"Data Gotowosci / Zaladunku: {dane['data_zal']}"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, sanitize("KOSZTY I WARUNKI:"), ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, sanitize(f"Ustalona stawka netto: {dane['stawka']}"), ln=True)
    pdf.multi_cell(0, 8, sanitize(f"Uwagi i dane auta: {dane['auto']} - {dane['opis']}"))
    
    return bytes(pdf.output(dest='S').encode('latin1'))

with st.spinner("Pobieranie zgłoszeń..."):
    df_zlecenia = fetch_data("Zlecenia")
    df_przewoznicy = fetch_data("Zleceniobiorcy")

lista_przewoznikow = df_przewoznicy['Skrócona Nazwa'].tolist() if not df_przewoznicy.empty else ["Brak danych"]

if not df_zlecenia.empty and 'Dział' in df_zlecenia.columns:
    df_zaopatrzenie = df_zlecenia[df_zlecenia['Dział'] == 'ZAOPATRZENIE']
    df_do_wyceny = df_zaopatrzenie[df_zaopatrzenie['Stawka'].astype(str) == '0']
    
    c1, c2 = st.columns(2)
    c1.error(f"🔴 Do pilnej wyceny: **{len(df_do_wyceny)}**")
    c2.success(f"🟢 Wszystkich zgłoszeń Zaopatrzenia w bazie: **{len(df_zaopatrzenie)}**")
    st.markdown("---")

    tab1, tab2 = st.tabs(["🔴 DO WYCENY (Panel Operacyjny)", "🟢 ZAAKCEPTOWANE (Generuj PDF)"])

    with tab1:
        if not df_do_wyceny.empty:
            kolumny_widok = ['Data wystawienia', 'Numer zlecenia', 'Miejsce Zaladunku', 'Miejsce Rozladunku', 'ID Projektu']
            obecne_kolumny = [k for k in kolumny_widok if k in df_do_wyceny.columns]
            st.dataframe(df_do_wyceny[obecne_kolumny], hide_index=True, use_container_width=True)
            
            st.markdown("### ✍️ Wprowadź wycenę i przejmij zlecenie:")
            with st.container(border=True):
                with st.form("wycena_form"):
                    lista_zlecen_do_wyboru = df_do_wyceny['Numer zlecenia'].tolist()
                    
                    w1, w2, w3, w4 = st.columns([2, 2, 1, 1])
                    wybrane_zlecenie = w1.selectbox("Wybierz zlecenie:", lista_zlecen_do_wyboru)
                    wybrany_przewoznik = w2.selectbox("Wybierz przewoźnika:", lista_przewoznikow)
                    stawka = w3.number_input("Stawka:", min_value=1.0, step=50.0)
                    logistyk = w4.radio("Twój podpis:", ["PD", "PK"]) # Logistyk wybiera siebie tutaj!
                    
                    submit_wycena = st.form_submit_button("✅ ZATWIERDŹ I PRZEJMIJ ZLECENIE", type="primary", use_container_width=True)

            if submit_wycena:
                with st.spinner("Zapisywanie w bazie..."):
                    try:
                        idx = df_zlecenia[df_zlecenia['Numer zlecenia'] == wybrane_zlecenie].index[0]
                        sheet_row = int(idx) + 2 
                        
                        # Pobieramy stare uwagi z DataFrame, żeby ich nie nadpisać
                        stare_uwagi = str(df_zlecenia.at[idx, 'Uwagi / Instrukcje'] if 'Uwagi / Instrukcje' in df_zlecenia.columns else "")
                        nowe_uwagi = f"Opiekun: {logistyk} | {stare_uwagi}"
                        
                        client = get_gsheets_client()
                        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit").worksheet("Zlecenia")
                        
                        # Aktualizujemy Przewoźnika(D/4), Uwagi(N/14), Typ(Q/17), Stawkę(R/18)
                        sheet.update_cell(sheet_row, 4, wybrany_przewoznik)
                        sheet.update_cell(sheet_row, 14, nowe_uwagi)
                        sheet.update_cell(sheet_row, 17, "ZAAKCEPTOWANE")
                        sheet.update_cell(sheet_row, 18, stawka)
                        
                        fetch_data.clear()
                        st.success(f"Zlecenie {wybrane_zlecenie} przejęte przez {logistyk} i wycenione!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd krytyczny podczas zapisu komórek: {e}")
        else:
            st.success("Wszystkie zlecenia z Zaopatrzenia zostały wycenione!")

    with tab2:
        df_zaakceptowane = df_zaopatrzenie[df_zaopatrzenie['Stawka'].astype(str) != '0']
        if not df_zaakceptowane.empty:
            lista_zaakceptowanych = df_zaakceptowane['Numer zlecenia'].tolist()
            c_sel, c_btn = st.columns([3, 1])
            nr_do_pdf = c_sel.selectbox("Wybierz Zlecenie Transportowe:", lista_zaakceptowanych, label_visibility="collapsed")
            wiersz_danych = df_zaakceptowane[df_zaakceptowane['Numer zlecenia'] == nr_do_pdf].iloc[0]
            
            dane_pdf = {
                "nr": str(wiersz_danych.get('Numer zlecenia', '')),
                "przewoznik": str(wiersz_danych.get('Zleceniobiorca', '')),
                "zaladunek": str(wiersz_danych.get('Miejsce Zaladunku', '')),
                "rozladunek": str(wiersz_danych.get('Miejsce Rozladunku', '')),
                "data_zal": str(wiersz_danych.get('Data Zaladunku', '')),
                "opis": str(wiersz_danych.get('Towar', 'Sprzęt')),
                "auto": str(wiersz_danych.get('Uwagi / Instrukcje', '')),
                "stawka": str(wiersz_danych.get('Stawka', ''))
            }
            
            gotowy_pdf = generate_transport_order_pdf(dane_pdf)
            with c_btn:
                st.download_button("📥 POBIERZ PDF", data=gotowy_pdf, file_name=f"Zlecenie_{nr_do_pdf.replace('/', '_')}.pdf", mime="application/pdf", type="primary", use_container_width=True)
            st.dataframe(df_zaakceptowane[obecne_kolumny], hide_index=True, use_container_width=True)
        else:
            st.info("Brak zaakceptowanych zleceń w bazie.")
else:
    st.warning("Silnik nie odnalazł w bazie żadnych zgłoszeń z działu ZAOPATRZENIE.")
