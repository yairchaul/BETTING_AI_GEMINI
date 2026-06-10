# -*- coding: utf-8 -*-
"""
BETTING_AI NEON - V22 (UFC con UFCStats - Datos 100% Reales)
NBA, MLB, UFC, Futbol con Gemini automatico
"""

import streamlit as st
from datetime import datetime
import pandas as pd
import os
import logging
import sqlite3
import json
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno de forma global
load_dotenv()

from espn_nba import ESPN_NBA
from espn_mlb import ESPN_MLB_Mejorado as ESPN_MLB
from espn_ufc import ESPN_UFC
from espn_futbol import ESPN_FUTBOL
from bet_tracker import BetTracker
from visual_nba_mejorado import VisualNBAMejorado
from visual_ufc_final import VisualUFCFinal
from visual_futbol_triple import VisualFutbolTriple
from visual_mlb import VisualMLB
from database_manager import db
from render_unificado import render_analisis_card
from motor_nba_pro_v17 import analizar_nba_pro_v17
from motor_mlb_pro import analizar_mlb_pro_v20
from motor_fut_pro import analizar_futbol_pro_v20
from scrapers.ufc_stats_scraper import UFCStatsScraper
from analyzers.ufc_analyzer import UFCAnalyzer

try:
    from cerebro_gemini_pro import CerebroGeminiPro
except ImportError:
    CerebroGeminiPro = None

try:
    from groq_ufc_engine import GroqUFCEngine
except ImportError:
    GroqUFCEngine = None

def get_api_key(name):
    try:
        if hasattr(st, "secrets") and name in st.secrets:
            return st.secrets[name]
        return os.getenv(name, "")
    except Exception as e:
        logger.error(f"Error cargando API Key {name}: {e}")
        return ""

