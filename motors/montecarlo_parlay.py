# -*- coding: utf-8 -*-
"""
MONTE CARLO DE PARLAYS — probabilidad combinada honesta + riesgo/retorno.

Dos aportes sobre el simple "producto de probabilidades":

1) CORRELACIÓN entre legs del MISMO evento (cópula gaussiana). Cuando dos picks
   vienen del mismo partido (p.ej. "Gana X" + "Over 1.5"), están correlacionados:
   si X golea, ambos suelen pegar juntos. El producto los trata como
   independientes y SUBESTIMA la probabilidad combinada; Monte Carlo lo corrige.

2) RIESGO/RETORNO: simula apostar el parlay muchas veces para mostrar ROI medio,
   % de veces rentable y el rango P5–P95 del bankroll. Así "no perder" (pocas
   legs) vs "gran ganancia" (muchas legs) se ve con su varianza real.

Usa solo stdlib (statistics.NormalDist + random), corre en Streamlit Cloud.
"""
import random
from statistics import NormalDist

_N = NormalDist()
_RHO_MISMO_EVENTO = 0.5   # correlación entre legs del mismo partido


def prob_combinada_mc(legs, n_sims: int = 20000, rho: float = _RHO_MISMO_EVENTO) -> float:
    """Probabilidad (0-1) de que GANEN TODAS las legs, con correlación intra-evento.

    legs: lista de dicts con 'prob' (0-100) y 'evento' (para agrupar correlación).
    """
    if not legs:
        return 0.0
    # Agrupar por evento y precomputar umbrales z = Phi^-1(prob)
    grupos = {}
    for l in legs:
        p = max(0.01, min(0.99, float(l.get("prob", 50)) / 100.0))
        thr = _N.inv_cdf(p)
        grupos.setdefault(l.get("evento", id(l)), []).append(thr)

    raiz_rho = rho ** 0.5
    raiz_1mrho = (1 - rho) ** 0.5
    wins = 0
    for _ in range(n_sims):
        gana_todo = True
        for thrs in grupos.values():
            if len(thrs) == 1:
                # leg única del evento → independiente
                if _N.inv_cdf(random.random()) > thrs[0]:
                    gana_todo = False
                    break
            else:
                z_ev = _N.inv_cdf(random.random())     # factor común del partido
                for thr in thrs:
                    z = raiz_rho * z_ev + raiz_1mrho * _N.inv_cdf(random.random())
                    if z > thr:
                        gana_todo = False
                        break
            if not gana_todo:
                break
        if gana_todo:
            wins += 1
    return wins / n_sims


def simular_estrategia(prob: float, cuota: float, n_apuestas: int = 30,
                       sims: int = 5000, stake: float = 100.0) -> dict:
    """Simula apostar `n_apuestas` veces un parlay de probabilidad `prob` y
    cuota `cuota`. Devuelve ROI medio, % de escenarios rentables y rango P5-P95."""
    finales = []
    for _ in range(sims):
        bank = 0.0
        for _ in range(n_apuestas):
            if random.random() < prob:
                bank += (cuota - 1) * stake   # gana
            else:
                bank -= stake                 # pierde
        finales.append(bank)
    finales.sort()
    invertido = n_apuestas * stake
    media = sum(finales) / len(finales)
    p = lambda q: finales[min(len(finales) - 1, int(q * len(finales)))]
    return {
        "roi_medio_pct": round(media / invertido * 100, 1),
        "pct_rentable": round(sum(1 for x in finales if x > 0) / len(finales) * 100, 1),
        "p5": round(p(0.05)), "p50": round(p(0.50)), "p95": round(p(0.95)),
        "ganancia_media": round(media),
    }


if __name__ == "__main__":
    # Demo: legs independientes vs correlacionadas (mismo evento)
    indep = [{"prob": 63, "evento": f"G{i}"} for i in range(3)]
    corr = [{"prob": 63, "evento": "MISMO"} for _ in range(3)]
    import math
    print("3 legs 63% INDEP   → producto:", round(0.63 ** 3 * 100, 1),
          "% | MC:", round(prob_combinada_mc(indep) * 100, 1), "%")
    print("3 legs 63% MISMO ev → producto:", round(0.63 ** 3 * 100, 1),
          "% | MC (corr):", round(prob_combinada_mc(corr) * 100, 1), "%")
    pc = prob_combinada_mc(indep)
    cuota = (1 / 0.63) ** 3
    print("\nRiesgo/retorno 3-leg indep (cuota %.2f, 30 apuestas):" % cuota)
    print(" ", simular_estrategia(pc, cuota))
