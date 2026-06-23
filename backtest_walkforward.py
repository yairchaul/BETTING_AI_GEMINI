# -*- coding: utf-8 -*-
"""
BACKTEST WALK-FORWARD (validación por ventanas móviles) — fútbol de selecciones.

A diferencia de backtest_futbol_db.py (que admite LEAKAGE: el historial de cada
equipo incluye el propio partido evaluado), este hace una validación honesta
"out-of-sample" estilo profesional:

  1. Se para en una fecha de corte del pasado (ej. 2021-01-01).
  2. ENTRENA el modelo SOLO con datos <= esa fecha.
  3. PREDICE los partidos del trimestre siguiente (que el modelo NUNCA vio).
  4. Avanza el corte 3 meses, reentrena y repite hasta hoy (walk-forward).

Métricas (las que importan para apuestas, no solo "acertó/falló"):
  • RPS  (Ranked Probability Score): castiga estar lejos del resultado real,
         premia asumir incertidumbre. Menor = mejor. ~0.33 = azar; <0.21 bueno.
  • Log-Loss: calidad de la probabilidad asignada al resultado real. Menor mejor.
  • Accuracy 1X2: % de veces que el resultado más probable fue el real.

El harness acepta PREDICTORES enchufables, para comparar en las MISMAS ventanas
el Dixon-Coles actual, los baselines y, más adelante, la capa ML.

Uso:  python backtest_walkforward.py [primer_corte AAAA-MM-DD] [paso_meses]
"""
import os
import sys
import json
import math
import logging
from datetime import datetime

import numpy as np

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

OUT_PATH = os.path.join("data", "walkforward_baseline.json")

# Resultado canónico: 0 = gana local, 1 = empate, 2 = gana visitante
HOME, DRAW, AWAY = 0, 1, 2


# ──────────────────────────────────────────────────────────────────────────
# Métricas probabilísticas
# ──────────────────────────────────────────────────────────────────────────
def rps(probs, outcome):
    """Ranked Probability Score para 3 categorías ordinales [L, E, V].
    probs: (p_local, p_empate, p_visit) que suman ~1. outcome: 0/1/2.
    RPS = 1/(r-1) * Σ_{i=1}^{r-1} (Σ_{j<=i} p_j - Σ_{j<=i} o_j)^2,  r=3."""
    o = [0.0, 0.0, 0.0]
    o[outcome] = 1.0
    cum_p = cum_o = 0.0
    s = 0.0
    for i in range(2):           # r - 1 = 2 sumas acumuladas
        cum_p += probs[i]
        cum_o += o[i]
        s += (cum_p - cum_o) ** 2
    return s / 2.0               # / (r - 1)


def log_loss(probs, outcome, eps=1e-12):
    """-log(prob asignada al resultado real). Menor = mejor."""
    return -math.log(max(eps, probs[outcome]))


def _resultado(gl, gv):
    return HOME if gl > gv else (DRAW if gl == gv else AWAY)


def _lams_a_probs(lam_l, lam_v, rho=0.0):
    """De (λ_local, λ_visit) saca ((pL,pE,pV), p_over2.5) vía la matriz Poisson
    con corrección τ de Dixon-Coles. Devuelve (None, None) si algo falla."""
    from motors.dixon_coles import matriz_marcadores
    M = matriz_marcadores(lam_l, lam_v, rho)
    p_home = float(np.tril(M, -1).sum())
    p_draw = float(np.trace(M))
    p_away = float(np.triu(M, 1).sum())
    s = p_home + p_draw + p_away
    if s <= 0:
        return None, None
    n = M.shape[0]
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    p_over25 = float(M[(ii + jj) > 2].sum())
    return (p_home / s, p_draw / s, p_away / s), p_over25


# Cache de entrenamiento por (modelo, corte): evita reentrenar DC/ML varias veces
# por ventana cuando varios predictores (DC, ML, blend) los comparten.
_TRAIN_CACHE = {}


