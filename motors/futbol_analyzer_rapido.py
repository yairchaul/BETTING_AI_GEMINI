# -*- coding: utf-8 -*-
"""
MOTOR DE FÚTBOL V2 — Momentum + Estadística Directa
Motor alternativo al jerárquico (V1).

Diferencias clave vs V1:
  • Sin reglas jerárquicas: usa probabilidades directas de victoria/empate/derrota
  • Ponderación exponencial de recencia (último partido = peso 5x)
  • BTTS conservador (threshold 70% en lugar de 60%)
  • Integra H2H histórico de international_results como desempate
  • Calibrado con tasas reales del WC para partidos de torneo
  • Propone moneyline cuando la diferencia de forma es clara (> 20pp)
  • Explica detalladamente por qué cada mercado fue/no fue elegido

Se llama en paralelo con V1. Si coinciden → confianza +5pp.
Si difieren → Gemini elige.
"""
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def _exp_pesos(n: int) -> list:
    """Pesos exponenciales: partido más reciente tiene peso 2^(n-1)."""
    return [2 ** i for i in range(n)]


def _tasa_ponderada(lista_bool: list) -> float:
    """Tasa de éxito ponderada por recencia (más reciente = más peso)."""
    if not lista_bool:
        return 0.0
    pesos = _exp_pesos(len(lista_bool))
    total = sum(pesos)
    exitos = sum(p * (1 if v else 0) for p, v in zip(pesos, lista_bool))
    return exitos / total * 100


def _avg_ponderado(lista: list) -> float:
    if not lista:
        return 0.0
    pesos = _exp_pesos(len(lista))
    return sum(p * v for p, v in zip(pesos, lista)) / sum(pesos)


