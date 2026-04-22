import streamlit as st
from datetime import datetime
import pandas as pd

# Importujemy silnik Vortex
from core import fetch_data, append_data, get_next_daily_number

# --- KONFIGURACJA STRONY ---
# Layout i stylistyka są teraz dziedziczone z app.py, ale doprecyzowujemy detale
st.markdown("<h1 style='color: #38bdf8;'>🚛 DYSPOZYCJA FLOTY</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Kreator zleceń transportowych dla transportu ciężkiego (Targi).</p>", unsafe_allow_html=True)

# --- POBIERANIE DANYCH PRZEZ SILNIK CORE ---
with st.spinner("Synchronizacja z bazą projektów..."):
    df_przewoznicy = fetch_data("Zleceniobiorcy")
    df_projekty = fetch_data("Projekty")

# --- PRZYGOTOWANIE LIST WYBORU ---
lista_przewoznikow = df_przewoznicy['Skrócona Nazwa'].tolist() if not df_przewoznicy.empty else ["Brak danych"]

# Inteligentna lista projektów: Nazwa Eventu + (Nazwa Projektu)
if not df_projekty.empty:
    def format_project_name(row):
        event = str(row.get('Nazwa Eventu', 'Nieznany Event'))
        klient = str(row.get('Nazwa Projektu', ''))
        return f"{event} ({klient})" if klient and klient != "nan" else event
    
    df_projekty['Display'] = df_projekty.apply(format_project_name, axis=1)
    lista_eventow = df_projekty['Display'].tolist()
else:
    lista_eventow = ["Brak projektów w bazie"]

# --- FORMULARZ OPERACYJNY ---
with st.container(border=True):
    with st.form("fleet_form_v3"):
        # SEKCJA 1: KTO I GDZIE
        st.markdown("#### 🔑 Identyfikacja i Partnerzy")
        c1, c2, c3 = st.columns([1, 2, 2])
        logistyk = c1.radio("Opiekun:", ["PD", "PK"], horizontal=True)
        wybrany_projekt_full = c2.selectbox("Projekt / Targi:", lista_eventow)
        wybrany_przewoznik = c3.selectbox("Przewoźnik:", lista_przewoznikow)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # SEKCJA 2: TABOR I TRASA
        st.markdown("#### 🚛 Tabor i Trasa")
        t1, t2, t3 = st.columns(3)
        typ_auta = t1.selectbox("Rodzaj naczepy:", ["MEGA", "Standard", "Zestaw 120m3", "Solo", "Bus"])
        miejsce_zal = t2.text_input("Start:", value="Magazyn Komorniki")
        
        # Wyciągamy samą nazwę eventu do adresu (bez nawiasu z klientem)
        czysta_nazwa_eventu = wybrany_projekt_full.split(" (")[0]
        miejsce_roz = t3.text_input("Cel:", value=f"Targi - {czysta_nazwa_eventu}")
        
        st.markdown("<br>", unsafe_allow_html=True)

        # SEKCJA 3: HARMONOGRAM (WIZUALNA)
        st.markdown("#### 📅 Harmonogram Cyklu")
        h1, h2, h3 = st.columns(3)
        d_zal_pl = h1.date_input("Załadunek PL", help="Kiedy auto ładuje się na magazynie?")
        d_roz_targi = h2.date_input("Rozładunek Targi", help="Kiedy auto ma być na stoisku?")
        d_emp_in = h3.date_input("Empties (Odbiór)", help="Odbiór pustych opakowań")
        
        h4, h5, h6 = st.columns(3)
        d_emp_out = h4.date_input("Empties (Zwrot)", help="Zwrot pustych do klienta")
        d_zal_powr = h5.date_input("Załadunek Powrotny", help="Kiedy auto wyjeżdża z targów?")
        d_roz_pl = h6.date_input("Rozładunek PL", help="Powrót na magazyn")

        st.markdown("<br>", unsafe_allow_html=True)

        # SEKCJA 4: KOSZTY I UWAGI
        st.markdown("#### 💰 Warunki i Logistyka")
        k1, k2, k3 = st.columns([1, 2, 2])
        stawka = k1.number_input("Stawka netto (PLN/EUR):", min_value=0.0, step=50.0)
        auto_dane = k2.text_input("Dane auta / kierowcy:", placeholder="np. PO 12345 / Jan Kowalski")
        instrukcje = k3.text_area("Dodatkowe instrukcje:", placeholder="Np. Wjazd bramą nr 4, wymagana kamizelka...", height=68)

        # PRZYCISK FINALIZACJI
        submit = st.form_submit_button("🚀 GENERUJ ZLECENIE I ZAPISZ W BAZIE", use_container_width=True, type="primary")

# --- LOGIKA ZAPISU ---
if submit:
    if "Brak" in wybrany_projekt_full:
        st.error("❌ Nie możesz wystawić zlecenia bez poprawnego projektu!")
    else:
        with st.spinner("Trwa procesowanie zlecenia w Vortex Engine..."):
            # 1. Generowanie inteligentnego numeru
            pref = czysta_nazwa_eventu[:3].upper()
            rok = datetime.now().strftime('%y')
            data_kod = datetime.now().strftime('%m%d')
            dzisiejszy_index = get_next_daily_number(datetime.now().strftime("%Y-%m-%d"))
            
            final_nr = f"{pref}{rok}/{data_kod}/{logistyk}{dzisiejszy_index:02d}"
            
            # 2. Budowa opisu technicznego
            harmonogram = f"CYKL: {d_zal_pl} -> {d_roz_targi} | EMP: {d_emp_in}/{d_emp_out} | POWRÓT: {d_zal_powr} -> {d_roz_pl}"
            pelne_uwagi = f"{instrukcje} || AUTO: {auto_dane} || {harmonogram}"
            
            # 3. Przygotowanie wiersza (Dokładnie 18 kolumn zgodnie z Twoją strukturą)
            wiersz = [
                datetime.now().strftime("%Y-%m-%d %H:%M"), # A: Data wystawienia
                final_nr,                                 # B: Numer zlecenia
                "LOGISTYKA CARGO",                        # C: Dział
                wybrany_przewoznik,                       # D: Zleceniobiorca
                miejsce_zal,                              # E: Miejsce Zaladunku
                miejsce_roz,                              # F: Miejsce Rozladunku
                str(d_zal_pl),                            # G: Data Zaladunku
                str(d_roz_pl),                            # H: Data Rozladunku
                f"Elementy zabudowy - {typ_auta}",        # I: Towar
                "", "", "", "",                           # J, K, L, M: Puste (Waga, Opakowania itp.)
                pelne_uwagi,                              # N: Uwagi
                "",                                       # O: Puste
                czysta_nazwa_eventu,                      # P: ID Projektu
                "TARGI",                                  # Q: Typ transportu
                stawka                                    # R: Stawka
            ]
            
            # 4. Wysyłka przez silnik
            if append_data("Zlecenia", wiersz):
                st.balloons()
                st.success(f"✅ Zlecenie zapisane pomyślnie pod numerem: {final_nr}")
                st.info("Dane są już widoczne w Historii i Dashboardzie.")
            else:
                st.error("Błąd krytyczny przy zapisie do Google Sheets. Sprawdź połączenie.")

st.caption("Vortex Nexus 3.0 | Module: Fleet Disposition")
