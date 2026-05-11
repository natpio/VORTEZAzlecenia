import streamlit as st
from datetime import datetime
import pandas as pd
from fpdf import FPDF
import tempfile
import os
import qrcode

# Założenie: core.py zostaje po staremu
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

    add_row("PRZEWOŹNIK", dane.get('przewoznik', ''), True)
    add_row("AUTO / KIEROWCA", dane.get('auto', ''), True)
    add_row("CENA TOTAL (NETTO)", f"{dane.get('stawka', '')} {dane.get('waluta', 'PLN')}", True)
    if dane.get('typ_zlecenia') == "Pełny event" and dane.get('postoj'):
        add_row("STAWKA ZA POSTÓJ / DZIEŃ", f"{dane.get('postoj', '')} {dane.get('waluta', 'PLN')}")
        
    pdf.ln(5)
    add_row("ZAŁADUNEK (MIEJSCE)", dane.get('zaladunek', ''))
    add_row("ZAŁADUNEK (DATA)", dane.get('data_zal', ''))
    pdf.ln(5)
    add_row("ROZŁADUNEK (MIEJSCE)", dane.get('rozladunek', ''))
    add_row("ROZŁADUNEK (DATA)", dane.get('data_roz', ''))
    
    if dane.get('typ_zlecenia') == "Pełny event":
        pdf.ln(5)
        add_row("ODBIÓR PUSTYCH (EMPTIES)", dane.get('data_emp_in', ''))
        add_row("ODBIÓR PEŁNYCH / POWRÓT", dane.get('data_emp_out', ''))
        
    pdf.ln(5)
    add_row("WAGA ŁADUNKU", f"{dane.get('waga', '')} kg")
    add_row("WARTOŚĆ TOWARU", f"{dane.get('wartosc', '')} PLN")
    add_row("UWAGI", dane.get('uwagi', ''))

    return bytes(pdf.output(dest='S').encode('latin1'))

# --- INTERFEJS UI ---
st.set_page_config(page_title="Szybkie Zlecenie", page_icon="🚀", layout="centered")

st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🚀 Szybkie Zlecenie</h2>", unsafe_allow_html=True)

# 1. POBRANIE BAZ DANYCH W TLE
with st.spinner("Ładowanie słowników..."):
    df_przewoznicy = fetch_data("Zleceniobiorcy")
    df_projekty = fetch_data("Projekty")
    df_miejsca = fetch_data("Miejsca")

lista_przewoznikow = df_przewoznicy['Skrócona Nazwa'].tolist() if not df_przewoznicy.empty else ["Brak danych"]
lista_eventow = df_projekty['Nazwa Eventu'].dropna().unique().tolist() if not df_projekty.empty else ["Brak"]
lista_miejsc_baza = df_miejsca['Nazwa do listy'].tolist() if not df_miejsca.empty else []

opcje_lokalizacji = ["Magazyn SQM Komorniki"] + lista_miejsc_baza + ["INNE (wpisz ręcznie)"]

# --- GŁÓWNY PRZEŁĄCZNIK (Zawsze poza formularzem, aby dynamicznie zmieniać układ) ---
st.markdown("<div style='text-align: center; padding: 10px; background: rgba(56, 189, 248, 0.1); border-radius: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
typ_zlecenia = st.radio("Rodzaj operacji logistycznej:", ["Tylko dostawa", "Pełny event"], horizontal=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- FORMULARZ ---
with st.form("quick_order_form"):
    
    # KARTA 1: KTO, GDZIE I ZA ILE
    with st.container(border=True):
        st.markdown("#### 1. Kontrahent i Finanse")
        c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1])
        przewoznik = c1.selectbox("Przewoźnik:", lista_przewoznikow)
        stawka = c2.number_input("Cena Total:", min_value=0, step=100)
        waluta = c3.selectbox("Waluta:", ["PLN", "EUR"])
        if typ_zlecenia == "Pełny event":
            postoj = c4.number_input("Stawka Postój/Dz:", min_value=0, step=50)
        else:
            postoj = 0

    # KARTA 2: TRASA I MIEJSCA
    with st.container(border=True):
        st.markdown("#### 2. Trasa i Lokalizacje")
        wydarzenie = st.selectbox("Docelowy Projekt / Targi:", lista_eventow)
        
        t1, t2 = st.columns(2)
        with t1:
            zal_select = st.selectbox("Start (Załadunek):", opcje_lokalizacji)
            zal_reczne = st.text_input("Wpisz miejsce załadunku:", placeholder="Tylko jeśli wybrano INNE") if zal_select == "INNE (wpisz ręcznie)" else ""
            
        with t2:
            roz_select = st.selectbox("Cel (Rozładunek):", opcje_lokalizacji)
            roz_reczne = st.text_input("Wpisz miejsce rozładunku:", placeholder="Tylko jeśli wybrano INNE") if roz_select == "INNE (wpisz ręcznie)" else ""

    # KARTA 3: HARMONOGRAM
    with st.container(border=True):
        st.markdown("#### 3. Harmonogram")
        if typ_zlecenia == "Pełny event":
            h1, h2, h3, h4 = st.columns(4)
            data_zal = h1.date_input("Załadunek:")
            data_roz = h2.date_input("Rozładunek:")
            data_emp_in = h3.date_input("Puste (Odbiór):")
            data_emp_out = h4.date_input("Pełne (Powrót):")
        else:
            h1, h2 = st.columns(2)
            data_zal = h1.date_input("Załadunek:")
            data_roz = h2.date_input("Rozładunek:")
            data_emp_in, data_emp_out = "", ""

    # KARTA 4: ŁADUNEK I DETALE
    with st.container(border=True):
        st.markdown("#### 4. Ładunek i Detale")
        d1, d2, d3 = st.columns([1, 1, 2])
        waga = d1.number_input("Waga (kg):", min_value=0, step=100)
        wartosc = d2.number_input("Wartość towaru (PLN):", min_value=0, step=1000)
        auto_kierowca = d3.text_input("Dane auta / kierowcy:", placeholder="np. PO 12345 / Jan Kowalski")
        
        u1, u2 = st.columns([3, 1])
        uwagi = u1.text_input("Dodatkowe instrukcje:")
        logistyk = u2.radio("Twój podpis:", ["PD", "PK"], horizontal=True)

    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.form_submit_button("⚡ GENERUJ ZLECENIE", type="primary", use_container_width=True)


