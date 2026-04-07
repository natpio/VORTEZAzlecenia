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
Zeskanowano w oficjalnym systemie."""

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img_byte_arr = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue(), secure_hash

# --- RYSOWANIE SIATKI CMR (PERFEKCYJNE ODWZOROWANIE Z NAPISAMI POBOCZNYMI) ---
def draw_cmr_page(pdf, data, qr_bytes, copy_number, copy_title):
    pdf.add_page()
    
    # Funkcja pomocnicza do rysowania standardowych rubryk z podwójnym tekstem
    def draw_box(x, y, w, h, num, pl_text, en_text, content="", thick_border=False):
        if thick_border:
            pdf.set_line_width(0.6) # Tłusta linia dla przewoźnika
        else:
            pdf.set_line_width(0.2) # Zwykła linia
            
        pdf.rect(x, y, w, h)
        
        pdf.set_line_width(0.2) # Powrót do zwykłej grubości na wypadek rysowania czegokolwiek innego
        
        if num:
            pdf.set_font("Roboto", "B", 7)
            pdf.set_xy(x+1, y+1)
            pdf.cell(4, 3, txt=str(num))
            tx = x + 5
        else:
            tx = x + 1
            
        pdf.set_font("Roboto", "", 5)
        pdf.set_xy(tx, y+1)
        pdf.cell(w-(tx-x), 3, txt=pl_text)
        if en_text:
            pdf.set_xy(tx, y+4)
            pdf.cell(w-(tx-x), 3, txt=en_text)
            
        if content:
            pdf.set_font("Roboto", "B", 8)
            pdf.set_xy(x+2, y+8)
            pdf.multi_cell(w-4, 4, txt=content)
    
    # --- PIONOWE NAPISY POBOCZNE ---
    # Lewy margines (Tekst obrócony o 90 stopni, idący z dołu do góry)
    with pdf.rotation(90, 7, 180):
        pdf.set_font("Roboto", "B", 6)
        pdf.text(7, 180, "Do wypełnienia pod odpowiedzialnością nadawcy 1-15 włącznie oraz")
        pdf.set_font("Roboto", "", 5)
        pdf.text(7, 183, "To be completed on sender's responsability including and")
        pdf.set_font("Roboto", "B", 6)
        pdf.text(7, 188, "19+21+22 Rubryki obwiedzione tłustymi liniami wypełnia przewoźnik.")
        pdf.set_font("Roboto", "", 5)
        pdf.text(7, 191, "The spaces framed with heavy lines must filied in by the carrier.")

    # Prawy margines (Tekst obrócony o 270 / -90 stopni, idący z góry do dołu)
    with pdf.rotation(270, 204, 30):
        pdf.set_font("Roboto", "B", 5)
        pdf.text(204, 30, "*W przypadku przewozu towarów niebezpiecznych, oprócz ewentualnego posiadania zaświadczenia, należy podać w ostatnim wierszu: klasę, liczbę oraz w danym przypadku literę.")
        pdf.set_font("Roboto", "", 5)
        pdf.text(204, 33, "*In case of dangerous goods mention, besides the possible certification, on the last line of the column the particulars of the class, the UN number and the packing group.")

    # --- NAGŁÓWEK ---
    pdf.set_font("Roboto", "B", 14)
    pdf.set_xy(10, 8)
    pdf.cell(5, 5, txt=str(copy_number))
    pdf.set_font("Roboto", "", 8)
    pdf.set_xy(15, 8)
    pdf.cell(85, 4, txt=copy_title.split(',')[0].strip())
    pdf.set_xy(15, 12)
    if len(copy_title.split(',')) > 1:
        pdf.cell(85, 4, txt=copy_title.split(',')[1].strip())
    
    # Prawa strona nagłówka
    pdf.set_font("Roboto", "B", 9)
    pdf.set_xy(105, 8)
    pdf.cell(95, 4, txt="MIĘDZYNARODOWY SAMOCHODOWY LIST PRZEWOZOWY")
    pdf.set_font("Roboto", "", 7)
    pdf.set_xy(105, 12)
    pdf.cell(95, 4, txt="INTERNATIONAL CONSIGNMENT NOTE")
    
    # Znaczek CMR i Numer
    pdf.set_font("Roboto", "B", 12)
    pdf.set_xy(140, 20)
    pdf.cell(15, 6, txt="CMR", border=1, align='C')
    pdf.set_font("Roboto", "B", 14)
    pdf.set_xy(160, 20)
    pdf.cell(35, 6, txt=f"No. {data['Numer zlecenia'].replace('ZLEC/', '')}")
    
    # Tekst Konwencji
    pdf.set_font("Roboto", "", 5)
    pdf.set_xy(105, 27)
    pdf.multi_cell(95, 2.5, txt="Niniejszy przewóz podlega postanowieniom konwencji o umowie międzynarodowej przewozu drogowego towarów (CMR) bez względu na jakąkolwiek przeciwną klauzulę. / This carriage is subject, notwithstanding any clause to the contrary, to the Convention on the Contract for the international Carriage of goods by road (CMR).")

    # --- LEWA KOLUMNA ---
    draw_box(10, 15, 95, 25, "1", "Nadawca (nazwisko lub nazwa, adres, kraj)", "Sender (name, address, country)", data['Zleceniodawca'])
    draw_box(10, 40, 95, 25, "2", "Odbiorca (nazwisko lub nazwa, adres, kraj)", "Consignee (name, address, country)", data['Odbiorca'])
    draw_box(10, 65, 95, 15, "3", "Miejsce przeznaczenia (miejscowość, kraj)", "Place of delivery of the goods (place, country)", data['Adres rozladunku'])
    draw_box(10, 80, 95, 15, "4", "Miejsce i data załadowania (miejscowość, kraj, data)", "Place and date of taking over the goods", f"{data['Adres zaladunku']}\nData: {data['Data zaladunku']}")
    draw_box(10, 95, 95, 20, "5", "Załączone dokumenty", "Documents attached")

    # Wklejenie kodu QR do Rubryki 5 (Załączone dokumenty)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(qr_bytes)
        tmp.flush()
        tmp_name = tmp.name
    pdf.image(tmp_name, x=75, y=98, w=15)
    os.remove(tmp_name)
    pdf.set_font("Roboto", "B", 6)
    pdf.set_xy(12, 105)
    pdf.cell(60, 4, txt="[x] Elektroniczny Certyfikat Zlecenia (Skanuj QR ->)")

    # --- PRAWA KOLUMNA (TŁUSTE RAMKI DLA PRZEWOŹNIKA) ---
    draw_box(105, 40, 95, 35, "16", "Przewoźnik (nazwisko lub nazwa, adres, kraj)", "Carrier (name, address, country)", f"{data['Zleceniobiorca']}\n{data['Pojazd_Kierowca']}", thick_border=True)
    draw_box(105, 75, 95, 15, "17", "Kolejni przewoźnicy (nazwisko lub nazwa, adres, kraj)", "Successive carriers", thick_border=True)
    draw_box(105, 90, 95, 25, "18", "Zastrzeżenia i uwagi przewoźnika", "Carrier's reservations and observations", thick_border=True)

    # --- TABELA TOWARÓW (Rubryki 6-12) ---
    y_t = 115
    pdf.set_line_width(0.2)
    pdf.rect(10, y_t, 190, 60)
    # Pionowe linie tabeli
    pdf.line(30, y_t, 30, y_t+60)
    pdf.line(45, y_t, 45, y_t+60)
    pdf.line(65, y_t, 65, y_t+60)
    pdf.line(130, y_t, 130, y_t+60)
    pdf.line(150, y_t, 150, y_t+60)
    pdf.line(175, y_t, 175, y_t+60)
    
    # Nagłówki kolumn towarów
    pdf.set_font("Roboto", "B", 6)
    pdf.set_xy(10, y_t)
    pdf.multi_cell(20, 3, txt="6 Cechy i numery\nMarks and Nos", align='C')
    pdf.set_xy(30, y_t)
    pdf.multi_cell(15, 3, txt="7 Ilość sztuk\nNumber of pkgs", align='C')
    pdf.set_xy(45, y_t)
    pdf.multi_cell(20, 3, txt="8 Opakowanie\nMethod of packing", align='C')
    pdf.set_xy(65, y_t)
    pdf.multi_cell(65, 3, txt="9 Rodzaj towaru\nNature of the goods", align='C')
    pdf.set_xy(130, y_t)
    pdf.multi_cell(20, 3, txt="10 Nr statystyczny\nStatistical number", align='C')
    pdf.set_xy(150, y_t)
    pdf.multi_cell(25, 3, txt="11 Waga brutto w kg\nGross weight in kg", align='C')
    pdf.set_xy(175, y_t)
    pdf.multi_cell(25, 3, txt="12 Objętość w m3\nVolume in m3", align='C')

    # Dane Towarowe
    pdf.set_font("Roboto", "B", 10)
    pdf.set_xy(30, y_t+20)
    pdf.cell(15, 5, txt=data['Ilosc opakowan'], align='C')
    pdf.set_xy(45, y_t+20)
    pdf.cell(20, 5, txt=data['Rodzaj opakowania'], align='C')
    pdf.set_xy(65, y_t+20)
    pdf.cell(65, 5, txt=data['Rodzaj towaru'], align='C')
    pdf.set_xy(150, y_t+20)
    pdf.cell(25, 5, txt=data['Waga brutto (kg)'], align='C')
    
    # ADR linia (dół tabeli)
    pdf.line(10, y_t+50, 130, y_t+50)
    pdf.set_font("Roboto", "", 6)
    pdf.set_xy(11, y_t+51)
    pdf.cell(20, 3, txt="Klasa / Class")
    pdf.set_xy(46, y_t+51)
    pdf.cell(20, 3, txt="Nr UN / Number")
    pdf.set_xy(90, y_t+51)
    pdf.cell(20, 3, txt="PG (ADR)")

    # --- DOLNA SEKCJA ---
    draw_box(10, 175, 95, 35, "13", "Instrukcje nadawcy", "Sender's instructions", data['Uwagi'])
    draw_box(10, 210, 95, 10, "14", "Postanowienia odnośnie przewoźnego", "Instruction as to payment carriage")
    
    miasto = data['Adres zaladunku'].split(',')[-1].strip() if ',' in data['Adres zaladunku'] else data['Adres zaladunku']
    draw_box(10, 220, 95, 15, "21", "Wystawiono w", "Established in", f"{miasto} , dnia: {data['Data wystawienia']}")

    # Tłusta ramka dla 19
    draw_box(105, 175, 95, 15, "19", "Postanowienia specjalne", "Special agreements", thick_border=True)
    
    # Rysowanie tabeli 20 (Do zapłacenia) - Tłusta ramka
    pdf.set_line_width(0.6)
    pdf.rect(105, 190, 95, 30)
    pdf.set_line_width(0.2) # powrót do normalnej dla linii wewnetrznych
    
    pdf.set_font("Roboto", "B", 7)
    pdf.set_xy(106, 191)
    pdf.cell(4, 3, txt="20")
    pdf.set_font("Roboto", "", 5)
    pdf.set_xy(110, 191)
    pdf.cell(20, 3, txt="Do zapłacenia\nTo be paid by")
    
    # Linie tabeli 20
    pdf.line(135, 190, 135, 220)
    pdf.line(155, 190, 155, 220)
    pdf.line(170, 190, 170, 220)
    y_row = 195
    for i in range(6):
        pdf.line(105, y_row, 200, y_row)
        y_row += 4.1
        
    pdf.set_xy(135, 191)
    pdf.cell(20, 3, txt="Nadawca / Sender", align='C')
    pdf.set_xy(155, 191)
    pdf.cell(15, 3, txt="Waluta", align='C')
    pdf.set_xy(170, 191)
    pdf.cell(30, 3, txt="Odbiorca / Consignee", align='C')
    
    labels = ["Przewoźne", "Bonifikaty", "Saldo", "Dopłaty", "Koszty dodatkowe", "Razem"]
    y_row = 196
    for lbl in labels:
        pdf.set_xy(106, y_row)
        pdf.cell(25, 3, txt=lbl)
        y_row += 4.1

    draw_box(105, 220, 95, 15, "15", "Zapłata / Cash on delivery", "")

    # --- PODPISY (DÓŁ) ---
    draw_box(10, 235, 63, 30, "22", "Podpis i stempel nadawcy", "Signature and stamp of the sender", thick_border=True) # Zgodnie z pionowym tekstem 22 jest w tłustej
    draw_box(73, 235, 63, 30, "23", "Podpis i stempel przewoźnika", "Signature and stamp of the carrier", thick_border=True)
    
    pdf.set_line_width(0.6)
    pdf.rect(136, 235, 64, 30)
    pdf.set_line_width(0.2)
    pdf.set_font("Roboto", "B", 7)
    pdf.set_xy(137, 236)
    pdf.cell(4, 3, txt="24")
    pdf.set_font("Roboto", "", 5)
    pdf.set_xy(141, 236)
    pdf.cell(50, 3, txt="Przesyłkę otrzymano / Goods received")
    pdf.set_xy(141, 240)
    pdf.cell(50, 3, txt="Miejscowość / Place ............................... dnia / on .............")
    pdf.set_xy(141, 260)
    pdf.cell(50, 3, txt="Podpis i stempel odbiorcy / Signature and stamp of the consignee")

    # Stopka oficjalna IRU
    pdf.set_font("Roboto", "B", 5)
    pdf.set_xy(10, 266)
    pdf.cell(190, 3, txt="Wzór CMR/IRU/Polska z 1976 dla międzynarodowych przewozów drogowych odpowiada ustaleniom, które zostały dokonane przez Międzynarodową Unię Transportu Drogowego/IRU/.")


# --- GŁÓWNA FUNKCJA BUDUJĄCA CAŁY PLIK PDF ---
def generate_pdf_package(data, qr_bytes):
    pdf = FPDF()
    # Pobieranie czcionek z obsługą PL znaków
    font_reg = "Roboto-Regular.ttf"
    font_bold = "Roboto-Bold.ttf"
    if not os.path.exists(font_reg):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf", font_reg)
    if not os.path.exists(font_bold):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf", font_bold)
        
    pdf.add_font("Roboto", "", font_reg)
    pdf.add_font("Roboto", "B", font_bold)
    
    # === STRONA 1: ZLECENIE TRANSPORTOWE ===
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

    # === STRONY 2, 3, 4: OFICJALNE DRUKI CMR ===
    draw_cmr_page(pdf, data, qr_bytes, 1, "Egzemplarz dla nadawcy, Copy for sender, Exemplar für den Absender")
    draw_cmr_page(pdf, data, qr_bytes, 2, "Egzemplarz dla odbiorcy, Copy for consignee, Exemplar für den Empfänger")
    draw_cmr_page(pdf, data, qr_bytes, 3, "Egzemplarz dla przewoźnika, Copy for carrier, Copy für den Frachtführer")

    return bytes(pdf.output()) 

# --- INTERFEJS APLIKACJI STREAMLIT ---
st.set_page_config(layout="wide", page_title="System Zleceń i CMR")
st.title("Oficjalne Zlecenia i Dokumenty CMR")

if st.button("🔄 Odśwież bazy z Google Sheets"):
    st.cache_data.clear()

lista_przewoznikow, df_przewoznicy, lista_miejsc, df_miejsca = load_data()

with st.form("form"):
    st.markdown("### Strony Dokumentów")
    col1, col2, col3 = st.columns(3)
    with col1:
        nr_zlecenia = st.text_input("Numer zlecenia", f"ZLEC/{datetime.now().strftime('%Y/%m')}/")
        zleceniodawca = st.text_area("Nadawca (Rubryka 1 CMR)", "Moja Firma Sp. z o.o.\nul. Testowa 1\n00-001 Warszawa\nNIP: 1234567890", height=100)
    with col2:
        wybrany_przewoznik = st.selectbox("Przewoźnik (Wybierz z bazy)", lista_przewoznikow)
        pojazd_kierowca = st.text_input("Pojazd i Kierowca (Rubryka 16 CMR)", "Nr rej: ABC 12345 / Jan Kowalski")
    with col3:
        odbiorca = st.text_area("Odbiorca Towaru (Rubryka 2 CMR)", "Firma Docelowa S.A.\nul. Odbiorcza 2\n50-001 Wrocław\nNIP: 0987654321", height=100)
        
    st.markdown("---")
    st.markdown("### Trasa i Ładunek")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        adres_zaladunku = st.selectbox("Miejsce Załadunku (Rubryka 4)", lista_miejsc)
        data_zaladunku = st.date_input("Data załadunku")
    with col_t2:
        adres_rozladunku = st.selectbox("Miejsce Rozładunku (Rubryka 3)", lista_miejsc)
        data_rozladunku = st.date_input("Data rozładunku")
        
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    rodzaj_towaru = col_p1.text_input("Rodzaj towaru (Rubryka 9)", "Elektronika")
    ilosc_opakowan = col_p2.text_input("Ilość opakowań (Rubryka 7)", "33")
    rodzaj_opakowania = col_p3.selectbox("Rodzaj opakowania (Rubryka 8)", ["EUR-paleta", "Karton", "Sztuka", "IBC"])
    waga = col_p4.text_input("Waga brutto w kg (Rubryka 11)", "24000")
    
    uwagi = st.text_area("Uwagi i Instrukcje dla kierowcy (Rubryka 13 CMR)")

    submit = st.form_submit_button("Generuj Pakiet PDF (Zlecenie + 3x Oficjalne CMR)")

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
    
    with st.spinner('Rysowanie matematycznej siatki CMR i generowanie dokumentów...'):
        pdf_bytes = generate_pdf_package(order_data, qr_bytes)
    
    wiersz_historii = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nr_zlecenia, zleceniodawca, wybrany_przewoznik, 
        adres_zaladunku, adres_rozladunku, str(data_zaladunku), str(data_rozladunku),
        rodzaj_towaru, ilosc_opakowan, rodzaj_opakowania, waga, pojazd_kierowca, uwagi, hash_qr
    ]
    append_to_gsheets("Zlecenia", wiersz_historii)
    
    st.success("Zapisano w bazie! Pobierz swój profesjonalny 4-stronicowy dokument poniżej.")
    st.download_button("📄 Pobierz Pakiet Oficjalny (Zlecenie + 3x CMR)", pdf_bytes, f"Pakiet_CMR_{nr_zlecenia.replace('/', '_')}.pdf", "application/pdf")