def _entrenar_dc(desde_anio, hasta_fecha):
    key = ("dc", desde_anio, hasta_fecha)
    if key not in _TRAIN_CACHE:
        from motors.dixon_coles import entrenar
        try:
            _TRAIN_CACHE[key] = entrenar(desde_anio=desde_anio, hasta_fecha=hasta_fecha, guardar=False)
        except Exception as e:
            logger.warning(f"DC entrenar falló ({hasta_fecha}): {e}")
            _TRAIN_CACHE[key] = None
    return _TRAIN_CACHE[key]


def _entrenar_ml(desde_anio, hasta_fecha):
    key = ("ml", desde_anio, hasta_fecha)
    if key not in _TRAIN_CACHE:
        from motors.ml_predictor import entrenar as ml_entrenar
        try:
            _TRAIN_CACHE[key] = ml_entrenar(desde_anio=desde_anio, hasta_fecha=hasta_fecha, guardar=False)
        except Exception as e:
            logger.warning(f"ML entrenar falló ({hasta_fecha}): {e}")
            _TRAIN_CACHE[key] = None
    return _TRAIN_CACHE[key]


# ──────────────────────────────────────────────────────────────────────────
# Predictores (Protocol): cada uno entrena con datos <= corte y predice 1X2.
#   entrenar(hasta_fecha) -> modelo (o None si no se puede)
#   predecir(modelo, local_norm, visita_norm, neutral) -> (pL, pE, pV) o None
# ──────────────────────────────────────────────────────────────────────────
class PredictorDixonColes:
    """El Dixon-Coles de producción (motors/dixon_coles), PURO: sin la forma de
    la DB, que sería leakage (datos 2026) en un backtest histórico."""
    nombre = "dixon_coles"

    def __init__(self, desde_anio=2018):
        self.desde_anio = desde_anio

    def entrenar(self, hasta_fecha):
        return _entrenar_dc(self.desde_anio, hasta_fecha)

    def predecir(self, modelo, local_norm, visita_norm, neutral):
        if not modelo:
            return None
        idx = modelo["idx"]
        if local_norm not in idx or visita_norm not in idx:
            return None
        i, j = idx[local_norm], idx[visita_norm]
        atk, dfn, h = modelo["atk"], modelo["dfn"], modelo["home_adv"]
        m = 0.0 if neutral else 1.0
        lam_l = math.exp(min(4.0, m * h + atk[i] - dfn[j]))
        lam_v = math.exp(min(4.0, atk[j] - dfn[i]))
        return _lams_a_probs(lam_l, lam_v, modelo.get("rho", 0.0))


class PredictorTasaBase:
    """Baseline: frecuencias L/E/V globales del set de entrenamiento (<= corte).
    Un modelo serio DEBE ganarle a esto. El harness le inyecta el modelo."""
    nombre = "tasa_base"

    def entrenar(self, hasta_fecha):
        return None  # el harness calcula ((pL,pE,pV), p_over25) con las filas <= corte

    def predecir(self, modelo, *_):
        return modelo  # modelo = ((pL, pE, pV), p_over25) precalculado


class PredictorUniforme:
    """Baseline tonto: 1/3 cada uno. Referencia absoluta de 'azar'."""
    nombre = "uniforme"

    def entrenar(self, hasta_fecha):
        return ((1 / 3, 1 / 3, 1 / 3), 0.5)

    def predecir(self, modelo, *_):
        return modelo


class PredictorML:
    """Capa ML supervisada (motors/ml_predictor): Poisson-GLM sobre features
    dinámicas (forma, racha, ELO, localía). λ → matriz → 1X2."""
    nombre = "ml_glm"

    def __init__(self, desde_anio=2018):
        self.desde_anio = desde_anio

    def entrenar(self, hasta_fecha):
        return _entrenar_ml(self.desde_anio, hasta_fecha)

    def predecir(self, modelo, local_norm, visita_norm, neutral):
        if not modelo:
            return None
        from motors.ml_predictor import predecir_lambdas
        lams = predecir_lambdas(modelo, local_norm, visita_norm, neutral)
        if not lams:
            return None
        return _lams_a_probs(lams[0], lams[1], 0.0)


