import streamlit as st
from datetime import datetime
import pandas as pd
from fpdf import FPDF
import tempfile
import os
import qrcode

# Założenie: core.py zostaje po staremu, importujemy potrzebne funkcje
from core import fetch_data, append_data, get_next_daily_number

# --- UPROSZCZONY GENERATOR PDF ---
def generate_quick_pdf(dane):
    def sanitize(text):
        replacements = {'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z',
                        'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S', 'Ź':'Z', 'Ż':'Z'}
        for pl, eng in replacements.items():
            text = str(text).replace(pl, eng)
        return text

    pdf = FPDF()
    pdf.add_page()
    
    # Próba dodania logo (jeśli plik istnieje)
    try:
        pdf.image("logosqm.jpg", 10, 8, 45)
    except Exception:
        pass
        
    pdf.set_xy(10, 35)
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, sanitize("ZLECENIE TRANSPORTOWE / TRANSPORT ORDER"), ln=True, align="C")
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, sanitize(f"DATA WYSTAWIENIA: {datetime.now().strftime('%d.%m.%Y')} | REF: {dane.get('nr', '')}"), ln=True, align="C")
    pdf.ln(10)

    # Funkcja do rysowania wierszy tabeli
    def add_row(left, right, bold=False):
        pdf.set_font("Arial", 'B', 8)
        pdf.set_fill_color(240, 240, 240)
        x, y = pdf.get_x(), pdf.get_y()
        pdf.rect(x, y, 60, 10, style='DF')
        pdf.set_xy(x, y + 2)
        pdf.cell(60, 5, sanitize(left), align='C')
        
        pdf.set_xy(x + 60, y)
        pdf.rect(x + 60, y, 130, 10)
        pdf.set_font("Arial", 'B' if bold else '', 9)
        pdf.set_xy(x + 62, y + 2)
        pdf.cell(126, 5, sanitize(str(right)))
        pdf.set_xy(10, y + 10)

    # Rysowanie tabeli z kluczowymi danymi
    add_row("PRZEWOŹNIK", dane.get('przewoznik', ''), True)
    add_row("AUTO / KIEROWCA", dane.get('auto', ''), True)
    add_row("STAWKA NETTO", f"{dane.get('stawka', '')} {dane.get('waluta', 'PLN')}", True)
    pdf.ln(5)
    add_row("ZAŁADUNEK (MIEJSCE)", dane.get('zaladunek', ''))
    add_row("ZAŁADUNEK (DATA)", dane.get('data_zal', ''))
    pdf.ln(5)
    add_row("ROZŁADUNEK (Targi)", dane.get('rozladunek', ''))
    add_row("ROZŁADUNEK (Data)", dane.get('data_roz', ''))
    pdf.ln(5)
    add_row("TOWAR", "Elementy Zabudowy Targowej")
    add_row("UWAGI", dane.get('uwagi', ''))

    return bytes(pdf.output(dest='S').encode('latin1'))

# --- INTERFEJS UI ---
st.set_page_config(page_title="Szybkie Zlecenie", page_icon="🚀", layout="centered")

st.markdown("<h2 style='text-align: center; color: #2c3e50;'>🚀 Szybkie Zlecenie Targowe</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7f8c8d; margin-bottom: 2rem;'>Błyskawiczne generowanie zleceń dla przewoźników i zapis do bazy.</p>", unsafe_allow_html=True)

# 1. Pobranie słowników w tle
df_przewoznicy = fetch_data("Zleceniobiorcy")
df_projekty = fetch_data("Projekty")

lista_przewoznikow = df_przewoznicy['Skrócona Nazwa'].tolist() if not df_przewoznicy.empty else ["Brak"]
lista_eventow = df_projekty['Nazwa Eventu'].dropna().unique().tolist() if not df_projekty.empty else ["Brak"]

# Używamy formularza, aby nie odświeżać strony po każdym wpisaniu litery
with st.form("quick_order_form"):
    
    # KARTA 1: KTO I ZA ILE
    with st.container(border=True):
        st.markdown("#### 1. Kontrahent i Koszty")
        col1, col2, col3 = st.columns([2, 1, 1])
        przewoznik = col1.selectbox("Wybierz przewoźnika:", lista_przewoznikow)
        stawka = col2.number_input("Stawka netto:", min_value=0, step=100)
        waluta = col3.selectbox("Waluta:", ["PLN", "EUR"])

    # KARTA 2: GDZIE I KIEDY
    with st.container(border=True):
        st.markdown("#### 2. Trasa i Harmonogram")
        wydarzenie = st.selectbox("Docelowe Targi (np. Hannover Messe):", lista_eventow)
        
        c_zal, c_roz = st.columns(2)
        with c_zal:
            zaladunek = st.text_input("Start (Załadunek):", value="Magazyn SQM, Komorniki")
            data_zal = st.date_input("Data załadunku:")
        
        with c_roz:
            rozladunek = st.text_input("Cel (Rozładunek):", value=f"Targi - {wydarzenie}")
            data_roz = st.date_input("Data rozładunku:")

    # KARTA 3: DETALE
    with st.container(border=True):
        st.markdown("#### 3. Pojazd i Opiekun")
        d1, d2, d3 = st.columns([2, 2, 1])
        auto_kierowca = d1.text_input("Dane auta / kierowcy:", placeholder="np. PO 12345 / Jan Kowalski")
        uwagi = d2.text_input("Dodatkowe instrukcje dla kierowcy:")
        logistyk = d3.radio("Opiekun:", ["PD", "PK"], index=0, horizontal=True)

    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.form_submit_button("⚡ GENERUJ I ZAPISZ ZLECENIE", type="primary", use_container_width=True)

# Akcja po kliknięciu
if submitted:
    with st.spinner("Generowanie dokumentu i zapis do bazy..."):
        # Generowanie numeru
        rok, mc_dzien = datetime.now().strftime('%y'), datetime.now().strftime('%m%d')
        dzisiejszy_index = get_next_daily_number(datetime.now().strftime("%Y-%m-%d"))
        pref = str(wydarzenie)[:3].upper() if wydarzenie else "TRG"
        nr_zlecenia = f"{pref}{rok}/{mc_dzien}/{logistyk}{dzisiejszy_index:02d}"

        # Budowa paczki danych do PDF
        dane_pdf = {
            "nr": nr_zlecenia,
            "przewoznik": przewoznik,
            "stawka": stawka,
            "waluta": waluta,
            "zaladunek": zaladunek,
            "data_zal": str(data_zal),
            "rozladunek": rozladunek,
            "data_roz": str(data_roz),
            "auto": auto_kierowca,
            "uwagi": uwagi
        }

        # 1. Tworzymy PDF w pamięci
        gotowy_pdf = generate_quick_pdf(dane_pdf)

        # 2. Zapisujemy w tle do bazy
        wiersz = [
            datetime.now().strftime("%Y-%m-%d %H:%M"), nr_zlecenia, "LOGISTYKA CARGO", przewoznik,
            zaladunek, rozladunek, str(data_zal), str(data_roz), "Elementy zabudowy targowej",
            "", "", "", "", f"AUTO: {auto_kierowca} || {uwagi}", "", wydarzenie, "TARGI", f"{stawka} {waluta}"
        ]
        
        if append_data("Zlecenia", wiersz):
            st.success(f"Zapisano zlecenie {nr_zlecenia} w bazie!")
            
            # Pokazujemy przycisk do pobrania gotowego pliku
            st.download_button(
                label="📥 POBIERZ GOTOWY PDF",
                data=gotowy_pdf,
                file_name=f"Zlecenie_{nr_zlecenia.replace('/', '_')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
