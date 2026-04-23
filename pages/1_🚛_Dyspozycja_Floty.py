import streamlit as st
from datetime import datetime
import pandas as pd
from fpdf import FPDF
import qrcode
import tempfile
import os

# Importujemy silnik Vortex
from core import fetch_data, append_data, get_next_daily_number, get_gsheets_client

# --- PROFESJONALNY GENERATOR PDF DLA PRZEWOŹNIKA ---
def generate_transport_order_pdf(dane):
    def sanitize(text):
        replacements = {'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z',
                        'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S', 'Ź':'Z', 'Ż':'Z'}
        for pl, eng in replacements.items():
            text = str(text).replace(pl, eng)
        return text

    pdf = FPDF()
    pdf.add_page()
    
    # 1. LOGO SQM
    try:
        pdf.image("logosqm.png", 10, 8, 45)
    except Exception:
        pass # Ignoruj jeśli pliku brak w repozytorium
        
    # 2. KOD QR
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(f"VORTEX-ZLECENIE-{dane.get('nr', 'UNKNOWN')}")
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        img_qr.save(tmp, format="PNG")
        qr_path = tmp.name
        
    try:
        pdf.image(qr_path, 175, 8, 25)
    except Exception:
        pass
    finally:
        if os.path.exists(qr_path):
            os.remove(qr_path)
            
    # 3. NAGŁÓWEK DOKUMENTU
    pdf.set_xy(10, 35)
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, sanitize("ZLECENIE TRANSPORTOWE / TRANSPORT ORDER"), ln=True, align="C")
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, sanitize(f"DATA WYSTAWIENIA / ISSUE DATE: {datetime.now().strftime('%d.%m.%Y')}"), ln=True, align="C")
    pdf.ln(5)

    # 4. FUNKCJA RYSUJĄCA TABELĘ
    def add_row(left_text, right_text, right_bold=False):
        left = sanitize(left_text)
        right = sanitize(str(right_text))
        right = right.replace('\r\n', '\n')
        
        # Obliczanie wymaganej wysokości wiersza (ok. 75 znaków w linii)
        lines = 0
        for paragraph in right.split('\n'):
            if len(paragraph) == 0:
                lines += 1
            else:
                lines += (len(paragraph) // 75) + 1
                
        row_h = lines * 5 + 4 # 5mm na linię tekstu + 4mm paddingu
        if row_h < 8: row_h = 8
        
        x = pdf.get_x()
        y = pdf.get_y()
        
        # Zabezpieczenie przed ucięciem tabeli na końcu strony
        if y + row_h > 280:
            pdf.add_page()
            y = pdf.get_y()
        
        # Lewa komórka (Szare tło nagłówka)
        pdf.set_font("Arial", 'B', 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(x, y, 70, row_h, style='DF')
        pdf.set_xy(x, y + (row_h/2) - 2) # Pionowe centrowanie tekstu
        pdf.cell(70, 4, left, align='C')
        
        # Prawa komórka (Białe tło wartości)
        pdf.set_xy(x + 70, y)
        pdf.rect(x + 70, y, 120, row_h)
        pdf.set_font("Arial", 'B' if right_bold else '', 9)
        pdf.set_xy(x + 72, y + 2) # Lekki margines tekstu
        pdf.multi_cell(116, 5, right)
        
        pdf.set_xy(10, y + row_h)

    # 5. ROZDZIELANIE DANYCH (Auto vs Uwagi)
    uwagi_parts = dane.get('auto', '').split("||")
    dane_kierowcy = ""
    uwagi_czyste = dane.get('auto', '')

    if len(uwagi_parts) > 1 and "AUTO:" in uwagi_parts[0]:
        dane_kierowcy = uwagi_parts[0].replace("AUTO:", "").strip()
        uwagi_czyste = " || ".join(uwagi_parts[1:]).strip()
    elif "AUTO:" in dane.get('auto', ''):
        dane_kierowcy = dane.get('auto', '').replace("AUTO:", "").strip()
        uwagi_czyste = ""

    # Sklejamy pełny opis ładunku
    ladunek_tekst = f"{dane.get('opis', '')}\n{uwagi_czyste}".strip()

    # 6. BUDOWA STRUKTURY TABELI ZGODNIE Z WZOREM
    add_row("NUMER ZLECENIA / ORDER NUMBER", dane.get('nr', ''), True)
    add_row("ZLECENIODAWCA / PRINCIPAL", "SQM Prosta Spółka Akcyjna\nul. Poznańska 165, 62-052 Komorniki\nNIP: 7792361182", True)
    add_row("MIEJSCE ZAŁADUNKU / LOADING PLACE", dane.get('zaladunek', ''))
    add_row("ZLECENIOBIORCA / CONTRACTOR", dane.get('przewoznik', ''), True)
    add_row("LADUNEK / CARGO", ladunek_tekst)
    add_row("UWAGI DO TRANSPORTU / TRANSPORT NOTES", "Towar musi zostać zabezpieczony pasami transportowymi. / The goods must be secured with transport belts.")
    add_row("MIEJSCE ROZLADUNKU / UNLOADING PLACE", dane.get('rozladunek', ''))
    add_row("KOSZT / COST", f"{dane.get('stawka', '')} PLN", True)
    add_row("DATA ZALADUNKU / LOADING DATE", dane.get('data_zal', ''))
    
    if dane.get('data_roz'):
        add_row("DATA DOSTAWY / DELIVERY DATE", dane.get('data_roz', ''))
        
    add_row("DANE POJAZDU I KIEROWCY / VEHICLE & DRIVER", dane_kierowcy, True)
    add_row("TERMIN PLATNOSCI / MATURITY", "30 dni / days")
    add_row("POSTANOWIENIA SPECJALNE / SPECIAL PROVISIONS", "Parking strzeżony. Obsługa imprez masowych. / Guarded parking. Mass event services.")
    
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
tab_targi, tab_zaopatrzenie = st.tabs(["🏗️ TRANSPORT TARGOWY", "📦 TRANSPORT ZAOPATRZENIA"])

# =================================================================
# ZAKŁADKA 1: TARGI (Pełny cykl)
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
            czysta_nazwa_eventu = wybrany_projekt_full.split(" (")[0] if "Brak" not in wybrany_projekt_full else "Brak"
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

            submit = st.form_submit_button("🚀 GENERUJ ZLECENIE W BAZIE", use_container_width=True, type="primary")

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
                pelne_uwagi = f"AUTO: {auto_dane} || Logistyk: {logistyk} | {instrukcje} | {harmonogram}"
                
                wiersz = [
                    datetime.now().strftime("%Y-%m-%d %H:%M"), final_nr, "LOGISTYKA CARGO", wybrany_przewoznik,
                    miejsce_zal, miejsce_roz, str(d_zal_pl), str(d_roz_pl), f"Elementy zabudowy - {typ_auta}",
                    "", "", "", "", pelne_uwagi, "", czysta_nazwa_eventu, "TARGI", stawka
                ]
                
                if append_data("Zlecenia", wiersz):
                    st.success(f"✅ Zapisano pod numerem: {final_nr}.")
                    st.balloons()

    st.markdown("---")
    st.subheader("📄 Generuj Zlecenie PDF dla Przewoźnika (Targi)")
    
    if not df_zlecenia.empty and 'Typ transportu' in df_zlecenia.columns:
        df_targi = df_zlecenia[df_zlecenia['Typ transportu'] == 'TARGI'].iloc[::-1].head(50)
        
        if not df_targi.empty:
            c_sel_t, c_btn_t = st.columns([3, 1])
            lista_nr_targi = df_targi['Numer zlecenia'].tolist()
            wybrane_targi_nr = c_sel_t.selectbox("Wybierz ostatnie zlecenia Targowe do druku:", lista_nr_targi)
            
            wiersz_targi = df_targi[df_targi['Numer zlecenia'] == wybrane_targi_nr].iloc[0]
            
            dane_pdf_targi = {
                "nr": str(wybrane_targi_nr),
                "przewoznik": str(wiersz_targi.get('Zleceniobiorca', '')),
                "zaladunek": str(wiersz_targi.get('Miejsce Zaladunku', '')),
                "rozladunek": str(wiersz_targi.get('Miejsce Rozladunku', '')),
                "data_zal": str(wiersz_targi.get('Data Zaladunku', '')),
                "data_roz": str(wiersz_targi.get('Data Rozladunku', '')),
                "opis": str(wiersz_targi.get('Towar', 'Elementy Zabudowy')),
                "auto": str(wiersz_targi.get('Uwagi / Instrukcje', '')),
                "stawka": str(wiersz_targi.get('Stawka', ''))
            }
            
            gotowy_pdf_targi = generate_transport_order_pdf(dane_pdf_targi)
            
            with c_btn_t:
                st.download_button("📥 POBIERZ PDF ZLECENIA", data=gotowy_pdf_targi, file_name=f"Zlecenie_{wybrane_targi_nr.replace('/', '_')}.pdf", mime="application/pdf", type="primary", use_container_width=True)


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
                with st.container(border=True):
                    st.write(f"**Przewoźnik:** {wiersz_danych.get('Zleceniobiorca', 'Brak')}")
                    st.write(f"**Trasa:** {wiersz_danych.get('Miejsce Zaladunku', '')} ➡️ {wiersz_danych.get('Miejsce Rozladunku', '')}")
                    
                    st.markdown("---")
                    dane_kierowcy = st.text_input("Wpisz numery rejestracyjne i dane kierowcy (opcjonalnie):", placeholder="np. PO 12345 / Jan Kowalski")
                    
                    # LOGIKA PRZETWARZANIA DANYCH W TLE
                    idx = df_zlecenia[df_zlecenia['Numer zlecenia'] == wybrane_zlecenie_zaop].index[0]
                    sheet_row = int(idx) + 2
                    
                    uwagi_kol = 'Uwagi / Instrukcje' if 'Uwagi / Instrukcje' in df_zlecenia.columns else df_zlecenia.columns[13]
                    stare_uwagi = str(df_zlecenia.at[idx, uwagi_kol])
                    nowe_uwagi = f"AUTO: {dane_kierowcy} || {stare_uwagi}" if dane_kierowcy else stare_uwagi
                    
                    dane_pdf = {
                        "nr": str(wybrane_zlecenie_zaop),
                        "przewoznik": str(wiersz_danych.get('Zleceniobiorca', '')),
                        "zaladunek": str(wiersz_danych.get('Miejsce Zaladunku', '')),
                        "rozladunek": str(wiersz_danych.get('Miejsce Rozladunku', '')),
                        "data_zal": str(wiersz_danych.get('Data Zaladunku', '')),
                        "data_roz": str(wiersz_danych.get('Data Rozladunku', '')) if 'Data Rozladunku' in wiersz_danych else "",
                        "opis": str(wiersz_danych.get('Towar', 'Sprzęt')),
                        "auto": nowe_uwagi,
                        "stawka": str(wiersz_danych.get(nazwa_kol_stawka, ''))
                    }
                    
                    gotowy_pdf = generate_transport_order_pdf(dane_pdf)
                    
                    c_btn_zap, c_btn_pob = st.columns(2)
                    with c_btn_zap:
                        if st.button("💾 ZAPISZ AUTO DO BAZY", type="primary", use_container_width=True):
                            try:
                                client = get_gsheets_client()
                                sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit").worksheet("Zlecenia")
                                sheet.update_cell(sheet_row, 14, nowe_uwagi)
                                fetch_data.clear() # Czyści cache
                                st.success("Zapisano!")
                            except Exception as e:
                                st.error(f"Błąd zapisu: {e}")
                                
                    with c_btn_pob:
                        st.download_button(
                            label="📥 POBIERZ PDF ZLECENIA", 
                            data=gotowy_pdf, 
                            file_name=f"Zlecenie_{wybrane_zlecenie_zaop.replace('/', '_')}.pdf", 
                            mime="application/pdf", 
                            use_container_width=True
                        )
        else:
            st.success("Brak wycenionych zleceń oczekujących na wystawienie papierów w Dziale Zaopatrzenia.")
    else:
        st.warning("Baza zleceń pusta.")

st.caption("Vortex Nexus 3.0 | Module: Fleet Disposition")
