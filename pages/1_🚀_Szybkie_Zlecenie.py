import streamlit as st
from datetime import datetime
from fpdf import FPDF
import qrcode
import tempfile
import os
import hashlib
from core import fetch_data, append_data, get_next_daily_number
from pricing import get_all_carrier_rates, TRANSIT_DAYS

# --- NOWOCZESNY GENERATOR PDF PRO (BEZPIECZNY DLA FPDF) ---
class PRO_TransportOrder(FPDF):
    def __init__(self, watermark_text="SQM"):
        super().__init__()
        self.watermark_text = watermark_text

    def add_watermark(self):
        self.set_font("Arial", 'B', 45)
        self.set_text_color(240, 240, 240) 
        for j in range(80, 297, 45):
            przesuniecie = 35 if (j // 45) % 2 == 0 else 0
            for i in range(-20, 210, 70):
                self.text(i + przesuniecie, j, self.watermark_text)
        self.set_text_color(0, 0, 0)

    def header(self):
        try:
            if os.path.exists("logosqm.png"):
                self.image("logosqm.png", 10, 8, 55)
            elif os.path.exists("logosqm.jpg"):
                self.image("logosqm.jpg", 10, 8, 55)
        except:
            pass
        
        self.set_font("Arial", 'B', 20)
        self.set_text_color(40, 40, 40)
        self.set_xy(80, 15)
        self.cell(90, 10, "TRANSPORT ORDER", ln=True, align='R')
        
        self.set_font("Arial", '', 9)
        self.set_text_color(100, 100, 100)
        self.set_xy(80, 25)
        self.cell(90, 5, "SQM Prosta Spolka Akcyjna | Logistics Department", ln=True, align='R')
        self.ln(15)

    def footer(self):
        self.set_y(-25)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, "Dokument wygenerowany systemowo przez Vortex Nexus 4.0 PRO. Dane poufne.", ln=True, align='C')
        self.cell(0, 5, f"Strona {self.page_no()} / {{nb}}", align='C')

def generate_pro_pdf(dane):
    def sanitize(text):
        text = str(text)
        replacements = {
            'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z',
            'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S', 'Ź':'Z', 'Ż':'Z',
            '€':'EUR', '–':'-', '—':'-', '”':'"', '„':'"', '’':"'", '“':'"', '\xa0':' '
        }
        for pl, eng in replacements.items():
            text = text.replace(pl, eng)
        # Twarde usunięcie znaków spoza latin-1 (np. chińskie znaczki, emoji, itp.)
        return text.encode('latin-1', 'ignore').decode('latin-1')

    pdf = PRO_TransportOrder()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.add_watermark()

    token_base = f"{dane['nr']}-{dane['przewoznik']}-{dane['stawka']}"
    secure_hash = hashlib.md5(token_base.encode()).hexdigest()[:12].upper()
    qr_content = f"SQM-VERIFY: {dane['nr']}\nVALID-HASH: {secure_hash}\nSYSTEM: VORTEX 4.0"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(qr_content)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        img_qr.save(tmp, format="PNG")
        qr_path = tmp.name

    pdf.image(qr_path, 175, 10, 25)
    if os.path.exists(qr_path):
        os.remove(qr_path)

    pdf.set_xy(10, 45)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(245, 245, 245)
    # Zastosowano sanitize do numeru i daty
    pdf.cell(85, 9, sanitize(f" REFERENCE: {dane['nr']}"), ln=False, fill=True)
    pdf.cell(5, 9, "", ln=False)
    pdf.cell(100, 9, sanitize(f" ISSUE DATE: {datetime.now().strftime('%d.%m.%Y')}"), ln=True, fill=True)
    pdf.ln(4)

    def draw_pro_section(title, fields):
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(56, 189, 248) 
        pdf.cell(0, 10, sanitize(title), ln=True)
        pdf.set_text_color(0, 0, 0)
        
        for label, val in fields:
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(55, 6, sanitize(label), border=0)
            
            pdf.set_font("Arial", '', 10)
            pdf.set_xy(x_start + 55, y_start + 0.5)
            pdf.multi_cell(135, 5, sanitize(val), border=0)
            
            y_end = pdf.get_y() + 1.5
            pdf.line(10, y_end, 200, y_end)
            pdf.set_xy(10, y_end + 1.5)
        pdf.ln(4)

    draw_pro_section("PARTIES & ASSETS", [
        ("CONTRACTOR / PRZEWOZNIK:", dane['przewoznik']),
        ("VEHICLE & DRIVER / AUTO:", dane['auto'] if dane['auto'] else "TBA"),
        ("VALUATION MODEL / TRYB:", dane['typ_zlecenia'])
    ])

    log_fields = [
        ("LOADING / ZALADUNEK:", dane['zaladunek']),
        ("DATE / DATA ZAL.:", dane['data_zal']),
        ("UNLOADING / ROZLADUNEK:", dane['rozladunek']),
        ("DATE / DATA ROZ.:", dane['data_roz'])
    ]
    if dane['typ_zlecenia'] == "Pełny event":
        log_fields.append(("EMPTIES IN / ODBIOR PUSTYCH:", dane['data_emp_in']))
        log_fields.append(("RETURN LOAD / POWROT:", dane['data_emp_out']))
    
    draw_pro_section("LOGISTICS TIMELINE", log_fields)

    draw_pro_section("FINANCIALS & CARGO", [
        ("CARGO TYPE:", "Exhibition Structures / AV Equipment"),
        ("GROSS WEIGHT:", f"{dane['waga']} kg"),
        ("TOTAL NET RATE:", f"{dane['stawka']} {dane['waluta']}"),
        ("OVERLAY PER DAY:", f"{dane['postoj']} {dane['waluta']}" if float(dane['postoj']) > 0 else "0.00"),
        ("PAYMENT TERMS / PLATNOSC:", "45 days after invoice receipt / 45 dni po otrzymaniu faktury")
    ])

    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(56, 189, 248)
    pdf.cell(0, 10, "SPECIAL PROVISIONS", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'I', 9)
    instructions = dane['uwagi'] if dane['uwagi'] else "Cargo must be secured with professional belts. Driver must follow exhibition center protocols."
    pdf.multi_cell(0, 6, sanitize(instructions))

    return bytes(pdf.output(dest='S').encode('latin1'))

