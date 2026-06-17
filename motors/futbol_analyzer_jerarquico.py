# -*- coding: utf-8 -*-
"""
ANALIZADOR JERÁRQUICO UNIFICADO — FÚTBOL V25
Soporta: ligas normales + Copa del Mundo 2026 + EURO + Copa América
Fixes v25: threshold ≥3.5, divisor dinámico, recency weighting, fase de torneo
"""

import logging
from utils.database_manager import db
from .motor_fut_pro import analizar_futbol_pro_v20

logger = logging.getLogger(__name__)

# ─── Reglas adicionales para partidos de torneo (eliminación directa) ─────────
TORNEO_BOOST = 0.95   # Los equipos se vuelven más cautelosos → ligero sesgo UNDER

# ─── Ranking FIFA aproximado jun-2026 (para fallback sin DB) ──────────────────
_FIFA_RANK = {
    "Argentina": 1, "France": 2, "England": 3, "Belgium": 4,
    "Brazil": 5, "Portugal": 6, "Netherlands": 7, "Spain": 8,
    "Croatia": 9, "Italy": 10, "USA": 11, "United States": 11,
    "Mexico": 12, "Switzerland": 13, "Uruguay": 14, "Colombia": 15,
    "Germany": 16, "Morocco": 17, "Senegal": 18, "Japan": 19,
    "South Korea": 20, "Denmark": 21, "Austria": 22, "Ecuador": 23,
    "Australia": 24, "Hungary": 25, "Poland": 26, "Serbia": 27,
    "Venezuela": 28, "Ukraine": 29, "Canada": 30, "Turkey": 31,
    "Czech Republic": 32, "Czechia": 32, "Slovakia": 33,
    "Romania": 34, "Egypt": 35, "Sweden": 36, "Algeria": 37,
    "Wales": 38, "Costa Rica": 40, "Bolivia": 45, "Paraguay": 46,
    "South Africa": 48, "Jamaica": 52, "Honduras": 55,
    "El Salvador": 60, "Panama": 65, "New Zealand": 70,
    "Guatemala": 75, "Trinidad and Tobago": 78,
}


