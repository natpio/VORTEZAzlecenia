import streamlit as st
import pandas as pd

# Importujemy silnik Vortex
from core import fetch_data, append_data

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #10b981;'>🏢 BAZA KONTRAHENTÓW I MIEJSC</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Słownik lokalizacji (magazyny, kontrahenci, punkty odbioru) dla działu zaopatrzenia.</p>", unsafe_allow_html=True)

# Przycisk szybkiego odświeżenia bazy
col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę z chmury", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# --- FORMULARZ DODAWANIA NOWEGO MIEJSCA ---
with st.expander("➕ KLIKNIJ TUTAJ, ABY DODAĆ NOWĄ LOKALIZACJĘ", expanded=False):
    with st.form("form_add_location", border=False):
        st.info("Nazwa krótka (do listy) to ta, która pojawi się w rozwijanym menu przy zgłaszaniu transportu.")
        
        # Wiersz 1: Nazewnictwo
        c1, c2 = st.columns(2)
        nazwa_skrocona = c1.text_input("Nazwa krótka (do listy) *Wymagane")
        pelna_firma = c2.text_input("Pełna nazwa firmy / Magazynu")
        
        # Wiersz 2: Adres (Rozdzielony zgodnie z Twoim arkuszem)
        d1, d2, d3, d4 = st.columns([2, 1, 1.5, 1.5])
        ulica = d1.text_input("Ulica i numer")
        kod_pocztowy = d2.text_input("Kod pocztowy")
        miasto = d3.text_input("Miasto")
        kraj = d4.text_input("Kraj", value="Polska")
        
        # Wiersz 3: Kontakt i Technologia
        o1, o2 = st.columns([3, 1])
        osoba_tel = o1.text_input("Osoba kontaktowa / Numer telefonu")
        rampa = o2.selectbox("Rampa załadunkowa:", ["TAK", "NIE", "BRAK DANYCH"])
        
        submit = st.form_submit_button("💾 Zapisz lokalizację w bazie", type="primary")
        
        if submit:
            if nazwa_skrocona:
                with st.spinner("Synchronizacja z Vortex Engine..."):
                    # Dokładne mapowanie 8 kolumn w Twoim arkuszu "Miejsca"
                    nowy_wiersz = [
                        nazwa_skrocona, 
                        pelna_firma, 
                        ulica, 
                        kod_pocztowy, 
                        miasto, 
                        kraj, 
                        osoba_tel, 
                        rampa
                    ]
                    
                    if append_data("Miejsca", nowy_wiersz):
                        st.success(f"Dodano lokalizację: '{nazwa_skrocona}'!")
                        st.rerun()
                    else:
                        st.error("Błąd zapisu. Sprawdź logi systemowe.")
            else:
                st.warning("⚠️ Pole 'Nazwa krótka' jest wymagane do poprawnego działania list rozwijanych!")

# --- WYŚWIETLANIE TABELI ---
st.markdown("### 📋 Rejestr Lokalizacji")
with st.spinner("Pobieranie danych..."):
    df_miejsca = fetch_data("Miejsca")

if not df_miejsca.empty:
    # Wyświetlamy tabelę z możliwością wyszukiwania i filtrowania
    st.dataframe(
        df_miejsca, 
        use_container_width=True, 
        hide_index=True,
        height=550
    )
    st.caption(f"Łącznie zdefiniowanych miejsc w systemie: {len(df_miejsca)}")
else:
    st.info("Baza kontrahentów jest pusta. Użyj formularza powyżej, aby dodać pierwsze miejsce.")

st.caption("Vortex Nexus 3.0 | Module: Locations Directory")
