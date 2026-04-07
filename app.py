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

# --- ZAAWANSOWANY KOD QR ---
def generate_security_qr(order_num, carrier, loading, unloading):
    SECRET_SALT = "CMR2026!SekretneZabezpieczenie" 
    raw_data = f"{order_num}|{carrier}|{loading}|{unloading}|{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()
    
    # Rozbudowana treść dla skanera (np. telefonu kierowcy/magazyniera)
    qr_payload = f"""--- WERYFIKACJA DOKUMENTU ---
Typ: ZLECENIE TRANSPORTOWE / CMR
Nr: {order_num}
Zleceniobiorca: {carrier}
Zaladunek: {loading}
Rozladunek: {unloading}
-----------------------------
Autentycznosc (SHA256):
{secure_hash}
Skanuj w systemie firmowym."""

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img_byte_arr = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue(), secure_hash

# --- GENEROWANIE PROFESJONALNEGO PDF (2 STRONY) ---
def generate_pdf(data, qr_bytes):
    pdf = FPDF()
    
    # 1. Pobieranie dwóch wariantów czcionki (Zwykła i Pogrubiona)
    font_reg = "Roboto-Regular.ttf"
    font_bold = "Roboto-Bold.ttf"
    if not os.path.exists(font_reg):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf", font_reg)
    if not os.path.exists(font_bold):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf", font_bold)
        
    pdf.add_font("Roboto", "", font_reg)
    pdf.add_font("Roboto", "B", font_bold)
    
    # ==========================================
    # STRONA 1: ZLECENIE TRANSPORTOWE
    # ==========================================
    pdf.add_page()
    
    # Nagłówek Zlecenia
    pdf.set_font("Roboto", "B", 16)
    pdf.cell(0, 10, txt=f"ZLECENIE TRANSPORTOWE NR: {data['Numer zlecenia']}", ln=True, align='C')
    pdf.set_font("Roboto", "", 10)
    pdf.cell(0, 5, txt=f"Data wystawienia: {data['Data wystawienia']}", ln=True, align='C')
    pdf.ln(10)
    
    # Ramki: Zleceniodawca i Zleceniobiorca
    pdf.set_font("Roboto", "B", 10)
    pdf.set_xy(10, 35)
    pdf.cell(90, 8, txt="ZLECENIODAWCA:", border=1, ln=0, align='C')
    pdf.set_xy(110, 35)
    pdf.cell(90, 8, txt="ZLECENIOBIORCA (PRZEWOŹNIK):", border=1, ln=1, align='C')
    
    pdf.set_font("Roboto", "", 10)
    pdf.set_xy(10, 43)
    pdf.multi_cell(90, 20, txt=data['Zleceniodawca'], border=1, align='C')
    pdf.set_xy(110, 43)
    pdf.multi_cell(90, 20, txt=data['Zleceniobiorca'], border=1, align='C')
    
    pdf.ln(10)
    
    # Tabela: Szczegóły Trasy
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(0, 10, txt="SZCZEGÓŁY TRASY", ln=True)
    pdf.set_font("Roboto", "B", 10)
    pdf.cell(95, 8, txt="MIEJSCE ZAŁADUNKU:", border=1)
    pdf.cell(95, 8, txt="MIEJSCE ROZŁADUNKU:", border=1, ln=True)
    
    pdf.set_font("Roboto", "", 10)
    # Rysowanie komórek z adresami
    x = pdf.get_x()
    y = pdf.get_y()
    pdf.multi_cell(95, 8, txt=f"Adres: {data['Adres zaladunku']}\nData: {data['Data zaladunku']}", border=1)
    pdf.set_xy(x + 95, y)
    pdf.multi_cell(95, 8, txt=f"Firma: {data['Odbiorca']}\nAdres: {data['Adres rozladunku']}\nData: {data['Data rozladunku']}", border=1)
    
    pdf.ln(5)
    
    # Tabela: Szczegóły Towaru
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(0, 10, txt="PARAMETRY TOWARU I ZLECENIA", ln=True)
    pdf.set_font("Roboto", "", 10)
    pdf.cell(60, 8, txt=f"Towar: {data['Rodzaj towaru']}", border=1)
    pdf.cell(60, 8, txt=f"Ilość: {data['Ilosc opakowan']} {data['Rodzaj opakowania']}", border=1)
    pdf.cell(70, 8, txt=f"Waga brutto: {data['Waga brutto (kg)']} kg", border=1, ln=True)
    pdf.multi_cell(0, 8, txt=f"Uwagi / Instrukcje specjalne: {data['Uwagi']}", border=1)
    
    # Podpisy i Pieczątki
    pdf.ln(20)
    pdf.cell(95, 10, txt="...........................................................", align='C')
    pdf.cell(95, 10, txt="...........................................................", ln=True, align='C')
    pdf.set_font("Roboto", "", 8)
    pdf.cell(95, 5, txt="Pieczątka i podpis Zleceniodawcy", align='C')
    pdf.cell(95, 5, txt="Pieczątka i podpis Zleceniobiorcy", ln=True, align='C')
    
    # Warunki zlecenia (Drobnym drukiem na dole)
    pdf.set_y(-40)
    pdf.set_font("Roboto", "", 6)
    warunki = "WARUNKI ZLECENIA: 1. Przewoźnik zobowiązuje się do wykonania transportu zgodnie z konwencją CMR i Prawem Przewozowym. 2. Pojazd musi być technicznie sprawny, czysty i wolny od zapachów. 3. Kierowca ma obowiązek uczestniczyć przy załadunku i rozładunku towaru, sprawdzić ilość i stan opakowań. 4. Zakaz przeładunków i doładunków bez pisemnej zgody Zleceniodawcy. 5. Zapłata za fracht nastąpi w terminie ustalonym na fakturze, pod warunkiem dostarczenia kompletu oryginalnych i czystych dokumentów (Faktura, CMR)."
    pdf.multi_cell(0, 3, txt=warunki, align='J')

    # ==========================================
    # STRONA 2: OFICJALNY DOKUMENT CMR
    # ==========================================
    pdf.add_page()
    pdf.set_font("Roboto", "B", 14)
    pdf.cell(0, 10, txt="MIĘDZYNARODOWY SAMOCHODOWY LIST PRZEWOZOWY / CMR", ln=True, align='C')
    
    # Rysowanie klasycznej siatki CMR (Współrzędne X, Y, Szerokość, Wysokość)
    pdf.set_font("Roboto", "B", 8)
    
    # Lewa Kolumna
    pdf.rect(10, 20, 95, 30)
    pdf.set_xy(10, 20)
    pdf.multi_cell(95, 5, txt=f"1. Nadawca (Sender)\n\n{data['Zleceniodawca']}")
    
    pdf.rect(10, 50, 95, 30)
    pdf.set_xy(10, 50)
    pdf.multi_cell(95, 5, txt=f"2. Odbiorca (Consignee)\n\n{data['Odbiorca']}\n{data['Adres rozladunku']}")
    
    pdf.rect(10, 80, 95, 20)
    pdf.set_xy(10, 80)
    pdf.multi_cell(95, 5, txt=f"3. Miejsce przeznaczenia (Place of delivery)\n{data['Adres rozladunku']}")
    
    pdf.rect(10, 100, 95, 20)
    pdf.set_xy(10, 100)
    pdf.multi_cell(95, 5, txt=f"4. Miejsce załadowania (Place of taking over)\n{data['Adres zaladunku']}\nData: {data['Data zaladunku']}")
    
    # Prawa Kolumna
    pdf.rect(105, 20, 95, 40)
    pdf.set_xy(105, 20)
    pdf.multi_cell(95, 5, txt=f"16. Przewoźnik (Carrier)\n\n{data['Zleceniobiorca']}")
    
    pdf.rect(105, 60, 95, 60)
    pdf.set_xy(105, 60)
    pdf.multi_cell(95, 5, txt="18. Zastrzeżenia i uwagi przewoźnika\n\n\n\n13. Instrukcje nadawcy\n" + data['Uwagi'])
    
    # Tabela Środkowa (Towar)
    pdf.rect(10, 120, 190, 40)
    pdf.line(40, 120, 40, 160) # Linie pionowe oddzielające kolumny w CMR
    pdf.line(70, 120, 70, 160)
    pdf.line(140, 120, 140, 160)
    
    pdf.set_xy(10, 120)
    pdf.cell(30, 5, txt="Znak i numery", align='C')
    pdf.cell(30, 5, txt="Ilość sztuk", align='C')
    pdf.cell(70, 5, txt="Rodzaj opakowania i towaru", align='C')
    pdf.cell(50, 5, txt="Waga brutto (kg)", align='C')
    
    # Wypełnienie towaru
    pdf.set_font("Roboto", "", 9)
    pdf.set_xy(40, 130)
    pdf.cell(30, 5, txt=data['Ilosc opakowan'], align='C')
    pdf.set_xy(70, 130)
    pdf.cell(70, 5, txt=f"{data['Rodzaj opakowania']} / {data['Rodzaj towaru']}", align='C')
    pdf.set_xy(140, 130)
    pdf.cell(50, 5, txt=data['Waga brutto (kg)'], align='C')
    
    # Dolna sekcja (Podpisy)
    pdf.set_font("Roboto", "B", 7)
    pdf.rect(10, 170, 60, 30)
    pdf.set_xy(10, 170)
    pdf.multi_cell(60, 4, txt="22. Podpis i pieczęć nadawcy\n(Signature and stamp of the sender)")
    
    pdf.rect(75, 170, 60, 30)
    pdf.set_xy(75, 170)
    pdf.multi_cell(60, 4, txt="23. Podpis i pieczęć przewoźnika\n(Signature and stamp of the carrier)")
    
    pdf.rect(140, 170, 60, 30)
    pdf.set_xy(140, 170)
    pdf.multi_cell(60, 4, txt="24. Podpis i pieczęć odbiorcy\n(Signature and stamp of the consignee)")

    # Wklejenie bezpiecznego kodu QR w lewym dolnym rogu strony CMR
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(qr_bytes)
        tmp.flush()
        tmp_name = tmp.name
        
    pdf.image(tmp_name, x=10, y=210, w=35)
    os.remove(tmp_name)
    
    pdf.set_font("Roboto", "", 8)
    pdf.set_xy(48, 215)
    pdf.multi_cell(100, 4, txt="<-- ZESKANUJ KOD QR\nSystem weryfikacji autentyczności dokumentu.\nHash: " + qr_bytes.hex()[:10] + "...")
        
    return bytes(pdf.output()) 