def _analisis_ranking_fifa(local: str, visitante: str, fase: str = "") -> dict:
    """Fallback por ranking FIFA cuando no hay historial en DB (típico en el
    Mundial). Emite los MERCADOS de alta probabilidad que mejor pegan —
    'favorito anota (Over 0.5)', Over 1.5, BTTS y gana favorito— con confianza
    realista que SÍ califica para el selector de picks/parlays."""
    r_l = next((v for k, v in _FIFA_RANK.items() if k.lower() in local.lower() or local.lower() in k.lower()), 60)
    r_v = next((v for k, v in _FIFA_RANK.items() if k.lower() in visitante.lower() or visitante.lower() in k.lower()), 60)
    diff = r_v - r_l            # positivo = local mejor ranked
    abs_diff = abs(diff)
    fav = local if diff > 0 else visitante
    es_elim = bool(fase) and any(x in fase.lower() for x in ["octavo", "cuarto", "semi", "final", "round of", "quarter"])

    opciones = []
    # Mercado más seguro: el favorito marca al menos un gol (Over 0.5)
    if abs_diff >= 12:
        opciones.append({"pick": f"{fav} OVER 0.5 goles (anota)",
                         "confianza": min(82, 70 + abs_diff // 4), "regla": 1})
    # Con favorito claro suele haber goles → Over 1.5 total
    if abs_diff >= 16:
        opciones.append({"pick": "OVER 1.5 goles",
                         "confianza": min(72, 58 + abs_diff // 5), "regla": 2})
    # Partidos parejos/ofensivos → ambos anotan
    if 8 <= abs_diff <= 24:
        opciones.append({"pick": "AMBOS ANOTAN (BTTS)", "confianza": 58, "regla": 3})
    # Gana el favorito (incluye prórroga en eliminación directa)
    if abs_diff >= 20:
        opciones.append({"pick": f"Gana {fav}" + (" (incluye prórroga)" if es_elim else ""),
                         "confianza": min(70, 56 + abs_diff // 5), "regla": 4})
    # COMBINADO (mayor pago): gana favorito + Over. En mismatches grandes sigue
    # siendo alta probabilidad y paga mucho más (caso Alemania: gana + Over 3.5).
    if abs_diff >= 20:
        p_gana = min(72, 56 + abs_diff // 5)
        linea_over = "2.5" if abs_diff >= 30 else "1.5"
        p_over = min(80, (66 if linea_over == "1.5" else 58) + abs_diff // 5)
        conf_combo = round(p_gana / 100.0 * p_over / 100.0 * 100)
        cuota_combo = round((100.0 / p_gana) * (100.0 / p_over), 2)
        opciones.append({
            "pick": f"Gana {fav} + Over {linea_over}",
            "confianza": conf_combo, "regla": 7, "combo": True, "cuota": cuota_combo,
        })

    # Caso muy parejo: Over 1.5 suave
    if not opciones:
        opciones.append({"pick": "OVER 1.5 goles", "confianza": 55, "regla": 2})

    # En eliminación directa los equipos se cierran → enfría mercados de goles
    if es_elim:
        for o in opciones:
            if "OVER" in o["pick"] or "BTTS" in o["pick"]:
                o["confianza"] = max(50, o["confianza"] - 4)

    # El pick primario es el más SEGURO (mayor confianza); el combinado queda
    # disponible en todas_opciones para el selector que optimiza por pago.
    opciones.sort(key=lambda x: x["confianza"], reverse=True)
    best = opciones[0]
    return {
        "pick": best["pick"],
        "confianza": best["confianza"],
        "regla": best["regla"],
        "todas_opciones": opciones,
        "nota": f"Ranking FIFA: #{r_l} {local} vs #{r_v} {visitante} (sin historial en DB).",
    }


def _pct(lista: list, condicion) -> float:
    """Porcentaje de elementos que cumplen la condición. Devuelve 0 si lista vacía."""
    if not lista:
        return 0.0
    return sum(1 for x in lista if condicion(x)) / len(lista) * 100


def _weighted_avg(lista: list) -> float:
    """Media ponderada dando más peso a los partidos recientes."""
    if not lista:
        return 0.0
    n = len(lista)
    pesos = list(range(1, n + 1))  # 1, 2, 3 … n (más reciente = mayor peso)
    total_peso = sum(pesos)
    return sum(v * w for v, w in zip(lista, pesos)) / total_peso


def analizar_futbol_jerarquico(
    local: str,
    visitante: str,
    es_torneo: bool = False,
    fase: str = "",
) -> dict:
    """
    Aplica reglas de descarte jerárquico para fútbol.

    Args:
        local:     Nombre del equipo local
        visitante: Nombre del equipo visitante
        es_torneo: True si es torneo internacional (Mundial, EURO, Copa América…)
        fase:      Fase del torneo ('Grupo', 'Octavos', 'Cuartos', 'Semifinal', 'Final')
    """
    s_l = db.get_team_stats_detailed(local, "soccer")
    s_v = db.get_team_stats_detailed(visitante, "soccer")

    if not s_l or not s_v:
        return _analisis_ranking_fifa(local, visitante, fase)

    gl = s_l.get("goles_favor", [])
    gc = s_l.get("goles_contra", [])
    ht_l = s_l.get("goles_ht", [0] * len(gl))

    gv = s_v.get("goles_favor", [])
    gc_v = s_v.get("goles_contra", [])
    ht_v = s_v.get("goles_ht", [0] * len(gv))

    # Mínimo 2 partidos por equipo para continuar
    if len(gl) < 2 or len(gv) < 2:
        return _analisis_ranking_fifa(local, visitante, fase)

    total_partidos = len(gl) + len(gv)

    # Totales por partido (favor + contra)
    totales_l = [f + c for f, c in zip(gl, gc)]
    totales_v = [f + c for f, c in zip(gv, gc_v)]
    todos_totales = totales_l + totales_v

    # Promedio ponderado por recencia
    avg_goles_l = _weighted_avg(totales_l)
    avg_goles_v = _weighted_avg(totales_v)

    # Aplicar factor conservador en fases eliminatorias
    fase_lower = (fase or "").lower()
    es_eliminacion = es_torneo and any(
        k in fase_lower for k in ("octavo", "cuarto", "semi", "final", "round of", "quarter", "knockout")
    )
    factor_fase = TORNEO_BOOST if es_eliminacion else 1.0

    viable_picks = []

    # ── Regla 1 — OVER 1.5 HT ≥ 60% ─────────────────────────────────────────
    hits_ht = (
        sum(1 for g in ht_l if g >= 2)
        + sum(1 for g in ht_v if g >= 2)
    )
    prob_ht = (hits_ht / total_partidos) * 100 * factor_fase
    if prob_ht >= 60:
        viable_picks.append({"pick": "OVER 1.5 HT", "confianza": round(prob_ht, 1), "regla": 1})

    # ── Regla 2 — OVER 3.5 ≥ 60% (fix: >= en lugar de >) ────────────────────
    prob_o35 = _pct(todos_totales, lambda t: t >= 3.5) * factor_fase  # FIX: >= 3.5
    if prob_o35 >= 60:
        viable_picks.append({"pick": "OVER 3.5 FT", "confianza": round(prob_o35, 1), "regla": 2})

    # ── Regla 3 — BTTS ≥ 60% ─────────────────────────────────────────────────
    hits_btts = (
        sum(1 for f, c in zip(gl, gc) if f > 0 and c > 0)
        + sum(1 for f, c in zip(gv, gc_v) if f > 0 and c > 0)
    )
    prob_btts = (hits_btts / total_partidos) * 100 * factor_fase
    if prob_btts >= 60:
        viable_picks.append({"pick": "AMBOS ANOTAN (BTTS)", "confianza": round(prob_btts, 1), "regla": 3})

    # ── Regla 4 — Over más cercano al 55% ────────────────────────────────────
    p_o15 = _pct(todos_totales, lambda t: t > 1.5)
    p_o25 = _pct(todos_totales, lambda t: t > 2.5)
    p_o35_raw = _pct(todos_totales, lambda t: t >= 3.5)
    dist = {
        abs(p_o15 - 55): "OVER 1.5",
        abs(p_o25 - 55): "OVER 2.5",
        abs(p_o35_raw - 55): "OVER 3.5",
    }
    mejor_over = dist[min(dist.keys())]
    viable_picks.append({"pick": mejor_over, "confianza": 55.0, "regla": 4})

    # ── Regla 5 — Moneyline ≥ 55% ────────────────────────────────────────────
    n_l = len(gl)
    n_v = len(gv)
    vic_l = s_l.get("victorias", 0)
    vic_v = s_v.get("victorias", 0)
    prob_l = (vic_l / n_l) * 100 if n_l > 0 else 0.0   # FIX: divisor dinámico
    prob_v = (vic_v / n_v) * 100 if n_v > 0 else 0.0

    if prob_l >= 55:
        viable_picks.append({"pick": f"LOCAL ({local})", "confianza": round(prob_l, 1), "regla": 5})
    if prob_v >= 55:
        viable_picks.append({"pick": f"VISITANTE ({visitante})", "confianza": round(prob_v, 1), "regla": 5})

    # ── Regla 6 — UNDER 2.5 en partidos de eliminación directa ──────────────
    if es_eliminacion:
        p_under25 = _pct(todos_totales, lambda t: t <= 2.5)
        if p_under25 >= 60:
            viable_picks.append({
                "pick": "UNDER 2.5 (Eliminación directa)",
                "confianza": round(p_under25, 1),
                "regla": 6,
            })

    # ── Regla 7 — COMBINADO (gana + Over), mayor pago ───────────────────────
    # Si hay un favorito claro (ML) y los goles acompañan, combinar ambos.
    ml_pick = next((p for p in viable_picks if p["regla"] == 5), None)
    over_pick = next((p for p in viable_picks if p["regla"] in (1, 2, 4)
                      and "OVER" in p["pick"]), None)
    if ml_pick and over_pick and not es_eliminacion:
        equipo = ml_pick["pick"].split("(")[-1].rstrip(")") if "(" in ml_pick["pick"] else ml_pick["pick"]
        conf_combo = round(ml_pick["confianza"] / 100.0 * over_pick["confianza"] / 100.0 * 100)
        cuota_combo = round((100.0 / max(1, ml_pick["confianza"])) * (100.0 / max(1, over_pick["confianza"])), 2)
        viable_picks.append({
            "pick": f"Gana {equipo} + {over_pick['pick']}",
            "confianza": conf_combo, "regla": 7, "combo": True, "cuota": cuota_combo,
        })

    # ── Selección primaria (jerarquía: regla más baja = más prioridad) ────────
    primary = {"pick": "REVISAR DATOS", "confianza": 0.0, "regla": 99}
    if viable_picks:
        viable_picks.sort(key=lambda x: x["regla"])
        primary = viable_picks[0]

    logger.info(
        f"Análisis futbol {local} vs {visitante} → {primary['pick']} "
        f"({primary['confianza']:.1f}% Regla {primary['regla']}) "
        f"[torneo={es_torneo} fase={fase}]"
    )

    return {
        "pick":         primary["pick"],
        "confianza":    primary["confianza"],
        "regla":        primary["regla"],
        "todas_opciones": viable_picks,
        "avg_goles_local":  round(avg_goles_l, 2),
        "avg_goles_visit":  round(avg_goles_v, 2),
        "es_torneo":    es_torneo,
        "fase":         fase,
        "es_eliminacion": es_eliminacion,
    }


# ──────────────────────────────────────────────────────────────────────────
# MERCADOS COMPLETOS (para el botón "Analizar IA"): Moneyline 1X2, Over/Under,
# BTTS sí/no, y posibles goleadores. Modelo Poisson sobre goles esperados.
# ──────────────────────────────────────────────────────────────────────────
import math as _math


def _poisson(k, lam):
    try:
        return _math.exp(-lam) * (lam ** k) / _math.factorial(k)
    except Exception:
        return 0.0


def _avg(lista, default=1.2):
    return sum(lista) / len(lista) if lista else default


def mercados_completos_futbol(local, visitante, es_torneo=False, fase=""):
    """Devuelve probabilidades de Moneyline (1X2), Over/Under 2.5, BTTS sí/no
    y goleadores probables. Usa historial (DB) o ranking FIFA como respaldo."""
    s_l = db.get_team_stats_detailed(local, "soccer")
    s_v = db.get_team_stats_detailed(visitante, "soccer")

    fuente = "historial"
    if s_l and s_v and s_l.get("goles_favor") and s_v.get("goles_favor"):
        gf_l, gc_l = _avg(s_l.get("goles_favor", [])), _avg(s_l.get("goles_contra", []))
        gf_v, gc_v = _avg(s_v.get("goles_favor", [])), _avg(s_v.get("goles_contra", []))
        xg_l = max(0.2, (gf_l + gc_v) / 2 * 1.10)   # localía
        xg_v = max(0.2, (gf_v + gc_l) / 2)
    else:
        # Respaldo por ranking FIFA
        r_l = next((v for k, v in _FIFA_RANK.items() if k.lower() in local.lower() or local.lower() in k.lower()), 60)
        r_v = next((v for k, v in _FIFA_RANK.items() if k.lower() in visitante.lower() or visitante.lower() in k.lower()), 60)
        diff = (r_v - r_l) / 20.0
        xg_l = max(0.3, 1.4 + diff * 0.5)
        xg_v = max(0.3, 1.4 - diff * 0.5)
        fuente = "ranking FIFA"

    pl = [_poisson(i, xg_l) for i in range(7)]
    pv = [_poisson(j, xg_v) for j in range(7)]
    p_home = p_draw = p_away = p_over25 = p_over15 = p_btts = 0.0
    for i in range(7):
        for j in range(7):
            p = pl[i] * pv[j]
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
            if i + j > 2.5:
                p_over25 += p
            if i + j > 1.5:
                p_over15 += p
            if i > 0 and j > 0:
                p_btts += p

    _r = lambda x: round(x * 100, 1)
    # Goleadores
    try:
        from motors.futbol_props import obtener_goleadores_partido
        goleadores = obtener_goleadores_partido(local, visitante)
    except Exception:
        goleadores = {"local": [], "visitante": []}

    return {
        "fuente": fuente,
        "xg_local": round(xg_l, 2), "xg_visitante": round(xg_v, 2),
        "moneyline": {"local": _r(p_home), "empate": _r(p_draw), "visitante": _r(p_away)},
        "over_under": {"over_2.5": _r(p_over25), "under_2.5": _r(1 - p_over25),
                       "over_1.5": _r(p_over15)},
        "btts": {"si": _r(p_btts), "no": _r(1 - p_btts)},
        "goleadores": goleadores,
    }
