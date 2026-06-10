# -*- coding: utf-8 -*-
def analizar_nba_pro_v17(partido):
    local = partido.get('local', 'Local')
    visitante = partido.get('visitante', 'Visitante')
    odds = partido.get('odds', {})
    record_local = partido.get('record_local', '0-0')
    record_visit = partido.get('record_visit', '0-0')
    
    def get_win_pct(record):
        try:
            wins, losses = map(int, record.split('-'))
            return wins / (wins + losses) if (wins + losses) > 0 else 0.5
        except:
            return 0.5
    
    local_wr = get_win_pct(record_local)
    visit_wr = get_win_pct(record_visit)
    
    if local_wr > visit_wr:
        ml_pick = local
        ml_conf = int(50 + (local_wr - visit_wr) * 50)
    else:
        ml_pick = visitante
        ml_conf = int(50 + (visit_wr - local_wr) * 50)
    
    total_wr = local_wr + visit_wr
    ou_line = odds.get('over_under', 225.5)
    if total_wr > 1.05:
        ou_pick = 'OVER'
        ou_conf = int(50 + (total_wr - 1.0) * 40)
    else:
        ou_pick = 'UNDER'
        ou_conf = int(50 + (1.0 - total_wr) * 40)
    
    spread = odds.get('spread', 0)
    if local_wr > visit_wr:
        spread_pick = f"{local} {spread}"
    else:
        spread_pick = f"{visitante} {spread}"
    
    return {
        'recomendacion': f"Gana {ml_pick}",
        'confianza': ml_conf,
        'moneyline': {'pick': ml_pick, 'confidence': ml_conf},
        'over_under': {'pick': ou_pick, 'line': ou_line, 'confidence': ou_conf},
        'spread': {'pick': spread_pick, 'confidence': ml_conf},
        'top_3pm_local': partido.get('top_3pm_local', {'nombre': 'N/A', 'triples_por_partido': 0}),
        'top_3pm_visit': partido.get('top_3pm_visit', {'nombre': 'N/A', 'triples_por_partido': 0}),
        'etiqueta_verde': ml_conf >= 60
    }
