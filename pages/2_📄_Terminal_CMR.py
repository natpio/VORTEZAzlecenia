import streamlit as st
import pandas as pd
import qrcode
import io
from fpdf import FPDF
from datetime import datetime

# Importujemy silnik Vortex
from core import fetch_data

# --- KONFIGURACJA DOKUMENTU ---
def generate_cmr_v3(data, qr_img):
    """Generuje 3-stronny dokument CMR (Standard International)."""
    pdf = FPDF()
    
    # Nagłówki stron CMR
    strony = [
        "1. EXEMPLAIRE POUR LE TRANSPORTEUR (CZARNY)",
        "2. EXEMPLAIRE POUR LE DESTINATAIRE (NIEBIESKI)",
        "3. EXEMPLAIRE POUR L'EXPEDITEUR (CZERWONY)"
    ]

    for label in strony:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "INTERNATIONAL CONSIGNMENT NOTE (CMR)", ln=True, align='C')
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 5, label, ln=True, align='C')
        pdf.ln(5)

        # Ramka danych
        pdf.set_font("Arial", 'B', 10)
        
        # Sekcja 1 & 2: Nadawca i Odbiorca
        pdf.rect(10, 30, 95, 40) # Nadawca
        pdf.set_xy(12, 32)
        pdf.cell(0, 5, "1. Sender (Name, Address, Country):")
        pdf.set_font("Arial", '', 10)
        pdf.set_xy(12, 38)
        pdf.multi_cell(90, 5, "VORTEX NEXUS LOGISTICS\nMagazyn Centralny Komorniki\nPOLAND")

        pdf.rect(105, 30, 95, 40) # Odbiorca
        pdf.set_font("Arial", 'B', 10)
        pdf.set_xy(107, 32)
        pdf.cell(0, 5, "2. Consignee (Name, Address, Country):")
        pdf.set_font("Arial", '', 10)
        pdf.set_xy(107, 38)
        pdf.multi_cell(90, 5, data['odbiorca'])

        # Sekcja 3 & 4: Miejsce zał / rozł
        pdf.rect(10, 70, 95, 30)
        pdf.set_xy(12, 72)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, "3. Place of taking over the goods:")
        pdf.set_font("Arial", '', 10)
        pdf.set_xy(12, 78)
        pdf.multi_cell(90, 5, data['zaladunek'])

        pdf.rect(105, 70, 95, 30)
        pdf.set_xy(107, 72)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, "4. Place of delivery of the goods:")
        pdf.set_font("Arial", '', 10)
        pdf.set_xy(107, 78)
        pdf.multi_cell(90, 5, data['rozladunek'])

        # Sekcja: Przewoźnik
        pdf.rect(10, 100, 190, 30)
        pdf.set_xy(12, 102)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, "16. Carrier (Name, Address, Country):")
        pdf.set_font("Arial", '', 10)
        pdf.set_xy(12, 108)
        pdf.multi_cell(180, 5, f"{data['przewoznik']}\nVehicle: {data['pojazd']}")

        # Sekcja: Towar
        pdf.rect(10, 130, 190, 50)
        pdf.set_xy(12, 132)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, "6-12. Marks, Nos, Number of packages, Method of packing, Nature of goods:")
        pdf.set_font("Arial", '', 11)
        pdf.set_xy(12, 140)
        pdf.multi_cell(180, 7, f"GOODS: {data['towar']}\nQUANTITY: As per packing list\nINSTRUCTIONS: {data['uwagi']}")

        # QR CODE & Footer
        pdf.image(qr_img, 165, 185, 30, 30)
        pdf.set_xy(10, 200)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"REF NR: {data['nr']}", ln=True)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 5, f"Generated via Vortex Nexus 3.0 Core Engine | {datetime.now().strftime('%Y-%m-%d %H:%M')}", align='R')

    return pdf.output(dest='S').encode('latin1')

# --- INTERFEJS TERMINALA ---
st.markdown("<h1 style='color: #38bdf8;'>📄 TERMINAL CMR</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Generowanie międzynarodowych listów przewozowych na podstawie zleceń Cargo.</p>", unsafe_allow_html=True)

with st.spinner("Ładowanie rejestru zleceń..."):
    df = fetch_data("Zlecenia")

if not df.empty:
    # Filtrujemy tylko zlecenia Cargo (Targowe)
    df_cargo = df[df['Dział'] == 'LOGISTYKA CARGO'].iloc[::-1] # Najnowsze na górze
    
    if not df_cargo.empty:
        with st.container(border=True):
            st.markdown("### 🔍 Wybierz zlecenie do wydruku")
            lista_nr = df_cargo['Numer zlecenia'].tolist()
            wybor = st.selectbox("Wybierz Numer Zlecenia:", lista_nr, index=0)
            
            # Pobieranie danych wybranego wiersza
            r = df_cargo[df_cargo['Numer zlecenia'] == wybor].iloc[0]
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Przewoźnik:** {r.get('Zleceniobiorca', 'N/A')}")
                st.write(f"**Trasa:** {r.get('Miejsce Zaladunku', 'N/A')} ➡️ {r.get('Miejsce Rozladunku', 'N/A')}")
            with c2:
                st.write(f"**Data:** {r.get('Data Zaladunku', 'N/A')}")
                st.write(f"**Towar:** {r.get('Towar', 'Sprzęt Eventowy')}")

            # Przygotowanie danych do dokumentu
            dane_doc = {
                "nr": str(wybor),
                "odbiorca": f"TARGI: {r.get('ID Projektu', 'N/A')}\n{r.get('Miejsce Rozladunku', 'N/A')}",
                "zaladunek": str(r.get('Miejsce Zaladunku', 'Magazyn PL')),
                "rozladunek": str(r.get('Miejsce Rozladunku', 'Targi')),
                "przewoznik": str(r.get('Zleceniobiorca', 'N/A')),
                "pojazd": str(r.get('Uwagi / Instrukcje', '')).split('AUTO: ')[-1].split(' ||')[0] if 'AUTO: ' in str(r.get('Uwagi / Instrukcje', '')) else "Do uzupełnienia",
                "towar": str(r.get('Towar', 'Elementy zabudowy')),
                "uwagi": str(r.get('Uwagi / Instrukcje', ''))
            }

            # Generowanie QR Code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"VORTEX-CMR-{wybor}")
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            
            qr_buffer = io.BytesIO()
            img_qr.save(qr_buffer, format="PNG")
            qr_buffer.seek(0)

            st.markdown("<br>", unsafe_allow_html=True)
            
            # Przycisk pobierania
            if st.button("🛠️ PRZYGOTUJ PAKIET CMR", type="primary", use_container_width=True):
                with st.spinner("Składanie dokumentów..."):
                    pdf_bytes = generate_cmr_v3(dane_doc, qr_buffer)
                    
                    st.success("✅ Pakiet CMR (3 strony) jest gotowy do pobrania!")
                    st.download_button(
                        label="📥 POBIERZ DOKUMENT PDF",
                        data=pdf_bytes,
                        file_name=f"CMR_{wybor.replace('/', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
    else:
        st.info("Brak aktywnych zleceń Cargo w bazie.")
else:
    st.error("Baza zleceń jest pusta lub niedostępna.")

st.caption("Vortex Nexus 3.0 | Module: CMR Terminal")
