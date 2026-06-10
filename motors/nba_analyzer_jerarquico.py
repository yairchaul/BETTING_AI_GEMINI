import json
from utils.database_manager import db # Moved to utils/
from datetime import datetime, timedelta

def analizar_nba_jerarquico(partido: dict):
    """
    Aplica el análisis Lambda (Expectativa de puntos) y reglas de NBA.
    """
    local = partido.get('local')
    visitante = partido.get('visitante')

    # --- DETECCIÓN AUTOMÁTICA DE BACK-TO-BACK (Fatiga) ---
    hoy = datetime.now().date()
    ayer = (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
    
    last_l = db.get_last_game_date(local, 'nba')
    last_v = db.get_last_game_date(visitante, 'nba')
    
    # Si la fecha del último partido es igual a ayer, es B2B
    is_b2b_l = last_l and last_l.strftime("%Y-%m-%d") == ayer
    is_b2b_v = last_v and last_v.strftime("%Y-%m-%d") == ayer

    ajuste_fatiga_l = -2.5 if is_b2b_l else 0
    ajuste_fatiga_v = -2.5 if is_b2b_v else 0

    # Obtenemos promedios reales (simulado si no hay en DB según Regla 9)
    s_l = db.get_team_stats_detailed(local, 'nba')
    s_v = db.get_team_stats_detailed(visitante, 'nba')
    
    off_l, def_l = s_l.get('promedio_favor', 110), s_l.get('promedio_contra', 110)
    off_v, def_v = s_v.get('promedio_favor', 110), s_v.get('promedio_contra', 110)
    
    # Proyección Lambda
    proy_l = ((off_l + def_v) / 2) + ajuste_fatiga_l
    proy_v = ((off_v + def_l) / 2) + ajuste_fatiga_v
    diff_puntos = proy_l - proy_v
    
    # Cálculo de Confianza Base
    local_winrate = s_l.get('victorias', 2.5) / 5
    visit_winrate = s_v.get('victorias', 2.5) / 5
    confianza = 50 + (abs(diff_puntos) * 3) + (abs(local_winrate - visit_winrate) * 20)
    
    # Penalizar confianza si hay fatiga B2B
    if is_b2b_l or is_b2b_v: confianza -= 5

    return {
        "proyeccion": f"{local} {proy_l:.1f} - {visitante} {proy_v:.1f}",
        "pick_sugerido": local if diff_puntos > 0 else visitante,
        "confianza": min(92, max(52, int(confianza))),
        "lambda_diff": round(diff_puntos, 2),
        "alertas": {"b2b_local": is_b2b_l, "b2b_visit": is_b2b_v}
    }