import streamlit as st
import pandas as pd

# Importujemy silnik Vortex
from core import fetch_data, append_data, update_row, delete_row

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #38bdf8;'>🚚 BAZA PRZEWOŹNIKÓW CARGO</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Zarządzanie flotą podwykonawców. Teraz z pełną możliwością edycji i usuwania danych.</p>", unsafe_allow_html=True)

# --- POBIERANIE DANYCH ---
df_przewoznicy = fetch_data("Zleceniobiorcy")

# --- PODZIAŁ NA ZAKŁADKI ---
tab1, tab2, tab3 = st.tabs(["📋 PRZEGLĄDAJ BAZĘ", "➕ DODAJ NOWEGO", "🛠️ ZARZĄDZAJ (EDYTUJ / USUŃ)"])

# ==========================================
# ZAKŁADKA 1: PRZEGLĄDANIE
# ==========================================
with tab1:
    col_refresh, col_empty = st.columns([1, 4])
    if col_refresh.button("🔄 Odśwież listę", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if not df_przewoznicy.empty:
        st.dataframe(df_przewoznicy, use_container_width=True, hide_index=True, height=500)
        st.caption(f"Łącznie przewoźników: {len(df_przewoznicy)}")
    else:
        st.info("Baza jest pusta.")

# ==========================================
# ZAKŁADKA 2: DODAWANIE
# ==========================================
with tab2:
    with st.form("add_carrier_v3"):
        st.subheader("Nowy podwykonawca")
        c1, c2 = st.columns(2)
        skrot = c1.text_input("Nazwa krótka (Skrót) *")
        pelna = c2.text_input("Pełna nazwa firmy *")
        
        c3, c4, c5 = st.columns([2, 2, 1])
        ulica = c3.text_input("Ulica i numer")
        miasto = c4.text_input("Kod i Miasto")
        kraj = c5.text_input("Kraj", value="Polska")
        
        c6, c7 = st.columns(2)
        nip = c6.text_input("NIP")
        pojazd = c7.text_input("Domyślny pojazd/kierowca")
        
        if st.form_submit_button("💾 Zapisz w bazie", type="primary", use_container_width=True):
            if skrot and pelna:
                if append_data("Zleceniobiorcy", [skrot, pelna, ulica, miasto, kraj, nip, pojazd]):
                    st.success("Dodano przewoźnika!")
                    st.rerun()
            else:
                st.warning("Pola oznaczone * są wymagane.")

# ==========================================
# ZAKŁADKA 3: EDYCJA I USUWANIE
# ==========================================
with tab3:
    if not df_przewoznicy.empty:
        lista_firm = df_przewoznicy['Skrócona Nazwa'].tolist()
        wybrany = st.selectbox("Wybierz firmę do modyfikacji:", lista_firm)
        
        # Pobieramy dane wybranej firmy i jej indeks wiersza (Pandas index + 2 dla Google Sheets)
        idx_pd = df_przewoznicy[df_przewoznicy['Skrócona Nazwa'] == wybrany].index[0]
        row_to_edit = df_przewoznicy.iloc[idx_pd]
        gs_row_index = int(idx_pd) + 2
        
        st.markdown("---")
        with st.form("edit_carrier_form"):
            st.warning(f"Tryb edycji: {wybrany}")
            e1, e2 = st.columns(2)
            n_skrot = e1.text_input("Skrót", value=str(row_to_edit.get('Skrócona Nazwa', '')))
            n_pelna = e2.text_input("Pełna nazwa", value=str(row_to_edit.get('Pełna Nazwa', '')))
            
            e3, e4, e5 = st.columns([2, 2, 1])
            n_ulica = e3.text_input("Ulica", value=str(row_to_edit.get('Ulica i numer', '')))
            n_miasto = e4.text_input("Miasto", value=str(row_to_edit.get('Kod pocztowy i Miasto', '')))
            n_kraj = e5.text_input("Kraj", value=str(row_to_edit.get('Kraj', 'Polska')))
            
            e6, e7 = st.columns(2)
            n_nip = e6.text_input("NIP", value=str(row_to_edit.get('NIP', '')))
            n_pojazd = e7.text_input("Pojazd", value=str(row_to_edit.get('Pojazd / Kierowca', '')))
            
            col_save, col_del = st.columns([3, 1])
            
            if col_save.form_submit_button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                nowe_dane = [n_skrot, n_pelna, n_ulica, n_miasto, n_kraj, n_nip, n_pojazd]
                if update_row("Zleceniobiorcy", gs_row_index, nowe_dane):
                    st.success("Zmiany zapisane!")
                    st.rerun()
            
            if col_del.form_submit_button("🗑️ USUŃ FIRMĘ", type="secondary", use_container_width=True):
                if delete_row("Zleceniobiorcy", gs_row_index):
                    st.error(f"Firma {wybrany} została usunięta.")
                    st.rerun()
    else:
        st.info("Baza jest pusta - nie ma czego edytować.")
