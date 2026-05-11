import streamlit as st
from datetime import datetime
from fpdf import FPDF
import qrcode
import tempfile
import os
import hashlib
from core import fetch_data, append_data, get_next_daily_number
from pricing import get_all_carrier_rates, TRANSIT_DAYS

# --- NOWOCZESNY GENERATOR PDF PRO (NAPRAWIONY) ---
class PRO_TransportOrder(FPDF):
    def __init__(self, watermark_text="SQM"):
        super().__init__()
        self.watermark_text = watermark_text

    def add_watermark(self):
        """Poprawna implementacja rotacji znaku wodnego dla fpdf2."""
        self.set_font("Arial", 'B', 50)
        self.set_text_color(245, 245, 245)  # Bardzo jasny szary
        
        # Generowanie siatki znaków wodnych
        for i in range(0, 210, 60):  # Szerokość A4
            for j in range(0, 297, 60):  # Wysokość A4
                # Używamy surowych transformacji do rotacji tekstu
                with self.rotation(angle=45, x=i, y=j):
                    self.text(i, j, self.watermark_text)
        self.set_text_color(0, 0, 0) # Powrót do czarnego

    def header(self):
        # Logo SQM (z pliku logosqm.png lub logosqm.jpg)
        try:
            if os.path.exists("logosqm.png"):
                self.image("logosqm.png", 10, 8, 55)
            elif os.path.exists("logosqm.jpg"):
                self.image("logosqm.jpg", 10, 8, 55)
        except:
            pass
        
        self.set_font("Arial", 'B', 20)
        self.set_text_color(40, 40, 40)
        self.set_xy(100, 15)
        self.cell(100, 10, "TRANSPORT ORDER", ln=True, align='R')
        
        self.set_font("Arial", '', 9)
        self.set_text_color(100, 100, 100)
        self.set_xy(100, 25)
        self.cell(100, 5, "SQM Prosta Spolka Akcyjna | Logistics Department", ln=True, align='R')
        self.ln(15)

    def footer(self):
        self.set_y(-25)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, "Dokument wygenerowany systemowo przez Vortex Nexus 4.0 PRO. Wszystkie dane sa poufne.", ln=True, align='C')
        self.cell(0, 5, f"Strona {self.page_no()} / {{nb}}", align='C')

def generate_pro_pdf(dane):
    def sanitize(text):
        replacements = {'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z',
                        'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S', 'Ź':'Z', 'Ż':'Z'}
        for pl, eng in replacements.items():
            text = str(text).replace(pl, eng)
        return text

    pdf = PRO_TransportOrder()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Dodajemy znak wodny przed innymi elementami
    pdf.add_watermark()

    # --- KOD QR (ZABEZPIECZENIE) ---
    raw_token = f"{dane['nr']}-{dane['przewoznik']}-{dane['stawka']}"
    secure_hash = hashlib.md5(raw_token.encode()).hexdigest()[:10].upper()
    qr_data = f"VERIFY-SQM-ORDER: {dane['nr']} | TOKEN: {secure_hash}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        img_qr.save(tmp, format="PNG")
        qr_path = tmp.name

    pdf.image(qr_path, 175, 40, 25)
    if os.path.exists(qr_path):
        os.remove(qr_path)

    # --- UKŁAD DOKUMENTU ---
    pdf.set_xy(10, 45)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(80, 8, f" REFERENCE: {dane['nr']}", ln=False, fill=True)
    pdf.cell(10, 8, "", ln=False)
    pdf.cell(100, 8, f" ISSUE DATE: {datetime.now().strftime('%d.%m.%Y')}", ln=True, fill=True)
    pdf.ln(5)

    def draw_section(title, fields):
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(56, 189, 248) 
        pdf.cell(0, 10, sanitize(title), ln=True)
        pdf.set_text_color(0, 0, 0)
        
        for label, val in fields:
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(50, 7, sanitize(label), border='B')
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 7, sanitize(val), border='B', ln=True)
        pdf.ln(5)

    draw_section("PARTIES & VEHICLE", [
        ("CONTRACTOR:", dane['przewoznik']),
        ("VEHICLE / DRIVER:", dane['auto'] if dane['auto'] else "TBA"),
        ("VALUATION TYPE:", dane['typ_zlecenia'])
    ])

    log_fields = [
        ("LOADING PLACE:", dane['zaladunek']),
        ("LOADING DATE:", dane['data_zal']),
        ("UNLOADING PLACE:", dane['rozladunek']),
        ("UNLOADING DATE:", dane['data_roz'])
    ]
    if dane['typ_zlecenia'] == "Pełny event":
        log_fields.append(("EMPTIES IN:", dane['data_emp_in']))
        log_fields.append(("RETURN LOAD:", dane['data_emp_out']))
    
    draw_section("LOGISTICS SCHEDULE", log_fields)

    draw_section("CARGO DETAILS & FINANCIALS", [
        ("GOODS TYPE:", "Event Structures / Technical Equipment"),
        ("WEIGHT:", f"{dane['waga']} kg"),
        ("TOTAL NET COST:", f"{dane['stawka']} {dane['waluta']}"),
        ("OVERLAY RATE:", f"{dane['postoj']} {dane['waluta']} / day" if float(dane['postoj']) > 0 else "0.00")
    ])

    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(56, 189, 248)
    pdf.cell(0, 10, "SPECIAL INSTRUCTIONS", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'I', 9)
    pdf.multi_cell(0, 6, sanitize(dane['uwagi'] if dane['uwagi'] else "Standard security protocols apply. Please secure cargo with belts."))

    return bytes(pdf.output(dest='S').encode('latin1'))

