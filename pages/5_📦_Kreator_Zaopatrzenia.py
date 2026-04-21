import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Kreator Zaopatrzenia | Zaopatrzenie")

# --- UKRYCIE DOMYŚLNEGO MENU I DEDYKOWANY PASEK BOCZNY (ZAOPATRZENIE) ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='color: #10b981;'>📦 ZAOPATRZENIE</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/5_📦_Kreator_Zaopatrzenia.py", label="Kreator Zaopatrzenia")
    st.page_link("pages/6_💰_Finanse_Projektu.py", label="Finanse Projektów (Koszty)")
    st.page_link("pages/7_🏢_Baza_Kontrahentow.py", label="Baza Kontrahentów / Miejsc")

# --- KONFIGURACJA BAZY DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=15) # Krótki czas cache, aby szybko widzieć nowe zgłoszenia
def load_procurement_data():
    try:
        client = get_gsheets_client()
        sh = client.open_by_url(SHEET_URL)
        df_zlecenia = pd.DataFrame(sh.worksheet("Zlecenia").get_all_records())
        df_miejsca = pd.DataFrame(sh.worksheet("Miejsca").get_all_records())
        return df_zlecenia, df_miejsca
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_z, df_m = load_procurement_data()

# --- INTERFEJS APLIKACJI ---
st.title("📦 System Zarządzania Zaopatrzeniem")
st.markdown("Obsługa transportu sprzętu wypożyczonego. Moduł dzieli proces na zgłoszenie zapotrzebowania i jego późniejszą wycenę przez logistyka.")

tab1, tab2 = st.tabs(["➕ Nowe Zgłoszenie (Zaopatrzeniowiec)", "💰 Wycena i Zatwierdzenie (Logistyka)"])

# ==========================================
# TAB 1: DLA ZAOPATRZENIOWCA
# ==========================================
with tab1:
    st.subheader("Formularz Zapotrzebowania Transportowego")
    st.info("Wypełnij poniższe dane. Zgłoszenie trafi do działu logistyki w celu wyceny i organizacji przewoźnika.")
    
    with st.form("form_procurement_request", border=True):
        c1, c2 = st.columns(2)
        id_p = c1.text_input("ID Projektu (Wpisz 5 cyfr)", max_chars=5)
        
        lista_miejsc = sorted(df_m['Nazwa do listy'].tolist()) if not df_m.empty else []
        kontrahent = c2.selectbox("Skąd lub dokąd transportujemy?", lista_miejsc)
        
        d1, d2 = st.columns(2)
        data_gotowosci = d1.date_input("Kiedy sprzęt będzie gotowy do jazdy?")
        kierunek = d2.radio("Sugerowany kierunek operacji:", ["Przywóz do nas (Inbound)", "Oddanie sprzętu (Zwrot)"])
        
        co_to = st.text_area("Co dokładnie jedzie? (Opis sprzętu, wymiary, waga, uwagi dla kierowcy)")
        
        submit_req = st.form_submit_button("Wyślij zapotrzebowanie do wyceny")
        
        if submit_req:
            if len(id_p) >= 4 and kontrahent:
                nr_ref = f"REQ/{id_p}/{datetime.now().strftime('%d%m%H%M')}"
                miejsce_zal = kontrahent if "Przywóz" in kierunek else "MAGAZYN WŁASNY"
                miejsce_roz = "MAGAZYN WŁASNY" if "Przywóz" in kierunek else kontrahent
                
                nowy_wiersz = [
                    datetime.now().strftime("%Y-%m-%d %H:%M"), # A: Data wystawienia
                    nr_ref,                  # B: Numer zlecenia
                    "ZAOPATRZENIE",          # C: Dział zgłaszający
                    "",                      # D: Przewoźnik (Czeka na Logistyka)
                    miejsce_zal,             # E: Załadunek
                    miejsce_roz,             # F: Rozładunek
                    str(data_gotowosci),     # G: Data załadunku
                    "",                      # H: Data rozładunku
                    "Sprzęt Wypożyczony",    # I: Rodzaj
                    "", "", "", "",          # J, K, L, M
                    co_to,                   # N: Uwagi
                    "",                      # O: Hash
                    id_p,                    # P: ID Projektu
                    "ZAOP_DO_WYCENY",        # Q: Status początkowy
                    0                        # R: Koszt początkowy
                ]
                
                with st.spinner("Przesyłanie zgłoszenia..."):
                    get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy_wiersz)
                    st.success(f"Zgłoszenie {nr_ref} zostało przesłane do logistyka!")
                    st.cache_data.clear()
            else:
                st.warning("Uzupełnij poprawnie ID Projektu oraz Miejsce!")

