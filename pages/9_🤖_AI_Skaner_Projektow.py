import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from PIL import Image
import json

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="Skaner AI | Projekty")

st.markdown("""<style>[data-testid="stSidebarNav"] {display: none !important;}</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='color: #8b5cf6;'>🤖 NARZĘDZIA AI</h2>", unsafe_allow_html=True)
    st.page_link("app.py", label="⬅ Wróć do Menu Głównego")
    st.divider()
    st.page_link("pages/1_🚛_Dyspozycja_Floty.py", label="Dyspozycja Floty")
    st.page_link("pages/8_🛠️_Obsluga_Zaopatrzenia.py", label="Obsługa Zaopatrzenia")
    st.page_link("pages/9_🤖_AI_Skaner_Projektow.py", label="AI Skaner Projektów")

# --- KONFIGURACJA BAZY ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1R7Iajr-AFFYwDFmeZCF6pasitNuY75Z4ArTpm89Xzhc/edit"

def get_gsheets_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("Brak konfiguracji klucza GEMINI_API_KEY w Streamlit Secrets.")

# --- INTERFEJS APLIKACJI ---
st.title("🤖 AI Skaner Projektów (OCR)")
st.markdown("Wgraj zrzut ekranu z zewnętrznego systemu. Sztuczna Inteligencja przeczyta tabelę i przygotuje gotowe dane do bazy.")

uploaded_file = st.file_uploader("Wgraj zrzut ekranu (PNG, JPG)", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Podgląd zrzutu ekranu", use_container_width=True)
    
    if st.button("🔍 Skanuj Tabelę za pomocą AI", type="primary", use_container_width=True):
        with st.spinner("AI analizuje obraz i wyciąga dane... To zajmie kilka sekund."):
            try:
                # Inicjalizacja najnowszego, standardowego modelu
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = """
                Przeanalizuj to zdjęcie tabeli. Zwróć dane WYŁĄCZNIE w formacie JSON jako lista obiektów.
                Dla każdego wiersza stwórz obiekt z dwoma kluczami:
                1. "Nazwa Eventu": Pobierz z kolumny "NAZWA TARGÓW".
                2. "ID Projektu": Pobierz z kolumny "NUMER PROJEKTU", ale wyciągnij z niej TYLKO 5 pierwszych cyfr (zignoruj słowa takie jak "NIE" lub "nie").
                Zignoruj puste wiersze. Nie dodawaj żadnego dodatkowego tekstu ani znaczników markdown poza samym formatem JSON.
                """
                
                response = model.generate_content([prompt, image])
                
                # Czyszczenie odpowiedzi JSON
                cleaned_response = response.text.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                data = json.loads(cleaned_response)
                
                if data:
                    st.session_state['scanned_data'] = pd.DataFrame(data)
                    st.success(f"Zeskanowano pomyślnie {len(data)} projektów!")
                else:
                    st.warning("AI nie znalazło żadnych danych w tabeli.")
                    
            except Exception as e:
                st.error(f"Błąd analizy AI: {e}")
                st.info("System diagnostyczny odpytuje serwery Google o listę dostępnych modeli dla Twojego klucza...")
                try:
                    # DIAGNOSTYKA: Pobieramy listę modeli przypisanych do Twojego klucza
                    dostepne_modele = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    st.write("**Lista dostępnych modeli (Skopiuj ją i wyślij do mnie, dobierzemy odpowiedni!):**")
                    st.write(dostepne_modele)
                except Exception as diag_e:
                    st.error(f"Błąd diagnostyki: {diag_e}. Upewnij się, że klucz API jest poprawny.")

# --- EDYCJA I ZAPIS DANYCH ---
if 'scanned_data' in st.session_state:
    st.markdown("### 📝 Krok 2: Weryfikacja i Zapis")
    st.info("Sprawdź poniższe dane. Możesz poprawić literówki przed zapisem do bazy.")
    
    edited_df = st.data_editor(st.session_state['scanned_data'], use_container_width=True, num_rows="dynamic")
    
    if st.button("💾 Zapisz zatwierdzone projekty do Google Sheets", type="primary"):
        with st.spinner("Wysyłanie do chmury..."):
            try:
                client = get_gsheets_client()
                worksheet = client.open_by_url(SHEET_URL).worksheet("Projekty")
                dane_do_zapisu = edited_df.values.tolist()
                worksheet.append_rows(dane_do_zapisu)
                
                st.success("Sukces! Projekty zostały dodane do bazy.")
                del st.session_state['scanned_data']
            except Exception as e:
                st.error(f"Błąd zapisu do bazy: {e}")