# --- INTERFEJS UŻYTKOWNIKA ---
st.set_page_config(page_title="Vortex PRO", page_icon="🚀", layout="centered")
st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🚀 Szybkie Zlecenie PRO</h2>", unsafe_allow_html=True)

with st.spinner("Ładowanie telemetrii..."):
    df_projekty = fetch_data("Projekty")
    df_miejsca = fetch_data("Miejsca")
    
lista_eventow = df_projekty['Nazwa Eventu'].dropna().unique().tolist() if not df_projekty.empty else ["Brak"]
lista_miejsc_baza = df_miejsca['Nazwa do listy'].tolist() if not df_miejsca.empty else []
opcje_lokalizacji = ["Magazyn SQM Komorniki"] + lista_miejsc_baza + ["INNE (wpisz ręcznie)"]

typ_zlecenia = st.radio("Tryb operacji:", ["Tylko dostawa", "Pełny event"], horizontal=True)

with st.container(border=True):
    st.markdown("#### 1. Kierunek i Harmonogram")
    lista_miast = sorted(list(TRANSIT_DAYS.keys()))
    c1, c2 = st.columns([3, 1])
    miasto_docelowe = c1.selectbox("Miasto docelowe:", ["Wybierz..."] + lista_miast)
    waga = c2.number_input("Waga (kg):", min_value=100, step=100, value=1000)
    
    d1, d2 = st.columns(2)
    data_zal = d1.date_input("Data załadunku (PL):", datetime.now())
    data_roz = d2.date_input("Data rozładunku (Targi):", datetime.now())
    
    if typ_zlecenia == "Pełny event":
        h1, h2 = st.columns(2)
        data_emp_in = h1.date_input("Odbiór pustych:")
        data_emp_out = h2.date_input("Powrót / Załadunek:")
    else:
        data_emp_in, data_emp_out = "", ""

slownik_stawek = get_all_carrier_rates(miasto_docelowe, waga, data_zal, data_roz, data_emp_out, typ_zlecenia)

with st.container(border=True):
    st.markdown("#### 2. Wybór Przewoźnika i Koszty")
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    
    lista_cennikowa = list(slownik_stawek.keys()) if slownik_stawek else ["Wybierz miasto..."]
    wybrany_przewoznik = f1.selectbox("Dostępni partnerzy:", ["Wybierz..."] + lista_cennikowa)
    
    dane_wybranego = slownik_stawek.get(wybrany_przewoznik, {"cost": 0.0, "postoj": 0.0})
    stawka_final = f2.number_input("Cena Total:", value=float(dane_wybranego.get("cost", 0.0)))
    waluta = f3.selectbox("Waluta:", ["EUR", "PLN"])
    
    if typ_zlecenia == "Pełny event":
        postoj = f4.number_input("Postój/Dzień:", value=float(dane_wybranego.get("postoj", 0.0)))
    else:
        postoj = 0.0

with st.container(border=True):
    st.markdown("#### 3. Logistyka Miejsc")
    projekt = st.selectbox("Przypisz do Projektu:", lista_eventow)
    l1, l2 = st.columns(2)
    with l1:
        z_sel = st.selectbox("Miejsce startu:", opcje_lokalizacji)
        z_man = st.text_input("Adres (ręcznie):") if z_sel == "INNE (wpisz ręcznie)" else ""
    with l2:
        r_sel = st.selectbox("Miejsce celu:", opcje_lokalizacji)
        r_man = st.text_input("Adres (ręcznie):") if r_sel == "INNE (wpisz ręcznie)" else ""

