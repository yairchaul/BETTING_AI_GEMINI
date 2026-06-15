# -*- coding: utf-8 -*-
# motors/analizar_nba_pro_v17.py

def analizar_nba_pro_v17(partido, is_back_to_back=False):
    local = partido.get('local', 'Local')
    visitante = partido.get('visitante', 'Visitante')
    local_record = partido.get('record_local', '0-0')
    visit_record = partido.get('record_visit', '0-0')
    odds = partido.get('odds', {})
    
    # Factor de cansancio (Back-to-Back)
    fatigue_penalty = 0
    if is_back_to_back:
        fatigue_penalty = 5 # Reducir confianza en 5% si es back-to-back
        # Podríamos hacer esto más sofisticado, por ejemplo, si el equipo local está en B2B y el visitante no, o viceversa.
        # Por simplicidad, aplicamos una penalización general si el partido es un B2B para cualquiera de los equipos.

    # Simulación de lógica de análisis (ejemplo básico)
    local_wins, local_losses = map(int, local_record.split('-'))
    visit_wins, visit_losses = map(int, visit_record.split('-'))

    local_win_pct = local_wins / (local_wins + local_losses) if (local_wins + local_losses) > 0 else 0.5
    visit_win_pct = visit_wins / (visit_wins + visit_losses) if (visit_wins + visit_losses) > 0 else 0.5

    if local_win_pct > visit_win_pct:
        pick = local
        confianza = int(50 + (local_win_pct - visit_win_pct) * 100) - fatigue_penalty
    else:
        pick = visitante
        confianza = int(50 + (visit_win_pct - local_win_pct) * 100) - fatigue_penalty

    # Ajustar confianza si es muy baja o muy alta
    confianza = max(40, min(90, confianza))

    # Placeholder para otros análisis (O/U, Spread)
    # En una implementación real, aquí se integrarían otros motores

    return {
        "recomendacion": f"Gana {pick}",
        "confianza": confianza,
        "pick": pick
    }