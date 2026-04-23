import streamlit as st
import pandas as pd
from datetime import datetime

# Importujemy silnik
from core import fetch_data, get_gsheets_client

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #10b981;'>🛠️ WYCENIARKA ZAOPATRZENIA</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Panel wewnętrzny: Akceptacja kosztów i przypisanie przewoźnika do budżetu projektu.</p>", unsafe_allow_html=True)

with st.spinner("Pobieranie zgłoszeń..."):
    df_zlecenia = fetch_data("Zlecenia")
    df_przewoznicy = fetch_data("Zleceniobiorcy")

lista_przewoznikow = df_przewoznicy['Skrócona Nazwa'].tolist() if not df_przewoznicy.empty else ["Brak danych"]

if not df_zlecenia.empty:
    nazwa_kolumny_dzial = df_zlecenia.columns[2]
    df_zaopatrzenie = df_zlecenia[df_zlecenia[nazwa_kolumny_dzial] == 'ZAOPATRZENIE']
    nazwa_kolumny_stawka = 'Stawka' if 'Stawka' in df_zlecenia.columns else df_zlecenia.columns[17]
    
    df_do_wyceny = df_zaopatrzenie[df_zaopatrzenie[nazwa_kolumny_stawka].astype(str) == '0']
    
    c1, c2 = st.columns(2)
    c1.error(f"🔴 Do pilnej wyceny: **{len(df_do_wyceny)}**")
    c2.success(f"🟢 Wszystkich zgłoszeń Zaopatrzenia w bazie: **{len(df_zaopatrzenie)}**")
    st.markdown("---")

    tab1, tab2 = st.tabs(["🔴 DO WYCENY", "🟢 ZAAKCEPTOWANE (Historia)"])

    with tab1:
        if not df_do_wyceny.empty:
            st.markdown("### 📋 Zgłoszenia oczekujące na Twoją wycenę:")
            kolumny_widok = ['Data wystawienia', 'Numer zlecenia', 'Data Zaladunku', 'Miejsce Zaladunku', 'Miejsce Rozladunku', 'Uwagi / Instrukcje', 'ID Projektu']
            
            obecne_kolumny = []
            for k in kolumny_widok:
                if k in df_do_wyceny.columns:
                    obecne_kolumny.append(k)
                elif k == 'Data Zaladunku': obecne_kolumny.append(df_do_wyceny.columns[6])
                elif k == 'Uwagi / Instrukcje': obecne_kolumny.append(df_do_wyceny.columns[13])

            st.dataframe(df_do_wyceny[obecne_kolumny], hide_index=True, use_container_width=True)
            
            st.markdown("### ✍️ Wprowadź wycenę i przekaż do Dyspozycji Floty:")
            with st.container(border=True):
                with st.form("wycena_form"):
                    lista_zlecen_do_wyboru = df_do_wyceny['Numer zlecenia'].tolist()
                    w1, w2, w3, w4 = st.columns([2, 2, 1, 1])
                    wybrane_zlecenie = w1.selectbox("Wybierz zlecenie:", lista_zlecen_do_wyboru)
                    wybrany_przewoznik = w2.selectbox("Wybierz przewoźnika:", lista_przewoznikow)
                    stawka = w3.number_input("Stawka netto:", min_value=1.0, step=50.0)
                    logistyk = w4.radio("Twój podpis:", ["PD", "PK"])
                    
                    submit_wycena = st.form_submit_button("✅ ZATWIERDŹ", type="primary", use_container_width=True)

            if submit_wycena:
                with st.spinner("Zapisywanie w budżetach..."):
                    try:
                        idx = df_zlecenia[df_zlecenia['Numer zlecenia'] == wybrane_zlecenie].index[0]
                        sheet_row = int(idx) + 2 
                        
                        uwagi_kolumna = 'Uwagi / Instrukcje' if 'Uwagi / Instrukcje' in df_zlecenia.columns else df_zlecenia.columns[13]
                        stare_uwagi = str(df_zlecenia.at[idx, uwagi_kolumna])
                        nowe_uwagi = f"Opiekun: {logistyk} | {stare_uwagi}"
                        
                        client = get_gsheets_client()
                        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit").worksheet("Zlecenia")
                        
                        sheet.update_cell(sheet_row, 4, wybrany_przewoznik)
                        sheet.update_cell(sheet_row, 14, nowe_uwagi)
                        sheet.update_cell(sheet_row, 17, "ZAAKCEPTOWANE")
                        sheet.update_cell(sheet_row, 18, stawka)
                        
                        fetch_data.clear()
                        st.success(f"Zlecenie {wybrane_zlecenie} wycenione! Jest teraz gotowe do wysyłki w module Dyspozycja Floty.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd zapisu: {e}")
        else:
            st.success("Brak zgłoszeń do wyceny.")

    with tab2:
        df_zaakceptowane = df_zaopatrzenie[df_zaopatrzenie[nazwa_kolumny_stawka].astype(str) != '0']
        if not df_zaakceptowane.empty:
            st.markdown("### 📚 Historia wycenionych zgłoszeń")
            st.info("Aby wygenerować ostateczne zlecenie PDF dla przewoźnika, przejdź do modułu **Dyspozycja Floty**.")
            
            obecne_kolumny_zakceptowane = [k for k in ['Data wystawienia', 'Numer zlecenia', 'Miejsce Zaladunku', 'Miejsce Rozladunku', 'Zleceniobiorca', 'Stawka', 'ID Projektu'] if k in df_zaakceptowane.columns]
            st.dataframe(df_zaakceptowane[obecne_kolumny_zakceptowane].sort_values(by='Data wystawienia', ascending=False), hide_index=True, use_container_width=True)
        else:
            st.info("Brak zaakceptowanych zleceń w bazie.")
else:
    st.warning("Baza danych jest pusta.")

st.caption("Vortex Nexus 3.0 | Module: Supply Internal Pricing")
