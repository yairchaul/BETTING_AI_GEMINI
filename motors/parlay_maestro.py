# -*- coding: utf-8 -*-
"""
PARLAY MAESTRO — optimizador EXACTO de parlays cross-deporte.

Matemática central: con legs independientes (1 por evento),
    EV + 1 = Π (p_i × cuota_i)  →  log(EV+1) = Σ log(edge_i)
donde edge_i = p_calibrada_i × cuota_i. Es ADITIVO en logs, así que el mejor
parlay de k legs es EXACTAMENTE el top-k de legs por edge — no hace falta
probar combinaciones. Sobre esa "frontera" (k = 2..8) se eligen 3 objetivos:

  • MÁS VIABLE   — la mayor probabilidad real de cobrar duplicando (cuota ≥ 2).
  • MEJOR EV     — el punto de la frontera con mayor valor esperado (>0 o nada:
                   si ningún parlay tiene EV positivo, se dice con honestidad).
  • MÁXIMO PAGO  — la cuota más alta que sigue siendo "viable" (prob ≥ piso).

Honestidad del dato (lección del 0/27 y del backtest O/U):
  • prob calibrada = mezcla del modelo con la TASA REAL del mercado
    (data/aprendizaje_mercados.json) + cap 90% (no existe el 99% seguro).
  • cuotas ESTIMADAS (no traídas de la casa) pagan un descuento del 5% en el
    edge — el mercado casi nunca regala precio.
  • la probabilidad combinada final es Monte Carlo con correlación intra-evento
    (motors.montecarlo_parlay), no un producto ingenuo.
  • stake sugerido = ¼ de Kelly (Kelly completo quiebra con probs imperfectas).

Módulo PURO: sin streamlit, testeable, usable desde la UI y desde backtests.
"""
import json
import logging
import math
import os

logger = logging.getLogger(__name__)

REALISMO_CAP = 90.0        # ninguna leg vale >90%
PRIOR_SIN_CALIBRAR = 55.0  # prior conservador para mercados sin tasa real
HAIRCUT_CUOTA_ESTIMADA = 0.95   # descuento de edge si la cuota no es real
MARGEN_MAX_SIN_CUOTA = 1.10     # sin cuota real no se asume >10% de valor por leg
PROB_PISO_PAGO = 10.0      # % mínimo de prob para el "máximo pago viable"
PROB_PISO_EV = 15.0        # % mínimo de prob para el "mejor EV"
K_MAX = 8                  # más de 8 legs es lotería, no estrategia

_TASAS_PATH = os.path.join("data", "aprendizaje_mercados.json")
_tasas_cache = None


# ──────────────────────────────────────────────────────────────────────────
# CALIBRACIÓN (única fuente de verdad — la UI delega aquí)
# ──────────────────────────────────────────────────────────────────────────

def _cargar_tasas(force=False):
    global _tasas_cache
    if _tasas_cache is None or force:
        try:
            with open(_TASAS_PATH, encoding="utf-8") as f:
                _tasas_cache = json.load(f).get("por_mercado", {})
        except Exception:
            _tasas_cache = {}
    return _tasas_cache


def _deporte_de(sport):
    s = (sport or "").upper()
    return ("MLB" if "MLB" in s else "SOCCER" if "FÚTBOL" in s or "FUTBOL" in s or "SOCCER" in s
            else "NBA" if "NBA" in s else "UFC" if "UFC" in s else "")


def rate_real_mercado(sport, mercado):
    """(win_rate, n_muestras) REALES del mercado, o (None, 0) si no hay datos."""
    t = _cargar_tasas().get(f"{_deporte_de(sport)} · {mercado}", {})
    return t.get("win_rate"), int(t.get("total", 0) or 0)


def calibrar_prob(leg) -> float:
    """Probabilidad calibrada de una leg (misma política que sacó a MLB del hoyo):
      • con tasa real del mercado → 60% tasa real + 40% modelo;
      • RUNLINE/HANDICAP ya vienen anclados al backtest en el motor → tal cual;
      • sin tasa (UFC, mercados nuevos) → 70% modelo + 30% prior conservador;
      • cap duro 90%."""
    mk = (leg.get("mercado") or "").upper()
    prob = float(leg.get("prob", 0) or 0)
    real, _n = rate_real_mercado(leg.get("sport", ""), leg.get("mercado", ""))
    if real is not None:
        p = prob * 0.4 + float(real) * 0.6
    elif "RUNLINE" in mk or "HAND" in mk:
        p = prob
    else:
        p = prob * 0.7 + PRIOR_SIN_CALIBRAR * 0.3
    return min(p, REALISMO_CAP)


