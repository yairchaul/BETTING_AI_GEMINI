# -*- coding: utf-8 -*-
"""Módulo para renderizar la pestaña de UFC."""

import streamlit as st
from utils.analista_total import AnalistaTotal
from utils.database_manager import db
import logging

logger = logging.getLogger(__name__)


def _correr_analisis_ufc(c, p1_data, p2_data):
    """Heurístico + IA PRIMARIA (si hay modelo seleccionado). Fusiona el aviso
    de contexto (racha, cambio de peso, lesión) que la IA detecta dinámicamente."""
    resultado = st.session_state.ufc_analyzer.analizar_combate(p1_data, p2_data)
    modelo = st.session_state.get("selected_ia_model", "Heurístico")
    if modelo != "Heurístico":
        try:
            analista = AnalistaTotal(
                gemini_client=st.session_state.get("gemini"),
                groq_client=st.session_state.get("groq"),
                deepseek_client=st.session_state.get("deepseek"),
                claude_client=st.session_state.get("claude"),
                new_ai_client=st.session_state.get("new_ai"),
                selected_model=modelo,
                conservative_mode=st.session_state.get("conservative_mode", False),
                token_log=st.session_state.get("token_log", []),
                token_alert_threshold=st.session_state.get("token_alert_threshold", 5000),
            )
            ia = analista.analizar_ufc(c, resultado)
            if ia and ia.get("pick") and "error" not in ia:
                resultado["ia"] = ia
                resultado["pick_ia"] = ia.get("pick")
                resultado["confianza_ia"] = ia.get("confianza", 0)
                resultado["razon_ia"] = ia.get("razon", "")
                resultado["alerta_ia"] = ia.get("alerta", "")
                resultado["proveedor_ia"] = ia.get("proveedor", modelo)
        except Exception as e:
            logger.warning(f"IA UFC no disponible: {e}")
    try:
        db.guardar_backtesting(
            "UFC", f"{p1_data.get('nombre')} vs {p2_data.get('nombre')}",
            resultado.get("recomendacion", ""))
    except Exception:
        pass
    return resultado


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

                    # IA PRIMARIA Y AUTOMÁTICA (nada manual): analiza al cargar la
                    # cartelera. Si hay modelo IA seleccionado, Gemini manda y avisa
                    # de contexto (racha, cambio de peso). Se cachea por pelea.
                    if idx not in st.session_state.analisis_ufc:
                        _modelo = st.session_state.get("selected_ia_model", "Heurístico")
                        _spin = (f"🤖 Analizando {p1_name} vs {p2_name} con {_modelo}..."
                                 if _modelo != "Heurístico" else "Analizando pelea...")
                        with st.spinner(_spin):
                            try:
                                st.session_state.analisis_ufc[idx] = _correr_analisis_ufc(c, p1_data, p2_data)
                            except Exception as _ae:
                                logger.error(f"Auto-análisis UFC {idx}: {_ae}")

                    try:
                        accion = st.session_state.visual_ufc.render(
                            combate=c,
                            idx=idx,
                            datos_peleador1=p1_data,
                            datos_peleador2=p2_data,
                            analisis_ufc=st.session_state.analisis_ufc.get(idx)
                        )

                        # Aviso de contexto que la IA detectó (racha, peso, lesión…)
                        _res = st.session_state.analisis_ufc.get(idx) or {}
                        if _res.get("alerta_ia"):
                            st.warning(f"🔔 Aviso IA: {_res['alerta_ia']}")
                        if _res.get("pick_ia"):
                            st.info(f"🤖 {_res.get('proveedor_ia', 'IA')}: **{_res['pick_ia']}** "
                                    f"({_res.get('confianza_ia', 0)}%) — {_res.get('razon_ia', '')}")

                        if accion == "analizar":
                            # Re-analizar a demanda (fuerza nueva consulta a la IA)
                            with st.spinner("Re-analizando..."):
                                st.session_state.analisis_ufc[idx] = _correr_analisis_ufc(c, p1_data, p2_data)
                            st.rerun()
                    except Exception as e:
                        logger.error(f"Error renderizando UFC combate {idx}: {e}")
            st.markdown("---")
    else: 
        st.info("👈 Carga combates de UFC desde el panel de control.")