import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
import os
import hashlib

# Importujemy silnik Vortex
from core import fetch_data

# --- GLOBALNY FILTR ZNAKÓW DLA FPDF ---
def pdf_sanitize(text):
    text = str(text)
    replacements = {
        'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z',
        'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S', 'Ź':'Z', 'Ż':'Z',
        '€':'EUR', '–':'-', '—':'-', '”':'"', '„':'"', '’':"'", '“':'"', '\xa0':' '
    }
    for pl, eng in replacements.items():
        text = text.replace(pl, eng)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- KLASA GENERATORA CMR PRO ---
class CMR_Pro_Generator(FPDF):
    def __init__(self, copy_num=1, copy_label=""):
        super().__init__()
        self.copy_num = copy_num
        self.copy_label = copy_label
        self.primary_color = (25, 118, 210)

    def header(self):
        # Logo
        try:
            if os.path.exists("logosqm.png"):
                self.image("logosqm.png", 10, 8, 45)
        except:
            pass
        
        # Tytuł dokumentu
        self.set_font("Arial", 'B', 16)
        self.set_text_color(40, 40, 40)
        self.set_xy(60, 10)
        self.cell(140, 8, pdf_sanitize("INTERNATIONAL CONSIGNMENT NOTE (CMR)"), ln=True, align='R')
        self.set_font("Arial", 'B', 11)
        self.set_text_color(100, 100, 100)
        self.set_xy(60, 18)
        self.cell(140, 5, pdf_sanitize("MIEDZYNARODOWY LIST PRZEWOZOWY"), ln=True, align='R')
        
        # Etykieta kopii (np. 1 - Egzemplarz dla nadawcy)
        self.set_xy(10, 30)
        self.set_fill_color(*self.primary_color)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", 'B', 10)
        label_text = f" COPY {self.copy_num} - {self.copy_label} "
        self.cell(self.get_string_width(label_text)+4, 7, pdf_sanitize(label_text), fill=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, pdf_sanitize(f"Strona {self.page_no()} | Wygenerowano przez Vorteza Orders dla SQM"), align='C')

def draw_cmr_box(pdf, title_en, title_pl, content, height=25, width=95):
    x = pdf.get_x()
    y = pdf.get_y()
    
    # Ramka
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(x, y, width, height)
    
    # Naglowek rubryki
    pdf.set_font("Arial", 'B', 7)
    pdf.set_text_color(100, 100, 100)
    pdf.set_xy(x + 2, y + 2)
    pdf.cell(width-4, 3, pdf_sanitize(title_en), ln=True)
    pdf.set_xy(x + 2, y + 5)
    pdf.cell(width-4, 3, pdf_sanitize(title_pl), ln=True)
    
    # Zawartość
    pdf.set_font("Arial", '', 9)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(x + 2, y + 10)
    pdf.multi_cell(width-4, 4, pdf_sanitize(content), border=0)
    
    # Powrót do pozycji pod ramką (jeśli nie chcemy obok)
    pdf.set_xy(x, y + height)

# --- LOGIKA TERMINALA ---
st.markdown("<h2 style='color: #38bdf8;'>📄 TERMINAL CMR PRO</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Generowanie 4-stronicowych dokumentów CMR zgodnie ze standardem międzynarodowym.</p>", unsafe_allow_html=True)

with st.spinner("Synchronizacja ze zleceniami..."):
    df = fetch_data("Zlecenia")