with st.container(border=True):
    st.markdown("#### 4. Realizacja i Uwagi")
    d_auto, d_wart = st.columns(2)
    c_auto = d_auto.text_input("Auto / Kierowca:", placeholder="np. PO 12345 / Jan Kowalski")
    wartosc_towaru = d_wart.number_input("Wartość towaru (PLN):", min_value=0, step=1000, value=100000)
    
    u1, u2 = st.columns([3, 1])
    domyslny_tekst = "Parking strzeżony, pasy zabezpieczajace; załadować po długości, casy nie mogą leżeć, kłódka / Guarded parking, safety belts; load lengthwise, the cases cannot lie down, safe lock"
    instrukcje = u1.text_area("Uwagi dla kierowcy (Special Provisions):", value=domyslny_tekst, height=70)
    podpis = u2.radio("Podpis:", ["PD", "PK"], horizontal=True)

st.markdown("<br>", unsafe_allow_html=True)

if st.button("⚡ GENERUJ I ZAPISZ ZLECENIE PRO", type="primary", use_container_width=True):
    if wybrany_przewoznik in ["Wybierz...", "Wybierz miasto..."]:
        st.error("Wybierz przewoźnika z listy!")
    else:
        with st.spinner("Zabezpieczanie i generowanie dokumentu..."):
            final_zal_db = z_man if z_sel == "INNE (wpisz ręcznie)" else z_sel
            final_roz_db = r_man if r_sel == "INNE (wpisz ręcznie)" else r_sel
            
            def build_full_address(place_name, manual_addr, df):
                if place_name == "INNE (wpisz ręcznie)":
                    return manual_addr
                if df is None or df.empty:
                    return place_name
                    
                row = df[df['Nazwa do listy'] == place_name]
                if not row.empty:
                    r = row.iloc[0]
                    firma = str(r.get('Nazwa pełna / Firma', '')).strip()
                    ulica = str(r.get('Ulica i numer', '')).strip()
                    kod = str(r.get('Kod pocztowy', '')).strip()
                    miasto = str(r.get('Miasto', '')).strip()
                    kraj = str(r.get('Kraj', '')).strip()
                    kontakt = str(r.get('Osoba / Tel', '')).strip()
                    
                    lines = []
                    if firma and firma != 'nan' and firma.lower() != 'none': 
                        lines.append(firma)
                    elif place_name and place_name != 'nan':
                        lines.append(place_name)
                        
                    adres_parts = []
                    if ulica and ulica != 'nan' and ulica.lower() != 'none': adres_parts.append(ulica)
                    miasto_part = f"{kod if kod != 'nan' and kod.lower() != 'none' else ''} {miasto if miasto != 'nan' and miasto.lower() != 'none' else ''}".strip()
                    if miasto_part: adres_parts.append(miasto_part)
                    if kraj and kraj != 'nan' and kraj.lower() != 'none': adres_parts.append(kraj)
                    
                    adres = ", ".join(adres_parts)
                    if adres: lines.append(adres)
                    
                    if kontakt and kontakt != 'nan' and kontakt.lower() != 'none':
                        lines.append(f"Kontakt: {kontakt}")
                        
                    return "\n".join(lines)
                return place_name

            full_zal_pdf = build_full_address(z_sel, z_man, df_miejsca)
            full_roz_pdf = build_full_address(r_sel, r_man, df_miejsca)
            
            rok, d_kod = datetime.now().strftime('%y'), datetime.now().strftime('%m%d')
            idx = get_next_daily_number(datetime.now().strftime("%Y-%m-%d"))
            pref = str(projekt)[:3].upper() if projekt != "Brak" else "TRG"
            nr_zlecenia = f"{pref}{rok}/{d_kod}/{podpis}{idx:02d}"
            
            paczka_pdf = {
                "typ_zlecenia": typ_zlecenia, "nr": nr_zlecenia, "przewoznik": wybrany_przewoznik,
                "stawka": stawka_final, "waluta": waluta, "postoj": postoj,
                "zaladunek": full_zal_pdf, "data_zal": str(data_zal),
                "rozladunek": full_roz_pdf, "data_roz": str(data_roz),
                "data_emp_in": str(data_emp_in), "data_emp_out": str(data_emp_out),
                "waga": waga, "auto": c_auto, "uwagi": instrukcje
            }
            
            historia = f"CYKL: {data_zal} -> {data_roz}" + (f" | EMP: {data_emp_in} | POWRÓT: {data_emp_out}" if typ_zlecenia == "Pełny event" else "")
            pelne_uwagi = f"AUTO: {c_auto} || WART: {wartosc_towaru}PLN || {historia} || {instrukcje}"
            
            wiersz_db = [
                datetime.now().strftime("%Y-%m-%d %H:%M"), nr_zlecenia, "LOGISTYKA CARGO", wybrany_przewoznik,
                final_zal_db, final_roz_db, str(data_zal), str(data_roz), "Zabudowa Targowa PRO",
                "", "", "", "", pelne_uwagi, "", projekt, "TARGI", f"{stawka_final} {waluta}"
            ]
            
            if append_data("Zlecenia", wiersz_db):
                pdf_bytes = generate_pro_pdf(paczka_pdf)
                st.success(f"✅ Zlecenie {nr_zlecenia} zapisane w bazie chmurowej!")
                st.download_button("📥 POBIERZ ZLECENIE PREMIUM PDF", data=pdf_bytes, file_name=f"Order_{nr_zlecenia.replace('/', '_')}.pdf", mime="application/pdf", use_container_width=True)