# --- INTERFEJS UŻYTKOWNIKA ---
st.set_page_config(layout="wide", page_title="Zlecenia Transportowe")
st.title("Wystawianie Zleceń i CMR")

if st.button("🔄 Odśwież bazy z Google Sheets"):
    st.cache_data.clear()

lista_przewoznikow, df_przewoznicy, lista_miejsc, df_miejsca = load_data()

with st.form("form"):
    st.markdown("### Dane Stron")
    col1, col2, col3 = st.columns(3)
    with col1:
        nr_zlecenia = st.text_input("Numer zlecenia", f"ZLEC/{datetime.now().strftime('%Y/%m')}/")
        zleceniodawca = st.text_area("Zleceniodawca (Firma, Adres, NIP)", "Moja Firma Sp. z o.o.\nul. Testowa 1\n00-001 Warszawa\nNIP: 1234567890", height=100)
    with col2:
        wybrany_przewoznik = st.selectbox("Zleceniobiorca / Przewoźnik (z bazy)", lista_przewoznikow)
        st.info("Pamiętaj: Pełne dane przewoźnika pobierane są z arkusza dla wybranej opcji.")
    with col3:
        odbiorca = st.text_area("Odbiorca Towaru (Nazwa firmy docelowej - do CMR)", "Odbiorca Docelowy S.A.", height=100)
        
    st.markdown("---")
    st.markdown("### Trasa i Towar")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        adres_zaladunku = st.selectbox("Miejsce Załadunku", lista_miejsc)
        data_zaladunku = st.date_input("Data załadunku")
    with col_t2:
        adres_rozladunku = st.selectbox("Miejsce Rozładunku", lista_miejsc)
        data_rozladunku = st.date_input("Data rozładunku")
        
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    rodzaj_towaru = col_p1.text_input("Rodzaj towaru", "Części zamienne")
    ilosc_opakowan = col_p2.text_input("Ilość opakowań", "33")
    rodzaj_opakowania = col_p3.selectbox("Rodzaj opakowania", ["EUR-paleta", "Karton", "Sztuka", "IBC"])
    waga = col_p4.text_input("Waga brutto (kg)", "24000")
    
    uwagi = st.text_area("Uwagi / Instrukcje specjalne na dokumentach")

    submit = st.form_submit_button("Generuj Profesjonalne Zlecenie i CMR (PDF)")

