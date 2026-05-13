import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib

# Ładujemy silnik Vortex
from core import fetch_data

# ==========================================
# KONFIGURACJA GŁÓWNA APLIKACJI
# ==========================================
st.set_page_config(page_title="Vortex Nexus 4.0 PRO", page_icon="🌌", layout="wide")

# ==========================================
# 1. WIDOK GŁÓWNY (DASHBOARD)
# ==========================================
def command_center():
    st.markdown("<h1 style='color: #38bdf8; font-weight: 900; margin-bottom: 0;'>🌌 COMMAND CENTER</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 1.1rem; margin-top: -10px;'>Vortex Nexus 4.0 PRO | System Zarządzania Logistyką SQM</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Pobranie danych
    with st.spinner("Synchronizacja z bazą danych..."):
        df_zlecenia = fetch_data("Zlecenia")

    # --- METRYKI OPERACYJNE ---
    dzisiaj = datetime.now().strftime("%Y-%m-%d")
    wszystkie_zlecenia = len(df_zlecenia) if not df_zlecenia.empty else 0
    oczekujace_wyceny = 0
    dzisiejsze_wyjazdy = 0

    if not df_zlecenia.empty:
        if 'Stawka' in df_zlecenia.columns:
            oczekujace_wyceny = len(df_zlecenia[df_zlecenia['Stawka'].astype(str) == "0"])
        if 'Data Zaladunku' in df_zlecenia.columns:
            dzisiejsze_wyjazdy = len(df_zlecenia[df_zlecenia['Data Zaladunku'].astype(str).str.contains(dzisiaj)])

    # --- KAFELKI KPI ---
    c1, c2, c3, c4 = st.columns(4)
    c1.info(f"**🗓️ Zlecenia Total**\n# {wszystkie_zlecenia}")
    c2.success(f"**🚚 Dzisiejsze Załadunki**\n# {dzisiejsze_wyjazdy}")
    if oczekujace_wyceny > 0:
        c3.error(f"**🔥 Oczekujące Wyceny**\n# {oczekujace_wyceny}")
    else:
        c3.success(f"**✅ Oczekujące Wyceny**\n# 0")
    c4.warning(f"**📡 Status Systemu**\nONLINE (PRO ENGINE)")

    st.markdown("---")

    # --- UKŁAD GŁÓWNY: WERYFIKATOR + TABELE ---
    col_main, col_verify = st.columns([2, 1])
    
    with col_main:
        st.markdown("<h4 style='color: #38bdf8;'>🚛 Ostatnie operacje (Top 5)</h4>", unsafe_allow_html=True)
        if not df_zlecenia.empty:
            kolumny_ostatnie = [k for k in ['Numer zlecenia', 'Zleceniobiorca', 'Miejsce Rozladunku', 'Stawka'] if k in df_zlecenia.columns]
            df_ostatnie = df_zlecenia[kolumny_ostatnie].iloc[::-1].head(5)
            st.dataframe(df_ostatnie, hide_index=True, use_container_width=True)
        else:
            st.info("Brak operacji w bazie.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #ef4444;'>⚡ Pilne: Do wyceny</h4>", unsafe_allow_html=True)
        if oczekujace_wyceny > 0:
            df_pilne = df_zlecenia[df_zlecenia['Stawka'].astype(str) == "0"]
            kolumny_pilne = [k for k in ['Data wystawienia', 'Numer zlecenia', 'Miejsce Zaladunku', 'Miejsce Rozladunku'] if k in df_pilne.columns]
            st.dataframe(df_pilne[kolumny_pilne], hide_index=True, use_container_width=True)
        else:
            st.success("Wszystkie zlecenia są wycenione. ☕")

    # --- NOWY MODUŁ: WERYFIKATOR DOKUMENTÓW PRO ---
    with col_verify:
        st.markdown("<h4 style='color: #8b5cf6;'>🕵️ Weryfikator PRO</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            st.write("Zeskanuj QR i wklej token poniżej:")
            hash_input = st.text_input("TOKEN (Hash):", placeholder="np. 8A4B9F1C3E2D")
            
            if hash_input:
                token_found = False
                hash_input = hash_input.strip().upper()
                
                with st.spinner("Analiza kryptograficzna..."):
                    for _, row in df_zlecenia.iterrows():
                        # Odtwarzamy bazę tokenu dokładnie tak, jak przy generowaniu PDF
                        nr = str(row.get('Numer zlecenia', ''))
                        prz = str(row.get('Zleceniobiorca', ''))
                        stk_raw = str(row.get('Stawka', '0'))
                        # Wyciągamy tylko liczbę (usuwamy EUR/PLN)
                        stk = stk_raw.split(' ')[0]
                        
                        # Próba dopasowania (jako float dla pewności)
                        try:
                            stk_val = float(stk)
                            token_base = f"{nr}-{prz}-{stk_val}"
                            calc_hash = hashlib.md5(token_base.encode()).hexdigest()[:12].upper()
                            
                            if calc_hash == hash_input:
                                st.success("✅ AUTENTYCZNY")
                                st.markdown(f"""
                                **Dane z bazy:**
                                * **Nr:** {nr}
                                * **Przewoźnik:** {prz}
                                * **Kwota:** {stk_raw}
                                """)
                                token_found = True
                                break
                        except:
                            continue
                            
                if not token_found:
                    st.error("❌ NIEZGODNOŚĆ!")
                    st.warning("Dane na dokumencie nie zgadzają się z bazą Vortex lub dokument został sfałszowany.")

# ==========================================
# 2. DEFINICJA STRON I STRUKTURY MENU
# ==========================================
dash_page = st.Page(command_center, title="Command Center", icon="🏠", default=True)

cargo_1 = st.Page("pages/1_🚀_Szybkie_Zlecenie.py", title="Szybkie Zlecenie")
cargo_2 = st.Page("pages/8_🛠️_Obsluga_Zaopatrzenia.py", title="Wyceniarka Zaopatrzenia")
cargo_3 = st.Page("pages/2_📄_Terminal_CMR.py", title="Terminal CMR")
cargo_4 = st.Page("pages/3_🚚_Baza_Przewoznikow.py", title="Baza Przewoźników")
cargo_5 = st.Page("pages/4_📊_Historia_Zlecen_Cargo.py", title="Historia Zleceń")

zaop_1 = st.Page("pages/5_📦_Zgloszenie_Zaopatrzenia.py", title="Zgłoś Transport")
zaop_2 = st.Page("pages/6_💰_Finanse_Projektu.py", title="Koszty Projektów")

ai_1 = st.Page("pages/9_🤖_AI_Skaner_Projektow.py", title="AI Skaner Projektów")
slownik_1 = st.Page("pages/7_🏢_Baza_Kontrahentow.py", title="Miejsca i Magazyny")

# ==========================================
# 3. URUCHOMIENIE NAWIGACJI
# ==========================================
pg = st.navigation({
    "Wydział Głównego Dowodzenia": [dash_page],
    "DYSPOZYTORNIA (Logistyk)": [cargo_1, cargo_2, cargo_3, cargo_4, cargo_5],
    "PROJEKTY (Zaopatrzenie)": [zaop_1, zaop_2],
    "NARZĘDZIA SYSTEMOWE": [ai_1, slownik_1]
})

pg.run()
