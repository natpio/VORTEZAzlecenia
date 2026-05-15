import streamlit as st
import pandas as pd

# Importujemy silnik Vortex
from core import fetch_data

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #38bdf8;'>📊 HISTORIA ZLECEŃ CARGO</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Rejestr i wyszukiwarka wszystkich zrealizowanych transportów ciężkich.</p>", unsafe_allow_html=True)

# Przycisk szybkiego odświeżenia bazy
col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież archiwum", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# --- POBIERANIE DANYCH ---
with st.spinner("Pobieranie archiwum z Vortex Engine..."):
    df_zlecenia = fetch_data("Zlecenia")

if not df_zlecenia.empty:
    # Filtrujemy tylko dział Cargo
    if 'Dział' in df_zlecenia.columns:
        df_cargo = df_zlecenia[df_zlecenia['Dział'] == 'LOGISTYKA CARGO'].copy()
    else:
        df_cargo = df_zlecenia.copy()

    if not df_cargo.empty:
        # --- WYSZUKIWARKA I FILTRY ---
        st.markdown("### 🔍 Wyszukiwarka i Filtry")
        
        # Wyciągamy unikalne wartości do list rozwijanych (omijamy puste)
        lista_eventow = ["Wszystkie"] + sorted(df_cargo['ID Projektu'].dropna().unique().astype(str).tolist())
        lista_przewoznikow = ["Wszyscy"] + sorted(df_cargo['Zleceniobiorca'].dropna().unique().astype(str).tolist())

        with st.container(border=True):
            f1, f2, f3 = st.columns(3)
            filtr_event = f1.selectbox("Filtruj wg Projektu / Targów:", lista_eventow)
            filtr_przew = f2.selectbox("Filtruj wg Przewoźnika:", lista_przewoznikow)
            wyszukiwarka = f3.text_input("Szukaj tekstu:", placeholder="np. PO 12345, Jan Kowalski, Berlin...")

        # Aplikowanie filtrów w locie
        df_filtered = df_cargo.copy()

        if filtr_event != "Wszystkie":
            df_filtered = df_filtered[df_filtered['ID Projektu'].astype(str) == filtr_event]
            
        if filtr_przew != "Wszyscy":
            df_filtered = df_filtered[df_filtered['Zleceniobiorca'].astype(str) == filtr_przew]
            
        if wyszukiwarka:
            df_filtered = df_filtered[
                df_filtered['Numer zlecenia'].astype(str).str.contains(wyszukiwarka, case=False, na=False) |
                df_filtered['Uwagi / Instrukcje'].astype(str).str.contains(wyszukiwarka, case=False, na=False) |
                df_filtered['Miejsce Rozladunku'].astype(str).str.contains(wyszukiwarka, case=False, na=False)
            ]

        # --- STATYSTYKI WYNIKÓW ---
        suma_kosztow = pd.to_numeric(df_filtered['Stawka'], errors='coerce').sum()
        
        m1, m2 = st.columns(2)
        m1.metric("Liczba znalezionych zleceń:", len(df_filtered))
        m2.metric("Suma kosztów w widoku (PLN/EUR):", f"{suma_kosztow:,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- WIDOK TABELI ---
        kolumny_do_widoku = [
            'Data wystawienia', 'Numer zlecenia', 'ID Projektu', 
            'Zleceniobiorca', 'Miejsce Zaladunku', 'Miejsce Rozladunku', 
            'Stawka', 'Uwagi / Instrukcje'
        ]
        
        obecne_kolumny = [col for col in kolumny_do_widoku if col in df_filtered.columns]
        
        # Sortujemy od najnowszych
        if 'Data wystawienia' in df_filtered.columns:
            df_filtered = df_filtered.sort_values(by='Data wystawienia', ascending=False)

        st.dataframe(
            df_filtered[obecne_kolumny],
            use_container_width=True, 
            hide_index=True,
            height=500
        )
    else:
        st.info("Brak wpisów z działu LOGISTYKA CARGO w bazie.")
else:
    st.error("Baza danych jest pusta lub niedostępna.")

st.caption("Vortex Nexus 3.0 | Module: Cargo History")
