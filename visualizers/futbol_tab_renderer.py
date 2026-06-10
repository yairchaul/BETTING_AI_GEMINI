# -*- coding: utf-8 -*-
"""Módulo para renderizar la pestaña de Fútbol."""

import streamlit as st
import subprocess
import sys
import sqlite3
from utils.analista_total import AnalistaTotal
from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
from utils.database_manager import db
import logging

logger = logging.getLogger(__name__)

def render_futbol_tab():
    """Renderiza el contenido completo de la pestaña de Fútbol."""
    if st.session_state.futbol_partidos and st.session_state.visual_futbol:
        search_term = st.text_input("🔍 Buscar en mis ligas cargadas:", "").lower()
        
        for liga, partidos in st.session_state.futbol_partidos.items():
            if search_term and search_term not in liga.lower(): continue
            
            if partidos:
                st.markdown(f"### ⚽ {liga}")
                for idx, p in enumerate(partidos):
                    res_h = st.session_state.analisis_futbol.get(f"{liga}_{idx}_h")
                    res_ia = st.session_state.analisis_futbol.get(f"{liga}_{idx}_ia")
                    try: 
                        accion = st.session_state.visual_futbol.render(p, idx, liga, st.session_state.tracker, analisis_heuristico=res_h, analisis_ia=res_ia)
                        if accion == "analizar":
                            with st.spinner(f"Analizando {liga}..."):
                                conn = sqlite3.connect("data/betting_stats.db")
                                check = conn.execute("SELECT COUNT(*) FROM historial_equipos WHERE nombre_equipo = ?", (p.get('home'),)).fetchone()[0]
                                if check == 0:
                                    st.toast(f"📥 Descargando historial para {p.get('home')}...")
                                    subprocess.run([sys.executable, "fetch_historical_soccer.py"])
                                conn.close()
                                
                                jerarquico_result = analizar_futbol_jerarquico(p.get('home'), p.get('away'))
                                heur_result = jerarquico_result 
                                st.session_state.analisis_futbol[f"{liga}_{idx}_h"] = heur_result
                                
                                # Corregir KeyError si 'recomendacion' no existe
                                recomendacion_pick = heur_result.get('recomendacion', heur_result.get('pick', 'N/A'))
                                if recomendacion_pick != 'N/A':
                                    db.guardar_backtesting("FUTBOL", f"{p.get('home')} vs {p.get('away')}", recomendacion_pick)
                                
                                if st.session_state.selected_ia_model != "Heurístico":
                                    with st.spinner(f"Consultando IA ({st.session_state.selected_ia_model})..."):
                                        analista_total = AnalistaTotal(
                                            gemini_client=st.session_state.get("gemini"),
                                            groq_client=st.session_state.get("groq"),
                                            deepseek_client=st.session_state.get("deepseek"),
                                            claude_client=st.session_state.get("claude"),
                                            new_ai_client=st.session_state.get("new_ai"),
                                            selected_model=st.session_state.selected_ia_model,
                                            conservative_mode=st.session_state.conservative_mode,
                                            token_log=st.session_state.token_log,
                                            token_alert_threshold=st.session_state.token_alert_threshold,
                                        )
                                        ia_result = analista_total.analizar_futbol(p, heur_result, jerarquico_result)
                                        st.session_state.analisis_futbol[f"{liga}_{idx}_ia"] = ia_result
                                else:
                                    st.session_state.analisis_futbol[f"{liga}_{idx}_ia"] = None
                                st.rerun()
                    except Exception as e: 
                        logger.error(f"Error renderizando Fútbol partido {idx} de {liga}: {e}")
                    st.markdown("---")
    else: 
        st.info("👈 Carga ligas de fútbol desde el panel de control.")