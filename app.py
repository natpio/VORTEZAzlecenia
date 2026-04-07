import streamlit as st
import pandas as pd
import qrcode
import hashlib
from datetime import datetime
import io
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURACJA ---
SHEET_NAME = "Baza_Zlecen_Transportowych"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_data():
    try:
        client = get_gsheets_client()
        spreadsheet = client.open(SHEET_NAME)
        
        ws_przewoznicy = spreadsheet.worksheet("Zleceniobiorcy")
        dane_przewoznicy = pd.DataFrame(ws_przewoznicy.get_all_records())
        lista_przewoznikow = dane_przewoznicy["Nazwa do listy"].tolist() if not dane_przewoznicy.empty else []
        
        ws_miejsca = spreadsheet.worksheet("Miejsca")
        dane_miejsca = pd.DataFrame(ws_miejsca.get_all_records())
        lista_miejsc = dane_miejsca["Nazwa do listy"].tolist() if not dane_miejsca.empty else []
        
        return lista_przewoznikow, dane_przewoznicy, lista_miejsc, dane_miejsca
    except Exception as e:
        st.error(f"Błąd łączenia z arkuszem: {e}")
        return [], pd.DataFrame(), [], pd.DataFrame()

def append_to_gsheets(worksheet_name, row_data):
    client = get_gsheets_client()
    client.open(SHEET_NAME).worksheet(worksheet_name).append_row(row_data)

def generate_security_qr(order_num, carrier, loading, unloading):
    SECRET_SALT = "CMR2026!SekretneZabezpieczenie" 
    raw_data = f"{order_num}|{carrier}|{loading}|{unloading}|{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"ZLECENIE: {order_num}\nHASH: {secure_hash[:16]}")
    qr.make(fit=True)
    img_byte_arr = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue(), secure_hash[:16]

def generate_pdf(data, qr_bytes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    
    # Nagłówek Zlecenia
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.cell(200, 10, txt=f"ZLECENIE TRANSPORTOWE NR: {data['Numer zlecenia']}", ln=True, align='C')
    pdf.set_font("Helvetica", size=10)
    pdf.ln(5)
    
    pdf.cell(200, 8, txt=f"Zleceniodawca: {data['Zleceniodawca']}", ln=True)
    pdf.cell(200, 8, txt=f"Zleceniobiorca: {data['Zleceniobiorca']}", ln=True)
    pdf.cell(200, 8, txt=f"Zaladunek: {data['Adres zaladunku']}", ln=True)
    pdf.cell(200, 8, txt=f"Rozladunek: {data['Adres rozladunku']}", ln=True)
    pdf.cell(200, 8, txt=f"Data zaladunku: {data['Data zaladunku']} | Data rozladunku: {data['Data rozladunku']}", ln=True)
    pdf.cell(200, 8, txt=f"Towar: {data['Rodzaj towaru']}, {data['Ilosc opakowan']} {data['Rodzaj opakowania']}, Waga: {data['Waga brutto (kg)']}kg", ln=True)
    
    # Szkic CMR
    pdf.ln(15)
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(200, 10, txt="--- SZKIC DOKUMENTU CMR ---", ln=True, align='C')
    pdf.set_font("Helvetica", size=10)
    
    # Tabela 2 kolumny dla CMR
    pdf.cell(95, 20, txt=f"1. Nadawca: {data['Zleceniodawca']}", border=1)
    pdf.cell(95, 20, txt=f"16. Przewoznik: {data['Zleceniobiorca']}", border=1, ln=True)
    
    pdf.cell(95, 20, txt=f"3. Przeznaczenie: {data['Adres rozladunku']}", border=1)
    pdf.cell(95, 20, txt=f"4. Miejsce zaladowania: {data['Adres zaladunku']}", border=1, ln=True)
    
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(qr_bytes)
        pdf.image(tmp.name, x=160, y=10, w=30)
        
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFEJS ---
st.set_page_config(layout="wide")
st.title("Wystawianie Zleceń i CMR")

if st.button("🔄 Odśwież bazy z Google Sheets"):
    st.cache_data.clear()

lista_przewoznikow, df_przewoznicy, lista_miejsc, df_miejsca = load_data()

with st.form("form"):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Strony Zlecenia")
        nr_zlecenia = st.text_input("Numer zlecenia", f"ZLEC/{datetime.now().strftime('%Y/%m')}/")
        zleceniodawca = st.text_input("Zleceniodawca", "Moja Firma Sp. z o.o.")
        wybrany_przewoznik = st.selectbox("Zleceniobiorca (Wybierz z bazy)", lista_przewoznikow)
        
    with col2:
        st.subheader("Trasa i Towar")
        adres_zaladunku = st.selectbox("Miejsce Załadunku", lista_miejsc)
        adres_rozladunku = st.selectbox("Miejsce Rozładunku", lista_miejsc)
        
        col_d1, col_d2 = st.columns(2)
        data_zaladunku = col_d1.date_input("Data załadunku")
        data_rozladunku = col_d2.date_input("Data rozładunku")
        
        col_t1, col_t2, col_t3 = st.columns(3)
        rodzaj_towaru = col_t1.text_input("Rodzaj towaru", "Części zamienne")
        ilosc_opakowan = col_t2.text_input("Ilość opakowań", "33")
        rodzaj_opakowania = col_t3.selectbox("Rodzaj opakowania", ["EUR", "Karton", "Sztuka"])
        waga = st.text_input("Waga brutto (kg)", "24000")
        uwagi = st.text_area("Uwagi / Instrukcje")

    submit = st.form_submit_button("Generuj PDF i Zapisz")

if submit:
    qr_bytes, hash_qr = generate_security_qr(nr_zlecenia, wybrany_przewoznik, adres_zaladunku, adres_rozladunku)
    
    # Zapis do Historii w Arkuszu
    wiersz_historii = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nr_zlecenia, zleceniodawca, wybrany_przewoznik, 
        adres_zaladunku, adres_rozladunku, str(data_zaladunku), str(data_rozladunku),
        rodzaj_towaru, ilosc_opakowan, rodzaj_opakowania, waga, "", uwagi, hash_qr
    ]
    append_to_gsheets("Zlecenia", wiersz_historii)
    st.success("Zapisano w Google Sheets!")

    order_data = {
        "Numer zlecenia": nr_zlecenia, "Zleceniodawca": zleceniodawca, "Zleceniobiorca": wybrany_przewoznik,
        "Adres zaladunku": adres_zaladunku, "Adres rozladunku": adres_rozladunku, 
        "Data zaladunku": str(data_zaladunku), "Data rozladunku": str(data_rozladunku),
        "Rodzaj towaru": rodzaj_towaru, "Ilosc opakowan": ilosc_opakowan, 
        "Rodzaj opakowania": rodzaj_opakowania, "Waga brutto (kg)": waga
    }
    
    pdf_bytes = generate_pdf(order_data, qr_bytes)
    st.download_button("📄 Pobierz PDF Zlecenia", pdf_bytes, f"{nr_zlecenia.replace('/', '_')}.pdf", "application/pdf")
