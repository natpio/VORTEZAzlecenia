import streamlit as st
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Vortex Nexus | Central Terminal",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- UKRYCIE DOMYŚLNEGO MENU BOCZNEGO ---
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
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1.3rem; margin-top: -10px; font-weight: 300;'>Enterprise Transport Management System v2.1</p>", unsafe_allow_html=True)
st.markdown("<br><br>", unsafe_allow_html=True)

# --- GŁÓWNY PODZIAŁ OPERACYJNY ---
col_cargo, col_space, col_zaop = st.columns([10, 1, 10])

# ==========================================
# FILAR 1: LOGISTYKA CARGO
# ==========================================
with col_cargo:
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #f8fafc;'>🚛 LOGISTYKA CARGO</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; height: 50px;'>Pełna kontrola nad transportem ciężkim (Targi) oraz obsługa i wycena zleceń zaopatrzeniowych.</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🚛 DYSPOZYCJA FLOTY (TARGI)", use_container_width=True):
            st.switch_page("pages/1_🚛_Dyspozycja_Floty.py")
            
        if st.button("🛠️ OBSŁUGA ZAOPATRZENIA (WYCENY I ZLECENIA)", use_container_width=True, type="primary"):
            st.switch_page("pages/8_🛠️_Obsluga_Zaopatrzenia.py")
            
        if st.button("📄 TERMINAL DOKUMENTÓW CMR", use_container_width=True):
            st.switch_page("pages/2_📄_Terminal_CMR.py")
            
        if st.button("🚚 BAZA PRZEWOŹNIKÓW CARGO", use_container_width=True):
            st.switch_page("pages/3_🚚_Baza_Przewoznikow.py")
            
        if st.button("📊 HISTORIA ZLECEŃ CARGO", use_container_width=True):
            st.switch_page("pages/4_📊_Historia_Zlecen_Cargo.py")

# ==========================================
# FILAR 2: ZAOPATRZENIE
# ==========================================
with col_zaop:
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #10b981;'>📦 ZAOPATRZENIE</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; height: 50px;'>Zgłaszanie potrzeb transportowych dla sprzętu wypożyczonego oraz monitorowanie budżetów projektów.</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("➕ ZGŁOŚ POTRZEBĘ TRANSPORTU", use_container_width=True, type="primary"):
            st.switch_page("pages/5_📦_Zgloszenie_Zaopatrzenia.py")
            
        if st.button("💰 FINANSE PROJEKTÓW (KOSZTY)", use_container_width=True):
            st.switch_page("pages/6_💰_Finanse_Projektu.py")
            
        if st.button("🏢 BAZA KONTRAHENTÓW / MIEJSC", use_container_width=True):
            st.switch_page("pages/7_🏢_Baza_Kontrahentow.py")

# ==========================================
# FILAR 3: NARZĘDZIA AI (NOWOŚĆ)
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
with st.container(border=True):
    st.markdown("<h2 style='text-align: center; color: #8b5cf6;'>🤖 INTELIGENTNE NARZĘDZIA (AI)</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>Automatyzacja procesów za pomocą modeli sztucznej inteligencji.</p>", unsafe_allow_html=True)
    
    # Przycisk na środku
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔍 AI SKANER PROJEKTÓW (Zrzuty ekranu)", use_container_width=True):
            st.switch_page("pages/9_🤖_AI_Skaner_Projektow.py")

# --- STOPKA SYSTEMOWA ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f"""
    <div style='text-align: center; color: #475569; font-size: 0.85rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 20px;'>
        VORTEX NEXUS CORE | Terminal Status: <span style='color: #10b981;'>ONLINE</span><br>
        Struktura ról zaktualizowana | {datetime.now().strftime("%d.%m.%Y %H:%M")}
    </div>
""", unsafe_allow_html=True)
