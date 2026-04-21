import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import qrcode
import io
import tempfile
from fpdf import FPDF
import urllib.request
import os

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Obsługa Zaopatrzenia | Cargo")

# --- UKRYCIE DOMYŚLNEGO MENU I DEDYKOWANY PASEK BOCZNY (CARGO) ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='color: #38bdf8;'>🚛 LOGISTYKA CARGO</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/1_🚛_Dyspozycja_Floty.py", label="Dyspozycja Floty (TARGI)")
    st.page_link("pages/8_🛠️_Obsluga_Zaopatrzenia.py", label="Obsługa Zaopatrzenia")
    st.page_link("pages/2_📄_Terminal_CMR.py", label="Terminal CMR")
    st.page_link("pages/3_🚚_Baza_Przewoznikow.py", label="Baza Przewoźników Cargo")
    st.page_link("pages/4_📊_Historia_Zlecen_Cargo.py", label="Historia Zleceń Cargo")

# --- BAZA DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=15)
def load_zlecenia():
    try:
        client = get_gsheets_client()
        sh = client.open_by_url(SHEET_URL)
        return pd.DataFrame(sh.worksheet("Zlecenia").get_all_records())
    except Exception as e:
        st.error(f"Błąd ładowania bazy: {e}")
        return pd.DataFrame()

df_zlecenia = load_zlecenia()

