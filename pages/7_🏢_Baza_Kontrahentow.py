import streamlit as st
import pandas as pd

# Importujemy nasz zaktualizowany silnik Vortex
from core import fetch_data, append_data, update_row, delete_row

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #10b981;'>🏢 BAZA KONTRAHENTÓW I MIEJSC</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Zarządzanie słownikiem lokalizacji. Teraz z pełną możliwością edycji i usuwania danych.</p>", unsafe_allow_html=True)

# --- POBIERANIE DANYCH ---
df_miejsca = fetch_data("Miejsca")

# --- PODZIAŁ NA ZAKŁADKI ---
tab1, tab2, tab3 = st.tabs(["📋 PRZEGLĄDAJ BAZĘ", "➕ DODAJ NOWĄ LOKALIZACJĘ", "🛠️ ZARZĄDZAJ (EDYTUJ / USUŃ)"])

# ==========================================
# ZAKŁADKA 1: PRZEGLĄDANIE
# ==========================================
with tab1:
    col_refresh, col_empty = st.columns([1, 4])
    if col_refresh.button("🔄 Odśwież listę", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if not df_miejsca.empty:
        st.dataframe(df_miejsca, use_container_width=True, hide_index=True, height=500)
        st.caption(f"Łącznie lokalizacji w bazie: {len(df_miejsca)}")
    else:
        st.info("Baza jest pusta. Dodaj pierwsze miejsce w zakładce obok.")

# ==========================================
# ZAKŁADKA 2: DODAWANIE NOWEJ LOKALIZACJI
# ==========================================
with tab2:
    with st.form("add_location_v3"):
        st.subheader("Nowa lokalizacja w słowniku")
        c1, c2 = st.columns(2)
        nazwa_skrocona = c1.text_input("Nazwa krótka (do listy) *", placeholder="np. SQM Poznań")
        pelna_firma = c2.text_input("Pełna nazwa firmy / Magazynu", placeholder="np. SQM Sp. z o.o. - Magazyn Główny")
        
        d1, d2, d3, d4 = st.columns([2, 1, 1.5, 1.5])
        ulica = d1.text_input("Ulica i numer")
        kod_pocztowy = d2.text_input("Kod pocztowy")
        miasto = d3.text_input("Miasto")
        kraj = d4.text_input("Kraj", value="Polska")
        
        o1, o2 = st.columns([3, 1])
        osoba_tel = o1.text_input("Osoba kontaktowa / Numer telefonu")
        rampa = o2.selectbox("Rampa załadunkowa:", ["TAK", "NIE", "BRAK DANYCH"])
        
        if st.form_submit_button("💾 Zapisz lokalizację w bazie", type="primary", use_container_width=True):
            if nazwa_skrocona:
                with st.spinner("Zapisywanie w chmurze..."):
                    # Dokładnie 8 kolumn zgodnie ze strukturą Arkusza Google
                    nowy_wiersz = [nazwa_skrocona, pelna_firma, ulica, kod_pocztowy, miasto, kraj, osoba_tel, rampa]
                    if append_data("Miejsca", nowy_wiersz):
                        st.success(f"Dodano lokalizację: '{nazwa_skrocona}'!")
                        st.rerun()
            else:
                st.warning("⚠️ Pole 'Nazwa krótka' jest wymagane do poprawnego działania list rozwijanych!")

# ==========================================
# ZAKŁADKA 3: ZARZĄDZANIE (EDYTUJ / USUŃ)
# ==========================================
with tab3:
    if not df_miejsca.empty:
        lista_miejsc = df_miejsca['Nazwa do listy'].tolist()
        wybrane = st.selectbox("Wybierz lokalizację do modyfikacji:", lista_miejsc)
        
        # Pobieramy dane wybranego wiersza i jego indeks
        idx_pd = df_miejsca[df_miejsca['Nazwa do listy'] == wybrane].index[0]
        row_to_edit = df_miejsca.iloc[idx_pd]
        gs_row_index = int(idx_pd) + 2
        
        st.markdown("---")
        with st.form("edit_location_form"):
            st.warning(f"Tryb edycji: {wybrane}")
            
            e1, e2 = st.columns(2)
            n_skrocona = e1.text_input("Nazwa krótka (do listy)", value=str(row_to_edit.get('Nazwa do listy', '')))
            n_pelna = e2.text_input("Pełna nazwa firmy", value=str(row_to_edit.get('Nazwa pełna / Firma', '')))
            
            e3, e4, e5, e6 = st.columns([2, 1, 1.5, 1.5])
            n_ulica = e3.text_input("Ulica", value=str(row_to_edit.get('Ulica i numer', '')))
            n_kod = e4.text_input("Kod pocztowy", value=str(row_to_edit.get('Kod pocztowy', '')))
            n_miasto = e5.text_input("Miasto", value=str(row_to_edit.get('Miasto', '')))
            n_kraj = e6.text_input("Kraj", value=str(row_to_edit.get('Kraj', 'Polska')))
            
            e7, e8 = st.columns([3, 1])
            n_kontakt = e7.text_input("Osoba / Tel", value=str(row_to_edit.get('Osoba / Tel', '')))
            
            # Logika wyboru dla selectboxa
            obecna_rampa = str(row_to_edit.get('Rampa (TAK/NIE)', 'BRAK DANYCH'))
            opcje_rampa = ["TAK", "NIE", "BRAK DANYCH"]
            default_rampa_idx = opcje_rampa.index(obecna_rampa) if obecna_rampa in opcje_rampa else 2
            n_rampa = e8.selectbox("Rampa:", opcje_rampa, index=default_rampa_idx)
            
            col_save, col_del = st.columns([3, 1])
            
            if col_save.form_submit_button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                nowe_dane = [n_skrocona, n_pelna, n_ulica, n_kod, n_miasto, n_kraj, n_kontakt, n_rampa]
                if update_row("Miejsca", gs_row_index, nowe_dane):
                    st.success("Dane lokalizacji zostały zaktualizowane!")
                    st.rerun()
            
            if col_del.form_submit_button("🗑️ USUŃ LOKALIZACJĘ", type="secondary", use_container_width=True):
                if delete_row("Miejsca", gs_row_index):
                    st.error(f"Lokalizacja {wybrane} została trwale usunięta z bazy.")
                    st.rerun()
    else:
        st.info("Baza kontrahentów jest pusta.")

st.caption("Vortex Nexus 3.0 | Module: Locations Directory Admin")
