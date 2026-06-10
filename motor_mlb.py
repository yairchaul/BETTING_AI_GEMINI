# -*- coding: utf-8 -*-
"""MOTOR MLB PRO - V2.3 CON POWER FACTOR"""
from mlb_records_real import get_diff, get_confianza, get_pick
from mapeo_equipos import EQUIPOS_TRAMPA # Importar la lista de equipos trampa
from database_manager import db

def calcular_power_factor(equipo):
    try:
        from predictor_hr import predictor_hr
        predicciones = predictor_hr.obtener_predicciones_para_equipo(equipo)
        if not predicciones: return 0, 0
        poder_total = sum([p['probabilidad'] for p in predicciones[:3]])
        return poder_total, len(predicciones[:3])
    except:
        return 0, 0

def clasificar_apuesta_v21(diff, confianza, pick, es_equipo_trampa=False):
    """Clasifica la apuesta con jerarquía V24 y hándicaps dinámicos."""
    if es_equipo_trampa:
        return "❌ EVITAR", None, None, 0, "Equipo Trampa"
    
    if confianza >= 80: # ÉLITE
        return "🟢 ÉLITE", "MONEYLINE", None, 3, "Alta Confianza"
    elif confianza >= 65: # SEGURO
        return "🟡 SEGURO", "HANDICAP", 1.5, 2, "Confianza Moderada, Handicap +1.5"
    elif confianza >= 55: # RESCATE
        return "🔵 RESCATE", "HANDICAP", 2.5, 1, "Pelea Cerrada, Handicap +2.5"
    else: # EVITAR
        return "🔴 EVITAR", None, None, 0, "Baja Confianza"

def analizar_mlb(partido):
    away = partido.get("visitante", "Visitante")
    home = partido.get("local", "Local")
    
    diff = get_diff(away, home)
    confianza_base = get_confianza(away, home)
    pick = get_pick(away, home)
    
    poder_away, _ = calcular_power_factor(away)
    poder_home, _ = calcular_power_factor(home)
    
    ajuste_poder = ((poder_home - poder_away) / 30) * 5
    confianza_final = (confianza_base + ajuste_poder) if pick == home else (confianza_base - ajuste_poder)
    confianza_final = min(95, max(30, confianza_final))
    
    # --- REGLA DE LANZADOR VULNERABLE (ERA Reciente > 5.0) ---
    try:
        import streamlit as st
        datos_k = st.session_state.get("datos_k", {})
        if datos_k:
            for eq_nombre, info in datos_k.items():
                if pick.lower() in eq_nombre.lower() or eq_nombre.lower() in pick.lower():
                    if info.get("era_reciente", 0.0) > 5.0:
                        confianza_final *= 0.85 # Reducción del 15%
                        break
    except: pass

    # --- REGLA DE APRENDIZAJE DINÁMICO ---
    es_equipo_trampa = pick in EQUIPOS_TRAMPA # Usar la lista importada
    if not es_equipo_trampa: # Solo aplicar penalización si no es ya un equipo trampa
        fallos_recientes = db.obtener_racha_fallos(pick)
        if fallos_recientes >= 3:
            confianza_final *= 0.80  # Bajamos un 20% la confianza
            es_equipo_trampa = True # Marcar como trampa temporalmente

    decision, tipo, handi, stake, razon_decision = clasificar_apuesta_v21(diff, confianza_final, pick, es_equipo_trampa)
    
    return {
        "recomendacion": f"{decision} - {pick}" if decision != "❌ EVITAR" else "EVITAR",
        "confianza": round(confianza_final, 1),
        "pick": pick,
        "decision": decision,
        "tipo_apuesta": tipo,
        "handicap": handi,
        "stake": stake,
        "poder_home": round(poder_home, 1),
        "poder_away": round(poder_away, 1)
    }