import streamlit as st
import pandas as pd

# Importujemy silnik Vortex
from core import fetch_data, append_data

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #38bdf8;'>🚚 BAZA PRZEWOŹNIKÓW CARGO</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Zarządzanie flotą podwykonawców i ich danymi kontaktowymi.</p>", unsafe_allow_html=True)

# Przycisk szybkiego odświeżenia bazy (czyści cache Streamlita)
col_btn, col_empty = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Odśwież bazę z chmury", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# --- FORMULARZ DODAWANIA NOWEGO PRZEWOŹNIKA ---
# Używamy expandera, żeby formularz nie zajmował ekranu, gdy tylko przeglądasz bazę
with st.expander("➕ KLIKNIJ TUTAJ, ABY DODAĆ NOWEGO PRZEWOŹNIKA", expanded=False):
    with st.form("add_carrier_form", border=False):
        st.info("Pamiętaj: Nazwa krótka (Skrót) będzie wyświetlana na listach rozwijanych w głównym kreatorze zleceń.")
        
        c1, c2 = st.columns(2)
        skrot = c1.text_input("Nazwa krótka (Skrót) *Wymagane")
        pelna_nazwa = c2.text_input("Pełna nazwa firmy *Wymagane")
        
        c3, c4 = st.columns(2)
        nip = c3.text_input("NIP (Opcjonalnie)")
        pojazd = c4.text_input("Domyślny pojazd i kierowca (Opcjonalnie)", placeholder="np. PO 12345 / Jan Kowalski")

        d1, d2, d3 = st.columns([2, 2, 1])
        ulica = d1.text_input("Ulica i numer")
        miasto = d2.text_input("Kod pocztowy i Miasto")
        kraj = d3.text_input("Kraj", value="Polska")
        
        submit = st.form_submit_button("💾 Zapisz Przewoźnika do Bazy", type="primary")
        
        if submit:
            if skrot and pelna_nazwa:
                with st.spinner("Wysyłanie danych do Vortex Engine..."):
                    # Dokładna kolejność zapisu odpowiadająca kolumnom w Twoim arkuszu
                    nowy_wiersz = [skrot, pelna_nazwa, ulica, miasto, kraj, nip, pojazd]
                    
                    if append_data("Zleceniobiorcy", nowy_wiersz):
                        st.success(f"Dodano firmę '{skrot}' do bazy!")
                        st.rerun()
                    else:
                        st.error("Wystąpił problem z zapisem. Sprawdź logi systemowe.")
            else:
                st.warning("⚠️ Pola 'Nazwa krótka' oraz 'Pełna nazwa' są absolutnie wymagane!")

# --- WYŚWIETLANIE TABELI ---
st.markdown("### 📋 Aktualna Lista Przewoźników")
with st.spinner("Pobieranie telemetrii..."):
    df_przewoznicy = fetch_data("Zleceniobiorcy")

if not df_przewoznicy.empty:
    st.dataframe(
        df_przewoznicy, 
        use_container_width=True, 
        hide_index=True,
        height=500
    )
    st.caption(f"Łącznie aktywnych przewoźników w systemie: {len(df_przewoznicy)}")
else:
    st.info("Baza przewoźników jest w tej chwili pusta. Dodaj pierwszy wpis używając formularza powyżej.")

st.caption("Vortex Nexus 3.0 | Module: Carrier Database")