def analizar_futbol_rapido(
    local: str,
    visitante: str,
    es_torneo: bool = False,
    fase: str = "",
) -> dict:
    """
    Análisis V2 del partido de fútbol.

    Retorna:
        pick:          la mejor apuesta según el motor V2
        confianza:     nivel de confianza (0-100)
        mercado:       tipo de mercado elegido
        razon:         explicación de por qué se eligió este pick
        todas_opciones: todas las opciones evaluadas con su probabilidad
        debug:         dict con todas las métricas calculadas
    """
    from utils.database_manager import db
    from motors.international_results import head_to_head

    s_l = db.get_team_stats_detailed(local, "soccer")
    s_v = db.get_team_stats_detailed(visitante, "soccer")

    debug = {}
    opciones = []

    # ── A. Estadísticas de forma directa ─────────────────────────────────────
    if s_l and s_v:
        gl = s_l.get("goles_favor", [])
        gc = s_l.get("goles_contra", [])
        gv = s_v.get("goles_favor", [])
        gc_v = s_v.get("goles_contra", [])

        n_l = len(gl)
        n_v = len(gv)

        if n_l >= 2 and n_v >= 2:
            # Tasa de victoria ponderada
            vic_l_lista = [1 if (gl[i] > gc[i]) else 0 for i in range(n_l)]
            vic_v_lista = [1 if (gv[i] > gc_v[i]) else 0 for i in range(n_v)]

            prob_l = _tasa_ponderada(vic_l_lista)
            prob_v = _tasa_ponderada(vic_v_lista)
            diff_forma = prob_l - prob_v

            debug["prob_local_forma"] = round(prob_l, 1)
            debug["prob_visita_forma"] = round(prob_v, 1)
            debug["diff_forma"] = round(diff_forma, 1)

            # Goles esperados ponderados
            xg_l = _avg_ponderado(gl)
            xg_c_l = _avg_ponderado(gc)
            xg_v = _avg_ponderado(gv)
            xg_c_v = _avg_ponderado(gc_v)
            xg_total = round((xg_l + xg_c_l + xg_v + xg_c_v) / 2, 2)

            debug["xg_l"] = round(xg_l, 2)
            debug["xg_v"] = round(xg_v, 2)
            debug["xg_total"] = xg_total

            # BTTS: ambos equipos anotaron >= 70% de sus partidos
            pct_anota_l = sum(1 for g in gl if g > 0) / n_l * 100
            pct_anota_v = sum(1 for g in gv if g > 0) / n_v * 100
            btts_prob = (pct_anota_l * pct_anota_v) / 100

            debug["pct_anota_l"] = round(pct_anota_l, 1)
            debug["pct_anota_v"] = round(pct_anota_v, 1)
            debug["btts_combinado"] = round(btts_prob, 1)

            # Over/Under: % de partidos con totales
            todos = [gl[i] + gc[i] for i in range(n_l)] + [gv[i] + gc_v[i] for i in range(n_v)]
            p_over15 = sum(1 for t in todos if t > 1.5) / len(todos) * 100
            p_over25 = sum(1 for t in todos if t > 2.5) / len(todos) * 100
            p_over35 = sum(1 for t in todos if t >= 3.5) / len(todos) * 100

            debug["p_over15"] = round(p_over15, 1)
            debug["p_over25"] = round(p_over25, 1)
            debug["p_over35"] = round(p_over35, 1)

            # ── Moneyline V2: solo cuando la forma lo justifica (>20pp diferencia) ──
            if diff_forma >= 20:
                # Local claramente en mejor forma
                opciones.append({
                    "pick": f"Gana {local}",
                    "confianza": round(min(78, 50 + diff_forma * 0.8), 1),
                    "mercado": "MONEYLINE",
                    "razon": f"Local en MUCHO mejor forma: {prob_l:.0f}% vs {prob_v:.0f}% (diff {diff_forma:.0f}pp)",
                    "fuente": "forma",
                })
            elif diff_forma <= -20:
                opciones.append({
                    "pick": f"Gana {visitante}",
                    "confianza": round(min(78, 50 + abs(diff_forma) * 0.8), 1),
                    "mercado": "MONEYLINE",
                    "razon": f"Visitante en MUCHO mejor forma: {prob_v:.0f}% vs {prob_l:.0f}% (diff {abs(diff_forma):.0f}pp)",
                    "fuente": "forma",
                })

            # ── Over/Under V2: basado en xG esperado ─────────────────────────
            if xg_total >= 3.0:
                opciones.append({
                    "pick": "OVER 2.5 goles",
                    "confianza": round(min(78, 45 + (xg_total - 3.0) * 15), 1),
                    "mercado": "OVER_UNDER",
                    "razon": f"xG total esperado {xg_total:.2f} ≥ 3.0 (forma ponderada)",
                    "fuente": "xg",
                })
            elif xg_total >= 2.0:
                opciones.append({
                    "pick": "OVER 1.5 goles",
                    "confianza": round(min(78, 55 + (xg_total - 2.0) * 10), 1),
                    "mercado": "OVER_UNDER",
                    "razon": f"xG total esperado {xg_total:.2f} ≥ 2.0",
                    "fuente": "xg",
                })
            if p_over15 >= 72:
                opciones.append({
                    "pick": "OVER 1.5 goles",
                    "confianza": round(min(78, p_over15 * 0.9), 1),
                    "mercado": "OVER_UNDER",
                    "razon": f"Tasa Over 1.5 en forma: {p_over15:.0f}% (threshold 72%)",
                    "fuente": "forma",
                })

            # ── BTTS V2: threshold conservador 70% ───────────────────────────
            if btts_prob >= 70:
                opciones.append({
                    "pick": "AMBOS ANOTAN (BTTS)",
                    "confianza": round(min(75, btts_prob * 0.9), 1),
                    "mercado": "BTTS",
                    "razon": (
                        f"{local} anota en {pct_anota_l:.0f}% · "
                        f"{visitante} anota en {pct_anota_v:.0f}% · "
                        f"probabilidad combinada {btts_prob:.0f}%"
                    ),
                    "fuente": "forma",
                })

    # ── B. H2H histórico (international_results) ─────────────────────────────
    try:
        h2h = head_to_head(local, visitante, n=15, solo_wc=es_torneo)
        if h2h.get("total", 0) >= 5:
            debug["h2h_total"] = h2h["total"]
            debug["h2h_local_pct"] = h2h["pct_local"]
            debug["h2h_avg_goles"] = h2h["avg_total"]

            if h2h["pct_local"] >= 60:
                opciones.append({
                    "pick": f"Gana {local}",
                    "confianza": round(min(72, h2h["pct_local"] * 0.85), 1),
                    "mercado": "H2H",
                    "razon": (f"H2H: {local} gana {h2h['pct_local']}% en {h2h['total']} partidos"),
                    "fuente": "h2h",
                })
            elif h2h["pct_visita"] >= 60:
                opciones.append({
                    "pick": f"Gana {visitante}",
                    "confianza": round(min(72, h2h["pct_visita"] * 0.85), 1),
                    "mercado": "H2H",
                    "razon": (f"H2H: {visitante} gana {h2h['pct_visita']}% en {h2h['total']} partidos"),
                    "fuente": "h2h",
                })

            if h2h["avg_total"] >= 2.8:
                opciones.append({
                    "pick": "OVER 2.5 goles",
                    "confianza": round(min(68, h2h["avg_total"] * 18), 1),
                    "mercado": "H2H_GOLES",
                    "razon": f"H2H avg goles {h2h['avg_total']} en {h2h['total']} partidos",
                    "fuente": "h2h",
                })
    except Exception as e:
        logger.debug(f"motor_rapido H2H: {e}")

    # ── C. Calibración WC ────────────────────────────────────────────────────
    if es_torneo and opciones:
        try:
            from motors.wc_cerebro import ajustar_pick
            for op in opciones:
                nueva_conf, nota_wc = ajustar_pick(op["pick"], op["confianza"], True, fase)
                if nota_wc:
                    op["confianza"] = nueva_conf
                    op["razon"] += f" | {nota_wc}"
        except Exception as e:
            logger.debug(f"wc_cerebro en motor_rapido: {e}")

    # ── D. Fallback por ranking FIFA ─────────────────────────────────────────
    if not opciones:
        try:
            from motors.futbol_analyzer_jerarquico import _analisis_ranking_fifa
            res_rank = _analisis_ranking_fifa(local, visitante, fase)
            return {
                "pick": res_rank["pick"],
                "confianza": res_rank["confianza"],
                "mercado": "RANKING_FIFA",
                "razon": f"Fallback ranking FIFA: {res_rank.get('nota','')}",
                "todas_opciones": res_rank.get("todas_opciones", []),
                "debug": debug,
                "fuente": "ranking_fallback",
            }
        except Exception:
            return {
                "pick": "SIN DATOS", "confianza": 0,
                "mercado": "N/A", "razon": "Sin datos suficientes",
                "todas_opciones": [], "debug": debug, "fuente": "none",
            }

    # ── E. Selección: mejor opción por confianza ─────────────────────────────
    # Desempate: preferir el que tiene más fuentes de acuerdo
    firma_count = defaultdict(int)
    for op in opciones:
        firma_count[op["pick"]] += 1

    opciones.sort(key=lambda x: (firma_count[x["pick"]], x["confianza"]), reverse=True)
    best = opciones[0]

    # Boost si varios sources coinciden en el mismo pick
    n_acuerdo = firma_count[best["pick"]]
    if n_acuerdo >= 2:
        best["confianza"] = round(min(88, best["confianza"] + n_acuerdo * 2), 1)
        best["razon"] += f" [+{n_acuerdo} sources coinciden]"

    return {
        "pick":           best["pick"],
        "confianza":      best["confianza"],
        "mercado":        best["mercado"],
        "razon":          best["razon"],
        "todas_opciones": opciones,
        "debug":          debug,
        "fuente":         best.get("fuente", ""),
    }
