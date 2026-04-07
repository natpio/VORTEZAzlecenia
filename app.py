import streamlit as st
import pandas as pd
import qrcode
import hashlib
from datetime import datetime
import io
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials
import tempfile
import urllib.request
import os

# --- KONFIGURACJA ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_data():
    try:
        client = get_gsheets_client()
        spreadsheet = client.open_by_url(SHEET_URL)
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
    client.open_by_url(SHEET_URL).worksheet(worksheet_name).append_row(row_data)

def generate_security_qr(order_num, carrier, loading, unloading):
    SECRET_SALT = "CMR2026!SekretneZabezpieczenie" 
    raw_data = f"{order_num}|{carrier}|{loading}|{unloading}|{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()
    
    qr_payload = f"""--- DOKUMENT ZABEZPIECZONY ---
Zlec: {order_num}
Przewoznik: {carrier[:20]}...
Trasa: {loading[:15]} -> {unloading[:15]}
SHA-256: {secure_hash}
Zeskanowano w systemie weryfikacyjnym."""

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img_byte_arr = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue(), secure_hash

# --- RYSOWANIE SIATKI CMR ---
def draw_cmr_page(pdf, data, qr_bytes, copy_title):
    pdf.add_page()
    pdf.set_line_width(0.2)
    
    # Nagłówek CMR
    pdf.set_font("Roboto", "B", 12)
    pdf.set_xy(105, 8)
    pdf.cell(95, 5, txt="MIĘDZYNARODOWY SAMOCHODOWY LIST PRZEWOZOWY", align='L')
    pdf.set_xy(105, 12)
    pdf.set_font("Roboto", "", 7)
    pdf.cell(95, 5, txt="INTERNATIONAL CONSIGNMENT NOTE   CMR", align='L')

    pdf.set_xy(10, 8)
    pdf.set_font("Roboto", "B", 10)
    pdf.cell(90, 5, txt=copy_title, align='C')

    # Box 1
    pdf.rect(10, 20, 95, 25)
    pdf.set_xy(11, 21)
    pdf.set_font("Roboto", "", 6)
    pdf.multi_cell(93, 3, txt="1 Nadawca (nazwisko lub nazwa, adres, kraj)\nSender (name, address, country)")
    pdf.set_xy(11, 28)
    pdf.set_font("Roboto", "B", 9)
    pdf.multi_cell(93, 4, txt=data['Zleceniodawca'])

    # Box 2
    pdf.rect(10, 45, 95, 25)
    pdf.set_xy(11, 46)
    pdf.set_font("Roboto", "", 6)
    pdf.multi_cell(93, 3, txt="2 Odbiorca (nazwisko lub nazwa, adres, kraj)\nConsignee (name, address, country)")
    pdf.set_xy(11, 53)
    pdf.set_font("Roboto", "B", 9)
    pdf.multi_cell(93, 4, txt=data['Odbiorca'])

    # Box 3
    pdf.rect(10, 70, 95, 15)
    pdf.set_xy(11, 71)
    pdf.set_font("Roboto", "", 6)
    pdf.multi_cell(93, 3, txt="3 Miejsce przeznaczenia (miejscowość, kraj)\nPlace of delivery of the goods (place, country)")
    pdf.set_xy(11, 77)
    pdf.set_font("Roboto", "B", 9)
    pdf.multi_cell(93, 4, txt=data['Adres rozladunku'])

    # Box 4
    pdf.rect(10, 85, 95, 15)
    pdf.set_xy(11, 86)
    pdf.set_font("Roboto", "", 6)
    pdf.multi_cell(93, 3, txt="4 Miejsce i data załadowania (miejscowość, kraj, data)\nPlace and date of taking over the goods")
    pdf.set_xy(11, 92)
    pdf.set_font("Roboto", "B", 9)
    pdf.multi_cell(93, 4, txt=f"{data['Adres zaladunku']} / {data['Data zaladunku']}")

    # Box 5
    pdf.rect(10, 100, 95, 15)
    pdf.set_xy(11, 101)
    pdf.set_font("Roboto", "", 6)
    pdf.multi_cell(93, 3, txt="5 Załączone dokumenty\nDocuments attached")

    # Box 16
    pdf.rect(105, 20, 95, 25)
    pdf.set_xy(106, 21)
    pdf.set_font("Roboto", "", 6)
    pdf.multi_cell(93, 3, txt="16 Przewoźnik (nazwisko lub nazwa, adres, kraj)\nCarrier (name, address, country)")
    pdf.set_xy(106, 28)
    pdf.set_font("Roboto", "B", 9)
    pelny_przewoznik = f"{data['Zleceniobiorca']}\n{data['Pojazd_Kierowca']}"
    pdf.multi_cell(93, 4, txt=pelny_przewoznik)

    # Box 17
    pdf.rect(105, 45, 95, 15)
    pdf.set_xy(106, 46)
    pdf.set_font("Roboto", "", 6)
    pdf.multi_cell(93, 3, txt="17 Kolejni przewoźnicy (nazwisko lub nazwa, adres, kraj)\nSuccessive carriers")

    # Box 18
    pdf.rect(105, 60, 95, 25)
    pdf.set_xy(106, 61)
    pdf.set_font("Roboto", "", 6)
    pdf.multi_cell(93, 3, txt="18 Zastrzeżenia i uwagi przewoźnika\nCarrier's reservations and observations")

    # Box 13
    pdf.rect(105, 85, 95, 30)
    pdf.set_xy(106, 86)
    pdf.set_font("Roboto", "", 6)
    pdf.multi_cell(93, 3, txt="13 Instrukcje nadawcy\nSender's instructions")
    pdf.set_xy(106, 93)
    pdf.set_font("Roboto", "B", 8)
    pdf.multi_cell(93, 4, txt=data['Uwagi'])

    # Tabela towarów (6 do 12)
    y_tbl = 115
    pdf.rect(10, y_tbl, 190, 45)
    pdf.line(30, y_tbl, 30, y_tbl+45)
    pdf.line(50, y_tbl, 50, y_tbl+45)
    pdf.line(75, y_tbl, 75, y_tbl+45)
    pdf.line(140, y_tbl, 140, y_tbl+45)
    pdf.line(165, y_tbl, 165, y_tbl+45)
    pdf.line(185, y_tbl, 185, y_tbl+45)

    pdf.set_font("Roboto", "", 6)
    pdf.set_xy(10, y_tbl)
    pdf.multi_cell(20, 3, txt="6 Cechy i numery\nMarks and Nos", align='C')
    pdf.set_xy(30, y_tbl)
    pdf.multi_cell(20, 3, txt="7 Ilość sztuk\nNumber of packages", align='C')
    pdf.set_xy(50, y_tbl)
    pdf.multi_cell(25, 3, txt="8 Sposób opakowania\nMethod of packing", align='C')
    pdf.set_xy(75, y_tbl)
    pdf.multi_cell(65, 3, txt="9 Rodzaj towaru\nNature of the goods", align='C')
    pdf.set_xy(140, y_tbl)
    pdf.multi_cell(25, 3, txt="10 Nr statystyczny\nStatistical number", align='C')
    pdf.set_xy(165, y_tbl)
    pdf.multi_cell(20, 3, txt="11 Waga brutto (kg)\nGross weight", align='C')
    pdf.set_xy(185, y_tbl)
    pdf.multi_cell(15, 3, txt="12 Objętość (m3)\nVolume", align='C')

    pdf.set_font("Roboto", "B", 9)
    pdf.set_xy(30, y_tbl+10)
    pdf.cell(20, 5, txt=data['Ilosc opakowan'], align='C')
    pdf.set_xy(50, y_tbl+10)
    pdf.cell(25, 5, txt=data['Rodzaj opakowania'], align='C')
    pdf.set_xy(75, y_tbl+10)
    pdf.cell(65, 5, txt=data['Rodzaj towaru'], align='C')
    pdf.set_xy(165, y_tbl+10)
    pdf.cell(20, 5, txt=data['Waga brutto (kg)'], align='C')

    # Box 14, 15, 21
    y_bot = 160
    pdf.rect(10, y_bot, 95, 15)
    pdf.set_font("Roboto", "", 6)
    pdf.set_xy(11, y_bot+1)
    pdf.multi_cell(93, 3, txt="14 Postanowienia odnośnie przewoźnego / Instruction as to payment carriage")
    
    pdf.rect(10, y_bot+15, 95, 10)
    pdf.set_xy(11, y_bot+16)
    pdf.multi_cell(93, 3, txt="15 Zapłata / Cash on delivery")

    pdf.rect(10, y_bot+25, 95, 15)
    pdf.set_xy(11, y_bot+26)
    pdf.multi_cell(93, 3, txt="21 Wystawiono w / Established in")
    pdf.set_xy(11, y_bot+31)
    pdf.set_font("Roboto", "B", 9)
    pdf.multi_cell(93, 4, txt=f"{data['Adres zaladunku'].split(',')[-1].strip()} , dnia: {data['Data wystawienia']}")

    # Box 19, 20
    pdf.rect(105, y_bot, 95, 15)
    pdf.set_font("Roboto", "", 6)
    pdf.set_xy(106, y_bot+1)
    pdf.multi_cell(93, 3, txt="19 Postanowienia specjalne / Special agreements")

    pdf.rect(105, y_bot+15, 95, 25)
    pdf.set_xy(106, y_bot+16)
    pdf.multi_cell(93, 3, txt="20 Do zapłacenia / To be paid by")

    # Signatures
    y_sig = 200
    pdf.rect(10, y_sig, 63, 30)
    pdf.set_xy(11, y_sig+1)
    pdf.multi_cell(61, 3, txt="22 Podpis i stempel nadawcy\nSignature and stamp of the sender")

    pdf.rect(73, y_sig, 63, 30)
    pdf.set_xy(74, y_sig+1)
    pdf.multi_cell(61, 3, txt="23 Podpis i stempel przewoźnika\nSignature and stamp of the carrier")

    pdf.rect(136, y_sig, 64, 30)
    pdf.set_xy(137, y_sig+1)
    pdf.multi_cell(62, 3, txt="24 Podpis i stempel odbiorcy\nSignature and stamp of the consignee")

    # Wklejenie bezpiecznego kodu QR w Box 22
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(qr_bytes)
        tmp.flush()
        tmp_name = tmp.name
    pdf.image(tmp_name, x=25, y=y_sig+8, w=20)
    os.remove(tmp_name)

    # Stopka
    pdf.set_xy(10, 232)
    pdf.set_font("Roboto", "", 5)
    pdf.multi_cell(190, 2, txt="Wzór CMR dla międzynarodowych przewozów drogowych odpowiada ustaleniom, które zostały dokonane przez Międzynarodową Unię Transportu Drogowego (IRU).")

