import streamlit as st
import pandas as pd

# Importujemy nasz potężny silnik
from core import fetch_data

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #10b981;'>💰 FINANSE PROJEKTU</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Monitorowanie kosztów logistyki i zaopatrzenia z podziałem na poszczególne eventy.</p>", unsafe_allow_html=True)

# Przycisk błyskawicznego odświeżenia
col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Przelicz koszty (Odśwież)", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# --- POBIERANIE DANYCH ---
with st.spinner("Ładowanie modułu finansowego z bazy danych..."):
    df_zlecenia = fetch_data("Zlecenia")

if not df_zlecenia.empty and 'ID Projektu' in df_zlecenia.columns:
    # Wyciągamy listę unikalnych projektów
    lista_projektow = sorted(df_zlecenia['ID Projektu'].dropna().unique().astype(str).tolist())
    # Filtrujemy puste i techniczne wartości
    lista_projektow = [p for p in lista_projektow if p.strip() != "" and p != "nan"]

    if lista_projektow:
        with st.container(border=True):
            wybrany_projekt = st.selectbox("📊 Wybierz Projekt (ID / Nazwa Targów):", lista_projektow)
            
            # Filtrowanie danych dla wybranego projektu
            df_projektu = df_zlecenia[df_zlecenia['ID Projektu'].astype(str) == wybrany_projekt].copy()
            
            if not df_projektu.empty:
                # Bezpieczna konwersja stawek na liczby
                df_projektu['Stawka_Num'] = pd.to_numeric(df_projektu.get('Stawka', 0), errors='coerce').fillna(0)
                
                # Koszty całkowite
                calkowity_koszt = df_projektu['Stawka_Num'].sum()
                
                # Podział na kierunki (Inbound = kierunek na nasz magazyn własny)
                koszt_inbound = df_projektu[df_projektu['Miejsce Rozladunku'].astype(str).str.contains("MAGAZYN", case=False, na=False)]['Stawka_Num'].sum()
                koszt_outbound = calkowity_koszt - koszt_inbound
                
                # Szukanie transportów oczekujących na wycenę (Stawka == "0")
                oczekujace = df_projektu[df_projektu['Stawka'].astype(str) == "0"]

                # --- DASHBOARD FINANSOWY ---
                st.markdown("### 💵 Budżet Logistyczny")
                k1, k2, k3 = st.columns(3)
                k1.metric("Łączny Koszt Logistyki", f"{calkowity_koszt:,.2f} PLN")
                k2.metric("📦 Ściągnięcie (Inbound)", f"{koszt_inbound:,.2f} PLN")
                k3.metric("🔄 Zwroty (Outbound)", f"{koszt_outbound:,.2f} PLN")
                
                if not oczekujace.empty:
                    st.warning(f"⚠️ **Uwaga:** Ten projekt posiada **{len(oczekujace)}** transport(y) oczekujące na wycenę u Logistyka. Łączny koszt na pewno ulegnie zmianie po ich zatwierdzeniu!")
                
                st.markdown("---")
                st.markdown("### 📋 Rejestr Operacji Projektowych")
                
                # Tabela z najważniejszymi danymi
                kolumny_do_tabeli = ['Data wystawienia', 'Numer zlecenia', 'Miejsce Zaladunku', 'Miejsce Rozladunku', 'Zleceniobiorca', 'Stawka', 'Dział']
                obecne_kolumny = [kol for kol in kolumny_do_tabeli if kol in df_projektu.columns]
                
                st.dataframe(
                    df_projektu[obecne_kolumny].sort_values(by='Data wystawienia', ascending=False),
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("Brak zrealizowanych operacji dla wybranego projektu.")
    else:
        st.warning("Nie znaleziono żadnych przypisanych projektów w bazie zleceń.")
else:
    st.error("Baza danych jest pusta lub brakuje w niej kolumny 'ID Projektu'.")

st.caption("Vortex Nexus 3.0 | Module: Project Finance")
