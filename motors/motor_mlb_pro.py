# -*- coding: utf-8 -*-
"""MOTOR MLB PRO - V2.3 CON POWER FACTOR"""
from mlb_records_real import get_diff, get_confianza, get_pick
from .backtest_engine import backtest_engine # Importación relativa
import streamlit as st # Necesario para st.session_state (mantener aquí si es estrictamente necesario para datos_k)
from mapeo_equipos import EQUIPOS_TRAMPA # Importar la lista de equipos trampa
from database_manager import db

def calcular_power_factor(equipo, game_pk=None):
    try:
        from .predictor_hr import predictor_hr # Importación relativa
        predicciones = predictor_hr.obtener_predicciones_para_equipo(equipo, game_pk=game_pk)
        if not predicciones: return 0, 0
        poder_total = sum([p.get('probabilidad', 0) for p in predicciones]) # Suma de probabilidades de HR
        return poder_total, len(predicciones) # Retorna la suma y el número de bateadores
    except Exception as e:
        return 0, 0 # En caso de error, retorna 0

def clasificar_apuesta_v21(diff, confianza, pick, es_equipo_trampa=False, pitcher_vulnerable=False):
    """Clasifica la apuesta con jerarquía V24 y hándicaps dinámicos."""
    if es_equipo_trampa:
        return "❌ EVITAR", None, None, 0, "Equipo Trampa detectado"
    
    if confianza >= 80: # ÉLITE
        return "🟢 ÉLITE", "MONEYLINE", None, 3, "Alta Confianza"
    elif confianza >= 65: # SEGURO
        return "🟡 SEGURO", "HANDICAP", 1.5, 2, "Confianza Moderada, Handicap +1.5"
    elif confianza >= 55: # RESCATE
        return "🔵 RESCATE", "HANDICAP", 2.5, 1, "Pelea Cerrada, Handicap +2.5"
    elif pitcher_vulnerable: # Si el pitcher es vulnerable, pero la confianza no es alta, sugerir handicap
        return "🔵 RESCATE", "HANDICAP", 1.5, 1, "Pitcher vulnerable, Handicap +1.5"
    else: # EVITAR
        return "🔴 EVITAR", None, None, 0, "Baja Confianza"

def analizar_mlb_pro_v20(partido, game_pk=None): # Asegurarse de que game_pk se recibe aquí
    away = partido.get("visitante", "Visitante")
    home = partido.get("local", "Local")
    
    diff = get_diff(away, home)
    confianza_base = get_confianza(away, home)
    pick = get_pick(away, home)
    
    poder_away, _ = calcular_power_factor(away, game_pk=game_pk)
    poder_home, _ = calcular_power_factor(home, game_pk=game_pk)
    
    # --- OBTENER PESOS DINÁMICOS ---
    pesos = backtest_engine.get_pesos_actuales()
    
    # --- AJUSTE DE CONFIANZA ML POR POWER FACTOR (DINÁMICO) ---
    ajuste_poder = ((poder_home - poder_away) / 30) * pesos.get('power_factor_ml', 5)
    confianza_final = (confianza_base + ajuste_poder) if pick == home else (confianza_base - ajuste_poder)
    confianza_final = min(95, max(30, confianza_final))
    
    # --- REGLA DE LANZADOR VULNERABLE (ERA Reciente > 5.0) ---
    pitcher_vulnerable = False
    try:
        datos_k = st.session_state.get("datos_k", {})
        if datos_k:
            # Buscar pitcher del equipo pick
            pitcher_pick_name = None
            if pick == home:
                pitcher_pick_name = partido.get("pitchers", {}).get("local", {}).get("nombre")
            else:
                pitcher_pick_name = partido.get("pitchers", {}).get("visitante", {}).get("nombre")
            
            if pitcher_pick_name:
                for team_key, info in datos_k.items():
                    if info.get("lanzador", "").lower() == pitcher_pick_name.lower():
                        if info.get("era_reciente", 0.0) > 5.0: # ERA reciente alta
                            confianza_final *= pesos.get('ml_pitcher_vulnerable_penalty', 0.85) # Reducción dinámica
                            pitcher_vulnerable = True
                            break
                        # Penalización si el pitcher es novato (WHIP > 1.45)
                        if info.get("whip", 0.0) > 1.45:
                            confianza_final *= pesos.get('ml_pitcher_novato_penalty', 0.88) # Reducción dinámica
                            pitcher_vulnerable = True
                        break
    except: pass

    # --- REGLA DE APRENDIZAJE DINÁMICO ---
    # Obtener clasificación del equipo desde backtest_engine
    clasificacion_equipo = backtest_engine.get_clasificacion_equipo(pick)
    es_equipo_trampa = clasificacion_equipo['clasificacion'] == 'TRAMPA'
    es_valor_oculto = clasificacion_equipo['clasificacion'] == 'VALOR_OCULTO'

    if not es_equipo_trampa: # Solo aplicar penalización si no es ya un equipo trampa
        fallos_recientes = db.obtener_racha_fallos(pick)
        if fallos_recientes >= 3:
            confianza_final *= pesos.get('ml_racha_fallos_penalty', 0.80)  # Bajamos la confianza dinámicamente
            es_equipo_trampa = True # Marcar como trampa temporalmente
    
    if es_valor_oculto:
        confianza_final += pesos.get('ml_valor_oculto_bonus', 8) # Bonificación dinámica

    decision, tipo, handi, stake, razon_decision = clasificar_apuesta_v21(diff, confianza_final, pick, es_equipo_trampa, pitcher_vulnerable)
    
    # --- CORRELACIÓN O/U CON HR% (DINÁMICO) ---
    try:
        ou_line = float(partido.get("odds", {}).get("over_under", 8.5))
    except: ou_line = 8.5

    sum_hr_probs = poder_home + poder_away # Suma de probabilidades de HR de ambos equipos
    # Benchmark: 100 es el poder promedio esperado. 
    # Si sum_hr_probs > 100 -> OVER | Si sum_hr_probs < 100 -> UNDER
    ou_adjustment = (sum_hr_probs - 100) * pesos.get('hr_ou_impact', 0.015)
    ou_final_line = ou_line + ou_adjustment

    ou_pick = "OVER" if ou_adjustment > 0.5 else "UNDER" if ou_adjustment < -0.5 else "NEUTRAL"
    ou_conf = min(95, max(30, int(50 + abs(ou_adjustment) * 8)))

    return {
        "recomendacion": f"{decision} - {pick}" if decision != "❌ EVITAR" else "EVITAR",
        "confianza": round(confianza_final, 1),
        "pick": pick,
        "decision": decision,
        "tipo_apuesta": tipo,
        "handicap": handi,
        "stake": stake,
        "poder_home": round(poder_home, 1),
        "poder_away": round(poder_away, 1), # Corregido: coma faltante
        "ou_pick": ou_pick,
        "ou_confianza": ou_conf,
        "ou_linea_ajustada": round(ou_final_line, 1)
    }
