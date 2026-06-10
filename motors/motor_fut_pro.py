# -*- coding: utf-8 -*-
from .backtest_engine import backtest_engine # Importación relativa

def analizar_futbol_pro_v20(partido):
    home_name = partido.get('home', 'Local')
    stats_l = partido.get('stats_local')
    stats_v = partido.get('stats_visitante')
    
    if not stats_l or not stats_v:
        return {
            'recomendacion': 'Sin datos para análisis profundo',
            'confianza': 50,
            'probabilidad': 0.5
        }
    
    # 1. Obtener Aprendizaje y Pesos Dinámicos
    pesos = backtest_engine.get_pesos_actuales()
    clasif_home = backtest_engine.get_clasificacion_equipo(home_name)
    clasif_away = backtest_engine.get_clasificacion_equipo(partido.get('away', 'Visitante'))
    
    # Penalizaciones/Bonificaciones por aprendizaje
    penalty_trampa = 0.80 if (clasif_home['clasificacion'] == 'TRAMPA' or clasif_away['clasificacion'] == 'TRAMPA') else 1.0
    bonus_valor = 1.12 if (clasif_home['clasificacion'] == 'VALOR_OCULTO') else 1.0

    avg_l = stats_l.get('promedio', 0)
    avg_v = stats_v.get('promedio', 0)
    total_goles = avg_l + avg_v
    avg_scored_l = stats_l.get('promedio_anotados', avg_l)
    avg_received_v = stats_v.get('promedio_recibidos', avg_v)

    # 2. Nueva Jerarquía de Decisión (Protocolo v5.0)
    # Prioridad 1: Over 1.5 en 1er Tiempo (Basado en tendencia agresiva)
    if total_goles >= 3.5 and (avg_scored_l > 1.8 or avg_v > 1.5):
        rec = "🔥 ÉLITE: Over 1.5 Goles (1T)"
        conf = 85 * pesos.get('fut_over_impact', 1.0)
        tipo = 'OVER_HT'
    # Prioridad 2: Over 3.5 Total
    elif total_goles >= 3.8:
        rec = "⭐ SEGURO: Over 3.5 Goles"
        conf = 82 * pesos.get('fut_over_impact', 0.95)
        tipo = 'OVER_35'
    # Prioridad 3: BTTS (Ambos Anotan)
    elif avg_scored_l >= 1.8 and avg_received_v >= 1.5:
        rec = "🟢 SEGURO: Ambos Anotan (BTTS)"
        conf = 85 * pesos.get('fut_btts_impact', 1.0)
        tipo = 'BTTS'
    # Prioridad 4: Over Córners
    elif partido.get('corners_proyectados', 0) >= 10.5 and partido.get('corners_line', 0) > 0:
        rec = "🟢 SEGURO: Over Córners"
        conf = 80 * pesos.get('fut_corners_impact', 1.0)
        tipo = 'CORNERS'
    # Prioridad 5: Over 2.5 Estándar
    elif total_goles > 2.6:
        rec = "🟡 VALOR: Over 2.5 Goles"
        conf = 72 * pesos.get('fut_over_impact', 0.95)
        tipo = 'OVER_25'
    # Prioridad 6: Under 2.5
    elif total_goles < 2.1:
        rec = "️ RESCATE: Under 2.5 Goles"
        conf = 70 * pesos.get('fut_under_impact', 1.0)
        tipo = 'UNDER_25'
    else:
        rec = "🔵 RESCATE: Over 2.0 Asiático"
        conf = 58 * penalty_trampa
        tipo = 'ASIAN_OVER'

    # 3. Aplicar Aprendizaje Dinámico al Veredicto
    conf = min(95, max(30, (conf * bonus_valor) * penalty_trampa))

    vic_l = stats_l.get('victorias', 0)
    vic_v = stats_v.get('victorias', 0)
    
    # Si el mercado de goles no es claro, ir por el ganador (Prioridad 5 en Protocolo)
    if conf < 65 and vic_l > vic_v + 1:
        rec = f"🎯 GANADOR: {home_name}"
        conf = 68 * bonus_valor
        tipo = 'MONEYLINE'

    return {
        'recomendacion': rec,
        'confianza': round(conf, 1),
        'tipo_apuesta': tipo,
        'goles_proyectados': round(total_goles, 2),
        'probabilidad': round(conf / 100, 2),
        'status_aprendizaje': clasif_home['clasificacion'],
        'pesos_aplicados': pesos
    }
