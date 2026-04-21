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

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Terminal CMR | Cargo")

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
    st.page_link("pages/2_📄_Terminal_CMR.py", label="Terminal CMR")
    st.page_link("pages/3_🚚_Baza_Przewoznikow.py", label="Baza Przewoźników Cargo")
    st.page_link("pages/4_📊_Historia_Zlecen_Cargo.py", label="Historia Zleceń Cargo")

# --- KONFIGURACJA BAZY DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=30)
def load_cargo_orders():
    try:
        client = get_gsheets_client()
        sh = client.open_by_url(SHEET_URL)
        df = pd.DataFrame(sh.worksheet("Zlecenia").get_all_records())
        # Filtrujemy tylko zlecenia typu TARGI
        if not df.empty and 'Typ transportu' in df.columns:
            return df[df['Typ transportu'] == "TARGI"]
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Błąd ładowania bazy: {e}")
        return pd.DataFrame()

# --- LOGIKA GENEROWANIA KODU QR ---
def generate_security_qr(order_num, carrier, loading, unloading):
    SECRET_SALT = "CMR2026!VortexCargo" 
    # Bezpieczne formatowanie stringów, zapobiega błędom jeśli wartość to NaN/None
    raw_data = f"{order_num}|{carrier}|{loading}|{unloading}|{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()
    qr_payload = f"--- VORTEX CARGO SECURITY ---\nRef: {order_num}\nPrzewoznik: {str(carrier)[:25]}\nTrasa: {loading} -> {unloading}\nSHA: {secure_hash}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img_byte_arr = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

# --- FUNKCJE RYSOWANIA CMR (FPDF) ---
def draw_cmr_page(pdf, data, qr_bytes, copy_number, copy_title):
    pdf.add_page()
    
    def draw_box(x, y, w, h, num, pl_text, en_text, content="", thick_border=False):
        pdf.set_line_width(0.6 if thick_border else 0.2)
        pdf.rect(x, y, w, h)
        pdf.set_line_width(0.2)
        if num:
            pdf.set_font("Roboto", "B", 7)
            pdf.set_xy(x+1, y+1); pdf.cell(4, 3, txt=str(num))
        pdf.set_font("Roboto", "", 5)
        pdf.set_xy(x+5 if num else x+1, y+1); pdf.cell(w-5, 3, txt=pl_text)
        pdf.set_xy(x+5 if num else x+1, y+4); pdf.cell(w-5, 3, txt=en_text)
        if content:
            pdf.set_font("Roboto", "B", 8)
            pdf.set_xy(x+2, y+8); pdf.multi_cell(w-4, 4, txt=str(content))

    # Nagłówek CMR
    pdf.set_font("Roboto", "B", 14); pdf.set_xy(10, 8); pdf.cell(5, 5, txt=str(copy_number))
    pdf.set_font("Roboto", "", 8); pdf.set_xy(15, 8); pdf.cell(85, 4, txt=copy_title)
    pdf.set_font("Roboto", "B", 12); pdf.set_xy(140, 10); pdf.cell(15, 6, txt="CMR", border=1, align='C')
    pdf.set_font("Roboto", "B", 12); pdf.set_xy(160, 10); pdf.cell(40, 6, txt=f"No. {data['Numer zlecenia']}")

    # Pola 1-5
    draw_box(10, 15, 95, 25, "1", "Nadawca", "Sender", data['Zleceniodawca'])
    draw_box(10, 40, 95, 25, "2", "Odbiorca", "Consignee", data['Odbiorca'])
    draw_box(10, 65, 95, 15, "3", "Miejsce przeznaczenia", "Place of delivery", data['Adres rozladunku'])
    draw_box(10, 80, 95, 15, "4", "Miejsce i data zaladowania", "Place and date of taking over", f"{data['Adres zaladunku']}\n{data['Data zaladunku']}")
    draw_box(10, 95, 95, 20, "5", "Zalaczone dokumenty", "Documents attached")

    # QR Code Security
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(qr_bytes); tmp.flush(); tmp_name = tmp.name
    pdf.image(tmp_name, x=75, y=98, w=15)
    os.remove(tmp_name)

    # Przewoźnik 16-18
    draw_box(105, 40, 95, 35, "16", "Przewoznik", "Carrier", f"{data['Zleceniobiorca']}\n{data.get('Pojazd_Kierowca', '')}", thick_border=True)
    draw_box(105, 75, 95, 15, "17", "Kolejni przewoznicy", "Successive carriers", thick_border=True)
    draw_box(105, 90, 95, 25, "18", "Zastrzezenia przewoznika", "Carrier's reservations", thick_border=True)

    # Tabela towarowa (Pola 6-12)
    y_t = 115; pdf.rect(10, y_t, 190, 60)
    pdf.line(65, y_t, 65, y_t+60); pdf.set_font("Roboto", "B", 9)
    pdf.set_xy(67, y_t+5); pdf.cell(60, 5, txt=f"TOWAR: {data['Rodzaj towaru']}")
    pdf.set_xy(67, y_t+12); pdf.cell(60, 5, txt=f"ILOSC: {data['Ilosc opakowan']} {data['Rodzaj opakowania']}")
    pdf.set_xy(150, y_t+5); pdf.cell(30, 5, txt=f"WAGA: {data['Waga brutto']} kg")

    # Podpisy 22-24
    draw_box(10, 235, 63, 30, "22", "Podpis nadawcy", "Sender signature", thick_border=True)
    draw_box(73, 235, 63, 30, "23", "Podpis przewoznika", "Carrier signature", thick_border=True)
    draw_box(136, 235, 64, 30, "24", "Podpis odbiorcy", "Consignee signature", thick_border=True)