# ==========================================
# TAB 2: DLA LOGISTYKA (WYCENA)
# ==========================================
with tab2:
    st.subheader("Kolejka Zgłoszeń do Wyceny")
    
    if not df_z.empty and 'Typ transportu' in df_z.columns:
        oczekujace = df_z[df_z['Typ transportu'] == "ZAOP_DO_WYCENY"]
        
        if not oczekujace.empty:
            st.warning(f"Masz {len(oczekujace)} zgłoszeń oczekujących na wycenę i organizację transportu.")
            
            for idx, row in oczekujace.iterrows():
                with st.expander(f"🔴 Zgłoszenie: {row['Numer zlecenia']} | Projekt: {row['ID Projektu']} | Trasa: {row['Miejsce Zaladunku']} ➡️ {row['Miejsce Rozladunku']}"):
                    st.write(f"**Data gotowości:** {row['Data Zaladunku']}")
                    st.write(f"**Co jedzie:** {row['Uwagi / Instrukcje']}")
                    
                    st.markdown("---")
                    st.markdown("**Panel Akceptacji Transportu (Dla Ciebie)**")
                    
                    with st.form(f"wycena_{row['Numer zlecenia']}"):
                        c1, c2 = st.columns(2)
                        stawka = c1.number_input("Koszt operacji (PLN/EUR)", min_value=0.0, step=10.0)
                        przewoznik = c2.text_input("Przewoźnik (Firma zewnętrzna lub Własny transport)")
                        
                        dane_auta = st.text_input("Dane kierowcy i numer rejestracyjny auta")
                        
                        typ_finalny = st.radio("Zatwierdź oficjalny typ kosztu dla tego ID Projektu:", 
                                               ["Inbound (Zatwierdzony)", "Zwrot (Zatwierdzony)"])
                        
                        submit_wycena = st.form_submit_button("Zatwierdź Koszt i Zaktualizuj Zlecenie")
                        
                        if submit_wycena:
                            try:
                                with st.spinner("Zatwierdzanie zlecenia..."):
                                    client = get_gsheets_client()
                                    ws = client.open_by_url(SHEET_URL).worksheet("Zlecenia")
                                    
                                    # Szukamy komórki z numerem zlecenia
                                    cell = ws.find(row['Numer zlecenia'])
                                    row_idx = cell.row
                                    
                                    # Konstruujemy pełną uwagę (stara uwaga + dane auta)
                                    nowa_uwaga = f"{row['Uwagi / Instrukcje']} || AUTO/KIEROWCA: {dane_auta}" if dane_auta else row['Uwagi / Instrukcje']
                                    
                                    # Aktualizacja w chmurze
                                    ws.update_cell(row_idx, 4, przewoznik)      # D: Przewoźnik
                                    ws.update_cell(row_idx, 14, nowa_uwaga)     # N: Uwagi
                                    ws.update_cell(row_idx, 17, typ_finalny)    # Q: Typ transportu (Klucz do Finansów)
                                    ws.update_cell(row_idx, 18, stawka)         # R: Stawka
                                    
                                    st.success(f"Zlecenie {row['Numer zlecenia']} zostało oficjalnie zatwierdzone z kosztem {stawka}.")
                                    st.cache_data.clear()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Błąd podczas wyceny: {e}")
        else:
            st.success("Wszystkie zgłoszenia zostały obsłużone. Pusto w kolejce! ☕")
    else:
        st.info("Brak danych w bazie.")
