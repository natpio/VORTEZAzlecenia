import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os

try:
    import openpyxl
except ImportError:
    st.error("Brak biblioteki 'openpyxl'. Dodaj ją do pliku requirements.txt!")
    st.stop()

# Importujemy silnik Vortex
from core import fetch_data

# ==========================================
# ⚙️ MAPOWANIE KOMÓREK SZABLONU CMR (EXCEL)
# Odczytane z wgranego szablonu cmr_template.xlsx
# ==========================================
MAP_CMR = {
    "1_Nadawca": "D6",               # Rubryka 1: Nadawca
    "2_Odbiorca": "D14",             # Rubryka 2: Odbiorca
    "3_Miejsce_Przeznaczenia": "D20",# Rubryka 3: Miejsce przeznaczenia (rozładunek)
    "4_Miejsce_Zaladunku": "D24",    # Rubryka 4: Miejsce i data załadunku
    "5_Zalaczone_Dokumenty": "D28",  # Rubryka 5: Załączone dokumenty
    "16_Przewoznik": "M14",          # Rubryka 16: Przewoźnik
    "17_Pojazd": "M20",              # Rubryka 17: Numery rejestracyjne
    "6_Towar": "D32",                # Rubryki 6-12: Cechy i opis towaru
    "11_Waga": "L32",                # Rubryka 11: Waga brutto
    "13_Instrukcje": "D40",          # Rubryka 13: Instrukcje nadawcy
    "21_Wystawiono_w": "E47",        # Rubryka 21: Miejscowość
    "21_Data_Wystawienia": "I47",    # Rubryka 21: Data
    "Ref_Zlecenia": "O6"             # Numer referencyjny zlecenia
}

def fill_excel_cmr(dane, template_path="cmr_template.xlsx"):
    """Ładuje szablon Excel, wstrzykuje dane w odpowiednie komórki i zwraca plik w pamięci."""
    wb = openpyxl.load_workbook(template_path)
    ws = wb.active # Bierzemy pierwszy aktywny arkusz
    
    # Wstrzykiwanie danych wg mapowania
    for klucz, komorka in MAP_CMR.items():
        if klucz in dane:
            # Ustawienie wartości komórki (openpyxl zachowuje formatowanie tła/ramek)
            ws[komorka] = dane[klucz]
            
    # Zapisujemy do pamięci (BytesIO) żeby użytkownik mógł to od razu pobrać
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# --- INTERFEJS TERMINALA ---
st.markdown("<h1 style='color: #38bdf8;'>📄 TERMINAL CMR (AUTO-EXCEL)</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Generowanie międzynarodowych listów przewozowych w oparciu o standaryzowany szablon Excel.</p>", unsafe_allow_html=True)

# Weryfikacja czy szablon w ogóle istnieje na serwerze
if not os.path.exists("cmr_template.xlsx"):
    st.error("🚨 BRAK SZABLONU: Wgraj plik `cmr_template.xlsx` do głównego folderu aplikacji na GitHubie, aby Terminal zadziałał!")
    st.stop()

with st.spinner("Ładowanie rejestru zleceń..."):
    df = fetch_data("Zlecenia")

if not df.empty:
    # Filtrowanie zleceń Cargo
    if 'Typ transportu' in df.columns:
        df_cargo = df[df['Typ transportu'] == 'TARGI'].iloc[::-1]
    else:
        df_cargo = df.copy()
    
    if not df_cargo.empty:
        with st.container(border=True):
            st.markdown("### 🔍 Wybierz zlecenie")
            lista_nr = df_cargo['Numer zlecenia'].astype(str).tolist()
            wybor = st.selectbox("Wybierz Numer Zlecenia z bazy:", lista_nr, index=0)
            
            r = df_cargo[df_cargo['Numer zlecenia'].astype(str) == wybor].iloc[0]
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Przewoźnik:** {r.get('Zleceniobiorca', 'N/A')}")
                st.write(f"**Trasa:** {r.get('Miejsce Zaladunku', 'N/A')} ➡️ {r.get('Miejsce Rozladunku', 'N/A')}")
            with c2:
                st.write(f"**Data Załadunku:** {r.get('Data Zaladunku', 'N/A')}")
                
            # Parsowanie uwag, aby wyciągnąć ewentualnie wpisanego kierowcę/auto
            uwagi_raw = str(r.get('Uwagi / Instrukcje', ''))
            pojazd = "TBA"
            if 'AUTO: ' in uwagi_raw:
                pojazd = uwagi_raw.split('AUTO: ')[-1].split(' ||')[0]
                
            # MAPOWANIE DANYCH Z BAZY POD SZABLON
            dane_doc = {
                "1_Nadawca": "SQM Prosta Spółka Akcyjna\nLogistics Department\nul. Piekarna 1\n62-052 Komorniki, Polska",
                "2_Odbiorca": f"TARGI / EVENT: {r.get('ID Projektu', 'N/A')}\n{r.get('Miejsce Rozladunku', 'N/A')}",
                "3_Miejsce_Przeznaczenia": str(r.get('Miejsce Rozladunku', '')),
                "4_Miejsce_Zaladunku": f"{r.get('Miejsce Zaladunku', '')}\nData: {r.get('Data Zaladunku', '')}",
                "5_Zalaczone_Dokumenty": f"Zlecenie: {wybor}",
                "16_Przewoznik": str(r.get('Zleceniobiorca', '')),
                "17_Pojazd": pojazd,
                "6_Towar": str(r.get('Towar', 'Exhibition Structures / Sprzęt AV')),
                "11_Waga": "Wg Packing List", 
                "13_Instrukcje": uwagi_raw,
                "21_Wystawiono_w": "Komorniki",
                "21_Data_Wystawienia": datetime.now().strftime('%Y-%m-%d'),
                "Ref_Zlecenia": f"REF: {wybor}"
            }

            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("⚡ GENERUJ PLIK EXCEL (CMR)", type="primary", use_container_width=True):
                with st.spinner("Wypełnianie szablonu CMR..."):
                    try:
                        excel_file = fill_excel_cmr(dane_doc)
                        st.success("✅ Dokument CMR pomyślnie wypełniony!")
                        
                        st.download_button(
                            label="📥 POBIERZ WYPEŁNIONY CMR (.XLSX)",
                            data=excel_file,
                            file_name=f"CMR_{wybor.replace('/', '_')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Wystąpił błąd podczas uzupełniania excela: {e}")
    else:
        st.info("Brak aktywnych zleceń w bazie.")
else:
    st.error("Baza zleceń jest pusta.")

st.caption("Vorteza Orders dla SQM | Module: CMR Excel Terminal")