# --- INTERFEJS STREAMLIT ---
st.set_page_config(page_title="Vortex PRO | Zlecenia", page_icon="🚀", layout="centered")
st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🚀 Szybkie Zlecenie PRO</h2>", unsafe_allow_html=True)

with st.spinner("Pobieranie bazy danych..."):
    df_projekty = fetch_data("Projekty")
    df_miejsca = fetch_data("Miejsca")
    
lista_eventow = df_projekty['Nazwa Eventu'].dropna().unique().tolist() if not df_projekty.empty else ["Brak"]
lista_miejsc_baza = df_miejsca['Nazwa do listy'].tolist() if not df_miejsca.empty else []
opcje_lokalizacji = ["Magazyn SQM Komorniki"] + lista_miejsc_baza + ["INNE (wpisz ręcznie)"]

st.markdown("<br>", unsafe_allow_html=True)
typ_zlecenia = st.radio("Model operacyjny:", ["Tylko dostawa", "Pełny event"], horizontal=True)

with st.container(border=True):
    st.markdown("#### 1. Kierunek i Waga")
    lista_miast = sorted(list(TRANSIT_DAYS.keys()))
    c1, c2 = st.columns([3, 1])
    miasto_docelowe = c1.selectbox("Wybierz miasto docelowe:", ["Wybierz..."] + lista_miast)
    waga = c2.number_input("Waga (kg):", min_value=100, step=100, value=1000)
    
    d1, d2 = st.columns(2)
    data_zal = d1.date_input("Data załadunku:", datetime.now())
    data_roz = d2.date_input("Data rozładunku:", datetime.now())
    
    if typ_zlecenia == "Pełny event":
        h1, h2 = st.columns(2)
        data_emp_in = h1.date_input("Odbiór pustych:")
        data_emp_out = h2.date_input("Powrót:")
    else:
        data_emp_in, data_emp_out = "", ""

slownik_stawek = get_all_carrier_rates(miasto_docelowe, waga, data_zal, data_roz, data_emp_out, typ_zlecenia)

with st.container(border=True):
    st.markdown("#### 2. Przewoźnik i Finanse")
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    
    lista_cennikowa = list(slownik_stawek.keys()) if slownik_stawek else ["Wybierz miasto..."]
    wybrany_przewoznik = f1.selectbox("Wybierz z cennika:", ["Wybierz..."] + lista_cennikowa)
    
    dane_wybranego = slownik_stawek.get(wybrany_przewoznik, {"cost": 0.0, "postoj": 0.0})
    stawka_domyslna = dane_wybranego.get("cost", 0.0)
    postoj_domyslny = dane_wybranego.get("postoj", 0.0)
    
    stawka_final = f2.number_input("Cena (auto):", min_value=0.0, step=50.0, value=float(stawka_domyslna))
    waluta = f3.selectbox("Waluta:", ["EUR", "PLN"])
    
    if typ_zlecenia == "Pełny event":
        postoj = f4.number_input("Postój/Dz:", min_value=0.0, step=50.0, value=float(postoj_domyslny))
    else:
        postoj = 0.0