class PredictorBlend:
    """Ensemble: mezcla las λ de Dixon-Coles y del ML-GLM (la idea del reel:
    combinar fuerza estructural + patrones recientes). w_ml = peso del ML."""

    def __init__(self, w_ml=0.4, desde_anio=2018):
        self.w_ml = w_ml
        self.desde_anio = desde_anio
        self.nombre = f"blend_ml{int(w_ml*100)}"

    def entrenar(self, hasta_fecha):
        return (_entrenar_dc(self.desde_anio, hasta_fecha),
                _entrenar_ml(self.desde_anio, hasta_fecha))

    def predecir(self, modelo, local_norm, visita_norm, neutral):
        mdc, mml = modelo
        if not mdc or not mml:
            return None
        idx = mdc["idx"]
        if local_norm not in idx or visita_norm not in idx:
            return None
        i, j = idx[local_norm], idx[visita_norm]
        atk, dfn, h = mdc["atk"], mdc["dfn"], mdc["home_adv"]
        m = 0.0 if neutral else 1.0
        lam_l_dc = math.exp(min(4.0, m * h + atk[i] - dfn[j]))
        lam_v_dc = math.exp(min(4.0, atk[j] - dfn[i]))
        from motors.ml_predictor import predecir_lambdas
        lams_ml = predecir_lambdas(mml, local_norm, visita_norm, neutral)
        if not lams_ml:
            return None
        lam_l = (1 - self.w_ml) * lam_l_dc + self.w_ml * lams_ml[0]
        lam_v = (1 - self.w_ml) * lam_v_dc + self.w_ml * lams_ml[1]
        return _lams_a_probs(lam_l, lam_v, mdc.get("rho", 0.0))


# ──────────────────────────────────────────────────────────────────────────
# Walk-forward
# ──────────────────────────────────────────────────────────────────────────
def _add_months(dt, months):
    m = dt.month - 1 + months
    y = dt.year + m // 12
    m = m % 12 + 1
    return dt.replace(year=y, month=m, day=1)


def _tasa_base_de(filas):
    """((pL, pE, pV), p_over2.5) a partir de los partidos de entrenamiento."""
    if not filas:
        return ((1 / 3, 1 / 3, 1 / 3), 0.5)
    c = [0, 0, 0]
    over = 0
    for r in filas:
        c[_resultado(r["goles_local"], r["goles_visita"])] += 1
        if (r["goles_local"] + r["goles_visita"]) > 2.5:
            over += 1
    n = sum(c)
    if not n:
        return ((1 / 3, 1 / 3, 1 / 3), 0.5)
    return (tuple(x / n for x in c), over / n)


