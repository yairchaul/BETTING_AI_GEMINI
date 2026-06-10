# -*- coding: utf-8 -*-
import streamlit as st
import json
from predictor_hr import predictor_hr

st.set_page_config(page_title="NEON AI - MULTI-SPORT", layout="wide")

# --- CSS MEJORADO (SIN ROMPER EL MAIN) ---
st.markdown("""
<style>
    .main { background-color: #0d1117; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .card-bet {
        background: #161b22;
        padding: 20px;
        border: 1px solid #30363d;
        border-radius: 15px;
        margin-bottom: 20px;
    }
    .status-evitar { color: #ff4b4b; font-weight: bold; background: rgba(255,75,75,0.1); padding: 10px; border-radius: 5px; }
    .status-rescate { color: #00d4ff; font-weight: bold; background: rgba(0,212,255,0.1); padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (CONTROLES) ---
with st.sidebar:
    st.title("⚙️ CONTROLES")
    st.button("🎯 CALIBRAR IA (BACKTESTING)")
    st.divider()
    st.subheader("🤖 ESTADO DE IA")
    st.success("GROQ: CONECTADO")
    st.success("GEMINI: ACTIVO")
    st.divider()
    if st.button("🔄 ACTUALIZAR TODOS LOS DEPORTES"):
        st.toast("Sincronizando con ESPN y Caliente...")

# --- CUERPO PRINCIPAL ---
st.title("🚀 APUESTAS_IA (MODO HÍBRIDO)")

# Tabs para deportes
tab_mlb, tab_nba, tab_ufc, tab_futbol = st.tabs(["⚾ MLB", "🏀 NBA", "🥊 UFC", "⚽ FUTBOL"])

with tab_mlb:
    # Simulación de la lógica mejorada
    with st.container():
        st.markdown('<div class="card-bet">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2,1,2])
        # ... (Aquí va la lógica de los equipos)
        
        # EL CAMBIO CLAVE:
        st.markdown("---")
        col_an, col_ia = st.columns(2)
        with col_an:
            st.markdown('<p class="status-evitar">❌ EVITAR APOSTAR (Criterio V2.1)</p>', unsafe_allow_html=True)
        with col_ia:
            if st.button("🔍 CONSULTAR IA (GROQ/GEMINI)"):
                st.info("IA analizando jerarquía... Rescate sugerido: +1.5 (Confianza Real: 62%)")
        st.markdown('</div>', unsafe_allow_html=True)

with tab_futbol:
    st.info("Cargando ligas: Premier, La Liga, Serie A...")
