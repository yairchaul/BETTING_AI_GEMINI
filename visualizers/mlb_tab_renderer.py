# -*- coding: utf-8 -*-
"""Módulo para renderizar la pestaña de MLB con integración completa."""
import streamlit as st
from utils.analista_total import AnalistaTotal
from motors import analizar_mlb_pro_v20 as analizar_mlb
from utils.database_manager import db
import logging

logger = logging.getLogger(__name__)

def render_mlb_tab():
    """Renderiza el contenido completo de la pestaña de MLB con HR, K y O/U."""
    if st.session_state.mlb_partidos and st.session_state.visual_mlb:
        for idx, p in enumerate(st.session_state.mlb_partidos):
            res_mlb = st.session_state.analisis_mlb.get(idx)

            # AUTO-ANÁLISIS: el pick base (money line, O/U, HR, K) aparece solo,
            # sin depender del botón. El botón pasa a hacer el análisis PROFUNDO.
            if res_mlb is None:
                try:
                    res_mlb = analizar_mlb(p, game_pk=p.get('game_pk'),
                                          predictor_hr=st.session_state.get('predictor_hr'))
                    st.session_state.analisis_mlb[idx] = res_mlb
                    db.guardar_backtesting("MLB", f"{p.get('visitante','?')} @ {p.get('local','?')}",
                                           f"Gana {res_mlb.get('pick','')}")
                except Exception as _ae:
                    logger.warning(f"Auto-análisis MLB {idx}: {_ae}")

            try:
                # El visualizador unificado `VisualMLB` ahora es autocontenido y
                # obtiene los datos de HR, K, O/U, etc., por sí mismo.
                # Simplificamos la llamada para no pasar argumentos redundantes.
                accion = st.session_state.visual_mlb.render(
                    p, idx, st.session_state.tracker,
                    analisis_mlb=res_mlb
                )
                
                if accion == "analizar":
                    with st.spinner("🔄 Ejecutando análisis completo MLB (HR + K + O/U)..."):
                        # 1. Análisis heurístico base
                        heur_res = analizar_mlb(p, game_pk=p.get('game_pk'))
                        
                        # 2. Análisis de Home Runs
                        if st.session_state.hr_analyzer:
                            try:
                                from motors.predictor_hr import predictor_hr as _hr_pred
                                # Inyectar pitchers del partido actual para que el predictor sepa el rival
                                pitchers_info = p.get('pitchers', {})
                                pitcher_local_name = pitchers_info.get('local', {}).get('nombre', 'TBD')
                                pitcher_visit_name = pitchers_info.get('visitante', {}).get('nombre', 'TBD')
                                
                                # Usar analizar_partido que cruza ambos equipos y pitchers
                                all_hr = _hr_pred.analizar_partido(
                                    p.get('visitante', ''), p.get('local', ''), p.get('game_pk')
                                )
                                
                                # Separar por equipo
                                hr_local = [r for r in all_hr if r.get('equipo', '').lower() in p.get('local', '').lower() or p.get('local', '').lower() in r.get('equipo', '').lower()]
                                hr_visit = [r for r in all_hr if r.get('equipo', '').lower() in p.get('visitante', '').lower() or p.get('visitante', '').lower() in r.get('equipo', '').lower()]
                                
                                # Agregar pitcher rival manualmente si aparece "Por anunciar"
                                for h in hr_local:
                                    if h.get('pitcher_rival') in ['Por anunciar', 'TBD', 'N/A', '']:
                                        h['pitcher_rival'] = pitcher_visit_name
                                for h in hr_visit:
                                    if h.get('pitcher_rival') in ['Por anunciar', 'TBD', 'N/A', '']:
                                        h['pitcher_rival'] = pitcher_local_name
                                
                                heur_res['hr_candidates_local'] = hr_local or []
                                heur_res['hr_candidates_visit'] = hr_visit or []
                            except Exception as e:
                                logger.error(f"Error en análisis HR: {e}")
                        
                        # 3. Análisis de Strikeouts (K)
                        if st.session_state.predictor_k:
                            try:
                                # CORRECCIÓN: Usar el método correcto del predictor de ponches
                                pitcher_local = p.get('pitchers', {}).get('local', {})
                                pitcher_visitante = p.get('pitchers', {}).get('visitante', {})
                                
                                k_local = st.session_state.predictor_k.predecir_ponches_pitcher(
                                    pitcher_local.get('nombre', 'TBD'),
                                    p.get('visitante', ''),
                                    p.get('odds', {}).get('pitcher_props', {}).get(pitcher_local.get('nombre', 'TBD'), 5.5)
                                )
                                k_visit = st.session_state.predictor_k.predecir_ponches_pitcher(
                                    pitcher_visitante.get('nombre', 'TBD'),
                                    p.get('local', ''),
                                    p.get('odds', {}).get('pitcher_props', {}).get(pitcher_visitante.get('nombre', 'TBD'), 5.5)
                                )
                                heur_res['k_projection_local'] = k_local
                                heur_res['k_projection_visit'] = k_visit
                            except Exception as e:
                                logger.error(f"Error en análisis K: {e}")
                        
                        # 4. Análisis Over/Under con clima
                        if st.session_state.motor_ou and st.session_state.clima_mlb:
                            try:
                                # CORRECCIÓN: El método obtener_clima solo necesita el estadio
                                clima = st.session_state.clima_mlb.obtener_clima(
                                    p.get('venue', 'Unknown Stadium')
                                )
                                heur_res['clima'] = clima
                                
                                # CORRECCIÓN: El método correcto es calcular_total, no calcular
                                ou_analysis = st.session_state.motor_ou.calcular_total(p)
                                heur_res['over_under_analysis'] = ou_analysis
                            except Exception as e:
                                logger.error(f"Error en análisis O/U: {e}")
                        
                        # 5. Decisión inteligente (jerarquía HR > K > O/U > Moneyline)
                        if st.session_state.motor_decision:
                            try:
                                # Firma real: decidir_mejor_apuesta(partido, resultado_heuristico, candidatos_hr, clima)
                                candidatos_hr_combinados = (
                                    heur_res.get('hr_candidates_local', []) +
                                    heur_res.get('hr_candidates_visit', [])
                                )
                                decision = st.session_state.motor_decision.decidir_mejor_apuesta(
                                    p,
                                    heur_res,
                                    candidatos_hr_combinados,
                                    heur_res.get('clima', {})
                                )
                                heur_res['pick_final'] = decision
                            except Exception as e:
                                logger.error(f"Error en decisión inteligente: {e}")
                        
                        st.session_state.analisis_mlb[idx] = heur_res
                        evento_mlb = f"{p.get('visitante','?')} @ {p.get('local','?')}"
                        db.guardar_backtesting("MLB", evento_mlb, heur_res.get('pick', ''))

                        # Registrar props K al backtesting
                        for lado, pitcher_key in [('k_projection_local', 'local'), ('k_projection_visit', 'visitante')]:
                            kp = heur_res.get(lado, {})
                            if kp and kp.get('linea') and kp.get('prediccion'):
                                pitcher_nm = p.get('pitchers', {}).get(pitcher_key, {}).get('nombre', 'TBD')
                                if pitcher_nm != 'TBD':
                                    db.guardar_backtesting("MLB-K", evento_mlb,
                                        f"K {kp['prediccion']} {kp['linea']} — {pitcher_nm}")

                        # Registrar HR candidates al backtesting
                        all_hr = heur_res.get('hr_candidates_local', []) + heur_res.get('hr_candidates_visit', [])
                        for hr in all_hr:
                            if hr.get('probabilidad', 0) >= 35:
                                db.guardar_backtesting("MLB-HR", evento_mlb,
                                    f"HR+ {hr.get('jugador','?')} (prob {hr.get('probabilidad',0):.0f}%)")

                        # Registrar Over/Under al backtesting
                        ou = heur_res.get('over_under_analysis', {})
                        if ou and ou.get('pick'):
                            db.guardar_backtesting("MLB-OU", evento_mlb, f"O/U: {ou['pick']}")

                        # 6. Validación con IA (opcional)
                        if st.session_state.selected_ia_model != "Heurístico":
                            with st.spinner(f"🤖 Validando con {st.session_state.selected_ia_model}..."):
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
                                ia_res = analista_total.analizar_mlb(
                                    p, heur_res, 
                                    heur_res.get('hr_candidates_local', []) + heur_res.get('hr_candidates_visit', []),
                                    heur_res.get('clima', {}),
                                    {'local': heur_res.get('k_projection_local'), 'visit': heur_res.get('k_projection_visit')},
                                    heur_res.get('over_under_analysis')
                                )
                                st.session_state.analisis_mlb[idx] = ia_res
                        st.rerun()
            except Exception as e:
                logger.error(f"Error renderizando MLB partido {idx}: {e}")
                st.error(f"⚠️ Error en partido {idx}: {str(e)[:100]}")
            
            st.markdown("---")
    else:
        st.info("👈 Carga partidos de la MLB desde el panel de control.")
