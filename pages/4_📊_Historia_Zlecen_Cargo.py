import streamlit as st
import pandas as pd
from core import fetch_data, update_data, delete_data

# Ustawienia strony
st.set_page_config(page_title="Vortex Nexus - Historia", page_icon="📊", layout="wide")

st.markdown("<h2 style='text-align: center; color: #38bdf8;'>📊 Historia i Zarządzanie Zleceniami Cargo</h2>", unsafe_allow_html=True)

# Pobieranie danych z bazy
with st.spinner("Synchronizacja z bazą Google Sheets..."):
    df = fetch_data("Zlecenia")

if df is None or df.empty:
    st.info("Baza zleceń jest obecnie pusta.")
else:
    # Tworzymy zakładki: Podgląd i Zarządzanie
    tab_view, tab_manage = st.tabs(["🔍 Przegląd i Filtrowanie", "⚙️ Edycja / Usuwanie Zleceń"])

    with tab_view:
        st.markdown("### Pełna lista operacji")
        
        # Filtrowanie bazy
        c1, c2, c3 = st.columns([2, 1, 1])
        search_query = c1.text_input("Szukaj (nr zlecenia, przewoźnik, miasto):", placeholder="Wpisz frazę...")
        
        # Logika filtrowania
        if search_query:
            mask = df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
            filtered_df = df[mask]
        else:
            filtered_df = df

        # Wyświetlanie tabeli
        st.dataframe(
            filtered_df, 
            use_container_width=True, 
            height=600,
            column_config={
                "Data utworzenia": st.column_config.TextColumn("Data wpisu"),
                "Numer": st.column_config.TextColumn("Nr Zlecenia"),
                "Stawka": st.column_config.TextColumn("Kwota")
            }
        )
        st.caption(f"Liczba wyświetlonych rekordów: {len(filtered_df)}")

    with tab_manage:
        st.markdown("### Panel Modyfikacji Zleceń")
        st.write("Wybierz zlecenie z listy, aby poprawić dane lub usunąć rekord z bazy.")

        # Ustalenie kolumny ID (zazwyczaj druga kolumna: 'Numer')
        id_col = "Numer" if "Numer" in df.columns else df.columns[1]
        
        # Lista wszystkich numerów zleceń do wyboru (najnowsze na górze)
        lista_zlecen = sorted(df[id_col].dropna().unique().tolist(), reverse=True)
        
        wybrany_nr = st.selectbox("Wybierz numer zlecenia do edycji:", ["---"] + lista_zlecen)

        if wybrany_nr != "---":
            # Wyciągnięcie danych konkretnego wiersza
            raw_row = df[df[id_col] == wybrany_nr].iloc[0]
            
            st.divider()
            
            # Formularz edycji
            with st.form("global_edit_form"):
                st.subheader(f"Edytujesz: {wybrany_nr}")
                
                col1, col2 = st.columns(2)
                
                # Pola edycji zaciągające obecne wartości
                new_przewoznik = col1.text_input("Przewoźnik:", value=str(raw_row.get("Przewoźnik", "")))
                new_zal = col1.text_input("Miejsce załadunku:", value=str(raw_row.get("Miejsce załadunku", "")))
                new_data_zal = col1.text_input("Data załadunku:", value=str(raw_row.get("Data załadunku", "")))
                
                new_projekt = col2.text_input("ID Projektu / Nazwa:", value=str(raw_row.get("Projekt", "")))
                new_roz = col2.text_input("Miejsce rozładunku:", value=str(raw_row.get("Miejsce rozładunku", "")))
                new_data_roz = col2.text_input("Data rozładunku:", value=str(raw_row.get("Data rozładunku", "")))
                
                new_uwagi = st.text_area("Uwagi i detale (Auto, Wartość, Instrukcje):", value=str(raw_row.get("Uwagi", "")))
                
                st.markdown("<br>", unsafe_allow_html=True)
                btn_col1, btn_col2, btn_spacer = st.columns([1, 1, 2])
                
                submit_save = btn_col1.form_submit_button("💾 Zapisz zmiany", type="primary", use_container_width=True)
                submit_delete = btn_col2.form_submit_button("🗑️ Usuń zlecenie", use_container_width=True)

            # Logika przycisków
            if submit_save:
                updates = {
                    "Przewoźnik": new_przewoznik,
                    "Miejsce załadunku": new_zal,
                    "Data załadunku": new_data_zal,
                    "Projekt": new_projekt,
                    "Miejsce rozładunku": new_roz,
                    "Data rozładunku": new_data_roz,
                    "Uwagi": new_uwagi
                }
                with st.spinner("Aktualizacja bazy danych..."):
                    if update_data("Zlecenia", id_col, wybrany_nr, updates):
                        st.success(f"Zlecenie {wybrany_nr} zostało zaktualizowane!")
                        st.balloons()
                        st.rerun()

            if submit_delete:
                st.warning(f"Czy na pewno chcesz bezpowrotnie usunąć zlecenie {wybrany_nr}?")
                confirm = st.checkbox("Tak, potwierdzam usunięcie rekordu.")
                if confirm:
                    with st.spinner("Usuwanie..."):
                        if delete_data("Zlecenia", id_col, wybrany_nr):
                            st.success("Zlecenie usunięte pomyślnie.")
                            st.rerun()
                else:
                    st.info("Zaznacz checkbox powyżej, aby potwierdzić usunięcie.")

# Stopka
st.divider()
st.caption("Nexus Vortex 4.0 PRO | System Zarządzania Logistyką SQM")
