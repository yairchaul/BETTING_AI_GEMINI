# -*- coding: utf-8 -*-
"""VISUAL MLB - NEON V24 COMPLETO (K + WHIP + O/U + HR)"""
import streamlit as st
import os
from datetime import datetime
from mlb_stats_api import obtener_whip_cacheado
from mapeo_equipos import traducir_equipo, obtener_abreviatura
from motors.motor_lanzadores import obtener_analisis_lanzadores
from decision_k import decidir_apuesta_k
from motors.motor_over_under import MotorOverUnder
import sqlite3
import json
import importlib
try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_OK = True
except ImportError:
    RAPIDFUZZ_OK = False

_predictor_hr = None
def get_predictor(mlb_partidos_hoy=None):
    global _predictor_hr
    if _predictor_hr is None:
        try:
            from motors import predictor_hr as phr_module
            importlib.reload(phr_module)
            _predictor_hr = phr_module.PredictorHR(mlb_partidos_hoy=mlb_partidos_hoy)
            if not _predictor_hr.bateadores_stats:
                _predictor_hr.cargar_datos()
        except:
            _predictor_hr = None
    return _predictor_hr

EQUIPO_A_ABREV = {
    "Tampa Bay Rays": "TB", "Cleveland Guardians": "CLE",
    "St. Louis Cardinals": "STL", "Pittsburgh Pirates": "PIT",
    "Boston Red Sox": "BOS", "Toronto Blue Jays": "TOR",
    "Los Angeles Angels": "LAA", "Chicago White Sox": "CHW",
    "Seattle Mariners": "SEA", "Minnesota Twins": "MIN",
    "New York Yankees": "NYY", "Texas Rangers": "TEX",
    "Chicago Cubs": "CHC", "San Diego Padres": "SD",
    "Miami Marlins": "MIA", "Los Angeles Dodgers": "LAD",
    "Detroit Tigers": "DET", "Cincinnati Reds": "CIN",
}

