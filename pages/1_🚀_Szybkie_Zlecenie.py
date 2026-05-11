import streamlit as st
from datetime import datetime
from fpdf import FPDF
from core import fetch_data, append_data, get_next_daily_number
from pricing import get_all_carrier_rates, TRANSIT_DAYS

# --- GENERATOR PDF ---
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
    except:
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
    add_row("CENA TOTAL (NETTO)", f"{dane.get('stawka', '')} {dane.get('waluta', 'EUR')}", True)
    
    if dane.get('typ_zlecenia') == "Pełny event" and float(dane.get('postoj', 0)) > 0:
        add_row("STAWKA ZA POSTÓJ / DZIEŃ", f"{dane.get('postoj', '')} {dane.get('waluta', 'EUR')}")
        
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

# --- INTERFEJS ---
st.set_page_config(page_title="Szybkie Zlecenie", page_icon="🚀", layout="centered")
st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🚀 Szybkie Zlecenie</h2>", unsafe_allow_html=True)

# Słowniki z Google Sheets
with st.spinner("Pobieranie bazy danych..."):
    df_projekty = fetch_data("Projekty")
    df_miejsca = fetch_data("Miejsca")
    
lista_eventow = df_projekty['Nazwa Eventu'].dropna().unique().tolist() if not df_projekty.empty else ["Brak"]
lista_miejsc_baza = df_miejsca['Nazwa do listy'].tolist() if not df_miejsca.empty else []
opcje_lokalizacji = ["Magazyn SQM Komorniki"] + lista_miejsc_baza + ["INNE (wpisz ręcznie)"]

st.markdown("<br>", unsafe_allow_html=True)
typ_zlecenia = st.radio("Model operacyjny:", ["Tylko dostawa", "Pełny event"], horizontal=True)

# SEKCJA 1: TRASA I PARAMETRY
with st.container(border=True):
    st.markdown("#### 1. Kierunek i Waga")
    lista_miast = sorted(list(TRANSIT_DAYS.keys()))
    c1, c2 = st.columns([3, 1])
    miasto_docelowe = c1.selectbox("Wybierz miasto docelowe:", ["Wybierz..."] + lista_miast)
    waga = c2.number_input("Waga (kg):", min_value=100, step=100, value=1000)
    
    d1, d2 = st.columns(2)
    data_zal = d1.date_input("Data załadunku:", datetime.now())
    data_roz = d2.date_input("Data rozładunku:", datetime.now())

# POBIERANIE STAWEK Z PRICING.PY
tryb_ceny = "full" if typ_zlecenia == "Pełny event" else "prop"
slownik_stawek = get_all_carrier_rates(miasto_docelowe, waga, data_zal, data_roz, tryb_ceny)

# SEKCJA 2: WYBÓR PRZEWOŹNIKA I AUTOMATYCZNA STAWKA
with st.container(border=True):
    st.markdown("#### 2. Przewoźnik i Finanse")
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    
    lista_cennikowa = list(slownik_stawek.keys()) if slownik_stawek else ["Wybierz miasto..."]
    wybrany_przewoznik = f1.selectbox("Wybierz z cennika:", ["Wybierz..."] + lista_cennikowa)
    
    stawka_domyslna = slownik_stawek.get(wybrany_przewoznik, 0.0)
    
    stawka_final = f2.number_input("Cena (auto):", min_value=0.0, step=50.0, value=float(stawka_domyslna))
    waluta = f3.selectbox("Waluta:", ["EUR", "PLN"])
    
    if typ_zlecenia == "Pełny event":
        postoj = f4.number_input("Postój/Dz:", min_value=0, step=50, value=150)
    else:
        postoj = 0

# SEKCJA 3: LOKALIZACJE I PROJEKT
with st.container(border=True):
    st.markdown("#### 3. Szczegóły transportu")
    wydarzenie = st.selectbox("Projekt:", lista_eventow)
    l1, l2 = st.columns(2)
    with l1:
        z_sel = st.selectbox("Załadunek:", opcje_lokalizacji)
        z_man = st.text_input("Adres (ręcznie):") if z_sel == "INNE (wpisz ręcznie)" else ""
    with l2:
        r_sel = st.selectbox("Rozładunek:", opcje_lokalizacji)
        r_man = st.text_input("Adres (ręcznie):") if r_sel == "INNE (wpisz ręcznie)" else ""