# --- GENEROWANIE PACZKI PDF ---
def generate_pdf_package(data, qr_bytes):
    pdf = FPDF()
    font_reg = "Roboto-Regular.ttf"
    font_bold = "Roboto-Bold.ttf"
    if not os.path.exists(font_reg):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf", font_reg)
    if not os.path.exists(font_bold):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf", font_bold)
        
    pdf.add_font("Roboto", "", font_reg)
    pdf.add_font("Roboto", "B", font_bold)
    
    # === STRONA 1: ZLECENIE ===
    pdf.add_page()
    pdf.set_font("Roboto", "B", 16)
    pdf.cell(0, 10, txt=f"ZLECENIE TRANSPORTOWE NR: {data['Numer zlecenia']}", ln=True, align='C')
    pdf.set_font("Roboto", "", 10)
    pdf.cell(0, 5, txt=f"Data wystawienia: {data['Data wystawienia']}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Roboto", "B", 10)
    pdf.set_xy(10, 35)
    pdf.cell(90, 8, txt="ZLECENIODAWCA:", border=1, ln=0, align='C')
    pdf.set_xy(110, 35)
    pdf.cell(90, 8, txt="ZLECENIOBIORCA (PRZEWOŹNIK):", border=1, ln=1, align='C')
    
    pdf.set_font("Roboto", "", 10)
    pdf.set_xy(10, 43)
    pdf.multi_cell(90, 25, txt=data['Zleceniodawca'], border=1, align='C')
    pdf.set_xy(110, 43)
    pdf.multi_cell(90, 25, txt=f"{data['Zleceniobiorca']}\n{data['Pojazd_Kierowca']}", border=1, align='C')
    pdf.ln(10)
    
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(0, 10, txt="SZCZEGÓŁY TRASY", ln=True)
    pdf.set_font("Roboto", "B", 10)
    pdf.cell(95, 8, txt="ZAŁADUNEK:", border=1)
    pdf.cell(95, 8, txt="ROZŁADUNEK:", border=1, ln=True)
    
    pdf.set_font("Roboto", "", 10)
    x, y = pdf.get_x(), pdf.get_y()
    pdf.multi_cell(95, 8, txt=f"Adres: {data['Adres zaladunku']}\nData: {data['Data zaladunku']}", border=1)
    pdf.set_xy(x + 95, y)
    pdf.multi_cell(95, 8, txt=f"Adres: {data['Adres rozladunku']}\nData: {data['Data rozladunku']}", border=1)
    pdf.ln(5)
    
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(0, 10, txt="TOWAR I WARUNKI", ln=True)
    pdf.set_font("Roboto", "", 10)
    pdf.cell(60, 8, txt=f"Towar: {data['Rodzaj towaru']}", border=1)
    pdf.cell(60, 8, txt=f"Ilość: {data['Ilosc opakowan']} {data['Rodzaj opakowania']}", border=1)
    pdf.cell(70, 8, txt=f"Waga: {data['Waga brutto (kg)']} kg", border=1, ln=True)
    pdf.multi_cell(0, 8, txt=f"Uwagi: {data['Uwagi']}", border=1)
    
    pdf.ln(20)
    pdf.cell(95, 10, txt="...........................................................", align='C')
    pdf.cell(95, 10, txt="...........................................................", ln=True, align='C')
    pdf.set_font("Roboto", "", 8)
    pdf.cell(95, 5, txt="Pieczątka i podpis Zleceniodawcy", align='C')
    pdf.cell(95, 5, txt="Pieczątka i podpis Zleceniobiorcy", ln=True, align='C')
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(qr_bytes)
        tmp.flush()
        tmp_name = tmp.name
    pdf.image(tmp_name, x=90, y=200, w=30)
    os.remove(tmp_name)

    # === STRONY 2, 3, 4: ORYGINALNE DRUKI CMR ===
    draw_cmr_page(pdf, data, qr_bytes, "1 Egzemplarz dla nadawcy / Copy for sender")
    draw_cmr_page(pdf, data, qr_bytes, "2 Egzemplarz dla odbiorcy / Copy for consignee")
    draw_cmr_page(pdf, data, qr_bytes, "3 Egzemplarz dla przewoźnika / Copy for carrier")

    return bytes(pdf.output()) 

