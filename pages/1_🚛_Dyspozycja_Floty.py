import streamlit as st
from datetime import datetime
import pandas as pd
from fpdf import FPDF

# Importujemy silnik Vortex
from core import fetch_data, append_data, get_next_daily_number, get_gsheets_client

# --- GENERATOR PDF DLA PRZEWOŹNIKA ---
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


# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #38bdf8;'>🚛 DYSPOZYCJA FLOTY</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Centralny panel operacyjny logistyki do zlecania transportów.</p>", unsafe_allow_html=True)

# POBIERANIE DANYCH
with st.spinner("Synchronizacja z bazą..."):
    df_przewoznicy = fetch_data("Zleceniobiorcy")
    df_projekty = fetch_data("Projekty")
    df_zlecenia = fetch_data("Zlecenia")

lista_przewoznikow = df_przewoznicy['Skrócona Nazwa'].tolist() if not df_przewoznicy.empty else ["Brak danych"]

if not df_projekty.empty:
    def format_project_name(row):
        event = str(row.get('Nazwa Eventu', 'Nieznany Event'))
        klient = str(row.get('Nazwa Projektu', ''))
        return f"{event} ({klient})" if klient and klient != "nan" else event
    
    df_projekty['Display'] = df_projekty.apply(format_project_name, axis=1)
    lista_eventow = df_projekty['Display'].tolist()
else:
    lista_eventow = ["Brak projektów w bazie"]


# --- PODZIAŁ NA DWA RODZAJE TRANSPORTU ---
tab_targi, tab_zaopatrzenie = st.tabs(["🏗️ TRANSPORT TARGOWY (Pełny cykl)", "📦 TRANSPORT ZAOPATRZENIA (Zlecenia PDF)"])

# =================================================================
# ZAKŁADKA 1: TARGI (Kreator pełny)
# =================================================================
with tab_targi:
    st.info("Kreator pełnych cykli transportowych na budowę stoisk targowych.")
    with st.container(border=True):
        with st.form("fleet_form_v3"):
            st.markdown("#### 🔑 Identyfikacja i Partnerzy")
            c1, c2, c3 = st.columns([1, 2, 2])
            logistyk = c1.radio("Opiekun:", ["PD", "PK"], horizontal=True)
            wybrany_projekt_full = c2.selectbox("Projekt / Targi:", lista_eventow)
            wybrany_przewoznik = c3.selectbox("Przewoźnik:", lista_przewoznikow)
            
            st.markdown("#### 🚛 Tabor i Trasa")
            t1, t2, t3 = st.columns(3)
            typ_auta = t1.selectbox("Rodzaj naczepy:", ["MEGA", "Standard", "Zestaw 120m3", "Solo", "Bus"])
            miejsce_zal = t2.text_input("Start:", value="Magazyn Komorniki")
            czysta_nazwa_eventu = wybrany_projekt_full.split(" (")[0]
            miejsce_roz = t3.text_input("Cel:", value=f"Targi - {czysta_nazwa_eventu}")

            st.markdown("#### 📅 Harmonogram Cyklu")
            h1, h2, h3 = st.columns(3)
            d_zal_pl = h1.date_input("Załadunek PL")
            d_roz_targi = h2.date_input("Rozładunek Targi")
            d_emp_in = h3.date_input("Empties (Odbiór)")
            
            h4, h5, h6 = st.columns(3)
            d_emp_out = h4.date_input("Empties (Zwrot)")
            d_zal_powr = h5.date_input("Załadunek Powrotny")
            d_roz_pl = h6.date_input("Rozładunek PL")

            st.markdown("#### 💰 Warunki i Logistyka")
            k1, k2, k3 = st.columns([1, 2, 2])
            stawka = k1.number_input("Stawka netto (PLN/EUR):", min_value=0.0, step=50.0)
            auto_dane = k2.text_input("Dane auta / kierowcy:", placeholder="np. PO 12345 / Jan Kowalski")
            instrukcje = k3.text_area("Dodatkowe instrukcje:", height=68)

            submit = st.form_submit_button("🚀 GENERUJ ZLECENIE (Baza danych)", use_container_width=True, type="primary")

    if submit:
        if "Brak" in wybrany_projekt_full:
            st.error("❌ Wybierz poprawny projekt!")
        else:
            with st.spinner("Procesowanie..."):
                pref = czysta_nazwa_eventu[:3].upper()
                rok = datetime.now().strftime('%y')
                data_kod = datetime.now().strftime('%m%d')
                dzisiejszy_index = get_next_daily_number(datetime.now().strftime("%Y-%m-%d"))
                final_nr = f"{pref}{rok}/{data_kod}/{logistyk}{dzisiejszy_index:02d}"
                
                harmonogram = f"CYKL: {d_zal_pl} -> {d_roz_targi} | EMP: {d_emp_in}/{d_emp_out} | POWRÓT: {d_zal_powr} -> {d_roz_pl}"
                pelne_uwagi = f"{instrukcje} || AUTO: {auto_dane} || {harmonogram}"
                
                wiersz = [
                    datetime.now().strftime("%Y-%m-%d %H:%M"), final_nr, "LOGISTYKA CARGO", wybrany_przewoznik,
                    miejsce_zal, miejsce_roz, str(d_zal_pl), str(d_roz_pl), f"Elementy zabudowy - {typ_auta}",
                    "", "", "", "", pelne_uwagi, "", czysta_nazwa_eventu, "TARGI", stawka
                ]
                
                if append_data("Zlecenia", wiersz):
                    st.success(f"✅ Zapisano pod numerem: {final_nr}. Przejdź do Terminala CMR, aby wygenerować dokumenty.")
                    st.balloons()