def aplicar_estilos():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #020617 0%, #0f172a 100%); border-right: 1px solid #334155; }
    .stButton > button { border-radius: 12px !important; background: linear-gradient(90deg, #3b82f6 0%, #9333ea 100%) !important; color: white !important; font-weight: bold !important; border: none !important; transition: all 0.3s !important; }
    .stButton > button:hover { transform: scale(1.02) !important; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important; }
    </style>
    """, unsafe_allow_html=True)

def cargar_base_ufc():
    try:
        with open("base_ufc_unificada.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def cargar_cuotas_ufc():
    try:
        with open("odds_caliente_ufc.json", "r", encoding="utf-8") as f:
            cuotas = json.load(f)
        odds = {}
        for p in cuotas:
            odds[p["p1"]] = p["m1"]
            odds[p["p2"]] = p["m2"]
        return odds
    except: return {}

def cargar_mlb_desde_json():
    try:
        with open("resultados_finales_corregidos.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except: return None

def inicializar_bd_ufc():
    os.makedirs("data", exist_ok=True)
    try:
        conn = sqlite3.connect("data/betting_stats.db")
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS peleadores_ufc_cache (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, datos_json TEXT, ultima_actualizacion TEXT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS eventos_ufc (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha TEXT, cartelera TEXT, ultima_actualizacion TEXT)""")
        conn.commit(); conn.close()
    except: pass

def main():
    st.set_page_config(page_title="BETTING_AI", page_icon="🎯", layout="wide")
    aplicar_estilos()
    
    if "init" not in st.session_state:
        inicializar_bd_ufc()
        st.session_state.scrapers = {"nba": ESPN_NBA(), "mlb": ESPN_MLB(), "ufc": ESPN_UFC(), "futbol": ESPN_FUTBOL()}
        st.session_state.tracker = BetTracker()
        st.session_state.visual_nba = VisualNBAMejorado()
        st.session_state.visual_ufc = VisualUFCFinal()
        st.session_state.visual_futbol = VisualFutbolTriple()
        st.session_state.visual_mlb = VisualMLB()
        st.session_state.motores = {"nba": analizar_nba_pro_v17, "mlb": analizar_mlb_pro_v20, "futbol": analizar_futbol_pro_v20}
        
        gemini_key = get_api_key("GEMINI_API_KEY")
        st.session_state.gemini = CerebroGeminiPro(gemini_key) if gemini_key and CerebroGeminiPro else None
        groq_key = get_api_key("GROQ_API_KEY")
        st.session_state.groq = GroqUFCEngine(groq_key) if groq_key and GroqUFCEngine else None
        
        st.session_state.ufc_scraper = UFCStatsScraper()
        st.session_state.ufc_analyzer = UFCAnalyzer()
        st.session_state.nba_partidos = []
        st.session_state.ufc_combates = []
        st.session_state.futbol_partidos = {}
        st.session_state.mlb_partidos = []
        st.session_state.init = True

    st.markdown("<div style='text-align:center;padding:10px'><h1 style='background:linear-gradient(90deg,#3b82f6,#9333ea);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.5rem;margin:0'>🎯 APUESTAS_IA</h1><p style='color:#94a3b8;margin:5px 0 0 0'>🏀 NBA &bull; ⚾ MLB &bull; 🥊 UFC &bull; ⚽ Futbol</p></div>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ CONTROLES")
        st.session_state.tracker.render_sidebar_tracker()
        st.markdown("---")
        with st.expander("🔧 Estado de IA", expanded=False):
            st.success("✅ Gemini conectado" if st.session_state.gemini else "❌ Gemini no disponible")
            st.success("✅ Groq conectado" if st.session_state.groq else "⚠️ Groq no disponible")
        st.markdown("---")
        
        if st.button("🏀 CARGAR NBA", use_container_width=True):
            with st.spinner("Cargando NBA..."):
                st.session_state.nba_partidos = st.session_state.scrapers["nba"].get_games()
                st.success(f"✅ {len(st.session_state.nba_partidos)} partidos" if st.session_state.nba_partidos else "⚠️ No hay partidos")

        if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("Cargando MLB..."):
                partidos_json = cargar_mlb_desde_json()
                st.session_state.mlb_partidos = partidos_json if partidos_json else st.session_state.scrapers["mlb"].get_games()
                st.success(f"✅ {len(st.session_state.mlb_partidos)} partidos" if st.session_state.mlb_partidos else "⚠️ No hay partidos")

        if st.button("🥊 CARGAR UFC", use_container_width=True):
            with st.spinner("🔄 Buscando cartelera UFC..."):
                st.session_state.ufc_combates = st.session_state.scrapers["ufc"].get_events()
                st.success(f"✅ {len(st.session_state.ufc_combates)} combates" if st.session_state.ufc_combates else "ℹ️ No hay eventos")

        st.markdown("---"); st.subheader("⚽ FUTBOL")
        ligas = st.session_state.scrapers["futbol"].get_available_leagues()
        for liga in ligas[:20]:
            if st.button(f"⚽ {liga}", key=f"btn_{liga}", use_container_width=True):
                with st.spinner(f"Cargando {liga}..."):
                    st.session_state.futbol_partidos[liga] = st.session_state.scrapers["futbol"].get_games(liga)
                    st.success(f"✅ {len(st.session_state.futbol_partidos[liga])} partidos")

    tab1, tab2, tab3, tab4 = st.tabs(["🏀 NBA", "🥊 UFC", "⚽ FUTBOL", "⚾ MLB"])

    with tab1:
        if st.session_state.nba_partidos:
            for idx, p in enumerate(st.session_state.nba_partidos):
                st.session_state.visual_nba.render(p, idx, st.session_state.tracker, None, None, None)
                st.markdown("---")
        else: st.info("👈 Carga NBA en el sidebar")

    with tab2:
        base_ufc = cargar_base_ufc()
        odds_ufc = cargar_cuotas_ufc()
        
        if st.session_state.ufc_combates:
            for idx, c in enumerate(st.session_state.ufc_combates):
                if isinstance(c, dict):
                    p1_raw = c.get('peleador1', c.get('peleador1_nombre', ''))
                    p2_raw = c.get('peleador2', c.get('peleador2_nombre', ''))
                    p1_nombre = p1_raw.get('nombre', '') if isinstance(p1_raw, dict) else str(p1_raw)
                    p2_nombre = p2_raw.get('nombre', '') if isinstance(p2_raw, dict) else str(p2_raw)
                else: continue
                if not p1_nombre or not p2_nombre: continue
                
                p1_stats = st.session_state.ufc_scraper.get_fighter_stats(p1_nombre)
                p2_stats = st.session_state.ufc_scraper.get_fighter_stats(p2_nombre)
                
                p1_base = next((p for p in base_ufc if p.get('nombre','') == p1_nombre), {})
                p2_base = next((p for p in base_ufc if p.get('nombre','') == p2_nombre), {})
                
                partido_visual = {
                    'peleador1': {
                        'nombre': p1_nombre,
                        'record': p1_stats.get('record', 'N/A') if p1_stats else 'N/A',
                        'altura': p1_stats.get('altura', 0) if p1_stats else 0,
                        'alcance': p1_stats.get('alcance', 0) if p1_stats else 0,
                        'ko_rate': p1_base.get('ko_rate', 'N/A'),
                        'sub_rate': p1_base.get('sub_rate', 'N/A'),
                        'dec_rate': p1_base.get('dec_rate', 'N/A'),
                        'odds': str(odds_ufc.get(p1_nombre, 'N/A'))
                    },
                    'peleador2': {
                        'nombre': p2_nombre,
                        'record': p2_stats.get('record', 'N/A') if p2_stats else 'N/A',
                        'altura': p2_stats.get('altura', 0) if p2_stats else 0,
                        'alcance': p2_stats.get('alcance', 0) if p2_stats else 0,
                        'ko_rate': p2_base.get('ko_rate', 'N/A'),
                        'sub_rate': p2_base.get('sub_rate', 'N/A'),
                        'dec_rate': p2_base.get('dec_rate', 'N/A'),
                        'odds': str(odds_ufc.get(p2_nombre, 'N/A'))
                    }
                }
                
                st.session_state.visual_ufc.render(partido_visual, idx, st.session_state.tracker, None)
                st.markdown("---")
        else: st.info("👈 Carga UFC en el sidebar")

    with tab3:
        if st.session_state.futbol_partidos:
            for liga, partidos in st.session_state.futbol_partidos.items():
                if partidos:
                    st.markdown(f"### ⚽ {liga}")
                    for idx, p in enumerate(partidos):
                        st.session_state.visual_futbol.render(p, idx, liga, st.session_state.tracker, None, None, None, None)
                        st.markdown("---")
        else: st.info("👈 Carga ligas en el sidebar")

    with tab4:
        if st.session_state.mlb_partidos:
            for idx, p in enumerate(st.session_state.mlb_partidos):
                st.session_state.visual_mlb.render(p, idx, st.session_state.tracker, None, None, None)
                st.markdown("---")
        else: st.info("👈 Carga MLB en el sidebar")

if __name__ == "__main__":
    main()
