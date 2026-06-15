# -*- coding: utf-8 -*-
"""VISUAL MLB - NEON V24 COMPLETO (K + WHIP + O/U + HR)"""
import streamlit as st
import os
from mlb_stats_api import obtener_whip_cacheado
from mapeo_equipos import traducir_equipo, obtener_abreviatura
from motors.motor_lanzadores import obtener_analisis_lanzadores
from decision_k import decidir_apuesta_k # Este sigue en raíz
from motor_over_under import MotorOverUnder # Está en raíz según contexto
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
            import predictor_hr as phr_module
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
        from datetime import datetime
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
            # Si es rescate, usar handicap +2.5 o +3.5 para mayor seguridad
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
        game_pk = p.get("game_pk") # Obtener game_pk
        # --- Logos ---
        away_logo = p.get('visitante_logo', '')
        home_logo = p.get('local_logo', '')
        
        ap = pit.get("visitante", {}).get("nombre", "TBD") if isinstance(pit.get("visitante"), dict) else str(pit.get("visitante", "TBD"))
        hp = pit.get("local", {}).get("nombre", "TBD") if isinstance(pit.get("local"), dict) else str(pit.get("local", "TBD"))
        
        # WHIP y K proyectados
        whip_away = obtener_whip_cacheado(ap)
        whip_home = obtener_whip_cacheado(hp)
        k9_away, k_proy_away, k9_home, k_proy_home = 0, 0, 0, 0
        era_reciente_away, era_reciente_home = 0.0, 0.0
        # --- DICCIONARIO DE TENDENCIA DE PONCHES RECIBIDOS (Benchmark MLB) ---
        K_TENDENCY_RIVAL = {
            "Seattle Mariners": 27.2, "Colorado Rockies": 26.5, "Oakland Athletics": 26.9,
            "Minnesota Twins": 25.5, "Boston Red Sox": 25.2, "Houston Astros": 19.8,
            "Cleveland Guardians": 20.8, "Toronto Blue Jays": 21.8, "Atlanta Braves": 23.8
        }

        def calcular_k_value(proy, rival_name, linea):
            tendencia = K_TENDENCY_RIVAL.get(rival_name, 22.5) # 22.5 es el promedio liga
            factor = tendencia / 22.5
            ajuste_real = proy * factor
            diff = ajuste_real - float(linea)
            if diff > 1.5: return "🟢 GRAN VALOR (K-Plus)", "#00ff41"
            if diff < -1.5: return "🔴 RIESGO (K-Low)", "#ff4b4b"
            return "➡️ VALOR NEUTRAL", "#94a3b8"

        try:
            datos_k = st.session_state.get("datos_k", obtener_analisis_lanzadores()) # Cargar si no está en session_state
            st.session_state["datos_k"] = datos_k # Asegurar que esté en session_state
            
            def lookup_pitcher_data(p_name, team_name):
                if not datos_k or p_name == "TBD": return 7.5, 4.3, 4.20, "R" # Valores MLB promedio si es TBD
                
                # 1. Intento por equipo (Exacto)
                if team_name in datos_k:
                    return datos_k[team_name].get("k9", 7.5), datos_k[team_name].get("k_proyectados", 4.3), datos_k[team_name].get("era_reciente", 4.20), datos_k[team_name].get("pitch_hand", "R")
                
                # 2. Intento Fuzzy por nombre de lanzador
                if RAPIDFUZZ_OK:
                    nombres_lanzadores = {v['lanzador']: v for v in datos_k.values()}
                    match = process.extractOne(p_name, nombres_lanzadores.keys(), scorer=fuzz.WRatio)
                    if match and match[1] > 80:
                        res = nombres_lanzadores[match[0]]
                        return res.get("k9", 7.5), res.get("k_proyectados", 4.3), res.get("era_reciente", 4.20), res.get("pitch_hand", "R")
                
                return 7.5, 4.3, 4.20, "R" # Default hand if not found

            k9_away, k_proy_away, era_reciente_away, hand_away = lookup_pitcher_data(ap, away)
            k9_home, k_proy_home, era_reciente_home, hand_home = lookup_pitcher_data(hp, home)
        except:
            pass

        # --- HTML para logos con animación ---
        away_logo_html = f'<img class="animated-logo" src="{away_logo}" style="height:50px; margin-bottom:10px;" alt="{away} logo">' if away_logo else ''
        home_logo_html = f'<img class="animated-logo" src="{home_logo}" style="height:50px; margin-bottom:10px;" alt="{home} logo">' if home_logo else ''

        st.markdown(f"""
        <style>
        @keyframes fadeInSlideUp {{
            from {{ opacity: 0; transform: translateY(15px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .animated-logo {{
            animation: fadeInSlideUp 0.6s ease-out forwards;
        }}
        </style>
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding:25px; border-radius:15px; border:1px solid #334155; margin-bottom:20px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);">
        <div style="display:flex;justify-content:space-between; align-items:center;">
        <div style="text-align:center;width:42%">{away_logo_html}<h2 style="color:#fff;margin:0; font-size:1.8rem;">{away}</h2><p style="color:#ff6600; font-weight:bold; margin-bottom:5px;">{away_rec}</p><p style="color:#fbbf24; font-size:1.2rem; margin:0;">🎲 {a_odds}</p><p style="color:#94a3b8;font-size:14px; margin:5px 0;">🥎 <b>{ap} ({hand_away})</b></p><p style="color:#00ff41;font-size:11px">⚡ K/9: {k9_away} | Proy: {k_proy_away}K | WHIP: {whip_away}</p></div>
        <div style="text-align:center;width:16%"><h1 style="color:#e94560; margin:0; font-size:2.5rem; text-shadow: 0 0 10px rgba(233,69,96,0.3);">VS</h1><p style="color:#94a3b8; margin-top:5px;">🕐 <b>{time}</b></p><p style="color:#3b82f6; font-weight:bold;">📊 O/U: {ou}</p><p style="color:#64748b;font-size:11px">🏟️ {venue}</p></div>
        <div style="text-align:center;width:42%">{home_logo_html}<h2 style="color:#fff;margin:0; font-size:1.8rem;">{home}</h2><p style="color:#ff6600; font-weight:bold; margin-bottom:5px;">{home_rec}</p><p style="color:#fbbf24; font-size:1.2rem; margin:0;">🎲 {h_odds}</p><p style="color:#94a3b8;font-size:14px; margin:5px 0;">🥎 <b>{hp} ({hand_home})</b></p><p style="color:#00ff41;font-size:11px">⚡ K/9: {k9_home} | Proy: {k_proy_home}K | WHIP: {whip_home}</p></div>
        </div></div>""", unsafe_allow_html=True)
        
        # Alertas de Pitchers (ERA reciente > 5.0)
        if era_reciente_away > 5.0 or era_reciente_home > 5.0:
            alertas = []
            if era_reciente_away > 5.0:
                alertas.append(f"🚩 **{ap}** ({away}) ERA: **{era_reciente_away:.2f}** (u3 salidas)")
            if era_reciente_home > 5.0:
                alertas.append(f"🚩 **{hp}** ({home}) ERA: **{era_reciente_home:.2f}** (u3 salidas)")
            
            st.warning("⚠️ **ALERTA DE LANZADOR VULNERABLE:** " + " | ".join(alertas))

        diff, conf, pick = self._get_metricas(p)

        # Mostrar análisis si ya existe en la persistencia
        if analisis_mlb:
            # COLOR ROJO si es vulnerable o confianza reducida
            es_vulnerable = era_reciente_away > 5.0 or era_reciente_home > 5.0
            is_elite = "ÉLITE" in str(analisis_mlb.get('decision', ''))
            color_pick = "#ff4b4b" if es_vulnerable else ("#00ff41" if is_elite else "#ffcc00")
            css_class = "elite-pick-card" if is_elite else ""
            
            st.markdown(f"""<div class="{css_class}" style="background:{color_pick}15;padding:20px;border-radius:12px;border-left:6px solid {color_pick}; margin-bottom:15px;">
            <h3 style="color:{color_pick};margin:0">🎯 PICK: {analisis_mlb.get('recomendacion', 'N/A')}</h3>
            <p style="color:#94a3b8;margin:0">{analisis_mlb.get('decision', '')} · Confianza: {analisis_mlb.get('confianza', 'N/A')}% · Stake: {analisis_mlb.get('stake', '')}</p>
            <p style="color:#94a3b8;margin:0">Tipo: {analisis_mlb.get('tipo_apuesta', 'N/A')} {analisis_mlb.get('handicap', '')}</p>
            </div>""", unsafe_allow_html=True)

            # Razones del motor (transparencia del mejor pick)
            for _r in analisis_mlb.get('razones', [])[:3]:
                st.caption(f"• {_r}")

            # Mostrar O/U del motor MLB
            if analisis_mlb.get('ou_pick'):
                ou_color = "#00ff41" if analisis_mlb['ou_pick'] == "OVER" else "#ff4b4b"
                st.markdown(f"""<div style="background:{ou_color}15;padding:10px;border-radius:8px;border-left:4px solid {ou_color}; margin-top:10px;">
                <h5 style="color:{ou_color};margin:0">📊 O/U: {analisis_mlb['ou_pick']} {analisis_mlb['ou_linea_ajustada']}</h5>
                <p style="color:#94a3b8;margin:0">Confianza O/U: {analisis_mlb['ou_confianza']}%</p>
                </div>""", unsafe_allow_html=True)
        else:
            st.info(f"🏆 PICK SUGERIDO: {pick} (Confianza: {conf}%)")
        
        # 📊 OVER/UNDER CALCULADO
        try:
            mou = MotorOverUnder()
            # Pasar el partido completo para que el motor O/U pueda usar el clima
            datos_ou_motor = {"away_avg_runs": 4.5, "home_avg_runs": 4.5, "venue": venue, "ou_line": float(ou) if ou != "N/A" else 8.5, "clima": p.get("clima", {})}
            resultado_ou = mou.calcular_total(datos_ou_motor, p.get("clima", {}))
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("📊 Total Proyectado", resultado_ou['total_proyectado'])
            with col2: st.metric("🎯 Linea", ou)
            with col3:
                rec = resultado_ou['recomendacion']
                color_ou = "#10b981" if rec == "OVER" else "#ef4444"
                st.markdown(f"### <span style='color:{color_ou}'>{rec}</span>", unsafe_allow_html=True)
        except:
            resultado_ou = None
        
        # ⚡ PROYECCIÓN DE STRIKES
        st.markdown("---")
        st.subheader("⚡ PROYECCIÓN DE STRIKES (K)")
        col_k1, col_k2 = st.columns(2)
        def render_k_proyection(pitcher_name, k_proy, k9, team_name, ou_line, pitcher_original_name):
            st.markdown(f"""<div style='background:rgba(255,255,255,0.05); padding:12px; border-radius:10px; text-align:center; border: 1px solid rgba(255,255,255,0.1);'>
                <span style='color:#888; font-size:12px;'>🎯 K PROYECTADOS</span><br><b style='font-size:1.6rem; color:#fff;'>{k_proy}</b><br>
                <small style='color:#00ff41;'>K/9: {k9}</small></div>""", unsafe_allow_html=True)
            try:
                dec_k = decidir_apuesta_k(pitcher_original_name, k_proy, float(ou_line)) # Pasar el nombre original del pitcher
                k_val_txt, k_val_col = calcular_k_value(k_proy, team_name, ou_line) # Ajustar para usar k_proy y team_name
                color_k = "#00ff41" if "OVER" in dec_k['jugada'] else "#ff4b4b"
                st.markdown(f"<div style='margin-top:10px; font-size:0.95rem; text-align:center;'><span style='color:{color_k}; font-weight:bold;'>{dec_k['jugada']}</span><br><small style='color:#94a3b8;'>{dec_k.get('motivo', '')}</small></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center; border-top:1px solid #333; padding-top:5px;'><b style='color:{k_val_col}; font-size:12px;'>K-Value: {k_val_txt}</b></div>", unsafe_allow_html=True)
            except Exception as e:
                st.caption(f"Error K-Props: {e}")

        with col_k1:
            st.markdown(f"**🥎 {ap}**") # ap es el nombre del pitcher visitante
            render_k_proyection(ap, k_proy_away, k9_away, away, ou, ap) # Pasar el nombre original del pitcher
        with col_k2:
            st.markdown(f"**🥎 {hp}**") # hp es el nombre del pitcher local
            render_k_proyection(hp, k_proy_home, k9_home, home, ou, hp) # Pasar el nombre original del pitcher

        
        # Botón ANALIZAR
        col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
        with col_btn2:
            if st.button("🚀 ANALIZAR MLB", key=f"mlb_analizar_{idx}", use_container_width=True):
                return "analizar"

        # Mostrar análisis si ya existe en la persistencia
        if analisis_mlb:
            # Ya se renderizó arriba, pero si se quiere un botón para re-analizar, se puede poner aquí
            pass

        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 ANALIZAR BLINDADO", key=f"mlb_btn_{idx}", use_container_width=True):
                dec, tipo, hand, stake, color = self.clasificar_v21_dinamico(diff, conf, pick) # Aquí se usa la lógica V24
                st.session_state[f"mlb_dec_{idx}"] = dec
                st.session_state[f"mlb_color_{idx}"] = color
                st.session_state[f"mlb_stake_{idx}"] = stake
                st.session_state[f"mlb_hand_{idx}"] = hand
        
        if f"mlb_dec_{idx}" in st.session_state:
            d = st.session_state[f"mlb_dec_{idx}"]
            c = st.session_state[f"mlb_color_{idx}"]
            s = st.session_state[f"mlb_stake_{idx}"]
            h = st.session_state.get(f"mlb_hand_{idx}", "")
            if "EVITAR" in d:
                st.warning(d)
                st.caption("📊 Opciones alternativas:")
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    ou_rec = "OVER" if resultado_ou and resultado_ou.get('recomendacion') == 'OVER' else "UNDER"
                    st.info(f"📈 {ou_rec} {ou}")
                with col_a2:
                    k_rec = f"OVER {k_proy_away}K" if k_proy_away > 5.5 else f"UNDER {k_proy_away}K"
                    st.info(f"⚡ {k_rec}")
            else:
                msg = f"{d} - {pick}"
                if h: msg += f" +{h}"
                is_elite_dec = "ÉLITE" in d
                css_class_dec = "elite-pick-card" if is_elite_dec else ""
                st.markdown(f"""<div class="{css_class_dec}" style="background:{c}22;padding:20px;border-radius:12px;border-left:8px solid {c}; box-shadow: 0 4px 15px rgba(0,0,0,0.2);"><h2 style="color:{c};margin:0">{msg}</h2><p style="color:#fbbf24; font-size:1.1rem; margin-top:5px;">💰 Stake Sugerido: <b>{s}</b></p></div>""", unsafe_allow_html=True)
        
        # 🤖 ANÁLISIS IA (GEMINI CON DATOS COMPLETOS)
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🤖 ANÁLISIS IA", key=f"mlb_ia_{idx}", use_container_width=True):
                st.session_state[f"mlb_ia_click_{idx}"] = True
        
        if st.session_state.get(f"mlb_ia_click_{idx}"):
            try:
                gemini = st.session_state.get("gemini")
                if gemini:
                    with st.spinner("🤖 Consultando Gemini con datos completos..."):
                        try:
                            contexto_ia = {
                                "visitante": away, "local": home,
                                "pitcher_v": ap, "pitcher_l": hp,
                                "whip_v": whip_away, "whip_l": whip_home,
                                "k_proy_v": k_proy_away, "k_proy_l": k_proy_home,
                                "k9_v": k9_away, "k9_l": k9_home,
                                "ou_calculado": resultado_ou.get('total_proyectado', ou) if resultado_ou else ou
                            }
                            contexto_ia["clima"] = p.get("clima", {}) # Añadir datos de clima
                            resp = gemini.orquestrar_decision_final("MLB", {**p, **contexto_ia}, {"pick": pick, "confianza": conf})
                            st.markdown("### 🤖 GEMINI - ANÁLISIS COMPLETO")
                            st.info(str(resp)[:600])
                        except:
                            st.warning("Gemini no disponible")
                else:
                    st.warning("IA no disponible")
            except Exception as e:
                st.error(str(e)[:100])
        
        # 💣 CANDIDATOS HR
        st.markdown("---")
        st.subheader("💣 CANDIDATOS A HOME RUN")
        ph = get_predictor()
        if ph and game_pk: # Asegurarse de tener game_pk para el lineup
            try:
                bats_away = ph.obtener_bateadores_activos(away, game_pk)
                bats_home = ph.obtener_bateadores_activos(home, game_pk)
                for b in bats_away: b['equipo'] = away
                for b in bats_home: b['equipo'] = home
                todos = bats_away + bats_home
                todos.sort(key=lambda x: x.get('hr_total', 0), reverse=True)
                if todos:
                    for b in todos[:4]:
                        # Registro para auto-aprendizaje
                        try:
                            from database_manager import db
                            conn = sqlite3.connect(db.db_path)
                            conn.execute("INSERT OR IGNORE INTO hr_candidates_history (fecha, jugador, probabilidad, pitcher_rival) VALUES (?, ?, ?, ?)",
                                        (datetime.now().strftime("%Y-%m-%d"), b.get('nombre'), b.get('probabilidad'), hp if b.get('equipo') == away else ap))
                            conn.commit(); conn.close()
                        except: pass
                        prob = b.get('probabilidad', 0)
                        fechas = b.get('fechas_recientes', [])
                        txt_fechas = f"📅 Recientes: {', '.join(fechas)}" if fechas else "📅 Sin HR recientes registrados"

                        is_high = prob >= 35
                        card_style = "elite-pick-card" if is_high else ""
                        st.markdown(f"""
                        <div class='{card_style}' style='background: rgba(255,255,255,0.05); padding: 12px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid {"#00ff41" if is_high else "#333"};'>
                            <div style='display: flex; justify-content: space-between; align-items: center;'>
                                <div>
                                    <b style='color: {"#00ff41" if is_high else "#fff"}; font-size: 1.1rem;'>{b.get('nombre')}</b>
                                    <br><small style='color: #888;'>{b.get('equipo')} • 💣 {b.get('hr_total')} HR • vs {hp if b.get('equipo') == away else ap}</small>
                                    <br><small style='color: #64748b;'>{txt_fechas}</small>
                                </div>
                                <div style='text-align: right;'>
                                    <span style='font-size: 1.5rem; color: #fbbf24; font-weight: bold;'>{prob:.0f}%</span>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else: st.info("Sin candidatos")
            except: st.info("Predictor HR no disponible")
        
        return None