# =================================================================
# ZAKŁADKA 2: ZAOPATRZENIE (Wysyłka i PDF)
# =================================================================
with tab_zaopatrzenie:
    st.info("Generowanie fizycznych Zleceń Transportowych (PDF) dla wycenionych zgłoszeń Zaopatrzenia.")
    
    if not df_zlecenia.empty:
        nazwa_kol_dzial = df_zlecenia.columns[2]
        nazwa_kol_stawka = 'Stawka' if 'Stawka' in df_zlecenia.columns else df_zlecenia.columns[17]
        
        # Filtrujemy zgłoszenia zaopatrzenia, które zostały już wycenione (Stawka != 0)
        df_zaop_gotowe = df_zlecenia[(df_zlecenia[nazwa_kol_dzial] == 'ZAOPATRZENIE') & (df_zlecenia[nazwa_kol_stawka].astype(str) != '0')]
        
        if not df_zaop_gotowe.empty:
            c_sel, c_form = st.columns([2, 3])
            
            lista_nr_zaop = df_zaop_gotowe['Numer zlecenia'].tolist()
            wybrane_zlecenie_zaop = c_sel.selectbox("Wybierz wycenione zlecenie z Zaopatrzenia:", lista_nr_zaop)
            
            wiersz_danych = df_zaop_gotowe[df_zaop_gotowe['Numer zlecenia'] == wybrane_zlecenie_zaop].iloc[0]
            
            with c_form:
                with st.form("form_pdf_zaop"):
                    st.write(f"**Przewoźnik:** {wiersz_danych.get('Zleceniobiorca', 'Brak')}")
                    st.write(f"**Trasa:** {wiersz_danych.get('Miejsce Zaladunku', '')} ➡️ {wiersz_danych.get('Miejsce Rozladunku', '')}")
                    
                    # Logistyk uzupełnia dane auta tuż przed wysyłką PDFa
                    st.markdown("---")
                    dane_kierowcy = st.text_input("Wpisz numery rejestracyjne i dane kierowcy (opcjonalnie):", placeholder="np. PO 12345 / Jan Kowalski")
                    
                    if st.form_submit_button("💾 ZAPISZ AUTO I GENERUJ PDF", type="primary", use_container_width=True):
                        idx = df_zlecenia[df_zlecenia['Numer zlecenia'] == wybrane_zlecenie_zaop].index[0]
                        sheet_row = int(idx) + 2
                        
                        uwagi_kol = 'Uwagi / Instrukcje' if 'Uwagi / Instrukcje' in df_zlecenia.columns else df_zlecenia.columns[13]
                        stare_uwagi = str(df_zlecenia.at[idx, uwagi_kol])
                        nowe_uwagi = f"AUTO: {dane_kierowcy} || {stare_uwagi}" if dane_kierowcy else stare_uwagi
                        
                        # Zapis w arkuszu
                        try:
                            client = get_gsheets_client()
                            sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit").worksheet("Zlecenia")
                            sheet.update_cell(sheet_row, 14, nowe_uwagi)
                            fetch_data.clear()
                            st.success("Zapisano dane auta!")
                        except Exception as e:
                            st.error(f"Błąd zapisu auta: {e}")
                            
                        # Po zapisie od razu przygotowujemy PDF
                        dane_pdf = {
                            "nr": str(wybrane_zlecenie_zaop),
                            "przewoznik": str(wiersz_danych.get('Zleceniobiorca', '')),
                            "zaladunek": str(wiersz_danych.get('Miejsce Zaladunku', '')),
                            "rozladunek": str(wiersz_danych.get('Miejsce Rozladunku', '')),
                            "data_zal": str(wiersz_danych.get('Data Zaladunku', '')),
                            "opis": str(wiersz_danych.get('Towar', 'Sprzęt')),
                            "auto": nowe_uwagi,
                            "stawka": str(wiersz_danych.get(nazwa_kol_stawka, ''))
                        }
                        
                        gotowy_pdf = generate_transport_order_pdf(dane_pdf)
                        st.download_button(
                            label="📥 POBIERZ ZLECENIE PDF DLA PRZEWOŹNIKA", 
                            data=gotowy_pdf, 
                            file_name=f"Zlecenie_{wybrane_zlecenie_zaop.replace('/', '_')}.pdf", 
                            mime="application/pdf", 
                            type="primary", 
                            use_container_width=True
                        )
        else:
            st.success("Brak wycenionych zleceń oczekujących na wystawienie papierów w Dziale Zaopatrzenia.")
    else:
        st.warning("Baza zleceń pusta.")

st.caption("Vortex Nexus 3.0 | Module: Fleet Disposition")