# SEKCJA 4: DETALE PDF
with st.container(border=True):
    st.markdown("#### 4. Kierowca i Uwagi")
    d_auto, d_wart = st.columns(2)
    c_auto = d_auto.text_input("Dane auta / kierowcy:", placeholder="np. PO 12345 / Jan Kowalski")
    wartosc_towaru = d_wart.number_input("Wartość towaru (PLN):", min_value=0, step=1000, value=50000)
    
    if typ_zlecenia == "Pełny event":
        h1, h2 = st.columns(2)
        data_emp_in = h1.date_input("Odbiór pustych:")
        data_emp_out = h2.date_input("Powrót:")
    else:
        data_emp_in, data_emp_out = "", ""

    u1, u2 = st.columns([3, 1])
    instrukcje = u1.text_input("Uwagi specjalne:")
    podpis = u2.radio("Opiekun:", ["PD", "PK"], horizontal=True)

st.markdown("<br>", unsafe_allow_html=True)

# PRZYCISK GENEROWANIA
if st.button("⚡ GENERUJ I ZAPISZ ZLECENIE", type="primary", use_container_width=True):
    if wybrany_przewoznik == "Wybierz..." or wybrany_przewoznik == "Wybierz miasto...":
        st.error("Wybierz poprawnego przewoźnika z listy!")
    else:
        with st.spinner("Zapisywanie..."):
            final_zal = z_man if z_sel == "INNE (wpisz ręcznie)" else z_sel
            final_roz = r_man if r_sel == "INNE (wpisz ręcznie)" else r_sel
            rok, d_kod = datetime.now().strftime('%y'), datetime.now().strftime('%m%d')
            idx = get_next_daily_number(datetime.now().strftime("%Y-%m-%d"))
            pref = str(wydarzenie)[:3].upper() if wydarzenie != "Brak" else "TRG"
            nr_zlecenia = f"{pref}{rok}/{d_kod}/{podpis}{idx:02d}"
            
            if typ_zlecenia == "Pełny event":
                historia = f"CYKL: {data_zal} -> {data_roz} | EMPTIES: {data_emp_in} | POWRÓT: {data_emp_out}"
            else:
                historia = f"DOSTAWA: {data_zal} -> {data_roz}"
                
            pelne_uwagi = f"AUTO: {c_auto} || WAGA: {waga}kg | WART: {wartosc_towaru}PLN || {historia} || {instrukcje}"
            
            paczka_pdf = {
                "typ_zlecenia": typ_zlecenia, "nr": nr_zlecenia, "przewoznik": wybrany_przewoznik,
                "stawka": stawka_final, "waluta": waluta, "postoj": postoj,
                "zaladunek": final_zal, "data_zal": str(data_zal),
                "rozladunek": final_roz, "data_roz": str(data_roz),
                "data_emp_in": str(data_emp_in), "data_emp_out": str(data_emp_out),
                "waga": waga, "wartosc": wartosc_towaru, "auto": c_auto, "uwagi": instrukcje
            }
            
            wiersz_db = [
                datetime.now().strftime("%Y-%m-%d %H:%M"), nr_zlecenia, "LOGISTYKA CARGO", wybrany_przewoznik,
                final_zal, final_roz, str(data_zal), str(data_roz), "Elementy Zabudowy",
                "", "", "", "", pelne_uwagi, "", wydarzenie, "TARGI", f"{stawka_final} {waluta}"
            ]
            
            if append_data("Zlecenia", wiersz_db):
                pdf_bytes = generate_quick_pdf(paczka_pdf)
                st.success(f"✅ Zlecenie {nr_zlecenia} zapisane w systemie!")
                st.download_button("📥 POBIERZ ZLECENIE PDF", data=pdf_bytes, file_name=f"Zlecenie_{nr_zlecenia.replace('/', '_')}.pdf", mime="application/pdf", use_container_width=True)
