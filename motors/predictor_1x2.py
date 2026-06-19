# -*- coding: utf-8 -*-
"""
PREDICTOR 1X2 — resultado del partido de fútbol (local / empate / visitante).

Módulo INDEPENDIENTE del pick jerárquico: su única tarea es estimar el RESULTADO
del partido (incluyendo el EMPATE) con su probabilidad, para mostrarlo en una
ventana aparte y poder backtestearlo solo.

Usa el modelo Poisson de mercados_completos_futbol (xG por equipo) que ya calcula
P(local), P(empate), P(visitante). Añade la mejor DOBLE OPORTUNIDAD (1X/12/X2),
que es la apuesta más segura cuando el empate es probable.
"""
import logging

logger = logging.getLogger(__name__)


def predecir_1x2(local: str, visitante: str, es_torneo: bool = False, fase: str = "") -> dict:
    """Devuelve el resultado probable 1X2 + doble oportunidad + xG."""
    try:
        from motors.futbol_analyzer_jerarquico import mercados_completos_futbol
        m = mercados_completos_futbol(local, visitante, es_torneo=es_torneo, fase=fase)
    except Exception as e:
        logger.warning(f"1X2 sin mercados ({local} vs {visitante}): {e}")
        return {}

    ml = m.get("moneyline", {}) or {}
    p_local = float(ml.get("local", 0) or 0)
    p_empate = float(ml.get("empate", 0) or 0)
    p_visit = float(ml.get("visitante", 0) or 0)

    # Ajuste de EMPATE en torneos: el Poisson de liga subestima los empates de
    # fase de grupos (equipos cautelosos, partidos cerrados). Backtest WC: 10/25
    # fueron empates y el modelo base no marcaba ninguno. Subimos el peso del
    # empate ~35% en torneos y renormalizamos.
    if es_torneo and (p_local + p_empate + p_visit) > 0:
        p_empate *= 1.35
        s = p_local + p_empate + p_visit
        p_local, p_empate, p_visit = (p_local / s * 100, p_empate / s * 100, p_visit / s * 100)

    opciones = [
        ("LOCAL", local, p_local),
        ("EMPATE", "Empate", p_empate),
        ("VISITANTE", visitante, p_visit),
    ]
    opciones.sort(key=lambda x: x[2], reverse=True)
    mejor = opciones[0]

    # Doble oportunidad (más segura cuando hay riesgo de empate)
    do = {
        "1X (local o empate)": round(p_local + p_empate, 1),
        "12 (no empate)": round(p_local + p_visit, 1),
        "X2 (empate o visita)": round(p_empate + p_visit, 1),
    }
    mejor_do = max(do.items(), key=lambda x: x[1])

    # Confianza del resultado: si el favorito 1X2 no llega a 45%, el empate
    # pesa mucho → se sugiere la doble oportunidad como pick más fiable.
    riesgo_empate = p_empate >= 28 or mejor[2] < 45
    if riesgo_empate or mejor[2] < 45:
        sugerencia = f"Doble oportunidad {mejor_do[0]}"
    else:
        sugerencia = f"{mejor[0]} ({mejor[1]})"

    return {
        "resultado_probable": mejor[0],
        "equipo": mejor[1],
        "prob": round(mejor[2], 1),
        "prob_1x2": {"local": round(p_local, 1), "empate": round(p_empate, 1),
                     "visitante": round(p_visit, 1)},
        "doble_oportunidad": {"mercado": mejor_do[0], "prob": mejor_do[1]},
        "riesgo_empate": bool(riesgo_empate),
        "sugerencia": sugerencia,
        "xg": {"local": m.get("xg_local"), "visitante": m.get("xg_visitante")},
        "fuente": m.get("fuente", ""),
    }


if __name__ == "__main__":
    import json
    for l, v in [("Spain", "Saudi Arabia"), ("Brazil", "Morocco"), ("Mexico", "South Korea")]:
        print(l, "vs", v, "->", json.dumps(predecir_1x2(l, v, es_torneo=True), ensure_ascii=False))