# --- GENERATOR PDF: ZLECENIE TRANSPORTOWE ---
def generate_transport_order_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # Pobieranie czcionek (polskie znaki)
    font_reg = "Roboto-Regular.ttf"
    font_bold = "Roboto-Bold.ttf"
    if not os.path.exists(font_reg):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf", font_reg)
    if not os.path.exists(font_bold):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf", font_bold)
    
    pdf.add_font("Roboto", "", font_reg, uni=True)
    pdf.add_font("Roboto", "B", font_bold, uni=True)
    
    # Generowanie kodu QR
    qr_data = f"ZLECENIE:{data.get('nr', '')} | STAWKA:{data.get('stawka', '')} | PRZEWOZNIK:{data.get('przewoznik', '')}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(qr_img, format='PNG')
    
    # Nagłówek
    pdf.set_font("Roboto", "B", 16)
    pdf.cell(0, 10, f"ZLECENIE TRANSPORTOWE NR: {data.get('nr', '')}", ln=True, align='C')
    pdf.set_font("Roboto", "", 10)
    pdf.cell(0, 5, f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')} (Terminal Logistyki)", ln=True, align='C')
    pdf.ln(10)
    
    # Kody QR z boku
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(qr_img.getvalue()); tmp.flush(); tmp_name = tmp.name
    pdf.image(tmp_name, x=160, y=10, w=30)
    os.remove(tmp_name)

    # Box 1: Strony zlecenia
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(95, 8, "ZLECENIODAWCA:", border=1)
    pdf.cell(95, 8, "ZLECENIOBIORCA (PRZEWOZNIK):", border=1, ln=True)
    
    pdf.set_font("Roboto", "", 10)
    # Zabezpieczenie przed błędem Streamlit: Usunięto parametr max_line_height
    pdf.multi_cell(95, 6, "VORTEX NEXUS LOGISTICS\nul. Magazynowa 10, 62-052 Komorniki\nKontakt: Logistyka Zaopatrzenia", border=1, align='L')
    
    y_before = pdf.get_y() - 18
    pdf.set_xy(105, y_before)
    pdf.multi_cell(95, 18, f"{data.get('przewoznik', '')}\nAuto/Kierowca: {data.get('auto', '')}", border=1, align='L')
    pdf.ln(5)

    # Box 2: Trasa
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(0, 8, "SZCZEGÓŁY TRANSPORTU", border=1, ln=True, fill=False)
    pdf.set_font("Roboto", "", 10)
    
    pdf.cell(40, 8, "MIEJSCE ZAŁADUNKU:", border=1)
    pdf.cell(150, 8, data.get('zaladunek', ''), border=1, ln=True)
    
    pdf.cell(40, 8, "MIEJSCE ROZŁADUNKU:", border=1)
    pdf.cell(150, 8, data.get('rozladunek', ''), border=1, ln=True)
    
    pdf.cell(40, 8, "DATA ZAŁADUNKU:", border=1)
    pdf.cell(150, 8, data.get('data_zal', ''), border=1, ln=True)
    
    pdf.cell(40, 8, "TOWAR / UWAGI:", border=1)
    pdf.multi_cell(150, 8, data.get('opis', ''), border=1)
    pdf.ln(5)

    # Box 3: Finanse
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(0, 8, "WARUNKI FINANSOWE", border=1, ln=True)
    pdf.set_font("Roboto", "", 12)
    pdf.cell(40, 10, "USTALONA STAWKA:", border=1)
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(150, 10, f"{data.get('stawka', '0')} PLN netto", border=1, ln=True)

    pdf.ln(20)
    pdf.set_font("Roboto", "", 10)
    pdf.cell(95, 5, ".......................................................", ln=False, align='C')
    pdf.cell(95, 5, ".......................................................", ln=True, align='C')
    pdf.cell(95, 5, "Podpis Zleceniodawcy", ln=False, align='C')
    pdf.cell(95, 5, "Podpis Przewoznika", ln=True, align='C')

    # Zabezpieczenie TypeError dla FPDF
    return pdf.output(dest='S').encode('latin-1')


# --- INTERFEJS APLIKACJI ---
st.title("🛠️ Centrum Obsługi Zaopatrzenia")
st.markdown("Miejsce, w którym Logistyk wycenia zgłoszenia od zaopatrzeniowców, wybiera przewoźników i generuje zlecenia transportowe.")

tab1, tab2 = st.tabs(["💰 Wycena i Zatwierdzanie (Nowe)", "📄 Generuj Zlecenie PDF (Gotowe)"])

# ==========================================
# TAB 1: WYCENA
# ==========================================
with tab1:
    st.subheader("Oczekujące zgłoszenia od zaopatrzeniowców")
    
    if not df_zlecenia.empty and 'Typ transportu' in df_zlecenia.columns:
        oczekujace = df_zlecenia[df_zlecenia['Typ transportu'] == "ZAOP_DO_WYCENY"]
        
        if not oczekujace.empty:
            for idx, row in oczekujace.iterrows():
                with st.expander(f"🔴 REQ: {row.get('Numer zlecenia', '')} | Projekt: {row.get('ID Projektu', '')} | 📍 {row.get('Miejsce Zaladunku', '')} ➡️ {row.get('Miejsce Rozladunku', '')}"):
                    st.write(f"**Data gotowości:** {row.get('Data Zaladunku', '')}")
                    st.write(f"**Sprzęt:** {row.get('Uwagi / Instrukcje', '')}")
                    
                    st.markdown("---")
                    with st.form(f"wycena_{row.get('Numer zlecenia', '')}"):
                        c1, c2 = st.columns(2)
                        stawka = c1.number_input("Koszt (PLN/EUR)", min_value=0.0)
                        przewoznik = c2.text_input("Przewoźnik (np. DPD, Własne Auto)")
                        
                        auto = st.text_input("Dane kierowcy / Numer rejestracyjny")
                        typ_final = st.radio("Zatwierdź oficjalny typ:", ["Inbound (Zatwierdzony)", "Zwrot (Zatwierdzony)"])
                        
                        if st.form_submit_button("Zatwierdź Koszt i Transport"):
                            try:
                                with st.spinner("Zatwierdzanie w systemie..."):
                                    client = get_gsheets_client()
                                    ws = client.open_by_url(SHEET_URL).worksheet("Zlecenia")
                                    
                                    cell = ws.find(row['Numer zlecenia'])
                                    row_idx = cell.row
                                    
                                    # Dodajemy auto do uwag
                                    stara_uwaga = str(row.get('Uwagi / Instrukcje', ''))
                                    nowa_uwaga = f"{stara_uwaga} || {auto}" if auto else stara_uwaga
                                    
                                    # Zapis do Google Sheets
                                    ws.update_cell(row_idx, 4, przewoznik)
                                    ws.update_cell(row_idx, 14, nowa_uwaga)
                                    ws.update_cell(row_idx, 17, typ_final)
                                    ws.update_cell(row_idx, 18, stawka)
                                    
                                    st.success(f"Zlecenie zatwierdzone. Przejdź do zakładki PDF, aby pobrać dokument.")
                                    st.cache_data.clear()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Wystąpił błąd podczas zapisu: {e}")
        else:
            st.success("Wszystkie zgłoszenia zostały wycenione. Pusto w kolejce!")
    else:
        st.info("Brak danych do wyświetlenia.")

# ==========================================
# TAB 2: GENERATOR PDF
# ==========================================
with tab2:
    st.subheader("Pobierz Zlecenie Transportowe (PDF)")
    
    if not df_zlecenia.empty and 'Typ transportu' in df_zlecenia.columns:
        zatwierdzone = df_zlecenia[df_zlecenia['Typ transportu'].isin(["Inbound (Zatwierdzony)", "Zwrot (Zatwierdzony)"])]
        
        if not zatwierdzone.empty:
            # Lista z numerami zleceń
            lista_numerow = [str(nr) for nr in zatwierdzone['Numer zlecenia'].tolist() if pd.notna(nr)][::-1]
            
            if lista_numerow:
                wybrane_nr = st.selectbox("Wybierz Zlecenie do wygenerowania PDF:", lista_numerow)
                row = zatwierdzone[zatwierdzone['Numer zlecenia'].astype(str) == wybrane_nr].iloc[0]
                
                st.write(f"**Przewoźnik:** {row.get('Zleceniobiorca', 'Brak')} | **Stawka:** {row.get('Stawka', '0')} PLN")
                
                if st.button("📄 GENERUJ ZLECENIE PDF", type="primary"):
                    with st.spinner("Generowanie pliku..."):
                        
                        # Bezpieczne dzielenie uwag
                        uwagi_pelne = str(row.get('Uwagi / Instrukcje', ''))
                        opis_towaru = uwagi_pelne.split("||")[0].strip() if "||" in uwagi_pelne else uwagi_pelne
                        dane_kierowcy = uwagi_pelne.split("||")[1].strip() if "||" in uwagi_pelne else "Brak danych auta"

                        dane_pdf = {
                            "nr": str(row.get('Numer zlecenia', '')),
                            "przewoznik": str(row.get('Zleceniobiorca', '')),
                            "zaladunek": str(row.get('Miejsce Zaladunku', '')),
                            "rozladunek": str(row.get('Miejsce Rozladunku', '')),
                            "data_zal": str(row.get('Data Zaladunku', '')),
                            "opis": opis_towaru,
                            "auto": dane_kierowcy,
                            "stawka": str(row.get('Stawka', '0'))
                        }
                        
                        pdf_file = generate_transport_order_pdf(dane_pdf)
                        bezpieczna_nazwa = wybrane_nr.replace('/', '_')
                        
                        st.download_button(
                            label="📥 POBIERZ GOTOWE ZLECENIE (PDF)",
                            data=pdf_file,
                            file_name=f"Zlecenie_{bezpieczna_nazwa}.pdf",
                            mime="application/pdf"
                        )
            else:
                st.warning("Brak zatwierdzonych zleceń z poprawnym numerem.")
        else:
            st.warning("Brak zatwierdzonych zleceń. Najpierw wyceń zgłoszenie w zakładce nr 1.")