if submit:
    qr_bytes, hash_qr = generate_security_qr(nr_zlecenia, wybrany_przewoznik, adres_zaladunku, adres_rozladunku)
    
    # Przygotowanie pełnej paczki danych
    order_data = {
        "Data wystawienia": datetime.now().strftime("%Y-%m-%d"),
        "Numer zlecenia": nr_zlecenia, 
        "Zleceniodawca": zleceniodawca, 
        "Zleceniobiorca": wybrany_przewoznik,
        "Odbiorca": odbiorca,
        "Adres zaladunku": adres_zaladunku, 
        "Adres rozladunku": adres_rozladunku, 
        "Data zaladunku": str(data_zaladunku), 
        "Data rozladunku": str(data_rozladunku),
        "Rodzaj towaru": rodzaj_towaru, 
        "Ilosc opakowan": ilosc_opakowan, 
        "Rodzaj opakowania": rodzaj_opakowania, 
        "Waga brutto (kg)": waga,
        "Uwagi": uwagi
    }
    
    # Generowanie PDF
    with st.spinner('Trwa generowanie profesjonalnych dokumentów...'):
        pdf_bytes = generate_pdf(order_data, qr_bytes)
    
    # Zapis do Google Sheets
    wiersz_historii = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nr_zlecenia, zleceniodawca, wybrany_przewoznik, 
        adres_zaladunku, adres_rozladunku, str(data_zaladunku), str(data_rozladunku),
        rodzaj_towaru, ilosc_opakowan, rodzaj_opakowania, waga, "", uwagi, hash_qr
    ]
    append_to_gsheets("Zlecenia", wiersz_historii)
    
    st.success("Sukces! Zlecenie zostało zarchiwizowane w Google Sheets.")
    st.download_button("📄 Pobierz Pakiet (Zlecenie + CMR)", pdf_bytes, f"Zlecenie_CMR_{nr_zlecenia.replace('/', '_')}.pdf", "application/pdf")