with st.container(border=True):
    st.markdown("#### 3. Szczegóły transportu")
    wydarzenie = st.selectbox("Projekt:", lista_eventow)
    l1, l2 = st.columns(2)
    with l1:
        z_sel = st.selectbox("Załadunek:", opcje_lokalizacji)
        z_man = st.text_input("Adres (ręcznie):") if z_sel == "INNE (wpisz ręcznie)" else ""
    with l2:
        r_sel = st.selectbox("Rozładunek:", opcje_lokalizacji)
        r_man = st.text_input("Adres (ręcznie):") if r_sel == "INNE (wpisz ręcznie)" else ""

with st.container(border=True):
    st.markdown("#### 4. Kierowca i Uwagi")
    d_auto, d_wart = st.columns(2)
    c_auto = d_auto.text_input("Dane auta / kierowcy:", placeholder="np. PO 12345 / Jan Kowalski")
    wartosc_towaru = d_wart.number_input("Wartość towaru (PLN):", min_value=0, step=1000, value=50000)

    u1, u2 = st.columns([3, 1])
    instrukcje = u1.text_input("Uwagi specjalne:")
    podpis = u2.radio("Opiekun:", ["PD", "PK"], horizontal=True)

st.markdown("<br>", unsafe_allow_html=True)

if st.button("⚡ GENERUJ ZLECENIE PREMIUM PDF", type="primary", use_container_width=True):
    if wybrany_przewoznik == "Wybierz..." or wybrany_przewoznik == "Wybierz miasto...":
        st.error("Wybierz poprawnego przewoźnika!")
    else:
        with st.spinner("Generowanie dokumentu PRO..."):
            final_zal = z_man if z_sel == "INNE (wpisz ręcznie)" else z_sel
            final_roz = r_man if r_sel == "INNE (wpisz ręcznie)" else r_sel
            rok, d_kod = datetime.now().strftime('%y'), datetime.now().strftime('%m%d')
            idx = get_next_daily_number(datetime.now().strftime("%Y-%m-%d"))
            pref = str(wydarzenie)[:3].upper() if wydarzenie != "Brak" else "TRG"
            nr_zlecenia = f"{pref}{rok}/{d_kod}/{podpis}{idx:02d}"
            
            paczka_pdf = {
                "typ_zlecenia": typ_zlecenia, "nr": nr_zlecenia, "przewoznik": wybrany_przewoznik,
                "stawka": stawka_final, "waluta": waluta, "postoj": postoj,
                "zaladunek": final_zal, "data_zal": str(data_zal),
                "rozladunek": final_roz, "data_roz": str(data_roz),
                "data_emp_in": str(data_emp_in), "data_emp_out": str(data_emp_out),
                "waga": waga, "wartosc": wartosc_towaru, "auto": c_auto, "uwagi": instrukcje
            }
            
            historia = f"CYKL: {data_zal} -> {data_roz}" + (f" | EMP: {data_emp_in} | POWRÓT: {data_emp_out}" if typ_zlecenia == "Pełny event" else "")
            pelne_uwagi = f"AUTO: {c_auto} || WART: {wartosc_towaru}PLN || {historia} || {instrukcje}"
            
            wiersz_db = [
                datetime.now().strftime("%Y-%m-%d %H:%M"), nr_zlecenia, "LOGISTYKA CARGO", wybrany_przewoznik,
                final_zal, final_roz, str(data_zal), str(data_roz), "Elementy Zabudowy",
                "", "", "", "", pelne_uwagi, "", wydarzenie, "TARGI", f"{stawka_final} {waluta}"
            ]
            
            if append_data("Zlecenia", wiersz_db):
                pdf_bytes = generate_pro_pdf(paczka_pdf)
                st.success(f"✅ Zlecenie PRO {nr_zlecenia} zapisane!")
                st.download_button("📥 POBIERZ ZLECENIE PRO PDF", data=pdf_bytes, file_name=f"Order_{nr_zlecenia.replace('/', '_')}.pdf", mime="application/pdf", use_container_width=True)