def confiabilidad(leg) -> float:
    """Cuánto RESPALDO de datos reales tiene la leg (0-1): n/40 acotado.
    RUNLINE se ancla al backtest de 669 juegos → 0.8 fijo."""
    mk = (leg.get("mercado") or "").upper()
    if "RUNLINE" in mk or "HAND" in mk:
        return 0.8
    _r, n = rate_real_mercado(leg.get("sport", ""), leg.get("mercado", ""))
    return min(1.0, n / 40.0)


def cuota_efectiva(leg) -> float:
    """Cuota usable para calcular valor. Si la cuota NO viene de una casa real
    (flag cuota_real), se acota a la cuota justa implícita de la prob calibrada
    +10%: una cuota plana inventada (ej. runline 1.80 con prob 84%) fabricaba
    EVs de +1400% — la mentira exacta que nos tuvo en 0/27."""
    cuota = float(leg.get("cuota", 1.9) or 1.9)
    if leg.get("cuota_real"):
        return cuota
    p = max(calibrar_prob(leg) / 100.0, 0.01)
    return min(cuota, round((1.0 / p) * MARGEN_MAX_SIN_CUOTA, 3))


def edge_leg(leg) -> float:
    """Edge de la leg = p_cal × cuota efectiva (>1 = valor). Cuota estimada
    paga además un descuento del 5% (el mercado casi nunca regala precio)."""
    e = (calibrar_prob(leg) / 100.0) * cuota_efectiva(leg)
    if not leg.get("cuota_real"):
        e *= HAIRCUT_CUOTA_ESTIMADA
    return e


# ──────────────────────────────────────────────────────────────────────────
# PROBABILIDAD COMBINADA + KELLY
# ──────────────────────────────────────────────────────────────────────────

def _prob_combinada(legs, n_sims=6000):
    """Prob (0-1) de que ganen todas: Monte Carlo con correlación intra-evento;
    si el módulo MC no está, producto de probs calibradas."""
    try:
        from .montecarlo_parlay import prob_combinada_mc
        mc = [{"prob": calibrar_prob(l), "evento": l.get("evento", "")} for l in legs]
        return prob_combinada_mc(mc, n_sims=n_sims)
    except Exception:
        p = 1.0
        for l in legs:
            p *= max(0.01, calibrar_prob(l) / 100.0)
        return p


def kelly_fraccion(prob, cuota) -> float:
    """Fracción de Kelly (0-1) para prob (0-1) y cuota decimal. 0 si no hay valor."""
    b = cuota - 1.0
    if b <= 0:
        return 0.0
    f = (prob * cuota - 1.0) / b
    return max(0.0, f)


def _parlay_dict(legs, objetivo, n_sims=6000):
    prob = _prob_combinada(legs, n_sims=n_sims)
    cuota = 1.0
    for l in legs:
        cuota *= cuota_efectiva(l)     # pago CONSERVADOR (cuotas estimadas acotadas)
    ev = prob * cuota - 1.0
    k4 = kelly_fraccion(prob, cuota) / 4.0          # ¼ Kelly
    conf = sum(confiabilidad(l) for l in legs) / len(legs)
    return {
        "objetivo": objetivo,
        "legs": legs,
        "n_legs": len(legs),
        "prob": round(prob * 100, 2),
        "cuota": round(cuota, 2),
        "ev_pct": round(ev * 100, 1),
        "kelly_pct": round(k4 * 100, 2),            # % del bank sugerido
        "stake_100": round(k4 * 100, 1),            # $ sugeridos con bank de $100
        "confiabilidad": round(conf, 2),
        "edge_medio": round(sum(edge_leg(l) for l in legs) / len(legs), 3),
    }


# ──────────────────────────────────────────────────────────────────────────
# SELECCIÓN ÓPTIMA
# ──────────────────────────────────────────────────────────────────────────