# --- AKCJA PO KLIKNIĘCIU ---
if submitted:
    # 1. Logika weryfikacji adresów (Select vs Wpis ręczny)
    ostateczny_zaladunek = zal_reczne if zal_select == "INNE (wpisz ręcznie)" else zal_select
    ostateczny_rozladunek = roz_reczne if roz_select == "INNE (wpisz ręcznie)" else roz_select

    if not ostateczny_zaladunek or not ostateczny_rozladunek:
        st.error("Uzupełnij poprawnie miejsca załadunku i rozładunku!")
    else:
        with st.spinner("Przetwarzanie dokumentów i zapis do bazy..."):
            rok, mc_dzien = datetime.now().strftime('%y'), datetime.now().strftime('%m%d')
            dzisiejszy_index = get_next_daily_number(datetime.now().strftime("%Y-%m-%d"))
            pref = str(wydarzenie)[:3].upper() if wydarzenie else "TRG"
            nr_zlecenia = f"{pref}{rok}/{mc_dzien}/{logistyk}{dzisiejszy_index:02d}"

            # Przygotowanie pełnego opisu do Google Sheets na podstawie trybu
            if typ_zlecenia == "Pełny event":
                harmonogram_str = f"ZAL: {data_zal} | ROZ: {data_roz} | EMP: {data_emp_in} | POWROT: {data_emp_out}"
            else:
                harmonogram_str = f"ZAL: {data_zal} | ROZ: {data_roz}"
            
            pelne_uwagi = f"TRYB: {typ_zlecenia} | WAGA: {waga}kg | WART: {wartosc}PLN | AUTO: {auto_kierowca} || {harmonogram_str} || UWAGI: {uwagi}"

            dane_pdf = {
                "typ_zlecenia": typ_zlecenia,
                "nr": nr_zlecenia,
                "przewoznik": przewoznik,
                "stawka": stawka,
                "postoj": postoj,
                "waluta": waluta,
                "zaladunek": ostateczny_zaladunek,
                "data_zal": str(data_zal),
                "rozladunek": ostateczny_rozladunek,
                "data_roz": str(data_roz),
                "data_emp_in": str(data_emp_in),
                "data_emp_out": str(data_emp_out),
                "waga": waga,
                "wartosc": wartosc,
                "auto": auto_kierowca,
                "uwagi": uwagi
            }

            gotowy_pdf = generate_quick_pdf(dane_pdf)

            # Zapis do Google Sheets
            wiersz = [
                datetime.now().strftime("%Y-%m-%d %H:%M"), nr_zlecenia, "LOGISTYKA CARGO", przewoznik,
                ostateczny_zaladunek, ostateczny_rozladunek, str(data_zal), str(data_roz), "Elementy zabudowy targowej",
                "", "", "", "", pelne_uwagi, "", wydarzenie, "TARGI", f"{stawka} {waluta}"
            ]
            
            if append_data("Zlecenia", wiersz):
                st.success(f"Zlecenie {nr_zlecenia} wygenerowane poprawnie!")
                
                st.download_button(
                    label="📥 POBIERZ GOTOWY PLIK PDF",
                    data=gotowy_pdf,
                    file_name=f"Zlecenie_{nr_zlecenia.replace('/', '_')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
