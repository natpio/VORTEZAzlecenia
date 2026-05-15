import streamlit as st
from datetime import datetime, timedelta
from fpdf import FPDF
import qrcode
import tempfile
import os
from core import fetch_data, append_data, get_next_daily_number
from pricing import get_all_carrier_rates, TRANSIT_DAYS

# --- POMOCNICZE FUNKCJE PDF (zachowane z oryginału) ---
def pdf_sanitize(text):
    text = str(text)
    replacements = {'ą':'a','ć':'c','ę':'e','ł':'l','ń':'n','ó':'o','ś':'s','ź':'z','ż':'z'}
    for pl, eng in replacements.items():
        text = text.replace(pl, eng)
    return text.encode('latin-1', 'ignore').decode('latin-1')

st.markdown("<h1 style='color: #38bdf8;'>🚀 SZYBKIE ZLECENIE v5.0</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Generowanie zleceń dla przewoźników stałych oraz giełdowych.</p>", unsafe_allow_html=True)

# Załadowanie danych pomocniczych
with st.spinner("Inicjalizacja systemów..."):
    df_projekty = fetch_data("Projekty")
    df_miejsca = fetch_data("Miejsca")
    lista_projektow = df_projekty['ID Projektu'].tolist() if not df_projekty.empty else []
    lista_miejsc = df_miejsca['Nazwa do listy'].tolist() if not df_miejsca.empty else []

with st.form("quick_order_v5"):
    # --- SEKCJA 1: PROJEKT I DATY ---
    col1, col2, col3 = st.columns(3)
    projekt = col1.selectbox("ID Projektu:", lista_projektow)
    data_zal = col2.date_input("Data załadunku:", datetime.now())
    typ_zlecenia = col3.selectbox("Typ operacji:", ["One-way (Tylko dostawa)", "Pełny event (Dostawa + Powrót)"])

    # --- SEKCJA 2: TRASA I ŁADUNEK ---
    c_m1, c_m2, c_w = st.columns([2, 2, 1])
    m_zal = c_m1.selectbox("Miejsce Załadunku:", lista_miejsc, index=0) # Domyślnie Magazyn
    m_roz = c_m2.selectbox("Miejsce Rozładunku:", lista_miejsc, index=min(1, len(lista_miejsc)-1))
    waga = c_w.number_input("Waga (kg):", min_value=100, step=100, value=1200)

    st.markdown("---")
    
    # --- SEKCJA 3: KLUCZOWA ZMIANA - WYBÓR PRZEWOŹNIKA ---
    st.subheader("🚚 Wybór Przewoźnika")
    source_type = st.radio(
        "Źródło transportu:",
        ["Z cennika (Przewoźnik stały)", "Z giełdy (Stawka negocjowana)"],
        horizontal=True
    )

    wybrany_przewoznik = ""
    stawka_final = 0.0
    waluta = "PLN"
    dni_tranzytu = 1

    if source_type == "Z cennika (Przewoźnik stały)":
        # Pobieramy miasto z wybranej nazwy miejsca rozładunku dla pricing.py
        city_for_price = m_roz.split("(")[-1].replace(")", "").strip() if "(" in m_roz else m_roz
        
        # Wywołujemy silnik wycen z pricing.py
        rates = get_all_carrier_rates(city_for_price, waga, typ_zlecenia, data_zal, None) # Brak daty powrotu w uproszczeniu
        
        if rates:
            options = [f"{k} - {v['total']} {v['currency']} (Dni: {v['transit']})" for k, v in rates.items()]
            sel_rate = st.selectbox("Wybierz przewoźnika z cennika:", options)
            
            # Parsowanie wyboru
            wybrany_przewoznik = sel_rate.split(" - ")[0]
            stawka_final = rates[wybrany_przewoznik]['total']
            waluta = rates[wybrany_przewoznik]['currency']
            dni_tranzytu = rates[wybrany_przewoznik]['transit']
        else:
            st.warning("⚠️ Brak stałych stawek dla tej relacji. Skorzystaj z opcji 'Z giełdy'.")
    
    else:
        # Tryb GIEŁDOWY - Pełna swoboda
        g_col1, g_col2, g_col3 = st.columns([2, 1, 1])
        wybrany_przewoznik = g_col1.text_input("Nazwa firmy przewozowej:", placeholder="np. TRANS-LOG Sp. z o.o.")
        stawka_final = g_col2.number_input("Stawka netto:", min_value=0.0, step=50.0)
        waluta = g_col3.selectbox("Waluta:", ["PLN", "EUR"])
        
        g_col4, g_col5 = st.columns(2)
        dni_tranzytu = g_col4.slider("Dni tranzytu (dla PDF):", 1, 5, 1)
        c_auto = g_col5.text_input("Typ auta / Nr rejestracyjny:", placeholder="np. BUS 10ep / PO12345")

    # --- SEKCJA 4: DODATKI ---
    instrukcje = st.text_area("Uwagi / Instrukcje dla kierowcy:", value="Standard event delivery. Side loading required.")
    
    submit = st.form_submit_button("🔥 GENERUJ ZLECENIE I ZAPISZ", type="primary", use_container_width=True)

# --- LOGIKA PO ZATWIERDZENIU ---
if submit:
    if not wybrany_przewoznik:
        st.error("Proszę podać nazwę przewoźnika!")
    else:
        with st.spinner("Generowanie dokumentacji..."):
            # 1. Obliczanie daty rozładunku na podstawie tranzytu
            data_roz = data_zal + timedelta(days=dni_tranzytu)
            
            # 2. Numeracja
            dzisiaj = datetime.now().strftime("%Y-%m-%d")
            kolejny = get_next_daily_number(dzisiaj)
            nr_zlecenia = f"CRG{datetime.now().strftime('%y/%m%d')}/P{kolejny:02d}"
            
            # 3. Przygotowanie danych do zapisu w Google Sheets (Format spójny z resztą systemu)
            # Uwzględniamy pole 'Dział' jako LOGISTYKA CARGO
            wiersz_db = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                nr_zlecenia,
                "LOGISTYKA CARGO",
                wybrany_przewoznik,
                m_zal,
                m_roz,
                str(data_zal),
                str(data_roz),
                "Zabudowa Targowa PRO", # Towar
                "", "", "", "", # Puste pola (wymiary itp)
                f"STAWKA: {stawka_final} {waluta} | {instrukcje}", # Uwagi
                "", # Kierowca
                str(projekt),
                "TARGI", # Kategoria
                str(stawka_final)
            ]
            
            if append_data("Zlecenia", wiersz_db):
                st.success(f"✅ Zlecenie {nr_zlecenia} zostało zapisane w bazie!")
                # Tutaj wywołanie generatora PDF (PRO_TransportOrder) z Twoich plików
                st.balloons()