if not df.empty:
    lista_nr = df[df['Dział'] == 'LOGISTYKA CARGO']['Numer zlecenia'].astype(str).tolist()
    wybor = st.selectbox("Wybierz Numer Zlecenia do wystawienia CMR:", ["Wybierz..."] + lista_nr)

    if wybor != "Wybierz...":
        r = df[df['Numer zlecenia'].astype(str) == wybor].iloc[0]
        
        with st.container(border=True):
            st.markdown(f"#### Dane do CMR dla: {wybor}")
            col1, col2 = st.columns(2)
            kierowca = col1.text_input("Kierowca / Nr Rejestracyjny:", value=str(r.get('Uwagi / Instrukcje', '')).split('AUTO: ')[-1].split(' ||')[0] if 'AUTO: ' in str(r.get('Uwagi / Instrukcje', '')) else "")
            waga = col2.text_input("Waga deklarowana (kg):", value="Wg specyfikacji")

        if st.button("⚡ GENERUJ WIELOPSTRONICOWY CMR PDF", type="primary", use_container_width=True):
            with st.spinner("Składanie stron dokumentu..."):
                pdf = FPDF()
                kopie = [
                    (1, "EGZEMPLARZ DLA NADAWCY (SENDER)"),
                    (2, "EGZEMPLARZ DLA ODBIORCY (CONSIGNEE)"),
                    (3, "EGZEMPLARZ DLA PRZEWOZNIKA (CARRIER)"),
                    (4, "ADMINISTRACJA (ADMINISTRATION)")
                ]

                for num, label in kopie:
                    # Ręczne symulowanie nagłówka dla każdej strony
                    pdf.add_page()
                    
                    # Logika nagłówka PRO (uproszczona wewnątrz pętli)
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 10, pdf_sanitize(f"CMR - COPY {num} / {label}"), ln=True, align='C')
                    pdf.ln(5)

                    # --- RUBRYKI CMR ---
                    y_start = pdf.get_y()
                    
                    # 1. Nadawca
                    draw_cmr_box(pdf, "1. SENDER", "Nadawca", "SQM Prosta Spółka Akcyjna\nul. Piekarna 1\n62-052 Komorniki, PL", height=30)
                    
                    # 2. Odbiorca
                    draw_cmr_box(pdf, "2. CONSIGNEE", "Odbiorca", str(r.get('Miejsce Rozladunku', '')), height=35)
                    
                    # 3. Miejsce przeznaczenia
                    draw_cmr_box(pdf, "3. PLACE OF DELIVERY", "Miejsce rozladunku", str(r.get('Miejsce Rozladunku', '')), height=25)
                    
                    # Pozycjonowanie obok (kolumna prawa)
                    pdf.set_xy(105, y_start)
                    
                    # 16. Przewoźnik
                    draw_cmr_box(pdf, "16. CARRIER", "Przewoznik", str(r.get('Zleceniobiorca', '')), height=30)
                    
                    # 17. Successive carriers
                    draw_cmr_box(pdf, "17. SUCCESSIVE CARRIERS", "Kolejni przewoznicy", str(kierowca), height=35)
                    
                    # 18. Reservations
                    draw_cmr_box(pdf, "18. RESERVATIONS", "Zastrzezenia", "N/A", height=25)

                    # Sekcja towarowa
                    pdf.set_xy(10, pdf.get_y() + 5)
                    draw_cmr_box(pdf, "6-12. DESCRIPTION OF GOODS", "Opis towaru", "Exhibition Structures / Sprzęt AV / Konstrukcje Targowe", width=190, height=40)
                    
                    # Podpis i Data
                    pdf.ln(5)
                    curr_y = pdf.get_y()
                    draw_cmr_box(pdf, "21. ESTABLISHED IN", "Wystawiono w", f"Komorniki, {datetime.now().strftime('%d.%m.%Y')}", width=60)
                    pdf.set_xy(70, curr_y)
                    draw_cmr_box(pdf, "22. SENDER SIGNATURE", "Podpis nadawcy", "", width=65)
                    pdf.set_xy(135, curr_y)
                    draw_cmr_box(pdf, "23. CARRIER SIGNATURE", "Podpis przewoznika", "", width=65)

                # Export
                pdf_bytes = pdf.output(dest='S').encode('latin1')
                st.success("✅ Dokument CMR (4 strony) gotowy!")
                st.download_button(
                    "📥 POBIERZ CMR PDF (PRO MULTI-PAGE)", 
                    data=pdf_bytes, 
                    file_name=f"CMR_{wybor.replace('/', '_')}.pdf", 
                    mime="application/pdf", 
                    use_container_width=True
                )
else:
    st.info("Brak zleceń do wystawienia CMR.")