def generate_full_cmr(data, qr_bytes):
    pdf = FPDF()
    font_reg = "Roboto-Regular.ttf"
    font_bold = "Roboto-Bold.ttf"
    if not os.path.exists(font_reg):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf", font_reg)
    if not os.path.exists(font_bold):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf", font_bold)
    
    pdf.add_font("Roboto", "", font_reg, uni=True)
    pdf.add_font("Roboto", "B", font_bold, uni=True)
    
    copies = [
        (1, "1. Egzemplarz dla nadawcy / Copy for sender"),
        (2, "2. Egzemplarz dla odbiorcy / Copy for consignee"),
        (3, "3. Egzemplarz dla przewoznika / Copy for carrier")
    ]
    for num, title in copies:
        draw_cmr_page(pdf, data, qr_bytes, num, title)
    return bytes(pdf.output())

# --- INTERFEJS TERMINALA ---
st.title("📄 Terminal CMR - LOGISTYKA CARGO")
st.markdown("Wybierz zlecenie z bazy TARGI, aby wygenerować komplet 3 kopii dokumentu CMR.")

df_orders = load_cargo_orders()

if not df_orders.empty:
    with st.container(border=True):
        col_sel, col_info = st.columns([1, 2])
        
        # Filtrujemy tylko te zlecenia, które mają nadany 'Numer zlecenia'
        lista_numerow = [str(nr) for nr in df_orders['Numer zlecenia'].tolist() if pd.notna(nr)][::-1]
        
        if lista_numerow:
            wybrany_nr = col_sel.selectbox("Wybierz Numer Zlecenia:", lista_numerow)
            
            row = df_orders[df_orders['Numer zlecenia'].astype(str) == wybrany_nr].iloc[0]
            
            # Bezpieczne wyświetlanie informacji
            miejsce_zal = row.get('Miejsce Zaladunku', 'Brak')
            miejsce_roz = row.get('Miejsce Rozladunku', 'Brak')
            zleceniobiorca = row.get('Zleceniobiorca', 'Brak')
            towar = row.get('Rodzaj towaru', 'Brak')
            
            col_info.info(f"📍 Trasa: **{miejsce_zal}** ➡️ **{miejsce_roz}**")
            col_info.write(f"🚛 Przewoźnik: {zleceniobiorca} | 📦 Towar: {towar}")

            if st.button("🌐 GENERUJ I POBIERZ PAKIET CMR", type="primary", use_container_width=True):
                with st.spinner("Przetwarzanie dokumentu i generowanie skrótów SHA-256..."):
                    qr_bytes = generate_security_qr(row.get('Numer zlecenia', ''), zleceniobiorca, miejsce_zal, miejsce_roz)
                    
                    # -----------------------------------------------------
                    # KULOODPORNE MAPOWANIE DANYCH (ZABEZPIECZENIE PRZED KEYERROR)
                    # -----------------------------------------------------
                    uwagi = str(row.get('Uwagi / Instrukcje', ''))
                    kierowca_auto = uwagi.split("||")[1].strip() if "||" in uwagi else ""
                    
                    pdf_data = {
                        "Numer zlecenia": str(row.get('Numer zlecenia', '')),
                        "Zleceniodawca": "VORTEX NEXUS LOGISTICS\nul. Magazynowa 10, 62-052 Komorniki",
                        "Odbiorca": f"TARGI / EVENT: {str(row.get('ID Projektu', ''))}\nLokalizacja: {miejsce_roz}",
                        "Adres zaladunku": miejsce_zal,
                        "Adres rozladunku": miejsce_roz,
                        "Data zaladunku": str(row.get('Data Zaladunku', '')),
                        "Zleceniobiorca": zleceniobiorca,
                        "Pojazd_Kierowca": kierowca_auto,
                        "Rodzaj towaru": towar if towar else "Sprzęt Eventowy",
                        "Ilosc opakowan": str(row.get('Ilosc opakowan', '')),
                        "Rodzaj opakowania": str(row.get('Rodzaj opakowania', '')),
                        "Waga brutto": str(row.get('Waga brutto', '')),
                        "Uwagi": uwagi
                    }
                    
                    pdf_out = generate_full_cmr(pdf_data, qr_bytes)
                    
                    st.success("Pakiet CMR gotowy!")
                    
                    bezpieczna_nazwa = str(row.get('Numer zlecenia', 'dokument')).replace('/', '_')
                    st.download_button(
                        label="📥 POBIERZ PDF (3 STRONY CMR)",
                        data=pdf_out,
                        file_name=f"CMR_{bezpieczna_nazwa}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.warning("Brak zleceń z poprawnym numerem w bazie.")
else:
    st.info("Brak zarejestrowanych zleceń typu TARGI w bazie.")
