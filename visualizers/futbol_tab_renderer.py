# -*- coding: utf-8 -*-
"""Módulo para renderizar la pestaña de Fútbol."""

import streamlit as st
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
                    key_h  = f"{liga}_{idx}_h"
                    key_ia = f"{liga}_{idx}_ia"
                    res_h  = st.session_state.analisis_futbol.get(key_h)
                    res_ia = st.session_state.analisis_futbol.get(key_ia)

                    # ── Auto-análisis heurístico (sin botón) ────────────────
                    if res_h is None:
                        try:
                            res_h = analizar_futbol_jerarquico(
                                p.get('home') or p.get('local', ''),
                                p.get('away') or p.get('visitante', ''),
                                es_torneo=p.get('es_torneo', False),
                                fase=p.get('fase', ''),
                            )
                            st.session_state.analisis_futbol[key_h] = res_h
                            pick_auto = res_h.get('pick', '')
                            if pick_auto and 'insuficiente' not in pick_auto.lower() and 'insuficiente' not in pick_auto.lower():
                                db.guardar_backtesting("FUTBOL", f"{p.get('home')} vs {p.get('away')}", pick_auto)
                        except Exception as _ae:
                            logger.warning(f"Auto-análisis fútbol falló partido {idx}: {_ae}")

                    try:
                        accion = st.session_state.visual_futbol.render(
                            p, idx, liga, st.session_state.tracker,
                            analisis_heuristico=res_h, analisis_ia=res_ia
                        )
                        if accion == "analizar":
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
                                    ia_result = analista_total.analizar_futbol(p, res_h, res_h)
                                    st.session_state.analisis_futbol[key_ia] = ia_result
                                st.rerun()
                            else:
                                st.info("Selecciona un modelo de IA en la barra lateral para análisis avanzado.")
                    except Exception as e:
                        logger.error(f"Error renderizando Fútbol partido {idx} de {liga}: {e}")
                    st.markdown("---")
    else: 
        st.info("👈 Carga ligas de fútbol desde el panel de control.")