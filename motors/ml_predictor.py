# -*- coding: utf-8 -*-
"""
ML PREDICTOR — Regresión de Poisson supervisada para goles esperados (λ).

Es la capa de "ML de verdad" estilo XGBoost del reel, pero implementada SIN
dependencias nuevas (solo numpy + el mismo optimizador Adam que ya usa
dixon_coles). XGBoost/PyMC no se pueden meter sin romper el deploy en Streamlit
Cloud (Python 3.14, requirements minimalista), y un Poisson-GLM es el modelo
CORRECTO para conteo de goles: λ = exp(w·x + b).

Diferencia clave vs. Dixon-Coles: DC modela fuerza ESTRUCTURAL (ataque/defensa)
con decaimiento temporal. Este modelo aprende de FEATURES DINÁMICAS que DC no
ve: forma reciente ofensiva/defensiva, racha (momentum), ELO y localía. La idea
es que aporte señal complementaria; si el backtest walk-forward no lo confirma,
NO se integra (misma disciplina que con ELO y el MLB runs model).

Anti-leakage: las features de cada partido se calculan con el estado de cada
selección ANTES de ese partido (recorrido cronológico). entrenar(hasta_fecha)
solo usa datos <= esa fecha → compatible con backtest_walkforward.py.
"""
import os
import json
import math
import logging
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join("data", "ml_predictor_params.json")
CACHE_DAYS = 14
K = 10                 # ventana de forma reciente (últimos K partidos)
_R0 = 1500.0           # rating ELO inicial
_HFA_ELO = 65.0        # ventaja de localía en puntos ELO
MIN_HIST = 3           # mínimo de partidos previos para generar fila/predicción

FEATURES = ["att_gf", "att_ga", "def_ga", "def_gf", "att_wr", "def_wr", "is_home", "elo_diff"]

_modelo = None         # cache en memoria


# ──────────────────────────────────────────────────────────────────────────
# Features (leakage-free): se calculan con el estado PREVIO de cada selección
# ──────────────────────────────────────────────────────────────────────────
def _avg(lst, default=1.2):
    s = lst[-K:]
    return sum(s) / len(s) if s else default


def _winrate(res, default=0.4):
    """Tasa de puntos en los últimos K (1=victoria, 0.5=empate, 0=derrota)."""
    s = res[-K:]
    return sum(s) / len(s) if s else default


def _feat(att, defn, is_home, elo_diff):
    """Vector de 8 features para (atacante, defensor, localía)."""
    return [
        _avg(att["gf"]),        # forma ofensiva del atacante
        _avg(att["ga"]),        # goles en contra del atacante (calidad global)
        _avg(defn["ga"]),       # fragilidad defensiva del defensor
        _avg(defn["gf"]),       # ofensiva del defensor (calidad global)
        _winrate(att["res"]),   # racha/momentum del atacante
        _winrate(defn["res"]),  # racha/momentum del defensor
        float(is_home),         # localía efectiva (0 si neutral o visitante)
        elo_diff / 100.0,       # diferencia ELO (atacante - defensor), escalada
    ]


def _k_elo(gd):
    return 30.0 * (1.0 if gd <= 1 else (1.5 if gd == 2 else 1.75))


def _elo_paso(rh, ra, gh, ga, neutral):
    """Actualiza ELO de ambos tras un partido (estilo World Football Elo)."""
    hfa = 0.0 if neutral else _HFA_ELO
    we = 1.0 / (1.0 + 10 ** (-(rh + hfa - ra) / 400.0))
    w = 1.0 if gh > ga else (0.5 if gh == ga else 0.0)
    d = _k_elo(abs(gh - ga)) * (w - we)
    return rh + d, ra - d


# ──────────────────────────────────────────────────────────────────────────
# Construcción del dataset de entrenamiento (cronológico, anti-leakage)
# ──────────────────────────────────────────────────────────────────────────
def _construir_filas(datos, hasta_fecha=None):
    """Recorre los partidos en orden cronológico. Para cada uno, genera DOS
    filas (goles del local y goles del visitante) con features del estado PREVIO,
    y DESPUÉS actualiza el estado. Devuelve (X, y, estado_final)."""
    estado = {}

    def _st(t):
        return estado.setdefault(t, {"gf": [], "ga": [], "res": [], "elo": _R0})

    X, y = [], []
    for r in datos:
        f = r["fecha"][:10]
        if hasta_fecha and f > hasta_fecha:
            break
        h, a = r["local"], r["visita"]
        gh, ga = r["goles_local"], r["goles_visita"]
        neutral = bool(r.get("neutral", False))
        eh, ea = _st(h), _st(a)
        elo_diff = eh["elo"] - ea["elo"]

        # Features ANTES de ver el resultado (solo pasado)
        if len(eh["gf"]) >= MIN_HIST and len(ea["gf"]) >= MIN_HIST:
            X.append(_feat(eh, ea, 0.0 if neutral else 1.0, elo_diff)); y.append(gh)
            X.append(_feat(ea, eh, 0.0, -elo_diff)); y.append(ga)

        # Actualizar estado DESPUÉS (ELO + historiales)
        eh["elo"], ea["elo"] = _elo_paso(eh["elo"], ea["elo"], gh, ga, neutral)
        eh["gf"].append(gh); eh["ga"].append(ga)
        eh["res"].append(1.0 if gh > ga else (0.5 if gh == ga else 0.0))
        ea["gf"].append(ga); ea["ga"].append(gh)
        ea["res"].append(1.0 if ga > gh else (0.5 if ga == gh else 0.0))
        for e in (eh, ea):
            for kk in ("gf", "ga", "res"):
                if len(e[kk]) > K:
                    e[kk] = e[kk][-K:]
    return X, y, estado


