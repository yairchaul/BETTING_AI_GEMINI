# -*- coding: utf-8 -*-
"""
MODELO DE CARRERAS MLB — "Dixon-Coles de las carreras".

Mismo enfoque que el motor de fútbol, aplicado a MLB: estima por máxima
verosimilitud la fuerza OFENSIVA (atk) y de PREVENCIÓN de carreras (def) de cada
equipo, más la ventaja de local. De ahí salen las carreras esperadas (λ) de cada
lado, y de la matriz Poisson se derivan TODOS los mercados de forma coherente:
money line, run line ±1.5 y totales (Over/Under).

    λ_local    = exp(home_adv + atk_local  − def_visitante)
    λ_visitante= exp(           atk_visit  − def_local)
    P(carreras = i,j) = Poisson(i; λ_local) · Poisson(j; λ_visitante)

Datos: temporada en curso vía la MLB Stats API oficial (paquete `statsapi`,
endpoint schedule). Se cachea en JSON (portable y commiteable, como el modelo de
fútbol) para que Streamlit Cloud lo cargue al instante.

Optimizador propio (Adam + gradiente analítico), sin scipy (roto en el entorno).
El abridor concreto NO entra todavía: este es el baseline a nivel EQUIPO; el
ajuste por abridor del día lo sigue haciendo motor_mlb_pro.
"""
import os
import json
import math
import logging
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join("data", "mlb_runs_params.json")
CACHE_DAYS = 3                  # la temporada avanza rápido → refrescar seguido
MAX_RUNS = 14                   # matriz 0..14 carreras por lado
REG = 1.5                       # ridge (shrinkage de equipos)
PIN = 1000.0                    # restricción Σatk≈0 (identificabilidad)
TEMPORADA = datetime.now().year

_FACT = np.array([math.factorial(k) for k in range(MAX_RUNS + 1)], dtype=float)
_modelo = None


def _norm(nombre: str) -> str:
    return (nombre or "").strip().lower()


# ──────────────────────────────────────────────────────────────────────────
# Datos: temporada vía statsapi
# ──────────────────────────────────────────────────────────────────────────
def _cargar_temporada(anio=None, hasta_fecha=None):
    """Lista de juegos finalizados (regular) de la temporada. Cada uno:
    {fecha, local, visitante, runs_local, runs_visit}. hasta_fecha 'YYYY-MM-DD'
    para backtesting (excluye juegos posteriores)."""
    anio = anio or TEMPORADA
    try:
        import statsapi
    except Exception as e:
        logger.warning(f"mlb_runs_model: statsapi no disponible ({e})")
        return []
    try:
        games = statsapi.schedule(start_date=f"03/01/{anio}", end_date=f"11/15/{anio}")
    except Exception as e:
        logger.warning(f"mlb_runs_model: schedule falló ({e})")
        return []

    filas = []
    for g in games:
        if g.get("status") != "Final" or g.get("game_type") != "R":
            continue
        fecha = g.get("game_date", "")
        if hasta_fecha and fecha > hasta_fecha:
            continue
        try:
            rl = int(g["home_score"]); rv = int(g["away_score"])
        except (KeyError, ValueError, TypeError):
            continue
        local = _norm(g.get("home_name"))
        visit = _norm(g.get("away_name"))
        if not local or not visit:
            continue
        filas.append({"fecha": fecha, "local": local, "visitante": visit,
                      "runs_local": rl, "runs_visit": rv})
    return filas