def ejecutar(primer_corte="2021-01-01", paso_meses=3, desde_anio_dc=2018, predictores=None):
    """Corre la validación walk-forward y devuelve un reporte por predictor.
    Todos los predictores se evalúan sobre el MISMO conjunto de partidos (los
    que el Dixon-Coles puede cubrir), para que la comparación sea justa."""
    from motors.international_results import _cargar_datos
    datos = _cargar_datos()
    if not datos:
        print("Sin datos de international_results.")
        return None
    datos = [r for r in datos if r.get("fecha") and len(r["fecha"]) >= 10]
    datos.sort(key=lambda x: x["fecha"])

    if predictores is None:
        predictores = [PredictorDixonColes(desde_anio_dc), PredictorTasaBase(), PredictorUniforme()]

    hoy = datetime.now()
    corte = datetime.strptime(primer_corte, "%Y-%m-%d")

    acc = {p.nombre: {"rps": 0.0, "ll": 0.0, "aciertos": 0, "n": 0,
                      "brier_ov": 0.0, "acc_ov": 0, "n_ov": 0} for p in predictores}
    n_ventanas = 0
    n_test_total = 0
    ventanas = []

    while corte < hoy:
        fin = _add_months(corte, paso_meses)
        corte_str = corte.strftime("%Y-%m-%d")
        fin_str = fin.strftime("%Y-%m-%d")

        test = [r for r in datos if corte_str < r["fecha"][:10] <= fin_str]
        if not test:
            corte = fin
            continue
        train_filas = [r for r in datos if r["fecha"][:10] <= corte_str]

        # Entrenar cada predictor SOLO con datos <= corte
        modelos = {}
        for p in predictores:
            if isinstance(p, PredictorTasaBase):
                modelos[p.nombre] = _tasa_base_de(train_filas)
            else:
                modelos[p.nombre] = p.entrenar(corte_str)

        evaluados = 0
        win = {p.nombre: {"rps": 0.0, "ac": 0, "n": 0} for p in predictores}
        for r in test:
            outcome = _resultado(r["goles_local"], r["goles_visita"])
            over_real = 1.0 if (r["goles_local"] + r["goles_visita"]) > 2.5 else 0.0
            probs_by, ok = {}, True
            for p in predictores:
                pr = p.predecir(modelos[p.nombre], r["local"], r["visita"], r.get("neutral", False))
                if not pr or not pr[0]:
                    ok = False
                    break
                probs_by[p.nombre] = pr
            if not ok:
                continue  # mismo set de partidos para todos
            for nombre, (p1x2, p_ov) in probs_by.items():
                a = acc[nombre]
                _r = rps(p1x2, outcome)
                a["rps"] += _r
                a["ll"] += log_loss(p1x2, outcome)
                _hit = max(range(3), key=lambda k: p1x2[k]) == outcome
                if _hit:
                    a["aciertos"] += 1
                a["n"] += 1
                w = win[nombre]
                w["rps"] += _r
                w["n"] += 1
                if _hit:
                    w["ac"] += 1
                if p_ov is not None:
                    a["brier_ov"] += (p_ov - over_real) ** 2
                    if (p_ov >= 0.5) == (over_real >= 0.5):
                        a["acc_ov"] += 1
                    a["n_ov"] += 1
            evaluados += 1

        n_ventanas += 1
        n_test_total += evaluados
        ventanas.append({
            "corte": corte_str, "fin": fin_str, "n": evaluados,
            "por_pred": {nm: {"rps": round(w["rps"] / max(1, w["n"]), 4),
                              "acc": round(w["ac"] / max(1, w["n"]) * 100, 1)}
                         for nm, w in win.items()},
        })
        print(f"  ventana {corte_str} → {fin_str}: {evaluados} partidos evaluados", flush=True)
        corte = fin

    return _reporte(acc, predictores, n_ventanas, n_test_total, primer_corte, paso_meses, ventanas)


