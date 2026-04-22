import streamlit as st
from datetime import datetime
import pandas as pd

# Importujemy silnik
from core import fetch_data, append_data, get_next_daily_number

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #10b981;'>📦 ZGŁOŚ TRANSPORT ZAOPATRZENIA</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Formularz dla działu projektowego do zamawiania transportu sprzętu. Zgłoszenia trafiają bezpośrednio do Wyceniarki logistyków.</p>", unsafe_allow_html=True)

# Pobieranie słownika miejsc z cache silnika
with st.spinner("Ładowanie bazy lokalizacji..."):
    df_miejsca = fetch_data("Miejsca")
    lista_miejsc = df_miejsca['Nazwa do listy'].tolist() if not df_miejsca.empty else ["Brak miejsc w bazie"]

with st.container(border=True):
    with st.form("form_req_v3"):
        st.subheader("1. Podstawowe informacje")
        c1, c2, c3 = st.columns([1, 1, 2])
        logistyk = c1.radio("Opiekun zgłoszenia:", ["PD", "PK"], horizontal=True)
        kierunek = c2.radio("Typ operacji:", ["Inbound (Ściągnięcie na magazyn)", "Zwrot (Odesłanie do kontrahenta)"])
        
        # Zabezpieczenie ID Projektu
        id_p = c3.text_input("ID Projektu (5 cyfr)", max_chars=5, placeholder="np. 35322")
        
        st.markdown("---")
        st.subheader("2. Szczegóły logistyczne")
        d1, d2 = st.columns(2)
        kontrahent = d1.selectbox("Miejsce (Zewnętrzny Magazyn / Firma)", lista_miejsc)
        data_gotowosci = d2.date_input("Data gotowości sprzętu do odbioru/dostawy")
        
        opis = st.text_area("Co transportujemy? (Ilość, waga, wymiary, uwagi)", height=100, placeholder="np. 2 palety sprzętu AV, rampa załadunkowa dostępna do 16:00")
        
        submit_btn = st.form_submit_button("🚀 WYŚLIJ DO WYCENY", type="primary", use_container_width=True)

if submit_btn:
    if len(id_p) >= 4 and "Brak" not in kontrahent:
        with st.spinner("Rejestrowanie w systemie..."):
            # Generowanie numeru zlecenia przez silnik core
            dzisiaj = datetime.now().strftime("%Y-%m-%d")
            kolejny = get_next_daily_number(dzisiaj)
            
            rok = datetime.now().strftime('%y')
            mc_dzien = datetime.now().strftime('%m%d')
            
            nr_zlecenia = f"CRG{rok}/{mc_dzien}/{logistyk}{kolejny:02d}"
            
            # Ustalanie trasy na podstawie kierunku
            m_zal = kontrahent if "Inbound" in kierunek else "MAGAZYN WŁASNY (Komorniki)"
            m_roz = "MAGAZYN WŁASNY (Komorniki)" if "Inbound" in kierunek else kontrahent
            
            # Wiersz dopasowany do 18 kolumn w Google Sheets
            nowy_wiersz = [
                datetime.now().strftime("%Y-%m-%d %H:%M"), 
                nr_zlecenia, 
                "ZAOPATRZENIE", 
                "", # Przewoźnik (puste do wyceny)
                m_zal, 
                m_roz, 
                str(data_gotowosci), 
                "", # Data rozładunku
                "Sprzęt Wypożyczony", 
                "", "", "", "", 
                f"Opiekun: {logistyk} | {opis}", 
                "", 
                id_p, 
                "ZAOP_DO_WYCENY", 
                "0" # Stawka początkowa jako "0" do przefiltrowania przez wyceniarkę
            ]
            
            if append_data("Zlecenia", nowy_wiersz):
                st.success(f"✅ Zgłoszenie zostało wysłane do logistyki! Numer: **{nr_zlecenia}**")
                st.info("Logistyk wyceni to zgłoszenie w swoim panelu. Dane zobaczysz wkrótce w kosztach projektu.")
                st.balloons()
            else:
                st.error("Błąd zapisu. Sprawdź logi silnika.")
    else:
        st.error("Uzupełnij poprawnie ID Projektu (min. 4 znaki) oraz wybierz kontrahenta z listy!")

st.caption("Vortex Nexus 3.0 | Module: Supply Request")
