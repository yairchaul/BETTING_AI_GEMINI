# -*- coding: utf-8 -*-
"""Módulo para renderizar la pestaña de UFC."""

import streamlit as st
from utils.analista_total import AnalistaTotal
from utils.database_manager import db
import logging

logger = logging.getLogger(__name__)

def render_ufc_tab():
    """Renderiza el contenido completo de la pestaña de UFC."""
    if st.session_state.ufc_combates and st.session_state.visual_ufc:
        for idx, c in enumerate(st.session_state.ufc_combates):
            if idx == 0 or st.session_state.ufc_combates[idx-1].get('evento') != c.get('evento'):
                st.markdown(f"## 🥊 {c.get('evento', 'UFC EVENT')}")
            
            if isinstance(c, dict):
                p1_name = c.get('peleador1', {}).get('nombre')
                p2_name = c.get('peleador2', {}).get('nombre')

                if p1_name and p2_name:
                    # --- CORRECCIÓN: Enriquecer datos antes de renderizar CON INDICADOR DE CARGA ---
                    # Usar el scraper de stats de UFC que está en session_state
                    
                    # Crear clave única para este combate en el caché de sesión
                    fight_key = f"{p1_name}_vs_{p2_name}"
                    if 'ufc_enriched_cache' not in st.session_state:
                        st.session_state.ufc_enriched_cache = {}
                    
                    # Si ya tenemos los datos enriquecidos en caché de sesión, usarlos
                    if fight_key in st.session_state.ufc_enriched_cache:
                        p1_data, p2_data = st.session_state.ufc_enriched_cache[fight_key]
                    else:
                        p1_data = c.get('peleador1', {}).copy()
                        p2_data = c.get('peleador2', {}).copy()

                        # Enriquecer con stats de UFCStats solo si el scraper está disponible
                        ufc_scraper = st.session_state.get('ufc_scraper')
                        if ufc_scraper:
                            with st.spinner(f"🔄 Cargando stats de {p1_name} y {p2_name}..."):
                                try:
                                    p1_stats = ufc_scraper.get_fighter_stats(p1_name)
                                    p2_stats = ufc_scraper.get_fighter_stats(p2_name)
                                    if p1_stats and 'error' not in p1_stats:
                                        p1_data.update(p1_stats)
                                    if p2_stats and 'error' not in p2_stats:
                                        p2_data.update(p2_stats)
                                except Exception as _e:
                                    logger.warning(f"Scraper UFC falló: {_e}")

                        # Guardar en caché de sesión
                        st.session_state.ufc_enriched_cache[fight_key] = (p1_data, p2_data)

                    try:
                        accion = st.session_state.visual_ufc.render(
                            combate=c, 
                            idx=idx, 
                            datos_peleador1=p1_data, 
                            datos_peleador2=p2_data,
                            analisis_ufc=st.session_state.analisis_ufc.get(idx)
                        )
    
                        if accion == "analizar":
                            with st.spinner("Analizando pelea..."):
                                # El analizador también usa los datos ya cargados
                                resultado = st.session_state.ufc_analyzer.analizar_combate(p1_data, p2_data)
                                st.session_state.analisis_ufc[idx] = resultado
                                db.guardar_backtesting("UFC", f"{p1_data['nombre']} vs {p2_data['nombre']}", resultado['recomendacion'])
                                    
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
                                        try:
                                            ia_result = analista_total.analizar_ufc(c, resultado)
                                            st.session_state.analisis_ufc[idx] = ia_result
                                        except Exception as e:
                                            logger.error(f"Fallo en API de UFC detectado: {e}")
                                            st.session_state.conservative_mode = True
                                            error_message = f"Error en API ({st.session_state.selected_ia_model}): {str(e)}"
                                            st.session_state.analisis_ufc[idx] = {"error": error_message}
                                            st.error(f"⚠️ {error_message}")
                                    st.rerun()
                    except Exception as e: 
                        logger.error(f"Error renderizando UFC combate {idx}: {e}")
            st.markdown("---")
    else: 
        st.info("👈 Carga combates de UFC desde el panel de control.")