# ──────────────────────────────────────────────────────────────────────────
# Ajuste por máxima verosimilitud (Poisson) — Adam + gradiente analítico
# ──────────────────────────────────────────────────────────────────────────
def _ajustar(filas, iters=5000, lr=0.05):
    equipos = sorted({f["local"] for f in filas} | {f["visitante"] for f in filas})
    idx = {t: i for i, t in enumerate(equipos)}
    n = len(idx)
    a = np.array([idx[f["local"]] for f in filas], dtype=np.intp)
    b = np.array([idx[f["visitante"]] for f in filas], dtype=np.intp)
    x = np.array([f["runs_local"] for f in filas], dtype=float)
    y = np.array([f["runs_visit"] for f in filas], dtype=float)

    atk = np.zeros(n); dfn = np.zeros(n); h = 0.03
    m_atk = np.zeros(n); v_atk = np.zeros(n)
    m_dfn = np.zeros(n); v_dfn = np.zeros(n)
    m_h = v_h = 0.0
    b1, b2, eps = 0.9, 0.999, 1e-8

    for t in range(1, iters + 1):
        eta_h = np.clip(h + atk[a] - dfn[b], -2.5, 2.5)
        eta_a = np.clip(atk[b] - dfn[a], -2.5, 2.5)
        lam = np.exp(eta_h); mu = np.exp(eta_a)
        rh = x - lam; ra = y - mu

        g_atk = np.bincount(a, weights=rh, minlength=n) + np.bincount(b, weights=ra, minlength=n)
        g_dfn = -np.bincount(b, weights=rh, minlength=n) - np.bincount(a, weights=ra, minlength=n)
        g_h = float(np.sum(rh))
        g_atk -= REG * atk
        g_dfn -= REG * dfn
        g_atk -= PIN * atk.sum()

        m_atk = b1 * m_atk + (1 - b1) * g_atk; v_atk = b2 * v_atk + (1 - b2) * g_atk * g_atk
        m_dfn = b1 * m_dfn + (1 - b1) * g_dfn; v_dfn = b2 * v_dfn + (1 - b2) * g_dfn * g_dfn
        m_h = b1 * m_h + (1 - b1) * g_h; v_h = b2 * v_h + (1 - b2) * g_h * g_h
        bc1 = 1 - b1 ** t; bc2 = 1 - b2 ** t
        atk += lr * (m_atk / bc1) / (np.sqrt(v_atk / bc2) + eps)
        dfn += lr * (m_dfn / bc1) / (np.sqrt(v_dfn / bc2) + eps)
        h += lr * (m_h / bc1) / (math.sqrt(v_h / bc2) + eps)

    return idx, atk, dfn, float(h)


def entrenar(anio=None, hasta_fecha=None, guardar=True):
    filas = _cargar_temporada(anio, hasta_fecha)
    if len(filas) < 200:
        logger.warning(f"mlb_runs_model: datos insuficientes ({len(filas)} juegos)")
        return None
    idx, atk, dfn, h = _ajustar(filas)
    modelo = {
        "idx": idx, "atk": np.asarray(atk), "dfn": np.asarray(dfn), "home_adv": h,
        "n_equipos": len(idx), "n_juegos": len(filas),
        "anio": anio or TEMPORADA, "hasta_fecha": hasta_fecha,
        "fecha_fit": datetime.now().strftime("%Y-%m-%d"),
        "media_runs": round(float(np.mean([f["runs_local"] + f["runs_visit"] for f in filas])), 2),
    }
    if guardar and hasta_fecha is None:
        try:
            os.makedirs("data", exist_ok=True)
            serial = dict(modelo)
            serial["atk"] = modelo["atk"].tolist(); serial["dfn"] = modelo["dfn"].tolist()
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(serial, f)
            logger.info(f"mlb_runs_model: guardado ({len(idx)} equipos, {len(filas)} juegos, "
                        f"home_adv={h:.3f}, media_runs={modelo['media_runs']})")
        except Exception as e:
            logger.warning(f"mlb_runs_model: no se pudo guardar ({e})")
    return modelo


def _modelo_activo(force_refit=False):
    global _modelo
    if _modelo is not None and not force_refit:
        return _modelo
    if not force_refit and os.path.exists(CACHE_PATH):
        try:
            edad = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_PATH))).days
            if edad < CACHE_DAYS:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    m = json.load(f)
                m["atk"] = np.asarray(m["atk"], dtype=float)
                m["dfn"] = np.asarray(m["dfn"], dtype=float)
                _modelo = m
                return _modelo
        except Exception as e:
            logger.warning(f"mlb_runs_model: cache ilegible ({e})")
    _modelo = entrenar()
    return _modelo


# ──────────────────────────────────────────────────────────────────────────
# Resolución de nombres de equipo (tolerante)
# ──────────────────────────────────────────────────────────────────────────
def _resolver_equipo(nombre, idx):
    n = _norm(nombre)
    if n in idx:
        return n
    # contención de tokens (p.ej. "yankees" → "new york yankees")
    qt = set(n.split())
    cands = [k for k in idx if qt and qt <= set(k.split())]
    if len(cands) == 1:
        return cands[0]
    cands2 = [k for k in idx if n in k or k in n]
    if len(cands2) == 1:
        return cands2[0]
    return None


# ──────────────────────────────────────────────────────────────────────────
# Predicción
# ──────────────────────────────────────────────────────────────────────────
def _poisson_col(lam):
    ks = np.arange(MAX_RUNS + 1)
    return np.exp(-lam) * np.power(lam, ks) / _FACT


