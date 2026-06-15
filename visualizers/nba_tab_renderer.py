# -*- coding: utf-8 -*-
"""Módulo para renderizar la pestaña de NBA — incluye Props (3PM, puntos)."""

import streamlit as st
import logging

from utils.analista_total import AnalistaTotal
from motors.motor_nba_over_under import MotorNBAOverUnder
from motors import analizar_nba_pro_v17 as analizar_nba
from motors.nba_props_analyzer import nba_props_analyzer
from utils.database_manager import db

logger = logging.getLogger(__name__)


def _render_props_section(local: str, visit: str):
    """Renderiza la sección de props de jugadores bajo la tarjeta del partido."""
    props = nba_props_analyzer.analizar_props_partido(local, visit, top_n=5)

    aviso = props.get("aviso", "")
    tres_l = props.get("tres_pm_local", [])
    tres_v = props.get("tres_pm_visit", [])
    pts_l  = props.get("puntos_local", [])
    pts_v  = props.get("puntos_visit", [])

    if aviso and not (tres_l or tres_v or pts_l or pts_v):
        st.caption(f"ℹ️ {aviso}")
        return

    with st.expander("🎯 Props de Jugadores", expanded=False):
        col_l, col_v = st.columns(2)

        # ── Triples locales ───────────────────────────────────────────────────
        with col_l:
            st.markdown(f"**{local}**")
            if tres_l:
                st.markdown("*Candidatos 3PM OVER*")
                for p in tres_l:
                    color = "#22c55e" if p["prob_over"] >= 65 else "#f59e0b"
                    st.markdown(
                        f"<div style='background:#1e293b;border-radius:6px;padding:6px 10px;margin-bottom:4px'>"
                        f"<span style='color:white;font-weight:600'>{p['jugador']}</span><br>"
                        f"<span style='color:#94a3b8;font-size:0.75rem'>Prom {p['prom_3pm']:.1f} | Adj {p['adj_3pm']:.1f} | Línea {p['linea']}</span><br>"
                        f"<span style='color:{color};font-weight:700'>{p['prob_over']:.0f}% OVER</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            if pts_l:
                st.markdown("*Puntos OVER*")
                for p in pts_l[:3]:
                    st.markdown(
                        f"<div style='background:#1e293b;border-radius:6px;padding:6px 10px;margin-bottom:4px'>"
                        f"<span style='color:white;font-weight:600'>{p['jugador']}</span> — "
                        f"<span style='color:#f59e0b'>Línea {p['linea']} pts · {p['prob_over']:.0f}%</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            if not tres_l and not pts_l:
                st.caption("Sin datos de props en DB para este equipo.")

        # ── Triples visitantes ────────────────────────────────────────────────
        with col_v:
            st.markdown(f"**{visit}**")
            if tres_v:
                st.markdown("*Candidatos 3PM OVER*")
                for p in tres_v:
                    color = "#22c55e" if p["prob_over"] >= 65 else "#f59e0b"
                    st.markdown(
                        f"<div style='background:#1e293b;border-radius:6px;padding:6px 10px;margin-bottom:4px'>"
                        f"<span style='color:white;font-weight:600'>{p['jugador']}</span><br>"
                        f"<span style='color:#94a3b8;font-size:0.75rem'>Prom {p['prom_3pm']:.1f} | Adj {p['adj_3pm']:.1f} | Línea {p['linea']}</span><br>"
                        f"<span style='color:{color};font-weight:700'>{p['prob_over']:.0f}% OVER</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            if pts_v:
                st.markdown("*Puntos OVER*")
                for p in pts_v[:3]:
                    st.markdown(
                        f"<div style='background:#1e293b;border-radius:6px;padding:6px 10px;margin-bottom:4px'>"
                        f"<span style='color:white;font-weight:600'>{p['jugador']}</span> — "
                        f"<span style='color:#f59e0b'>Línea {p['linea']} pts · {p['prob_over']:.0f}%</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            if not tres_v and not pts_v:
                st.caption("Sin datos de props en DB para este equipo.")


def render_nba_tab():
    """Renderiza el contenido completo de la pestaña de NBA."""
    if not (st.session_state.nba_partidos and st.session_state.visual_nba):
        st.info("👈 Carga partidos de la NBA desde el panel de control.")
        return

    for idx, p in enumerate(st.session_state.nba_partidos):
        res_heur = st.session_state.analisis_nba.get(f"heur_{idx}")
        res_ia   = st.session_state.analisis_nba.get(f"ia_{idx}")

        try:
            # ── O/U NBA ───────────────────────────────────────────────────────
            nba_ou_prediction = None
            if st.session_state.get("motor_nba_ou"):
                ou_line = float(p.get("odds", {}).get("overUnder", 0))
                if ou_line > 0:
                    nba_ou_prediction = st.session_state.motor_nba_ou.predict_over_under({
                        "local":           p.get("local"),
                        "visitante":       p.get("visitante"),
                        "over_under_line": ou_line,
                    })

            # ── Renderizar tarjeta principal ──────────────────────────────────
            accion = st.session_state.visual_nba.render(
                p, idx, st.session_state.tracker,
                analisis_heuristico=res_heur,
                analisis_gemini=res_ia,
                nba_ou_prediction=nba_ou_prediction,
            )

            # ── Props de jugadores ────────────────────────────────────────────
            _render_props_section(p.get("local", ""), p.get("visitante", ""))

            # ── Botón ANALIZAR ────────────────────────────────────────────────
            if accion == "analizar":
                with st.spinner("Analizando NBA..."):
                    p_ajustado = p.copy()
                    p_ajustado["record_local"] = p.get("records", {}).get("local", "0-0")
                    p_ajustado["record_visit"] = p.get("records", {}).get("visitante", "0-0")

                    resultado = analizar_nba(p_ajustado)
                    st.session_state.analisis_nba[f"heur_{idx}"] = resultado
                    db.guardar_backtesting("NBA", f"{p['local']} vs {p['visitante']}", resultado["recomendacion"])

                    if st.session_state.selected_ia_model != "Heurístico":
                        with st.spinner(f"Consultando IA ({st.session_state.selected_ia_model})..."):
                            analista = AnalistaTotal(
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
                                ia_result = analista.analizar_nba(p, resultado)
                                st.session_state.analisis_nba[f"ia_{idx}"] = ia_result
                            except Exception as e:
                                logger.error(f"Fallo IA NBA: {e}")
                                st.session_state.conservative_mode = True
                                st.error("⚠️ Error de conexión. Modo ahorro de tokens activado.")
                    else:
                        st.session_state.analisis_nba[f"ia_{idx}"] = None
                    st.rerun()

        except Exception as e:
            logger.error(f"Error renderizando NBA partido {idx}: {e}")

        st.markdown("---")
