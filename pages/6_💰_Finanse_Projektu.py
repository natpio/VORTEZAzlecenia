import streamlit as st
import pandas as pd

# Importujemy silnik
from core import fetch_data

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #10b981;'>💰 FINANSE PROJEKTU</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Monitorowanie kosztów logistyki. System inteligentnie zlicza również transporty współdzielone (wiele ID po przecinku).</p>", unsafe_allow_html=True)

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Przelicz koszty (Odśwież)", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

with st.spinner("Ładowanie modułu finansowego..."):
    df_zlecenia = fetch_data("Zlecenia")

if not df_zlecenia.empty and 'ID Projektu' in df_zlecenia.columns:
    
    # 1. PARSOWANIE PROJEKTÓW WSPÓŁDZIELONYCH (ROZBIJANIE PO PRZECINKU)
    unikalne_projekty = set()
    for ids in df_zlecenia['ID Projektu'].dropna().astype(str):
        for pid in ids.split(','): # Rozdzielamy jeśli wpisano z przecinkiem
            clean_id = pid.strip()
            if clean_id and clean_id != "nan":
                unikalne_projekty.add(clean_id)
                
    lista_projektow = sorted(list(unikalne_projekty))

    if lista_projektow:
        with st.container(border=True):
            wybrany_projekt = st.selectbox("📊 Wybierz Projekt (ID / Nazwa Targów):", lista_projektow)
            
            # 2. INTELIGENTNE FILTROWANIE (SZUKAMY CZY ID ZAWIERA SIĘ W STRINGU)
            df_projektu = df_zlecenia[df_zlecenia['ID Projektu'].astype(str).str.contains(wybrany_projekt, case=False, na=False)].copy()
            
            if not df_projektu.empty:
                df_projektu['Stawka_Num'] = pd.to_numeric(df_projektu.get('Stawka', 0), errors='coerce').fillna(0)
                
                calkowity_koszt = df_projektu['Stawka_Num'].sum()
                koszt_inbound = df_projektu[df_projektu['Miejsce Rozladunku'].astype(str).str.contains("MAGAZYN", case=False, na=False)]['Stawka_Num'].sum()
                koszt_outbound = calkowity_koszt - koszt_inbound
                oczekujace = df_projektu[df_projektu['Stawka'].astype(str) == "0"]

                st.markdown("### 💵 Budżet Logistyczny")
                k1, k2, k3 = st.columns(3)
                k1.metric("Łączny Koszt Logistyki", f"{calkowity_koszt:,.2f} PLN")
                k2.metric("📦 Ściągnięcie (Inbound)", f"{koszt_inbound:,.2f} PLN")
                k3.metric("🔄 Zwroty (Outbound)", f"{koszt_outbound:,.2f} PLN")
                
                # Dodatkowa informacja o wspólnym transporcie
                st.info("💡 **Zasada liczenia:** Jeśli transport obsługiwał kilka projektów (np. auto za 1000 PLN wiozło sprzęt dla projektu A i B), pełen koszt zlecenia pokaże się w budżecie obu z nich.")

                if not oczekujace.empty:
                    st.warning(f"⚠️ **Uwaga:** Ten projekt posiada **{len(oczekujace)}** transport(y) oczekujące na wycenę u Logistyka. Łączny koszt ulegnie zmianie!")
                
                st.markdown("---")
                st.markdown("### 📋 Rejestr Operacji Projektowych")
                
                kolumny_do_tabeli = ['Data wystawienia', 'Numer zlecenia', 'Miejsce Zaladunku', 'Miejsce Rozladunku', 'Zleceniobiorca', 'Stawka', 'ID Projektu']
                obecne_kolumny = [kol for kol in kolumny_do_tabeli if kol in df_projektu.columns]
                
                st.dataframe(df_projektu[obecne_kolumny].sort_values(by='Data wystawienia', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.info("Brak zrealizowanych operacji dla wybranego projektu.")
    else:
        st.warning("Nie znaleziono żadnych przypisanych projektów w bazie zleceń.")
else:
    st.error("Baza danych jest pusta lub brakuje w niej kolumny 'ID Projektu'.")

st.caption("Vortex Nexus 3.0 | Module: Project Finance")
