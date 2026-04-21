import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Vortex TMS | Nexus",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Wczytanie CSS (jeśli wciąż używasz pliku style.css)
try:
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
    pass

# --- HEADER ---
st.markdown("<h1 style='text-align: center; color: #38bdf8; font-size: 3.5rem; font-weight: 900; margin-bottom: 0;'>VORTEX NEXUS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1.2rem; margin-top: -10px;'>Wybierz moduł operacyjny</p>", unsafe_allow_html=True)
st.markdown("<br><br>", unsafe_allow_html=True)

# --- PODZIAŁ NA DWA FILARY ---
col_cargo, col_space, col_zaop = st.columns([10, 1, 10])

# FILAR 1: LOGISTYKA CARGO
with col_cargo:
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #f8fafc;'>🚛 LOGISTYKA CARGO</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; height: 40px;'>Zarządzanie główną flotą, naczepami na eventy i generowanie dokumentów CMR.</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("🚛 DYSPOZYCJA FLOTY (GŁÓWNE ZLECENIA)", use_container_width=True, type="primary"):
            st.switch_page("pages/1_🚛_Dyspozycja_Floty.py")
            
        if st.button("📄 TERMINAL CMR", use_container_width=True):
            st.switch_page("pages/2_📄_Terminal_CMR.py")
            
        if st.button("🚚 BAZA PRZEWOŹNIKÓW", use_container_width=True):
            st.switch_page("pages/3_🚚_Baza_Przewoznikow.py")
            
        if st.button("📊 HISTORIA CARGO", use_container_width=True):
            st.switch_page("pages/4_📊_Historia_Zlecen_Cargo.py")

# FILAR 2: ZAOPATRZENIE
with col_zaop:
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #f8fafc;'>📦 ZAOPATRZENIE</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; height: 40px;'>Zarządzanie sprzętem wypożyczonym, kontrola kosztów projektowych i baza kontrahentów.</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("📦 KREATOR ZAOPATRZENIA (ZGŁOSZENIA)", use_container_width=True, type="primary"):
            st.switch_page("pages/5_📦_Kreator_Zaopatrzenia.py")
            
        if st.button("💰 FINANSE PROJEKTÓW", use_container_width=True):
            st.switch_page("pages/6_💰_Finanse_Projektu.py")
            
        if st.button("🏢 BAZA KONTRAHENTÓW", use_container_width=True):
            st.switch_page("pages/7_🏢_Baza_Kontrahentow.py")

st.markdown("<br><br><p style='text-align: center; color: #475569; font-size: 0.8rem;'>Vortex Nexus Core v2.0 | System online</p>", unsafe_allow_html=True)
