import streamlit as st
import pandas as pd
from datetime import datetime

# Ładujemy nasz nowy silnik!
from core import fetch_data

# ==========================================
# KONFIGURACJA GŁÓWNA APLIKACJI
# ==========================================
st.set_page_config(page_title="Vortex Nexus 3.0", page_icon="🌌", layout="wide")

# ==========================================
# 1. WIDOK GŁÓWNY (DASHBOARD)
# ==========================================
def command_center():
    st.markdown("<h1 style='color: #38bdf8; font-weight: 900; margin-bottom: 0;'>🌌 COMMAND CENTER</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 1.1rem; margin-top: -10px;'>Podsumowanie operacyjne Vortex Nexus w czasie rzeczywistym.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Błyskawiczne pobranie danych z bufora w core.py
    with st.spinner("Pobieranie telemetrii z bazy danych..."):
        df_zlecenia = fetch_data("Zlecenia")

    # --- WYLICZANIE METRYK ---
    dzisiaj = datetime.now().strftime("%Y-%m-%d")
    
    oczekujace_wyceny = 0
    dzisiejsze_wyjazdy = 0
    wszystkie_zlecenia = len(df_zlecenia) if not df_zlecenia.empty else 0

    if not df_zlecenia.empty:
        # Zabezpieczenie nazw kolumn i liczenie
        cols = df_zlecenia.columns.tolist()
        
        # Oczekujące wyceny (Logika: Jeśli wpada z Zaopatrzenia i ma Stawkę 0)
        if 'Stawka' in cols:
            oczekujace_wyceny = len(df_zlecenia[df_zlecenia['Stawka'].astype(str) == "0"])
            
        # Wyjazdy na dzisiaj (szukamy dzisiejszej daty w Dacie Załadunku)
        if 'Data Zaladunku' in cols:
            dzisiejsze_wyjazdy = len(df_zlecenia[df_zlecenia['Data Zaladunku'].astype(str).str.contains(dzisiaj)])

    # --- GÓRNY PASEK WYNIKÓW (KAFELKI) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.info(f"**🗓️ Zlecenia Total**\n# {wszystkie_zlecenia}")
    with c2:
        st.success(f"**🚚 Dzisiejsze Załadunki**\n# {dzisiejsze_wyjazdy}")
    with c3:
        if oczekujace_wyceny > 0:
            st.error(f"**🔥 Oczekujące Wyceny**\n# {oczekujace_wyceny}")
        else:
            st.success(f"**✅ Oczekujące Wyceny**\n# 0")
    with c4:
        st.warning(f"**📡 Status Systemu**\nONLINE (Silnik v3)")

    st.markdown("---")

    # --- TABELE OPERACYJNE ---
    col_left, col_space, col_right = st.columns([10, 1, 10])
    
    with col_left:
        st.markdown("<h4 style='color: #ef4444;'>⚡ Pilne: Do wyceny (Zaopatrzenie)</h4>", unsafe_allow_html=True)
        if oczekujace_wyceny > 0 and 'Stawka' in df_zlecenia.columns:
            df_pilne = df_zlecenia[df_zlecenia['Stawka'].astype(str) == "0"]
            kolumny_pilne = [k for k in ['Data wystawienia', 'Numer zlecenia', 'Miejsce Zaladunku', 'Miejsce Rozladunku'] if k in df_pilne.columns]
            st.dataframe(df_pilne[kolumny_pilne], hide_index=True, use_container_width=True)
        else:
            st.success("Brak zaległych wycen! Logistycy mogą wypić kawę. ☕")

    with col_right:
        st.markdown("<h4 style='color: #38bdf8;'>🚛 Ostatnie operacje (Top 5)</h4>", unsafe_allow_html=True)
        if not df_zlecenia.empty:
            kolumny_ostatnie = [k for k in ['Numer zlecenia', 'Zleceniobiorca', 'Miejsce Rozladunku', 'Stawka'] if k in df_zlecenia.columns]
            # Odwracamy tabelę, żeby najnowsze były na górze i bierzemy 5 pierwszych
            df_ostatnie = df_zlecenia[kolumny_ostatnie].iloc[::-1].head(5)
            st.dataframe(df_ostatnie, hide_index=True, use_container_width=True)
        else:
            st.info("Brak operacji w bazie.")

# ==========================================
# 2. DEFINICJA STRON I STRUKTURY MENU
# ==========================================
# Strona domyślna
dash_page = st.Page(command_center, title="Command Center", icon="🏠", default=True)

# Sekcja CARGO
cargo_1 = st.Page("pages/1_🚛_Dyspozycja_Floty.py", title="Dyspozycja Floty (Targi)")
cargo_2 = st.Page("pages/8_🛠️_Obsluga_Zaopatrzenia.py", title="Wyceniarka Zaopatrzenia")
cargo_3 = st.Page("pages/2_📄_Terminal_CMR.py", title="Terminal CMR")
cargo_4 = st.Page("pages/3_🚚_Baza_Przewoznikow.py", title="Baza Przewoźników")
cargo_5 = st.Page("pages/4_📊_Historia_Zlecen_Cargo.py", title="Historia Zleceń")

# Sekcja ZAOPATRZENIE
zaop_1 = st.Page("pages/5_📦_Zgloszenie_Zaopatrzenia.py", title="Zgłoś Transport")
zaop_2 = st.Page("pages/6_💰_Finanse_Projektu.py", title="Koszty Projektów")

# Sekcja AI & SŁOWNIKI
ai_1 = st.Page("pages/9_🤖_AI_Skaner_Projektow.py", title="AI Skaner Projektów")
slownik_1 = st.Page("pages/7_🏢_Baza_Kontrahentow.py", title="Miejsca i Magazyny")

# ==========================================
# 3. URUCHOMIENIE NOWEJ NAWIGACJI
# ==========================================
pg = st.navigation({
    "Wydział Głównego Dowodzenia": [dash_page],
    "DYSPOZYTORNIA (Logistyk)": [cargo_1, cargo_2, cargo_3, cargo_4, cargo_5],
    "PROJEKTY (Zaopatrzenie)": [zaop_1, zaop_2],
    "NARZĘDZIA SYSTEMOWE": [ai_1, slownik_1]
})

# Odpalamy silnik nawigacji!
pg.run()
