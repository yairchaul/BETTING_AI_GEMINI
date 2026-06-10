# -*- coding: utf-8 -*-
"""UTILIDADES - Funciones auxiliares"""
import os, json, sqlite3, pandas as pd, logging, requests
from datetime import datetime

logger = logging.getLogger(__name__)

def inicializar_bd_ufc():
    os.makedirs("data", exist_ok=True)
    try:
        conn = sqlite3.connect("data/betting_stats.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS peleadores_ufc_cache (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, datos_json TEXT, ultima_actualizacion TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS eventos_ufc (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha TEXT, cartelera TEXT, ultima_actualizacion TEXT)")
        conn.commit(); conn.close(); return True
    except Exception as e:
        logger.error(f"Error BD: {e}"); return False

def cargar_css(css_file="estilos_neon.css"):
    try:
        with open(css_file, "r", encoding="utf-8") as f:
            import streamlit as st
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True); return True
    except: return False

def cargar_mlb_desde_json():
    try:
        with open("resultados_finales_corregidos.json", "r", encoding="utf-8") as f: return json.load(f)
    except: return None

def mostrar_player_props_nba(analisis):
    import streamlit as st
    col1, col2 = st.columns(2)
    with col1:
        top3 = analisis.get('top_3pm_local')
        if top3: st.markdown(f"**🏀 {top3.get('nombre', 'N/A')}**"); st.caption(f"🎯 {top3.get('triples_por_partido', 0)} triples/partido")
    with col2:
        top3 = analisis.get('top_3pm_visit')
        if top3: st.markdown(f"**🏀 {top3.get('nombre', 'N/A')}**"); st.caption(f"🎯 {top3.get('triples_por_partido', 0)} triples/partido")

def mostrar_player_props_mlb(analisis):
    import streamlit as st
    col1, col2 = st.columns(2)
    with col1:
        hr = analisis.get('top_hr_local')
        if hr:
            items = hr if isinstance(hr, list) else [hr]
            for h in items[:2]: st.markdown(f"**⚾ {h.get('nombre', 'N/A')}**"); st.caption(f"💪 {h.get('hr', 0)} HR")
    with col2:
        hr = analisis.get('top_hr_visit')
        if hr:
            items = hr if isinstance(hr, list) else [hr]
            for h in items[:2]: st.markdown(f"**⚾ {h.get('nombre', 'N/A')}**"); st.caption(f"💪 {h.get('hr', 0)} HR")

def render_profit_card():
    import streamlit as st
    try:
        if os.path.exists("data/bitacora_maestra.csv"):
            df = pd.read_csv("data/bitacora_maestra.csv")
            if 'acierto' in df.columns:
                ganadas = len(df[df['acierto'] == True]); perdidas = len(df[df['acierto'] == False])
                if ganadas + perdidas > 0:
                    profit = ((ganadas * 0.90) - perdidas) * 10; color = "#00ff41" if profit >= 0 else "#ff4b4b"
                    st.sidebar.markdown(f'<div class="profit-card"><span>Profit Estimado</span><h2 style="color:{color};margin:0">${profit:.2f} USD</h2><span>{ganadas}W / {perdidas}L</span></div>', unsafe_allow_html=True)
    except: pass