def _reporte(acc, predictores, n_ventanas, n_test, primer_corte, paso_meses, ventanas=None):
    res = {}
    for p in predictores:
        a = acc[p.nombre]
        n = max(1, a["n"])
        n_ov = max(1, a["n_ov"])
        res[p.nombre] = {
            "n": a["n"],
            "rps": round(a["rps"] / n, 4),
            "log_loss": round(a["ll"] / n, 4),
            "accuracy_1x2": round(a["aciertos"] / n * 100, 1),
            "brier_over25": round(a["brier_ov"] / n_ov, 4),
            "acc_over25": round(a["acc_ov"] / n_ov * 100, 1),
        }
    rep = {
        "timestamp": datetime.now().isoformat(),
        "primer_corte": primer_corte,
        "paso_meses": paso_meses,
        "n_ventanas": n_ventanas,
        "n_partidos_evaluados": n_test,
        "ventanas": ventanas or [],
        "predictores": res,
    }
    os.makedirs("data", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    return rep


def _imprimir(rep):
    print("=" * 74)
    print("BACKTEST WALK-FORWARD — validación out-of-sample (sin leakage)")
    print(f"Desde {rep['primer_corte']} · paso {rep['paso_meses']}m · "
          f"{rep['n_ventanas']} ventanas · {rep['n_partidos_evaluados']} partidos")
    print("=" * 74)
    print(f"{'PREDICTOR':<16}{'N':>7}{'RPS':>10}{'LogLoss':>10}{'Acc1X2':>9}{'BrierOv':>10}{'AccOv2.5':>10}")
    print("-" * 74)
    # Ordenar por RPS ascendente (mejor primero)
    for nombre, m in sorted(rep["predictores"].items(), key=lambda kv: kv[1]["rps"]):
        print(f"{nombre:<16}{m['n']:>7}{m['rps']:>10.4f}{m['log_loss']:>10.4f}"
              f"{m['accuracy_1x2']:>8.1f}%{m['brier_over25']:>10.4f}{m['acc_over25']:>9.1f}%")
    print("-" * 74)
    print("RPS, Log-Loss, BrierOv: MENOR mejor. Acc 1X2 / Acc Ov 2.5: MAYOR mejor.")
    print("Referencia fútbol: RPS < 0.21 bueno; ~0.33 azar. Brier Over 0.25 = azar.")
    print("=" * 74)


def _imprimir_ventanas(rep, pred="dixon_coles"):
    """Desglose VENTANA POR VENTANA del predictor indicado (RPS y Acc 1X2),
    para ver el rendimiento por trimestre (p.ej. 2026)."""
    vts = rep.get("ventanas", [])
    if not vts:
        return
    print()
    print("=" * 74)
    print(f"DESGLOSE POR VENTANA — {pred} (RPS y Acc 1X2 de cada trimestre)")
    print("=" * 74)
    print(f"{'VENTANA':<26}{'N':>6}{'RPS':>10}{'Acc 1X2':>10}")
    print("-" * 74)
    for v in vts:
        pp = v.get("por_pred", {}).get(pred, {})
        if not pp:
            continue
        etiqueta = f"{v['corte']} → {v['fin']}"
        print(f"{etiqueta:<26}{v['n']:>6}{pp.get('rps', 0):>10.4f}{pp.get('acc', 0):>9.1f}%")
    print("-" * 74)
    # Promedio ponderado del año 2026 (ventanas cuyo corte empieza en 2026)
    v2026 = [v for v in vts if v["corte"][:4] == "2026" and v.get("por_pred", {}).get(pred)]
    if v2026:
        n26 = sum(v["n"] for v in v2026)
        if n26:
            rps26 = sum(v["por_pred"][pred]["rps"] * v["n"] for v in v2026) / n26
            acc26 = sum(v["por_pred"][pred]["acc"] * v["n"] for v in v2026) / n26
            print(f"SOLO 2026: {len(v2026)} ventanas · {n26} partidos · "
                  f"RPS {rps26:.4f} · Acc {acc26:.1f}%")
    print("=" * 74)


if __name__ == "__main__":
    args = sys.argv[1:]
    modo_ml = "ml" in args
    detalle = "detalle" in args
    args = [a for a in args if a not in ("ml", "detalle")]
    primer_corte = args[0] if len(args) > 0 else "2021-01-01"
    paso = int(args[1]) if len(args) > 1 else 3

    if modo_ml:
        # Comparación: Dixon-Coles vs capa ML vs blends, en las MISMAS ventanas.
        predictores = [
            PredictorDixonColes(), PredictorML(),
            PredictorBlend(w_ml=0.3), PredictorBlend(w_ml=0.5),
            PredictorTasaBase(),
        ]
        print(f"Comparación DC vs ML vs blends desde {primer_corte}, paso {paso}m...")
        rep = ejecutar(primer_corte=primer_corte, paso_meses=paso, predictores=predictores)
    else:
        print(f"Walk-forward desde {primer_corte}, paso {paso} meses. Entrenando por ventana...")
        rep = ejecutar(primer_corte=primer_corte, paso_meses=paso)
    if rep:
        _imprimir(rep)
        if detalle:
            _imprimir_ventanas(rep)
