import streamlit as st

st.set_page_config(
    page_title="System TMS - Dashboard",
    page_icon="🚚",
    layout="wide"
)

st.title("🚚 Witaj w Systemie Zleceń i CMR")
st.markdown("---")

st.markdown("""
### Jak korzystać z systemu?
Użyj menu po lewej stronie, aby nawigować między modułami:
* **📝 Nowe Zlecenie** - Wystawianie profesjonalnych zleceń i oficjalnych druków CMR z kodami QR.
* **📄 Kreator CMR** - Szybkie generowanie samego listu przewozowego.
* **🚚 Baza Przewoźników** - Zarządzanie danymi Twoich podwykonawców.
* **🏢 Baza Miejsc** - Słownik miejsc załadunków i rozładunków.
* **📊 Historia Zleceń** - Archiwum wystawionych dokumentów.
""")

st.info("👈 Wybierz moduł z menu po lewej, aby rozpocząć pracę.")
