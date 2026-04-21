import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import qrcode
import hashlib
import io
import tempfile
from fpdf import FPDF
import urllib.request
import os

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Kreator Zaopatrzenia | Zaopatrzenie")

# --- UKRYCIE DOMYŚLNEGO MENU ---
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none !important;}</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='color: #10b981;'>📦 ZAOPATRZENIE</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/5_📦_Kreator_Zaopatrzenia.py", label="Kreator Zaopatrzenia")
    st.page_link("pages/6_💰_Finanse_Projektu.py", label="Finanse Projektów (Koszty)")
    st.page_link("pages/7_🏢_Baza_Kontrahentow.py", label="Baza Kontrahentów / Miejsc")

# --- BAZA DANYCH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_data(ttl=15)
def load_procurement_data():
    client = get_gsheets_client()
    sh = client.open_by_url(SHEET_URL)
    return pd.DataFrame(sh.worksheet("Zlecenia").get_all_records()), pd.DataFrame(sh.worksheet("Miejsca").get_all_records())

df_z, df_m = load_procurement_data()

# --- GENERATOR PDF: ZLECENIE TRANSPORTOWE ---
def generate_transport_order_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # Pobieranie czcionek (aby działały polskie znaki)
    font_reg = "Roboto-Regular.ttf"
    font_bold = "Roboto-Bold.ttf"
    if not os.path.exists(font_reg):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf", font_reg)
    if not os.path.exists(font_bold):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf", font_bold)
    
    pdf.add_font("Roboto", "", font_reg, uni=True)
    pdf.add_font("Roboto", "B", font_bold, uni=True)
    
    # Generowanie kodu QR
    qr_data = f"ZLECENIE:{data['nr']} | STAWKA:{data['stawka']} | PRZEWOZNIK:{data['przewoznik']}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(qr_img, format='PNG')
    
    # Rysowanie PDF
    pdf.set_font("Roboto", "B", 16)
    pdf.cell(0, 10, f"ZLECENIE TRANSPORTOWE NR: {data['nr']}", ln=True, align='C')
    pdf.set_font("Roboto", "", 10)
    pdf.cell(0, 5, f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
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
    # POPRAWKA: Usunięto parametr max_line_height=6, który wywalał błąd na Streamlit
    pdf.multi_cell(95, 6, "VORTEX NEXUS LOGISTICS\nul. Magazynowa 10, 62-052 Komorniki\nKontakt: Logistyka Zaopatrzenia", border=1, align='L')
    
    # Wracamy na górę dla drugiej kolumny (Trick we FPDF)
    y_before = pdf.get_y() - 18
    pdf.set_xy(105, y_before)
    pdf.multi_cell(95, 18, f"{data['przewoznik']}\nAuto/Kierowca: {data['auto']}", border=1, align='L')
    pdf.ln(5)

    # Box 2: Trasa
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(0, 8, "SZCZEGÓŁY TRANSPORTU", border=1, ln=True, fill=False)
    pdf.set_font("Roboto", "", 10)
    
    pdf.cell(40, 8, "MIEJSCE ZAŁADUNKU:", border=1)
    pdf.cell(150, 8, data['zaladunek'], border=1, ln=True)
    
    pdf.cell(40, 8, "MIEJSCE ROZŁADUNKU:", border=1)
    pdf.cell(150, 8, data['rozladunek'], border=1, ln=True)
    
    pdf.cell(40, 8, "DATA ZAŁADUNKU:", border=1)
    pdf.cell(150, 8, data['data_zal'], border=1, ln=True)
    
    pdf.cell(40, 8, "TOWAR / UWAGI:", border=1)
    pdf.multi_cell(150, 8, data['opis'], border=1)
    pdf.ln(5)

    # Box 3: Finanse
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(0, 8, "WARUNKI FINANSOWE", border=1, ln=True)
    pdf.set_font("Roboto", "", 12)
    pdf.cell(40, 10, "USTALONA STAWKA:", border=1)
    pdf.set_font("Roboto", "B", 12)
    pdf.cell(150, 10, f"{data['stawka']} PLN netto", border=1, ln=True)

    pdf.ln(20)
    pdf.set_font("Roboto", "", 10)
    pdf.cell(95, 5, ".......................................................", ln=False, align='C')
    pdf.cell(95, 5, ".......................................................", ln=True, align='C')
    pdf.cell(95, 5, "Podpis Zleceniodawcy", ln=False, align='C')
    pdf.cell(95, 5, "Podpis Przewoznika", ln=True, align='C')

    return pdf.output(dest='S').encode('latin-1')


# --- INTERFEJS ---
st.title("📦 System Zarządzania Zaopatrzeniem")

tab1, tab2, tab3 = st.tabs(["➕ Nowe Zgłoszenie", "💰 Kolejka Wycen (Zatwierdzanie)", "📄 Generuj Zlecenie PDF (Dla Zatwierdzonych)"])

with tab1:
    st.subheader("Zgłoś zapotrzebowanie (Dla Zaopatrzeniowca)")
    with st.form("form_req"):
        id_p = st.text_input("ID Projektu (5 cyfr)")
        kontrahent = st.selectbox("Miejsce", df_m['Nazwa do listy'].tolist() if not df_m.empty else [])
        d_gotowosci = st.date_input("Data gotowości")
        kierunek = st.radio("Kierunek:", ["Inbound", "Zwrot"])
        opis = st.text_area("Co jedzie?")
        if st.form_submit_button("Wyślij do logistyka"):
            nr_ref = f"REQ/{id_p}/{datetime.now().strftime('%d%H%M')}"
            m_zal = kontrahent if "Inbound" in kierunek else "MAGAZYN"
            m_roz = "MAGAZYN" if "Inbound" in kierunek else kontrahent
            nowy = [datetime.now().strftime("%Y-%m-%d %H:%M"), nr_ref, "ZAOPATRZENIE", "", m_zal, m_roz, str(d_gotowosci), "", "Sprzęt Wypożyczony", "", "", "", "", opis, "", id_p, "ZAOP_DO_WYCENY", 0]
            get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia").append_row(nowy)
            st.success("Wysłano!")
            st.cache_data.clear()

with tab2:
    st.subheader("Oczekujące na wycenę (Dla Logistyka)")
    if not df_z.empty:
        do_wyceny = df_z[df_z['Typ transportu'] == "ZAOP_DO_WYCENY"]
        for idx, row in do_wyceny.iterrows():
            with st.expander(f"Zgłoszenie: {row['Numer zlecenia']} | Trasa: {row['Miejsce Zaladunku']} ➡️ {row['Miejsce Rozladunku']}"):
                with st.form(f"wycena_{row['Numer zlecenia']}"):
                    stawka = st.number_input("Stawka PLN", min_value=0.0)
                    przewoznik = st.text_input("Przewoźnik")
                    auto = st.text_input("Auto/Kierowca")
                    typ = st.radio("Zatwierdź jako:", ["Inbound (Zatwierdzony)", "Zwrot (Zatwierdzony)"])
                    if st.form_submit_button("Zatwierdź"):
                        ws = get_gsheets_client().open_by_url(SHEET_URL).worksheet("Zlecenia")
                        cell = ws.find(row['Numer zlecenia'])
                        ws.update_cell(cell.row, 4, przewoznik)
                        ws.update_cell(cell.row, 14, f"{row['Uwagi / Instrukcje']} || {auto}")
                        ws.update_cell(cell.row, 17, typ)
                        ws.update_cell(cell.row, 18, stawka)
                        st.success("Zatwierdzono! Przejdź do zakładki nr 3, aby pobrać PDF.")
                        st.cache_data.clear()
                        st.rerun()

with tab3:
    st.subheader("Pobierz Zlecenie Transportowe (PDF)")
    st.info("Poniżej znajdują się zlecenia, które wyceniłeś i zatwierdziłeś. Wybierz jedno, aby wygenerować dokument dla przewoźnika.")
    
    if not df_z.empty:
        # Filtrujemy tylko zatwierdzone zlecenia zaopatrzenia
        zatwierdzone = df_z[df_z['Typ transportu'].isin(["Inbound (Zatwierdzony)", "Zwrot (Zatwierdzony)"])]
        
        if not zatwierdzone.empty:
            wybrane_nr = st.selectbox("Wybierz Zlecenie do wygenerowania PDF:", zatwierdzone['Numer zlecenia'].tolist()[::-1])
            row = zatwierdzone[zatwierdzone['Numer zlecenia'] == wybrane_nr].iloc[0]
            
            st.write(f"**Przewoźnik:** {row.get('Zleceniobiorca', 'Brak')} | **Stawka:** {row.get('Stawka', '0')} PLN")
            
            if st.button("📄 GENERUJ ZLECENIE PDF", type="primary"):
                with st.spinner("Generowanie pliku..."):
                    dane_pdf = {
                        "nr": str(row.get('Numer zlecenia', '')),
                        "przewoznik": str(row.get('Zleceniobiorca', '')),
                        "zaladunek": str(row.get('Miejsce Zaladunku', '')),
                        "rozladunek": str(row.get('Miejsce Rozladunku', '')),
                        "data_zal": str(row.get('Data Zaladunku', '')),
                        "opis": str(row.get('Uwagi / Instrukcje', '')).split("||")[0],
                        "auto": str(row.get('Uwagi / Instrukcje', '')).split("||")[1] if "||" in str(row.get('Uwagi / Instrukcje', '')) else "",
                        "stawka": str(row.get('Stawka', '0'))
                    }
                    
                    pdf_file = generate_transport_order_pdf(dane_pdf)
                    
                    st.download_button(
                        label="📥 POBIERZ GOTOWE ZLECENIE",
                        data=pdf_file,
                        file_name=f"Zlecenie_Transportowe_{wybrane_nr.replace('/', '_')}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.warning("Brak zatwierdzonych zleceń. Najpierw wyceń zgłoszenie w zakładce nr 2.")