# --- INTERFEJS ---
st.set_page_config(layout="wide", page_title="System Zleceń")
st.title("Wystawianie Zleceń i CMR")

if st.button("🔄 Odśwież bazy z Google Sheets"):
    st.cache_data.clear()

lista_przewoznikow, df_przewoznicy, lista_miejsc, df_miejsca = load_data()

with st.form("form"):
    st.markdown("### Strony Dokumentów")
    col1, col2, col3 = st.columns(3)
    with col1:
        nr_zlecenia = st.text_input("Numer zlecenia", f"ZLEC/{datetime.now().strftime('%Y/%m')}/")
        zleceniodawca = st.text_area("Nadawca / Zleceniodawca", "Moja Firma Sp. z o.o.\nul. Testowa 1\n00-001 Warszawa\nNIP: 1234567890", height=100)
    with col2:
        wybrany_przewoznik = st.selectbox("Przewoźnik (Wybierz)", lista_przewoznikow)
        pojazd_kierowca = st.text_input("Pojazd i Kierowca (do rubryki 16)", "Nr rej: ABC 12345 / Jan Kowalski")
    with col3:
        odbiorca = st.text_area("Odbiorca Towaru (Rubryka 2)", "Firma Docelowa S.A.\nul. Odbiorcza 2\n50-001 Wrocław\nNIP: 0987654321", height=100)
        
    st.markdown("---")
    st.markdown("### Trasa i Ładunek")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        adres_zaladunku = st.selectbox("Miejsce Załadunku", lista_miejsc)
        data_zaladunku = st.date_input("Data załadunku")
    with col_t2:
        adres_rozladunku = st.selectbox("Miejsce Rozładunku", lista_miejsc)
        data_rozladunku = st.date_input("Data rozładunku")
        
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    rodzaj_towaru = col_p1.text_input("Rodzaj towaru", "Elektronika")
    ilosc_opakowan = col_p2.text_input("Ilość opakowań", "33")
    rodzaj_opakowania = col_p3.selectbox("Rodzaj opakowania", ["EUR-paleta", "Karton", "Sztuka"])
    waga = col_p4.text_input("Waga brutto (kg)", "24000")
    
    uwagi = st.text_area("Uwagi i Instrukcje dla kierowcy (Rubryka 13 CMR)")

    submit = st.form_submit_button("Generuj Pakiet PDF (Zlecenie + 3x CMR)")