# ──────────────────────────────────────────────────────────────────────────
# Ajuste del Poisson-GLM por descenso de gradiente (Adam) — sin scipy/sklearn
# ──────────────────────────────────────────────────────────────────────────
def _fit_poisson(X, y, iters=4000, lr=0.05, l2=1e-3):
    """Minimiza la NLL de Poisson: λ=exp(Xw+b). El gradiente respecto a η=Xw+b
    es (λ - y), limpio y convexo. Estandariza features para que Adam converja."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, d = X.shape
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std < 1e-6] = 1.0
    Xs = (X - mean) / std

    w = np.zeros(d)
    b = math.log(max(0.1, float(y.mean())))   # arranque en la media de goles
    mw = np.zeros(d); vw = np.zeros(d); mb = 0.0; vb = 0.0
    beta1, beta2, eps = 0.9, 0.999, 1e-8

    for t in range(1, iters + 1):
        eta = np.clip(Xs @ w + b, -3.0, 3.0)
        lam = np.exp(eta)
        resid = lam - y                        # dNLL/dη
        gw = Xs.T @ resid / n + l2 * w
        gb = float(resid.mean())
        mw = beta1 * mw + (1 - beta1) * gw
        vw = beta2 * vw + (1 - beta2) * gw * gw
        mb = beta1 * mb + (1 - beta1) * gb
        vb = beta2 * vb + (1 - beta2) * gb * gb
        bc1 = 1 - beta1 ** t
        bc2 = 1 - beta2 ** t
        w -= lr * (mw / bc1) / (np.sqrt(vw / bc2) + eps)
        b -= lr * (mb / bc1) / (math.sqrt(vb / bc2) + eps)
    return w, b, mean, std


# ──────────────────────────────────────────────────────────────────────────
# Entrenamiento / cache
# ──────────────────────────────────────────────────────────────────────────
def entrenar(desde_anio=2018, hasta_fecha=None, guardar=True):
    """Construye features, ajusta el Poisson-GLM y (opcional) cachea en JSON.
    Igual que dixon_coles: solo guarda cache cuando hasta_fecha es None, para
    que el walk-forward (con corte) no pise el modelo de producción."""
    from motors.international_results import _cargar_datos
    datos = [r for r in _cargar_datos()
             if r.get("fecha") and len(r["fecha"]) >= 10 and r["fecha"][:4] >= str(desde_anio)]
    datos.sort(key=lambda x: x["fecha"])
    X, y, estado = _construir_filas(datos, hasta_fecha)
    if len(X) < 200:
        logger.warning("ml_predictor: datos insuficientes para entrenar")
        return None
    w, b, mean, std = _fit_poisson(X, y)

    estado_ser = {t: {"gf": e["gf"][-K:], "ga": e["ga"][-K:], "res": e["res"][-K:],
                      "elo": round(e["elo"], 2)}
                  for t, e in estado.items()}
    modelo = {
        "w": w.tolist(), "b": float(b), "mean": mean.tolist(), "std": std.tolist(),
        "estado": estado_ser, "feature_names": FEATURES, "n_filas": len(X),
        "desde_anio": desde_anio, "hasta_fecha": hasta_fecha,
        "fecha_fit": datetime.now().strftime("%Y-%m-%d"),
    }
    if guardar and hasta_fecha is None:
        try:
            os.makedirs("data", exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(modelo, f)
            logger.info(f"ml_predictor: modelo guardado ({len(X)} filas, {len(estado_ser)} equipos)")
        except Exception as e:
            logger.warning(f"ml_predictor: no se pudo guardar cache: {e}")
    return modelo


def _modelo_activo(force=False):
    global _modelo
    if _modelo is not None and not force:
        return _modelo
    if not force and os.path.exists(CACHE_PATH):
        try:
            edad = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_PATH))).days
            if edad < CACHE_DAYS:
                with open(CACHE_PATH, encoding="utf-8") as f:
                    _modelo = json.load(f)
                return _modelo
        except Exception as e:
            logger.warning(f"ml_predictor: cache ilegible ({e}), reentrenando")
    _modelo = entrenar()
    return _modelo


# ──────────────────────────────────────────────────────────────────────────
# Predicción
# ──────────────────────────────────────────────────────────────────────────
def _lookup(est, name):
    """Resuelve el nombre de la selección a una clave del estado."""
    if name in est:
        return name
    try:
        from motors.international_results import _resolve, _norm
        r = _resolve(name)
        if r in est:
            return r
        n = _norm(name)
        if n in est:
            return n
    except Exception:
        pass
    return None


def predecir_lambdas(modelo, home, away, neutral=True):
    """(λ_local, λ_visitante) según el GLM, o None si falta historial."""
    if not modelo:
        return None
    est = modelo["estado"]
    h = _lookup(est, home)
    a = _lookup(est, away)
    if not h or not a:
        return None
    eh, ea = est[h], est[a]
    if len(eh["gf"]) < MIN_HIST or len(ea["gf"]) < MIN_HIST:
        return None
    w = np.asarray(modelo["w"], dtype=float)
    b = float(modelo["b"])
    mean = np.asarray(modelo["mean"], dtype=float)
    std = np.asarray(modelo["std"], dtype=float)
    elo_diff = eh["elo"] - ea["elo"]

    def _lam(att, defn, is_home, ed):
        x = (np.asarray(_feat(att, defn, is_home, ed), dtype=float) - mean) / std
        return float(np.exp(np.clip(x @ w + b, -3.0, 3.0)))

    lam_h = _lam(eh, ea, 0.0 if neutral else 1.0, elo_diff)
    lam_a = _lam(ea, eh, 0.0, -elo_diff)
    return lam_h, lam_a


def predecir(home, away, neutral=True, modelo=None, rho=0.0):
    """Predicción completa estilo dixon_coles.predecir (para integrarla al motor):
    disponible, xg_local/visit, prob 1X2, over/under, btts y la matriz."""
    modelo = modelo or _modelo_activo()
    lams = predecir_lambdas(modelo, home, away, neutral)
    if not lams:
        return {"disponible": False}
    lam_l, lam_v = lams
    from motors.dixon_coles import matriz_marcadores
    M = matriz_marcadores(lam_l, lam_v, rho)
    n = M.shape[0]
    p_home = float(np.tril(M, -1).sum())
    p_draw = float(np.trace(M))
    p_away = float(np.triu(M, 1).sum())
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    tot = ii + jj
    p_o15 = float(M[tot > 1].sum())
    p_o25 = float(M[tot > 2].sum())
    p_o35 = float(M[tot > 3].sum())
    p_btts = float(M[(ii > 0) & (jj > 0)].sum())
    _r = lambda v: round(v * 100, 1)
    return {
        "disponible": True,
        "xg_local": round(lam_l, 2), "xg_visit": round(lam_v, 2),
        "prob": {"local": _r(p_home), "empate": _r(p_draw), "visitante": _r(p_away)},
        "over_under": {"over_1.5": _r(p_o15), "over_2.5": _r(p_o25),
                       "over_3.5": _r(p_o35), "under_2.5": _r(1 - p_o25)},
        "btts": {"si": _r(p_btts), "no": _r(1 - p_btts)},
        "mercados": {
            "local": _r(p_home), "empate": _r(p_draw), "visitante": _r(p_away),
            "over_1.5": _r(p_o15), "over_2.5": _r(p_o25), "over_3.5": _r(p_o35),
            "under_1.5": _r(float(M[tot <= 1].sum())), "under_2.5": _r(1 - p_o25),
            "under_3.5": _r(float(M[tot <= 3].sum())),
            "btts_si": _r(p_btts), "btts_no": _r(1 - p_btts),
        },
    }


def info():
    m = _modelo_activo()
    if not m:
        return "ml_predictor: sin modelo (datos insuficientes)"
    return (f"ml_predictor: {m['n_filas']} filas · {len(m['estado'])} equipos "
            f"· desde {m['desde_anio']} · fit {m['fecha_fit']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Entrenando ML predictor (Poisson-GLM)...")
    entrenar()
    print(info())
    for l, v in [("Argentina", "Austria"), ("Brazil", "Haiti"), ("Mexico", "South Korea")]:
        r = predecir(l, v)
        if not r["disponible"]:
            print(f"\n{l} vs {v}: no disponible")
            continue
        print(f"\n{l} vs {v}  (xG {r['xg_local']} - {r['xg_visit']})")
        print(f"  1X2: L {r['prob']['local']}% | E {r['prob']['empate']}% | V {r['prob']['visitante']}%")
        print(f"  Over 2.5: {r['over_under']['over_2.5']}% | BTTS: {r['btts']['si']}%")