def get_lambdas(local, visitante, modelo=None):
    modelo = modelo or _modelo_activo()
    if not modelo:
        return None
    idx = modelo["idx"]
    tl = _resolver_equipo(local, idx); tv = _resolver_equipo(visitante, idx)
    if not tl or not tv:
        return None
    i, j = idx[tl], idx[tv]
    atk, dfn, h = modelo["atk"], modelo["dfn"], modelo["home_adv"]
    lam_l = math.exp(min(2.5, h + atk[i] - dfn[j]))
    lam_v = math.exp(min(2.5, atk[j] - dfn[i]))
    return float(lam_l), float(lam_v)


def matriz_carreras(lam_l, lam_v):
    lam_l = float(np.clip(lam_l, 0.3, 12.0))
    lam_v = float(np.clip(lam_v, 0.3, 12.0))
    M = np.outer(_poisson_col(lam_l), _poisson_col(lam_v))
    s = M.sum()
    return M / s if s > 0 else M


def predecir(local, visitante, linea_total=8.5, modelo=None):
    """Money line, run line ±1.5 y total Over/Under desde la matriz de carreras."""
    modelo = modelo or _modelo_activo()
    lams = get_lambdas(local, visitante, modelo=modelo)
    if lams is None:
        return {"disponible": False}
    lam_l, lam_v = lams
    M = matriz_carreras(lam_l, lam_v)
    n = M.shape[0]
    p_local = float(np.tril(M, -1).sum())      # i > j (no hay empates en MLB, pero ~0)
    p_visit = float(np.triu(M, 1).sum())
    # repartir la diagonal (empates teóricos de Poisson) proporcionalmente
    diag = float(np.trace(M))
    if p_local + p_visit > 0:
        p_local += diag * p_local / (p_local + p_visit)
        p_visit += diag * p_visit / (p_local + p_visit)

    I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    tot = I + J
    p_over = float(M[tot > linea_total].sum())
    margen = I - J
    p_local_115 = float(M[margen >= 2].sum())   # local -1.5 (gana por 2+)
    p_visit_115 = float(M[margen <= -2].sum())   # visitante -1.5
    p_local_p15 = float(M[margen >= -1].sum())   # local +1.5 (pierde por ≤1 o gana)
    p_visit_p15 = float(M[margen <= 1].sum())    # visitante +1.5
    p_local_p25 = float(M[margen >= -2].sum())   # local +2.5 (pierde por ≤2 o gana)
    p_visit_p25 = float(M[margen <= 2].sum())    # visitante +2.5

    _r = lambda v: round(v * 100, 1)
    return {
        "disponible": True,
        "runs_local": round(lam_l, 2), "runs_visit": round(lam_v, 2),
        "total_esperado": round(lam_l + lam_v, 2),
        "moneyline": {"local": _r(p_local), "visitante": _r(p_visit)},
        "run_line": {
            "local_-1.5": _r(p_local_115), "visitante_-1.5": _r(p_visit_115),
            "local_+1.5": _r(p_local_p15), "visitante_+1.5": _r(p_visit_p15),
            "local_+2.5": _r(p_local_p25), "visitante_+2.5": _r(p_visit_p25),
        },
        "total": {"linea": linea_total, "over": _r(p_over), "under": _r(1 - p_over)},
    }


def info():
    m = _modelo_activo()
    if not m:
        return "mlb_runs_model: sin modelo"
    return (f"mlb_runs_model: {m['n_equipos']} equipos · {m['n_juegos']} juegos · "
            f"ventaja_local={m['home_adv']:.3f} · media_runs={m.get('media_runs')} · "
            f"temporada {m['anio']} · fit {m['fecha_fit']}")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("Entrenando modelo de carreras MLB…")
    entrenar()
    print(info())
    for l, v in [("Los Angeles Dodgers", "Colorado Rockies"),
                 ("New York Yankees", "Boston Red Sox"),
                 ("Chicago White Sox", "Houston Astros")]:
        r = predecir(l, v)
        if not r["disponible"]:
            print(f"\n{l} vs {v}: no disponible"); continue
        print(f"\n{l} (local) vs {v}:  runs {r['runs_local']} - {r['runs_visit']} (total {r['total_esperado']})")
        print(f"  ML: local {r['moneyline']['local']}% / visita {r['moneyline']['visitante']}%")
        print(f"  Total {r['total']['linea']}: Over {r['total']['over']}% / Under {r['total']['under']}%")
        print(f"  Run line: local -1.5 {r['run_line']['local_-1.5']}% | visita +1.5 {r['run_line']['visitante_+1.5']}%")