if submit:
    qr_bytes, hash_qr = generate_security_qr(nr_zlecenia, wybrany_przewoznik, adres_zaladunku, adres_rozladunku)
    
    order_data = {
        "Data wystawienia": datetime.now().strftime("%Y-%m-%d"),
        "Numer zlecenia": nr_zlecenia, "Zleceniodawca": zleceniodawca, 
        "Zleceniobiorca": wybrany_przewoznik, "Pojazd_Kierowca": pojazd_kierowca,
        "Odbiorca": odbiorca, "Adres zaladunku": adres_zaladunku, 
        "Adres rozladunku": adres_rozladunku, "Data zaladunku": str(data_zaladunku), 
        "Data rozladunku": str(data_rozladunku), "Rodzaj towaru": rodzaj_towaru, 
        "Ilosc opakowan": ilosc_opakowan, "Rodzaj opakowania": rodzaj_opakowania, 
        "Waga brutto (kg)": waga, "Uwagi": uwagi
    }
    
    with st.spinner('Tworzenie siatki CMR i generowanie dokumentów...'):
        pdf_bytes = generate_pdf_package(order_data, qr_bytes)
    
    wiersz_historii = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nr_zlecenia, zleceniodawca, wybrany_przewoznik, 
        adres_zaladunku, adres_rozladunku, str(data_zaladunku), str(data_rozladunku),
        rodzaj_towaru, ilosc_opakowan, rodzaj_opakowania, waga, pojazd_kierowca, uwagi, hash_qr
    ]
    append_to_gsheets("Zlecenia", wiersz_historii)
    
    st.success("Zapisano w bazie! Pobierz swój 4-stronicowy dokument poniżej.")
    st.download_button("📄 Pobierz Pakiet (Zlecenie + 3x CMR)", pdf_bytes, f"Zlecenie_CMR_{nr_zlecenia.replace('/', '_')}.pdf", "application/pdf")