def _mejor_leg_por_evento(pool, key_fn):
    """Deduplica: se queda con la MEJOR leg de cada evento según key_fn."""
    mejor = {}
    for l in pool:
        ev = l.get("evento", "")
        if ev not in mejor or key_fn(l) > key_fn(mejor[ev]):
            mejor[ev] = l
    return list(mejor.values())


def frontera_por_edge(pool, k_max=K_MAX, n_sims=6000):
    """La frontera EXACTA de parlays óptimos: para cada k, el top-k por edge
    (1 leg por evento). Devuelve la lista k=2..k_max con métricas completas."""
    legs = sorted(_mejor_leg_por_evento(pool, edge_leg), key=edge_leg, reverse=True)
    out = []
    for k in range(2, min(k_max, len(legs)) + 1):
        out.append(_parlay_dict(legs[:k], objetivo=f"frontera_k{k}", n_sims=n_sims))
    return out


def seleccionar(pool, n_sims=6000, seed=None):
    """El corazón del MAESTRO. Devuelve los 3 parlays objetivo + la frontera +
    la mejor jugada de cada partido y de cada deporte. Todo con probabilidades
    CALIBRADAS — si el día no da para un parlay +EV, lo dice sin maquillaje."""
    if seed is not None:
        import random
        random.seed(seed)

    pool = [l for l in pool if float(l.get("prob", 0) or 0) > 0]
    if len(_mejor_leg_por_evento(pool, edge_leg)) < 2:
        return {"error": "Se necesitan picks de al menos 2 eventos distintos."}

    frontera = frontera_por_edge(pool, n_sims=n_sims)

    # ── MEJOR EV: el punto de la frontera con máximo EV y prob razonable ──
    cand_ev = [f for f in frontera if f["prob"] >= PROB_PISO_EV]
    mejor_ev = max(cand_ev, key=lambda f: f["ev_pct"], default=None)
    if mejor_ev and mejor_ev["ev_pct"] <= 0:
        mejor_ev = None          # honestidad: hoy no hay parlay con valor

    # ── MÁS VIABLE: máxima prob que al menos duplica (cuota ≥ 2) ──────────
    por_prob = sorted(_mejor_leg_por_evento(pool, calibrar_prob),
                      key=calibrar_prob, reverse=True)
    legs_viable, cuota_acc = [], 1.0
    for l in por_prob:
        legs_viable.append(l)
        cuota_acc *= cuota_efectiva(l)
        if cuota_acc >= 2.0 and len(legs_viable) >= 2:
            break
    mas_viable = (_parlay_dict(legs_viable, "mas_viable", n_sims)
                  if len(legs_viable) >= 2 and cuota_acc >= 2.0 else None)

    # ── MÁXIMO PAGO VIABLE: la cuota más alta con prob ≥ piso ─────────────
    cand_pago = [f for f in frontera if f["prob"] >= PROB_PISO_PAGO]
    mejor_pago = max(cand_pago, key=lambda f: f["cuota"], default=None)

    for p, obj in ((mejor_ev, "mejor_ev"), (mejor_pago, "mejor_pago")):
        if p:
            p["objetivo"] = obj

    # ── Mejor jugada por PARTIDO y por DEPORTE (ranking por edge) ─────────
    por_partido = sorted(_mejor_leg_por_evento(pool, edge_leg),
                         key=edge_leg, reverse=True)
    por_deporte = {}
    for l in por_partido:
        dep = l.get("sport", "?")
        por_deporte.setdefault(dep, l)

    return {
        "frontera": frontera,
        "mejor_ev": mejor_ev,
        "mas_viable": mas_viable,
        "mejor_pago": mejor_pago,
        "mejor_por_partido": [
            {"evento": l.get("evento"), "sport": l.get("sport"),
             "pick": l.get("pick"), "mercado": l.get("mercado"),
             "prob_cal": round(calibrar_prob(l), 1),
             "cuota": cuota_efectiva(l),
             "edge": round(edge_leg(l), 3)}
            for l in por_partido],
        "mejor_por_deporte": {
            dep: {"evento": l.get("evento"), "pick": l.get("pick"),
                  "mercado": l.get("mercado"),
                  "prob_cal": round(calibrar_prob(l), 1),
                  "edge": round(edge_leg(l), 3)}
            for dep, l in por_deporte.items()},
        "n_pool": len(pool),
        "n_eventos": len(por_partido),
        "nota": (None if mejor_ev else
                 "Hoy NINGÚN parlay tiene EV positivo con probabilidades calibradas: "
                 "el 'más viable' es el menos malo, no un regalo. Considera no apostar."),
    }


