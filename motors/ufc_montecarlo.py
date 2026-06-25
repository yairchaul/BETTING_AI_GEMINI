# -*- coding: utf-8 -*-
"""
MONTE CARLO UFC — simula la pelea round-por-round miles de veces para obtener
probabilidades COHERENTES de ganador, método (KO/TKO · Sumisión · Decisión) y
totales de rounds, todo del MISMO experimento (a diferencia de las 3 heurísticas
sueltas que pueden contradecirse entre sí).

Sin dependencias nuevas (solo random/math) → compatible con el deploy de
Streamlit Cloud, igual que dixon_coles y ml_predictor.

Anclas (vienen del UFCAnalyzer ya calibrado, no se reinventan):
  • p_win_f1   : prob. de que gane el peleador 1 (modelo de score calibrado).
  • p_finish   : prob. de que la pelea termine ANTES de la decisión (1 − distancia).
  • ko_split   : entre los finales, qué fracción son KO/TKO (vs sumisión).

Lo que el MC APORTA encima de eso: el reparto de los finales por round (riesgo
por asalto constante derivado de la prob. de distancia) y, con el minuto del
final muestreado dentro del round, los totales O/U con la convención REAL del
sportsbook (la línea X.5 = el minuto 2:30 del round X+1).
"""
import math
import random

MIN_POR_ROUND = 5.0


def _hazard_por_round(p_distance: float, rounds: int) -> float:
    """Riesgo de que la pelea termine en un round dado. Se calibra para que la
    probabilidad de NO terminar en ninguno de los `rounds` iguale p_distance:
        (1 − h)^rounds = p_distance   →   h = 1 − p_distance^(1/rounds)."""
    p_distance = max(0.03, min(0.97, p_distance))
    return 1.0 - p_distance ** (1.0 / max(1, rounds))


def simular_combate(p_win_f1: float, p_finish: float, ko_split: float,
                    rounds: int = 3, n: int = 20000,
                    p_win_f1_decision: float = None, seed: int = 42) -> dict:
    """Corre n simulaciones round-por-round. Devuelve probabilidades de ganador,
    método y totales de rounds, más la duración media. Todo en una pasada."""
    rng = random.Random(seed)
    p_win_f1 = max(0.0, min(1.0, p_win_f1))
    p_finish = max(0.0, min(1.0, p_finish))
    ko_split = max(0.0, min(1.0, ko_split))
    if p_win_f1_decision is None:
        p_win_f1_decision = p_win_f1
    p_distance = 1.0 - p_finish
    h = _hazard_por_round(p_distance, rounds)

    cont = {"f1": 0, "f2": 0, "KO/TKO": 0, "Sumisión": 0, "Decisión": 0}
    minutos = []  # minuto total en que terminó cada pelea simulada

    for _ in range(n):
        terminado = False
        for r in range(1, rounds + 1):
            if rng.random() < h:                       # final en este round
                gana_f1 = rng.random() < p_win_f1      # el finalizador suele ser el ganador
                metodo = "KO/TKO" if rng.random() < ko_split else "Sumisión"
                cont["f1" if gana_f1 else "f2"] += 1
                cont[metodo] += 1
                minutos.append((r - 1) * MIN_POR_ROUND + rng.uniform(0.0, MIN_POR_ROUND))
                terminado = True
                break
        if not terminado:                              # llega a las tarjetas
            gana_f1 = rng.random() < p_win_f1_decision
            cont["f1" if gana_f1 else "f2"] += 1
            cont["Decisión"] += 1
            minutos.append(rounds * MIN_POR_ROUND)

    # Totales de rounds con la convención de sportsbook: línea X.5 = minuto 2:30
    # del round X+1 → umbral en minutos = X*5 + 2.5.
    rounds_totales = []
    for linea in (1.5, 2.5, 3.5, 4.5):
        if linea > rounds:
            continue
        umbral_min = (linea - 0.5) * MIN_POR_ROUND + 2.5   # X.5 → X*5 + 2.5
        prob_over = sum(1 for m in minutos if m > umbral_min) / n
        prob_over = round(prob_over * 100)
        pick = "OVER" if prob_over >= 50 else "UNDER"
        rounds_totales.append({
            "linea": linea, "pick": pick,
            "prob_over": prob_over,
            "confianza": max(prob_over, 100 - prob_over),
            "etiqueta": f"{pick} {linea} rounds",
        })

    metodo_probs = {
        "KO/TKO": round(cont["KO/TKO"] / n * 100),
        "Sumisión": round(cont["Sumisión"] / n * 100),
        "Decisión": round(cont["Decisión"] / n * 100),
    }
    prob_win_f1 = round(cont["f1"] / n * 100)
    return {
        "n": n,
        "prob_win_f1": prob_win_f1,
        "prob_win_f2": 100 - prob_win_f1,
        "metodo_probs": metodo_probs,
        "prob_distancia": metodo_probs["Decisión"],   # llega a decisión
        "rounds_totales": rounds_totales,
        "duracion_media_min": round(sum(minutos) / max(1, len(minutos)), 1),
    }
