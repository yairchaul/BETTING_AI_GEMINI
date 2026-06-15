# -*- coding: utf-8 -*-
"""MOTOR NBA PRO V18 — Ganador + Hándicap + Over/Under con EV y mejor mercado."""
import re


def _win_pct(record):
    try:
        w, l = map(int, str(record).split('-')[:2])
        return w / (w + l) if (w + l) > 0 else 0.5
    except Exception:
        return 0.5


def _streak_val(s):
    try:
        m = re.match(r'([WL])(\d+)', str(s).strip().upper())
        if m:
            n = int(m.group(2))
            return n if m.group(1) == 'W' else -n
    except Exception:
        pass
    return 0


def _prob_implicita(ml):
    try:
        v = float(str(ml).replace('+', ''))
        if v == 0:
            return None
        return 100 / (v + 100) if v > 0 else abs(v) / (abs(v) + 100)
    except Exception:
        return None


def analizar_nba_pro_v17(partido, is_back_to_back=False):
    local = partido.get('local', 'Local')
    visitante = partido.get('visitante', 'Visitante')
    odds = partido.get('odds', {}) or {}

    rec_l = partido.get('local_record') or partido.get('record_local', '0-0')
    rec_v = partido.get('visitante_record') or partido.get('record_visit', '0-0')
    wr_l = _win_pct(rec_l)
    wr_v = _win_pct(rec_v)

    st_l = _streak_val(partido.get('local_streak', ''))
    st_v = _streak_val(partido.get('visitante_streak', ''))

    # Score: récord (peso fuerte) + racha + ventaja de local
    score = (wr_l - wr_v) * 100 + (st_l - st_v) * 1.5 + 2.5
    pick_team = local if score >= 0 else visitante
    ml_conf = int(min(85, max(50, 50 + abs(score) * 0.9)))

    # ── Moneyline + EV (probabilidad real vs implícita del mercado) ──
    ml = odds.get('moneyline', {}) if isinstance(odds.get('moneyline'), dict) else {}
    ml_pick_odds = ml.get('local') if pick_team == local else ml.get('visitante')
    p_impl = _prob_implicita(ml_pick_odds)
    prob_real = ml_conf / 100
    ev = 0
    if p_impl and p_impl > 0:
        # EV% = (prob_real / prob_implícita - 1) * 100
        ev = round((prob_real / p_impl - 1) * 100, 1)

    # ── Over/Under ──
    ou_line = odds.get('overUnder') or odds.get('over_under', 225.5)
    try:
        ou_line = float(ou_line)
    except Exception:
        ou_line = 225.5
    ritmo = wr_l + wr_v  # proxy de ritmo ofensivo combinado
    # Proyección de puntos totales: línea ajustada por ritmo de ambos equipos
    total_proyectado = round(ou_line + (ritmo - 1.0) * 12, 1)
    if ritmo >= 1.10:
        ou_pick, ou_conf = 'OVER', int(min(70, 52 + (ritmo - 1.0) * 35))
    elif ritmo <= 0.90:
        ou_pick, ou_conf = 'UNDER', int(min(70, 52 + (1.0 - ritmo) * 35))
    else:
        ou_pick, ou_conf = ('OVER' if ritmo >= 1.0 else 'UNDER'), 52

    # EV del O/U con las cuotas reales de ESPN (over_odds / under_odds)
    ou_odds_pick = odds.get('over_odds') if ou_pick == 'OVER' else odds.get('under_odds')
    p_impl_ou = _prob_implicita(ou_odds_pick)
    ou_ev = round((ou_conf / 100 / p_impl_ou - 1) * 100, 1) if (p_impl_ou and p_impl_ou > 0) else 0

    # ── Hándicap (spread) ──
    spread_data = odds.get('spread', {})
    spread_val = spread_data.get('local') if isinstance(spread_data, dict) else spread_data
    if spread_val in (None, 'N/A'):
        spread_val = -4.5 if pick_team == local else 4.5
    hcap_pick = f"{pick_team} {spread_val:+g}" if isinstance(spread_val, (int, float)) else f"{pick_team} {spread_val}"
    # Si la confianza es alta, el favorito suele cubrir hándicaps cortos
    hcap_conf = int(max(50, ml_conf - 8))

    # ── Mejor mercado: el de mayor confianza ──
    mercados = [
        {'mercado': 'MONEYLINE', 'pick': f"Gana {pick_team}", 'confianza': ml_conf, 'ev': ev},
        {'mercado': 'HÁNDICAP', 'pick': hcap_pick, 'confianza': hcap_conf, 'ev': 0},
        {'mercado': 'TOTAL (O/U)', 'pick': f"{ou_pick} {ou_line}", 'confianza': ou_conf, 'ev': ou_ev},
    ]
    mejor = max(mercados, key=lambda m: m['confianza'])

    # EV global: el del mejor mercado que tenga cuota (prioriza O/U, que sí trae cuota)
    ev_global = ev
    if ev == 0 and ou_ev != 0:
        ev_global = ou_ev

    return {
        'recomendacion': f"Gana {pick_team}",
        'confianza': ml_conf,
        'ev': ev_global,
        'total_proyectado': total_proyectado,
        'moneyline': {'pick': pick_team, 'confidence': ml_conf, 'ev': ev},
        'over_under': {'pick': ou_pick, 'line': ou_line, 'confidence': ou_conf, 'ev': ou_ev},
        'spread': {'pick': hcap_pick, 'confidence': hcap_conf},
        'mercados': mercados,
        'mejor_mercado': mejor,
        'record_local': rec_l,
        'record_visit': rec_v,
        'etiqueta_verde': ml_conf >= 60,
    }
