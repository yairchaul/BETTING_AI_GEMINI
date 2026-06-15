# -*- coding: utf-8 -*-
def analizar_futbol(partido):
    stats_l = partido.get('stats_local')
    stats_v = partido.get('stats_visitante')
    
    if not stats_l or not stats_v:
        return {
            'recomendacion': 'Sin datos para análisis profundo',
            'confianza': 50,
            'probabilidad': 0.5
        }
    
    avg_l = stats_l.get('promedio', 0)
    avg_v = stats_v.get('promedio', 0)
    avg_scored_l = stats_l.get('promedio_anotados', avg_l) # Necesita scraper detallado
    avg_received_v = stats_v.get('promedio_recibidos', avg_v)
    
    total_goles = avg_l + avg_v
    
    # --- JERARQUÍA FÚTBOL V24 ---
    # Regla Over 2.5 ÉLITE
    if total_goles >= 3.2:
        rec = "🟢 ÉLITE: Over 2.5 Goles"
        conf = 88
    # Regla BTTS ÉLITE
    elif avg_scored_l >= 1.8 and avg_received_v >= 1.5:
        rec = "🟢 ÉLITE: Ambos Anotan (BTTS)"
        conf = 85
    elif total_goles > 2.6:
        rec = "🟡 SEGURO: Over 2.5 Goles"
        conf = 72
    elif total_goles < 2.1:
        rec = "🟡 SEGURO: Under 2.5 Goles"
        conf = 70
    else:
        rec = "🔵 RESCATE: Over 2.0 Asiático"
        conf = 58

    # Filtro de Memoria / Ganador
    vic_l = stats_l.get('victorias', 0)
    vic_v = stats_v.get('victorias', 0)
    
    if vic_l > vic_v + 1:
        if vic_l >= 4: # Racha fuerte
            rec = f"🟢 ÉLITE: Gana {partido.get('home', 'Local')}"
            conf = max(conf, 82)

    return {
        'recomendacion': rec,
        'confianza': conf,
        'goles_proyectados': round(total_goles, 2),
        'probabilidad': conf / 100
    }