class VisualMLB:
    def __init__(self):
        self.TRAMPAS = ["Miami Marlins", "Colorado Rockies", "Athletics"]
    
    def _abreviar(self, nombre):
        return EQUIPO_A_ABREV.get(nombre, nombre[:3].upper())
    
    def clasificar_v21_dinamico(self, diff, confianza, pick):
        import os
        equipos_trampa = ["Los Angeles Angels", "Miami Marlins", "Colorado Rockies", "Athletics"]
        try:
            if os.path.exists("data/aprendizaje_semanal.json"):
                with open("data/aprendizaje_semanal.json", "r", encoding="utf-8") as f:
                    aprend = json.load(f)
                if aprend.get("equipos_trampa"):
                    equipos_trampa = aprend["equipos_trampa"]
        except: pass
        dia_semana = datetime.now().weekday()
        factor_dia = 0.85 if dia_semana == 6 else 0.90 if dia_semana == 3 else 1.0
        
        # --- JERARQUÍA V24 con Hándicaps Dinámicos ---
        if confianza >= 80: # ÉLITE
            return "🟢 ÉLITE", "MONEYLINE", None, "3u", "#00ff41"
        elif confianza >= 65: # SEGURO
            return "🟡 SEGURO", "HANDICAP", 1.5, "2u", "#ffcc00"
        elif confianza >= 55: # RESCATE
            handicap_val = 2.5 if diff < 5 else 3.5
            return "🔵 RESCATE", "HANDICAP", handicap_val, "1u", "#3b82f6"
        else: # EVITAR
            return "🔴 EVITAR", None, None, "0u", "#ef4444"
    
    def _get_metricas(self, p, analisis_mlb=None):
        away = p.get("visitante") or p.get("away", "")
        home = p.get("local") or p.get("home", "")
        try:
            from mlb_records_real import get_diff, get_confianza, get_pick
            if away and home: return get_diff(away, home), get_confianza(away, home), get_pick(away, home)
        except: pass
        return 0, 50, home if home else "Local"
    
    def render(self, p, idx, tracker=None, analisis_mlb=None):
        away = p.get("visitante") or p.get("away", "Visitante")
        home = p.get("local") or p.get("home", "Local")
        away_rec = p.get("visit_record") or p.get("away_record", "0-0")
        home_rec = p.get("local_record") or p.get("home_record", "0-0")
        odds = p.get("odds", {})
        a_odds = odds.get("moneyline", {}).get("visitante") or odds.get("moneyline", {}).get("away", "N/A")
        h_odds = odds.get("moneyline", {}).get("local") or odds.get("moneyline", {}).get("home", "N/A")
        ou = odds.get("over_under", "N/A")
        time = p.get("hora") or p.get("time", "TBD")
        venue = p.get("venue", "TBD")
        pit = p.get("pitchers", {})
        game_pk = p.get("game_pk")
        ap = pit.get("visitante", {}).get("nombre", "TBD") if isinstance(pit.get("visitante"), dict) else str(pit.get("visitante", "TBD"))
        hp = pit.get("local", {}).get("nombre", "TBD") if isinstance(pit.get("local"), dict) else str(pit.get("local", "TBD"))
        
        whip_away = obtener_whip_cacheado(ap)
        whip_home = obtener_whip_cacheado(hp)
        k9_away, k_proy_away, k9_home, k_proy_home = 0, 0, 0, 0
        era_reciente_away, era_reciente_home = 4.20, 4.20
        hand_away, hand_home = "R", "R"
        mock_away, mock_home = True, True

        try:
            datos_k = st.session_state.get("datos_k", obtener_analisis_lanzadores())
            st.session_state["datos_k"] = datos_k
            
            def lookup_pitcher_data(p_name, team_name):
                if not datos_k or p_name == "TBD" or p_name == "None": return 7.5, 4.3, 4.20, "R", True
                if team_name in datos_k:
                    return datos_k[team_name].get("k9", 7.5), datos_k[team_name].get("k_proyectados", 4.3), datos_k[team_name].get("era_reciente", 4.20), datos_k[team_name].get("pitch_hand", "R"), False
                return 7.5, 4.3, 4.20, "R", True

            k9_away, k_proy_away, era_reciente_away, hand_away, mock_away = lookup_pitcher_data(ap, away)
            k9_home, k_proy_home, era_reciente_home, hand_home, mock_home = lookup_pitcher_data(hp, home)
        except: pass

        st.markdown(f"""<div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding:25px; border-radius:15px; border:1px solid #334155; margin-bottom:20px;">
        <div style="display:flex;justify-content:space-between; align-items:center;">
        <div style="text-align:center;width:42%"><h2 style="color:#fff;margin:0;">{away}</h2><p style="color:#ff6600; font-weight:bold;">{away_rec}</p><p style="color:#fbbf24;">🎲 {a_odds}</p><p style="color:#94a3b8;font-size:14px;">🥎 <b>{ap} ({hand_away})</b></p><p style="color:{"#fbbf24" if mock_away else "#00ff41"};font-size:11px">⚡ K/9: {k9_away} | Proy: {k_proy_away}K {"⚠️" if mock_away else ""}</p></div>
        <div style="text-align:center;width:16%"><h1 style="color:#e94560; margin:0;">VS</h1><p style="color:#94a3b8;">🕐 <b>{time}</b></p><p style="color:#3b82f6;">📊 O/U: {ou}</p></div>
        <div style="text-align:center;width:42%"><h2 style="color:#fff;margin:0;">{home}</h2><p style="color:#ff6600; font-weight:bold;">{home_rec}</p><p style="color:#fbbf24;">🎲 {h_odds}</p><p style="color:#94a3b8;font-size:14px;">🥎 <b>{hp} ({hand_home})</b></p><p style="color:{"#fbbf24" if mock_home else "#00ff41"};font-size:11px">⚡ K/9: {k9_home} | Proy: {k_proy_home}K {"⚠️" if mock_home else ""}</p></div>
        </div></div>""", unsafe_allow_html=True)
        
        if mock_away or mock_home:
            st.caption("⚠️ Algunos datos de lanzadores no se encontraron y están basados en promedios de la liga.")

            st.metric(f"🥎 {hp}", f"{k_proy_home} K", delta=f"{k9_home} K/9")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
        with col_btn2:
            if st.button("🚀 ANALIZAR MLB", key=f"mlb_analizar_{idx}", use_container_width=True):
                return "analizar"

        # 🤖 ANÁLISIS IA (Botón interno reconectado)
        if st.button("🤖 ANÁLISIS IA", key=f"mlb_ia_{idx}", use_container_width=True):
            st.session_state[f"mlb_ia_click_{idx}"] = True
        
        if st.session_state.get(f"mlb_ia_click_{idx}"):
            gemini = st.session_state.get("gemini")
            if gemini:
                with st.spinner("Consultando Gemini..."):
                    diff, conf, pick = self._get_metricas(p)
                    resp = gemini.orquestrar_decision_final("MLB", p, {"pick": pick, "confianza": conf})
                    st.info(str(resp)[:600])

        # 💣 CANDIDATOS HR
        st.subheader("💣 CANDIDATOS A HOME RUN")
        ph = get_predictor()
        if ph and game_pk:
            try:
                bats = ph.obtener_bateadores_activos(away, game_pk) + ph.obtener_bateadores_activos(home, game_pk)
                if bats:
                    for b in sorted(bats, key=lambda x: x.get('hr_total', 0), reverse=True)[:3]:
                        st.markdown(f"✅ **{b.get('nombre')}** ({b.get('hr_total')} HR) - Prob: {b.get('probabilidad')}%")
            except: st.caption("Candidatos no disponibles")
        
        return None
