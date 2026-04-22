import streamlit as st
import pandas as pd
from PIL import Image
import json

# Importujemy nasz silnik
from core import get_gsheets_client, init_ai_model, fetch_data, SHEET_URL

# --- KONFIGURACJA STRONY ---
st.markdown("<h1 style='color: #8b5cf6;'>🤖 AI SKANER PROJEKTÓW</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Zautomatyzowane wyciąganie danych z tabel (zrzutów ekranu) za pomocą modelu Google Gemini.</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Wgraj zrzut ekranu (PNG, JPG)", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Podgląd zrzutu ekranu", use_container_width=True)
    
    if st.button("🔍 Skanuj Tabelę za pomocą AI", type="primary", use_container_width=True):
        with st.spinner("AI analizuje obraz i wyciąga dane... To zajmie kilka sekund."):
            # Pobieramy zainicjowany model z naszego silnika
            model = init_ai_model()
            
            if model:
                try:
                    prompt = """
                    Przeanalizuj to zdjęcie tabeli. Zwróć dane WYŁĄCZNIE w formacie JSON jako lista obiektów.
                    Dla każdego wiersza stwórz obiekt z TRZEMA kluczami, zachowując dokładnie tę kolejność:
                    1. "Nazwa Eventu": Pobierz z kolumny "NAZWA TARGÓW".
                    2. "ID Projektu": Pobierz z kolumny "NUMER PROJEKTU", ale wyciągnij z niej TYLKO 5 pierwszych cyfr (zignoruj słowa takie jak "NIE" lub "nie").
                    3. "Nazwa Projektu": Pobierz z kolumny "NAZWA PROJEKTU" (najbardziej po prawej stronie tabeli, np. Astra Zeneka, Canon).
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
                    error_msg = str(e)
                    st.error(f"Błąd analizy AI: {error_msg}")
                    if "429" in error_msg:
                        st.warning("⚠️ Osiągnięto limit zapytań (5 na minutę). Odczekaj 60 sekund i spróbuj ponownie.")

# --- EDYCJA I ZAPIS DANYCH ---
if 'scanned_data' in st.session_state:
    st.markdown("### 📝 Krok 2: Weryfikacja i Zapis")
    st.info("Sprawdź poniższe dane przed zapisem do bazy. Pamiętaj, aby kolejność kolumn w Arkuszu Google (A, B, C) odpowiadała tym poniżej!")
    
    # Edytowalna tabela
    edited_df = st.data_editor(st.session_state['scanned_data'], use_container_width=True, num_rows="dynamic")
    
    if st.button("💾 Zapisz zatwierdzone projekty do Google Sheets", type="primary"):
        with st.spinner("Wysyłanie do chmury..."):
            try:
                # Używamy klienta z silnika żeby bezpośrednio dodać wiele wierszy na raz
                client = get_gsheets_client()
                worksheet = client.open_by_url(SHEET_URL).worksheet("Projekty")
                
                dane_do_zapisu = edited_df.values.tolist()
                worksheet.append_rows(dane_do_zapisu)
                
                # Zmuszamy silnik do odświeżenia projektów w tle!
                fetch_data.clear()
                
                st.success("Sukces! Projekty zostały dodane do bazy. Będą widoczne w listach rozwijanych we wszystkich modułach.")
                del st.session_state['scanned_data']
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu do bazy: {e}")

st.caption("Vortex Nexus 3.0 | Module: AI Scanner")
