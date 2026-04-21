import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Vortex Nexus | Central Terminal",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- UKRYCIE DOMYŚLNEGO MENU BOCZNEGO ---
# Wymuszamy ukrycie automatycznej listy plików, aby menu było sterowane tylko przez nas
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
        .stApp {
            background: radial-gradient(circle at 50% 0%, #1e293b 0%, #020617 100%);
        }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SYSTEMOWY ---
st.markdown("<h1 style='text-align: center; color: #38bdf8; font-size: 4rem; font-weight: 900; margin-bottom: 0;'>VORTEX NEXUS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1.3rem; margin-top: -10px; font-weight: 300;'>Enterprise Transport Management System v2.0</p>", unsafe_allow_html=True)
st.markdown("<br><br>", unsafe_allow_html=True)

# --- GŁÓWNY PODZIAŁ OPERACYJNY ---
col_cargo, col_space, col_zaop = st.columns([10, 1, 10])

# FILAR 1: LOGISTYKA CARGO
with col_cargo:
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #f8fafc;'>🚛 LOGISTYKA CARGO</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; height: 50px;'>Zarządzanie flotą ciężką, planowanie naczep na TARGI, obsługa dokumentacji CMR oraz baza przewoźników cargo.</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Przyciski nawigacyjne do modułów Cargo
        if st.button("🚛 DYSPOZYCJA FLOTY (TARGI)", use_container_width=True, type="primary"):
            st.switch_page("pages/1_🚛_Dyspozycja_Floty.py")
            
        if st.button("📄 TERMINAL DOKUMENTÓW CMR", use_container_width=True):
            st.switch_page("pages/2_📄_Terminal_CMR.py")
            
        if st.button("🚚 BAZA PRZEWOŹNIKÓW CARGO", use_container_width=True):
            st.switch_page("pages/3_🚚_Baza_Przewoznikow.py")
            
        if st.button("📊 HISTORIA ZLECEŃ CARGO", use_container_width=True):
            st.switch_page("pages/4_📊_Historia_Zlecen_Cargo.py")

# FILAR 2: ZAOPATRZENIE
with col_zaop:
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #f8fafc;'>📦 ZAOPATRZENIE</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; height: 50px;'>Obsługa sprzętu wypożyczonego (Inbound/Zwrot), kreator zapotrzebowania, finanse projektów i baza kontrahentów.</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Przyciski nawigacyjne do modułów Zaopatrzenia
        if st.button("📦 KREATOR ZAOPATRZENIA (ZGŁOSZENIA)", use_container_width=True, type="primary"):
            st.switch_page("pages/5_📦_Kreator_Zaopatrzenia.py")
            
        if st.button("💰 FINANSE PROJEKTÓW (KOSZTY)", use_container_width=True):
            st.switch_page("pages/6_💰_Finanse_Projektu.py")
            
        if st.button("🏢 BAZA KONTRAHENTÓW / MIEJSC", use_container_width=True):
            st.switch_page("pages/7_🏢_Baza_Kontrahentow.py")

# --- STOPKA SYSTEMOWA ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f"""
    <div style='text-align: center; color: #475569; font-size: 0.85rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 20px;'>
        VORTEX NEXUS CORE | Terminal Status: <span style='color: #10b981;'>ONLINE</span><br>
        Zalogowano jako: Admin Terminal | {datetime.now().strftime("%d.%m.%Y %H:%M")}
    </div>
""", unsafe_allow_html=True)

# --- SIDEBAR (OPCJONALNY PODGLĄD STATUSU) ---
with st.sidebar:
    st.image("https://img.icons8.com/nolan/128/vortex.png", width=80)
    st.markdown("### SYSTEM STATUS")
    st.info("Aplikacja została pomyślnie zrefaktoryzowana. Działy Cargo i Zaopatrzenie działają w trybie odseparowanym.")
    if st.button("Wyczyść Cache Systemu"):
        st.cache_data.clear()
        st.rerun()
