# -*- coding: utf-8 -*-
"""VISUAL MLB - NEON V24 COMPLETO (K + WHIP + O/U + HR)"""
import streamlit as st
import os
from datetime import datetime
from motors.mlb_stats_api import obtener_whip_cacheado
from utils.mapeo_equipos import traducir_equipo, obtener_abreviatura
from motors.motor_lanzadores import obtener_analisis_lanzadores
try:
    from decision_k import decidir_apuesta_k
except ImportError:
    def decidir_apuesta_k(pitcher_name, proy_k, linea_casa=4.5):
        return {"recomendacion": "N/A", "valor": False}
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
        away_rec = p.get("visit_record") or p.get("away_record") or p.get("visitante_record", "0-0")
        home_rec = p.get("local_record") or p.get("home_record", "0-0")

        # ── Forma reciente: racha (verde Ganó / rojo Perdió) + carreras/juego ──
        # Contexto que ahora SÍ pesa en el moneyline (racha) y da visión del equipo.
        def _forma_mlb_html(streak_str, team):
            partes = []
            try:
                from motors.motor_mlb_pro import _parse_streak
                n = _parse_streak(streak_str)
            except Exception:
                n = 0
            if n != 0:
                col = "#22c55e" if n > 0 else "#ef4444"
                ico = "🔥" if n >= 3 else ("✅" if n > 0 else ("❄️" if n <= -3 else "🔻"))
                partes.append(f"<span style='color:{col};font-weight:700'>{ico} "
                              f"{'Ganó' if n > 0 else 'Perdió'} {abs(n)}</span>")
            try:
                from motors.motor_over_under import MotorOverUnder
                rpg = MotorOverUnder.TEAM_RUNS_AVG.get(team)
                if rpg:
                    partes.append(f"<span style='color:#94a3b8'>{rpg} C/juego</span>")
            except Exception:
                pass
            return (f"<p style='font-size:11px;margin:2px 0'>{' · '.join(partes)}</p>"
                    if partes else "")

        away_forma = _forma_mlb_html(p.get("visitante_streak", ""), away)
        home_forma = _forma_mlb_html(p.get("local_streak", ""), home)
        odds = p.get("odds", {})
        a_odds = odds.get("moneyline", {}).get("visitante") or odds.get("moneyline", {}).get("away", "N/A")
        h_odds = odds.get("moneyline", {}).get("local") or odds.get("moneyline", {}).get("home", "N/A")
        # Si no hay momio, mostrar "—" en vez de "N/A"/None (no romper el layout)
        a_odds = "—" if a_odds in (None, "", "N/A", "None") else a_odds
        h_odds = "—" if h_odds in (None, "", "N/A", "None") else h_odds
        ou = odds.get("over_under", "N/A")
        _hora_utc = p.get("hora") or p.get("time", "")
        # Convertir hora UTC → CDMX (America/Mexico_City)
        def _a_cdmx(h_utc):
            try:
                from datetime import datetime, timezone, timedelta
                from zoneinfo import ZoneInfo
                today = datetime.now(timezone.utc).date()
                dt_utc = datetime.strptime(f"{today} {h_utc}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                return dt_utc.astimezone(ZoneInfo("America/Mexico_City")).strftime("%H:%M CDMX")
            except Exception:
                return h_utc or "TBD"
        time = _a_cdmx(_hora_utc) if _hora_utc else "TBD"
        venue = p.get("venue", "TBD")
        pit = p.get("pitchers", {})
        game_pk = p.get("game_pk")
        ap = pit.get("visitante", {}).get("nombre", "TBD") if isinstance(pit.get("visitante"), dict) else str(pit.get("visitante", "TBD"))
        hp = pit.get("local", {}).get("nombre", "TBD") if isinstance(pit.get("local"), dict) else str(pit.get("local", "TBD"))
        logo_v = p.get("visitante_logo", "")
        logo_l = p.get("local_logo", "")
        img_v = f'<img src="{logo_v}" width="45" style="margin-bottom:6px;">' if logo_v else ""
        img_l = f'<img src="{logo_l}" width="45" style="margin-bottom:6px;">' if logo_l else ""
        
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
        <div style="text-align:center;width:42%">{img_v}<h2 style="color:#fff;margin:0;">{away}</h2><p style="color:#ff6600; font-weight:bold;">{away_rec}</p>{away_forma}<div style="display:inline-block;margin:2px 0;padding:2px 12px;border-radius:14px;background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.45)"><span style="color:#3b82f6;font-weight:800;">🎲 {a_odds}</span></div><p style="color:#94a3b8;font-size:14px;">🥎 <b>{ap} ({hand_away})</b></p><p style="color:{"#fbbf24" if mock_away else "#00ff41"};font-size:11px">⚡ K/9: {k9_away} | Proy: {k_proy_away}K {"⚠️" if mock_away else ""}</p></div>
        <div style="text-align:center;width:16%"><h1 style="color:#e94560; margin:0;">VS</h1><p style="color:#94a3b8;">🕐 <b>{time}</b></p><p style="color:#3b82f6;">📊 O/U: {ou}</p></div>
        <div style="text-align:center;width:42%">{img_l}<h2 style="color:#fff;margin:0;">{home}</h2><p style="color:#ff6600; font-weight:bold;">{home_rec}</p>{home_forma}<div style="display:inline-block;margin:2px 0;padding:2px 12px;border-radius:14px;background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.45)"><span style="color:#3b82f6;font-weight:800;">🎲 {h_odds}</span></div><p style="color:#94a3b8;font-size:14px;">🥎 <b>{hp} ({hand_home})</b></p><p style="color:{"#fbbf24" if mock_home else "#00ff41"};font-size:11px">⚡ K/9: {k9_home} | Proy: {k_proy_home}K {"⚠️" if mock_home else ""}</p></div>
        </div></div>""", unsafe_allow_html=True)
        
        if mock_away or mock_home:
            st.metric(f"🥎 {hp}", f"{k_proy_home} K", delta=f"{k9_home} K/9")

        # ── Resultado del análisis previo ────────────────────────────────────
        if analisis_mlb:
            pick_r = analisis_mlb.get("pick") or analisis_mlb.get("recomendacion", "")
            conf_r = analisis_mlb.get("confianza", 0)
            stake_r = analisis_mlb.get("stake", "")
            razon_r = analisis_mlb.get("razon", "")
            mercado_r = analisis_mlb.get("mercado", "")
            err_r = analisis_mlb.get("error", "")
            if err_r and pick_r in (None, "", "N/A"):
                st.warning(f"⚠️ Motor: {err_r[:100]}")
            elif pick_r and pick_r != "N/A":
                color = "#22c55e" if conf_r >= 65 else "#f59e0b" if conf_r >= 50 else "#ef4444"
                label = f"{'📊 HEURÍSTICO' if not mercado_r else '🤖 IA'}"
                st.markdown(
                    f"<div style='background:#1e293b;border-radius:10px;padding:14px;margin:8px 0'>"
                    f"<div style='color:#94a3b8;font-size:0.75rem'>{label}</div>"
                    f"<div style='color:{color};font-size:1.3rem;font-weight:700'>🎯 {pick_r}</div>"
                    f"<div style='color:#fff;font-size:0.85rem'>"
                    f"Confianza: <b>{conf_r}%</b>  ·  Stake: <b>{stake_r}</b>"
                    f"{'  ·  Mercado: <b>' + mercado_r + '</b>' if mercado_r else ''}"
                    f"</div>"
                    f"{'<div style=color:#94a3b8;font-size:0.8rem;margin-top:6px>' + razon_r + '</div>' if razon_r else ''}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # ── 🏆 MEJOR APUESTA del partido (mejor mercado ponderado por histórico) ──
            ma = analisis_mlb.get("mejor_apuesta")
            if ma:
                st.markdown(
                    "<div style='background:linear-gradient(90deg,#0ea5e922,transparent);"
                    "border-left:4px solid #0ea5e9;border-radius:8px;padding:10px 14px;margin:6px 0'>"
                    f"<span style='color:#38bdf8;font-weight:800;font-size:1.02rem'>🏆 MEJOR APUESTA: {ma['pick']}</span>"
                    f"<span style='color:#cbd5e1;font-size:0.82rem'>  ·  {ma['mercado']} · conf {ma['confianza']:.0f}%</span></div>",
                    unsafe_allow_html=True)
                _alts = ma.get("alternativas", [])[1:4]
                if _alts:
                    st.caption("Alternativas: " + " · ".join(
                        f"{a['mercado']} {a['confianza']:.0f}%" for a in _alts))
                # Registrar MEJOR APUESTA en pick_memory para backtest automático
                try:
                    from motors.pick_memory import pick_memory as _pm
                    if _pm is not None:
                        _evento_str = f"{p.get('visitante','?')} @ {p.get('local','?')}"
                        _pm.registrar(
                            deporte="MLB",
                            mercado=ma.get("mercado", "MEJOR APUESTA"),
                            pick=ma["pick"],
                            confianza=ma.get("confianza", 0),
                            evento=_evento_str,
                        )
                except Exception:
                    pass
            if analisis_mlb.get("alerta_upset"):
                st.warning(f"⚠️ {analisis_mlb['alerta_upset']}")

        # ── 📊 Proyecciones del motor (O/U + Hándicap) ───────────────────────
        if analisis_mlb:
            tp = analisis_mlb.get("total_proyectado")
            oul = analisis_mlb.get("ou_linea_ajustada")
            oup = analisis_mlb.get("ou_pick")
            rl = analisis_mlb.get("run_line", {})
            cols_proj = st.columns(2)
            with cols_proj[0]:
                if tp is not None and oul:
                    flecha = "📈" if oup == "OVER" else "📉"
                    st.metric(f"{flecha} O/U carreras",
                              f"{oup} {oul}" if oup else f"línea {oul}",
                              delta=f"calculo {tp} carreras")
            with cols_proj[1]:
                if rl and rl.get("pick"):
                    # rl['pick'] ya incluye la línea (ej. "Boston Red Sox +1.5"),
                    # así que NO concatenar rl['linea'] otra vez (era "+1.5 +1.5").
                    st.metric("🎯 Hándicap (Run Line)",
                              rl['pick'],
                              delta=f"{rl.get('confianza',0)}% confianza")
                    # Alternativas analizadas (ambos lados): que se vea que comparó.
                    _alts = rl.get("alternativas", [])
                    if len(_alts) > 1:
                        st.caption("Otras líneas: " +
                                   " · ".join(f"{a['pick']} {a['prob']}%" for a in _alts[1:4]))

        # ── Estadio + factor de HR ───────────────────────────────────────────
        if venue and venue != "TBD":
            pf_txt = ""
            if all_hr_pf := (analisis_mlb.get("hr_candidates", [{}])[0].get("park_factor") if analisis_mlb and analisis_mlb.get("hr_candidates") else None):
                if all_hr_pf >= 1.05:
                    pf_txt = " · 🔥 favorece HR"
                elif all_hr_pf <= 0.95:
                    pf_txt = " · 🧊 reduce HR"
            st.caption(f"🏟️ {venue}{pf_txt}")

        # ── 💣 CANDIDATOS A HOME RUN (con barras, como el layout clásico) ────
        all_hr = []
        if analisis_mlb:
            all_hr = (analisis_mlb.get("hr_candidates")
                      or (analisis_mlb.get("hr_candidates_local", []) + analisis_mlb.get("hr_candidates_visit", [])))
        # Fallback: pedir al predictor si el análisis no trajo candidatos
        if not all_hr and game_pk:
            ph = get_predictor()
            if ph:
                try:
                    all_hr = ph.obtener_bateadores_activos(away, game_pk) + ph.obtener_bateadores_activos(home, game_pk)
                except Exception:
                    all_hr = []

        if all_hr:
            st.markdown("#### 💣 CANDIDATOS A HOME RUN")
            top_hr = sorted(all_hr, key=lambda x: x.get("probabilidad", x.get("prob", 0)), reverse=True)[:6]
            _na = (away or "").lower().strip()
            _nh = (home or "").lower().strip()
            for hr in top_hr:
                prob = hr.get("probabilidad", hr.get("prob", 0))
                nombre = hr.get("jugador", hr.get("nombre", "?"))
                equipo = hr.get("equipo", "")
                # El rival es el ABRIDOR del equipo contrario (ya cargado arriba: ap/hp)
                eq = (equipo or "").lower().strip()
                if eq == _na or eq in _na or _na in eq:
                    rival = hp        # visitante batea vs abridor local
                elif eq == _nh or eq in _nh or _nh in eq:
                    rival = ap        # local batea vs abridor visitante
                else:
                    rival = hr.get("pitcher_rival", hr.get("pitcher", ""))
                pitcher_txt = (f"vs {rival}" if rival and str(rival) not in ("TBD", "None", "")
                               else "vs abridor por confirmar")
                en_lineup = hr.get("en_lineup")
                proyectada = hr.get("lineup_proyectada")
                if en_lineup and proyectada:
                    lineup_txt = " <span style='color:#3b82f6;font-size:0.7rem'>🔵 en alineación (proyectada)</span>"
                elif en_lineup:
                    lineup_txt = " <span style='color:#22c55e;font-size:0.7rem'>✅ en alineación confirmada</span>"
                elif en_lineup is False:
                    lineup_txt = " <span style='color:#ef4444;font-size:0.7rem'>❌ fuera de la alineación</span>"
                else:
                    lineup_txt = " <span style='color:#f59e0b;font-size:0.7rem'>⚠️ alineación por confirmar</span>"
                col_hr1, col_hr2 = st.columns([3, 1])
                with col_hr1:
                    st.markdown(f"**{nombre}** <span style='color:#94a3b8;font-size:0.8rem'>({equipo})</span>"
                                + f" <span style='color:#a78bfa;font-size:0.75rem'>{pitcher_txt}</span>"
                                + lineup_txt,
                                unsafe_allow_html=True)
                    # Barra escalada al rango realista (0-22%)
                    st.progress(min(1.0, prob / 22))
                with col_hr2:
                    # Umbrales calibrados al rango real de HR (un HR/juego es raro)
                    color_hr = "#22c55e" if prob >= 14 else "#f59e0b" if prob >= 9 else "#94a3b8"
                    st.markdown(f"<div style='text-align:right;color:{color_hr};font-weight:800;font-size:1.2rem'>{prob:.0f}%</div>",
                                unsafe_allow_html=True)

        # ── 🏏 TOTAL DE BASES (Over 1.5 por bateador) ────────────────────────
        tb_picks = analisis_mlb.get("tb_picks", []) if analisis_mlb else []
        if tb_picks:
            with st.expander("🏏 Total de bases por bateador (Over/Under 1.5)", expanded=False):
                for tb in tb_picks:
                    color_tb = "#22c55e" if tb.get('prediccion') == "OVER" else "#ef4444"
                    st.markdown(
                        f"**{tb.get('jugador','?')}** "
                        f"<span style='color:#94a3b8;font-size:0.8rem'>({tb.get('equipo','')})</span> → "
                        f"<b style='color:{color_tb}'>{tb.get('pick','')}</b> "
                        f"<span style='color:#64748b;font-size:0.75rem'>{tb.get('confianza',0)}%</span>",
                        unsafe_allow_html=True)

        # ── 🎯 RUN LINE (Hándicap de carreras) ───────────────────────────────
        rl = analisis_mlb.get("run_line", {}) if analisis_mlb else {}
        if rl and rl.get("pick"):
            st.caption(f"🎯 Run Line: **{rl['pick']}** ({rl.get('confianza',0)}%)")

        # ── ⚡ PONCHES DEL LANZADOR (Over/Under) ──────────────────────────────
        k_picks = analisis_mlb.get("k_picks", []) if analisis_mlb else []
        if k_picks:
            st.markdown("#### ⚡ PONCHES DEL LANZADOR (Over/Under)")
            for kp in k_picks:
                pred = kp.get('prediccion', kp.get('pick', ''))
                color_k = "#22c55e" if pred == "OVER" else "#ef4444"
                col_k1, col_k2 = st.columns([3, 1])
                with col_k1:
                    st.markdown(
                        f"🎳 **{kp.get('pitcher', '?')}** "
                        f"<span style='color:#94a3b8;font-size:0.8rem'>(K/9: {kp.get('k9', 0)} · proy: {kp.get('proyeccion', 0)} K)</span>",
                        unsafe_allow_html=True)
                with col_k2:
                    st.markdown(
                        f"<div style='text-align:right;color:{color_k};font-weight:700'>"
                        f"{pred} {kp.get('linea', '')} <span style='color:#64748b;font-size:0.75rem'>{kp.get('confianza', 0)}%</span></div>",
                        unsafe_allow_html=True)
                # Escalera de líneas (casa la que ponga el book) + Plan B seguro
                esc = kp.get('escalera') or []
                if esc:
                    st.caption("📊 Casa tu línea: " +
                               " · ".join(f"{e['linea']}→O{e['over']}/U{e['under']}" for e in esc))
                pb = kp.get('plan_b')
                if pb:
                    st.caption(f"🛡️ Plan B (si la línea no coincide): **{pb['pick']}** ({pb['confianza']}%)")

        # ── Decisión de la IA (si se ejecutó) ────────────────────────────────
        _pick_ia = analisis_mlb.get("pick_ia") if analisis_mlb else None
        if analisis_mlb and _pick_ia and _pick_ia != "N/A":
            st.markdown(
                f"<div style='background:#1e1b4b;border-left:4px solid #818cf8;border-radius:8px;padding:10px;margin:8px 0'>"
                f"<span style='color:#a5b4fc;font-size:0.75rem'>🤖 IA</span> "
                f"<b style='color:#fff'>{_pick_ia}</b> "
                f"<span style='color:#818cf8'>({analisis_mlb.get('confianza_ia', 0)}%"
                f"{' · ' + analisis_mlb.get('mercado_ia', '') if analisis_mlb.get('mercado_ia') else ''})</span>"
                f"{'<div style=color:#94a3b8;font-size:0.78rem;margin-top:4px>' + analisis_mlb.get('razon_ia', '') + '</div>' if analisis_mlb.get('razon_ia') else ''}"
                f"</div>", unsafe_allow_html=True)
        elif analisis_mlb and analisis_mlb.get("ia_error"):
            st.warning(f"⚠️ IA: {analisis_mlb['ia_error'][:100]}")

        # ── Botones de análisis (AL FINAL, debajo de todos los datos) ────────
        st.markdown("")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_lbl = "🔄 ACTUALIZAR ANÁLISIS" if analisis_mlb else "🚀 ANALIZAR MLB"
            if st.button(btn_lbl, key=f"mlb_analizar_{idx}", use_container_width=True):
                return "analizar"
        with col_btn2:
            if st.button("➕ Agregar al Parlay", key=f"mlb_parlay_{idx}", use_container_width=True):
                st.toast("Pick MLB disponible en el tab PARLAYS", icon="🎰")

        return None