# ──────────────────────────────────────────────────────────────────────────
# BACKTEST del selector sobre el historial REAL de picks
# ──────────────────────────────────────────────────────────────────────────

def backtest_maestro(history_path=os.path.join("data", "pick_history.json"),
                     min_picks_dia=4, verbose=False,
                     out_path=os.path.join("data", "parlay_maestro_backtest.json")):
    """Simula día a día qué habría armado el MAESTRO con los picks realmente
    registrados/resueltos y los califica contra sus resultados:
      • push → la leg se elimina y la cuota se divide (regla estándar de casa);
      • todas ganan → paga Π cuotas; una pierde → −1.
    OJO: las tasas de calibración provienen del MISMO historial → es un chequeo
    de cordura del SELECTOR, no una prueba de rentabilidad futura."""
    try:
        picks = json.load(open(history_path, encoding="utf-8"))
    except Exception as e:
        return {"error": f"no se pudo leer {history_path}: {e}"}

    por_dia = {}
    for p in picks:
        if p.get("estado") not in ("ganado", "perdido", "push"):
            continue
        f = p.get("fecha_evento") or p.get("fecha")
        por_dia.setdefault(f, []).append(p)

    resultados = {"mejor_ev": [], "mas_viable": [], "mejor_pago": []}
    detalle = []
    for fecha in sorted(por_dia):
        dia = por_dia[fecha]
        if len(dia) < min_picks_dia:
            continue
        pool = [{"sport": p.get("liga") or p.get("deporte", ""),
                 "evento": p.get("evento", ""), "mercado": p.get("mercado", ""),
                 "pick": p.get("pick", ""), "prob": p.get("confianza", 0),
                 "cuota": p.get("cuota", 1.9)} for p in dia]
        sel = seleccionar(pool, n_sims=2000, seed=42)
        if sel.get("error"):
            continue
        estado_de = {(p.get("evento", ""), p.get("pick", "")): p["estado"] for p in dia}

        for obj in resultados:
            par = sel.get(obj)
            if not par:
                continue
            cuota, gano, resoluble = 1.0, True, True
            for l in par["legs"]:
                est = estado_de.get((l.get("evento", ""), l.get("pick", "")))
                if est is None:
                    resoluble = False
                    break
                if est == "push":
                    continue                    # leg fuera, cuota no multiplica
                if est == "perdido":
                    gano = False
                cuota *= cuota_efectiva(l)
            if not resoluble:
                continue
            profit = (cuota - 1.0) if gano else -1.0
            resultados[obj].append(profit)
            detalle.append({"fecha": fecha, "objetivo": obj, "n_legs": par["n_legs"],
                            "cuota_prevista": par["cuota"], "prob_prevista": par["prob"],
                            "gano": gano, "profit": round(profit, 2)})
            if verbose:
                print(f"{fecha} {obj}: {'GANA' if gano else 'pierde'} "
                      f"({par['n_legs']} legs, prob prevista {par['prob']}%)")

    def _res(vals):
        n = len(vals)
        w = sum(1 for v in vals if v > 0)
        return {"n": n, "ganados": w,
                "win_rate": round(100 * w / n, 1) if n else 0.0,
                "roi_pct": round(100 * sum(vals) / n, 1) if n else 0.0}

    reporte = {"por_objetivo": {k: _res(v) for k, v in resultados.items()},
               "dias_evaluados": len({d['fecha'] for d in detalle}),
               "detalle": detalle}
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(reporte, f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    return reporte


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    rep = backtest_maestro(verbose=True)
    if rep.get("error"):
        print(rep["error"])
    else:
        print(f"\nDías evaluados: {rep['dias_evaluados']}")
        for obj, r in rep["por_objetivo"].items():
            print(f"  {obj:12s}: {r['ganados']}/{r['n']} ({r['win_rate']}%) ROI {r['roi_pct']:+.1f}%")
