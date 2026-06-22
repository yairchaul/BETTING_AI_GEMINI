# -*- coding: utf-8 -*-
"""
MOTOR DIXON-COLES — fuerza ofensiva/defensiva + Poisson con corrección τ.

Replica la base matemática del método profesional de predicción de fútbol
(Dixon & Coles, 1997): estima por máxima verosimilitud los coeficientes de
ATAQUE y DEFENSA de cada selección, una ventaja de localía global, y un
parámetro de correlación ρ que corrige la conocida subestimación de Poisson
en los marcadores bajos (0-0, 1-0, 0-1, 1-1).

Con esos coeficientes calcula los goles esperados (λ) de cada equipo y de ahí
la MATRIZ de probabilidad de cada marcador exacto → marcador correcto, 1X2,
Over/Under y BTTS, todos derivados de la MISMA matriz.

Diferencias vs. los notebooks de Colab que circulan:
  • Sin scipy.optimize: optimizador propio (Adam) sobre el gradiente analítico
    de la log-verosimilitud Poisson (problema cóncavo → converge fiable). El
    proyecto ya evita scipy; esto funciona igual en Streamlit Cloud.
  • Sin PyMC/MCMC en vivo: muestrear miles de combinaciones tarda minutos por
    partido y volvería la app inusable. El ajuste se CACHEA (semanal) y en vivo
    sólo se leen los coeficientes.
  • Decaimiento temporal (un partido de hace 3 años pesa menos que uno reciente)
    vía pesos exp(-ξ·días).

Fuente de datos: martj42/international_results (reutiliza motors.international_results).
Sólo cubre SELECCIONES. Para clubes, predecir() devuelve disponible=False y el
motor de fútbol cae a su lógica previa.
"""
import os
import math
import pickle
import logging
from datetime import datetime

import numpy as np

from motors.international_results import _cargar_datos, _resolve

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join("data", "dixon_coles_params.pkl")
CACHE_DAYS = 7                  # refrescar coeficientes semanalmente
DESDE_ANIO_DEFAULT = 2018       # como en los videos: datos recientes, menos ruido
MIN_PARTIDOS = 8                # un equipo necesita ≥8 apariciones para tener coef. propio
HALF_LIFE_DAYS = 540            # vida media del decaimiento temporal (~18 meses)
XI = math.log(2) / HALF_LIFE_DAYS
MAX_GOLES = 7                   # matriz 0..7 por lado
REG = 2.0                       # ridge (shrinkage de equipos con pocos datos)
PIN = 1000.0                    # fuerza la restricción de identificabilidad Σatk≈0

_FACT = np.array([math.factorial(k) for k in range(MAX_GOLES + 1)], dtype=float)

# Cache en memoria del módulo
_modelo = None


# ──────────────────────────────────────────────────────────────────────────
# Carga + preparación de datos
# ──────────────────────────────────────────────────────────────────────────
def _preparar_datos(desde_anio=DESDE_ANIO_DEFAULT, hasta_fecha=None, ref_fecha=None):
    """Filtra el dataset y arma arrays numpy para el ajuste.

    hasta_fecha: 'YYYY-MM-DD' — sólo partidos <= esa fecha (para backtesting).
    ref_fecha:   fecha de referencia del decaimiento temporal (por defecto, la
                 más reciente usada). Partidos más viejos pesan menos.
    Devuelve (arrays, idx_equipo) o None si no hay datos.
    """
    filas = _cargar_datos()
    if not filas:
        return None

    desde_str = f"{desde_anio}-01-01"
    sel = []
    for r in filas:
        f = r.get("fecha", "")
        if f < desde_str:
            continue
        if hasta_fecha and f > hasta_fecha:
            continue
        sel.append(r)
    if len(sel) < 200:
        return None

    # Conteo de apariciones para decidir qué equipos tienen coeficiente propio
    apariciones = {}
    for r in sel:
        apariciones[r["local"]] = apariciones.get(r["local"], 0) + 1
        apariciones[r["visita"]] = apariciones.get(r["visita"], 0) + 1
    elegibles = {t for t, c in apariciones.items() if c >= MIN_PARTIDOS}
    if len(elegibles) < 8:
        return None

    idx = {t: i for i, t in enumerate(sorted(elegibles))}

    if ref_fecha is None:
        ref_fecha = max(r["fecha"] for r in sel)
    try:
        ref_dt = datetime.strptime(ref_fecha[:10], "%Y-%m-%d")
    except Exception:
        ref_dt = datetime.now()

    a, b, x, y, m, w = [], [], [], [], [], []
    for r in sel:
        tl, tv = r["local"], r["visita"]
        if tl not in idx or tv not in idx:
            continue
        try:
            dt = datetime.strptime(r["fecha"][:10], "%Y-%m-%d")
            dias = max(0, (ref_dt - dt).days)
        except Exception:
            dias = 0
        a.append(idx[tl])
        b.append(idx[tv])
        x.append(r["goles_local"])
        y.append(r["goles_visita"])
        m.append(0.0 if r.get("neutral") else 1.0)   # ventaja local sólo si NO es neutral
        w.append(math.exp(-XI * dias))

    if len(a) < 200:
        return None

    arrays = {
        "a": np.asarray(a, dtype=np.intp),
        "b": np.asarray(b, dtype=np.intp),
        "x": np.asarray(x, dtype=float),
        "y": np.asarray(y, dtype=float),
        "m": np.asarray(m, dtype=float),
        "w": np.asarray(w, dtype=float),
        "n": len(idx),
    }
    return arrays, idx


# ──────────────────────────────────────────────────────────────────────────
# Ajuste por máxima verosimilitud (Poisson) con gradiente analítico + Adam
# ──────────────────────────────────────────────────────────────────────────
def _ajustar_poisson(arr, iters=6000, lr=0.08):
    """Maximiza la log-verosimilitud Poisson ponderada para estimar
    atk[], dfn[] (ataque/defensa por equipo) y h (ventaja de localía).

    λ_local = exp(h·m + atk_i − dfn_j)   μ_visit = exp(atk_j − dfn_i)
    Problema cóncavo → Adam con gradiente analítico converge de forma fiable.
    Incluye ridge (shrinkage) y una penalización que fija Σatk≈0
    (identificabilidad: λ,μ son invariantes a desplazar atk y dfn juntos).
    """
    a, b, x, y, m, w = arr["a"], arr["b"], arr["x"], arr["y"], arr["m"], arr["w"]
    n = arr["n"]

    atk = np.zeros(n)
    dfn = np.zeros(n)
    h = 0.25  # arranque típico de ventaja local

    # Estados de Adam
    def _z():
        return (np.zeros(n), np.zeros(n), 0.0)
    m_atk, m_dfn, m_h = _z()
    v_atk, v_dfn, v_h = _z()
    b1, b2, eps = 0.9, 0.999, 1e-8

    for t in range(1, iters + 1):
        eta_home = h * m + atk[a] - dfn[b]
        eta_away = atk[b] - dfn[a]
        np.clip(eta_home, -4.0, 4.0, out=eta_home)
        np.clip(eta_away, -4.0, 4.0, out=eta_away)
        lam = np.exp(eta_home)
        mu = np.exp(eta_away)

        # Residuales ponderados
        rh = w * (x - lam)
        ra = w * (y - mu)

        # Gradiente de la log-verosimilitud
        g_atk = (np.bincount(a, weights=rh, minlength=n)
                 + np.bincount(b, weights=ra, minlength=n))
        g_dfn = (-np.bincount(b, weights=rh, minlength=n)
                 - np.bincount(a, weights=ra, minlength=n))
        g_h = float(np.sum(m * rh))

        # Ridge (shrinkage hacia 0 de equipos con pocos datos)
        g_atk -= REG * atk
        g_dfn -= REG * dfn
        # Restricción Σatk≈0 (identificabilidad)
        g_atk -= PIN * atk.sum()

        # Paso de Adam (ascenso de gradiente)
        m_atk = b1 * m_atk + (1 - b1) * g_atk
        v_atk = b2 * v_atk + (1 - b2) * g_atk * g_atk
        m_dfn = b1 * m_dfn + (1 - b1) * g_dfn
        v_dfn = b2 * v_dfn + (1 - b2) * g_dfn * g_dfn
        m_h = b1 * m_h + (1 - b1) * g_h
        v_h = b2 * v_h + (1 - b2) * g_h * g_h

        bc1 = 1 - b1 ** t
        bc2 = 1 - b2 ** t
        atk += lr * (m_atk / bc1) / (np.sqrt(v_atk / bc2) + eps)
        dfn += lr * (m_dfn / bc1) / (np.sqrt(v_dfn / bc2) + eps)
        h += lr * (m_h / bc1) / (math.sqrt(v_h / bc2) + eps)

        if t % 500 == 0:
            gnorm = math.sqrt(float(g_atk @ g_atk + g_dfn @ g_dfn) + g_h * g_h)
            if gnorm < 1e-3:
                break

    return atk, dfn, float(h)


def _ajustar_rho(arr, atk, dfn, h):
    """Estima ρ (corrección Dixon-Coles de marcadores bajos) por barrido 1-D,
    manteniendo fijos atk/dfn/h. Sólo los marcadores en {(0,0),(0,1),(1,0),(1,1)}
    aportan; el resto tiene τ=1 (log 0)."""
    a, b, x, y, m, w = arr["a"], arr["b"], arr["x"], arr["y"], arr["m"], arr["w"]
    eta_home = np.clip(h * m + atk[a] - dfn[b], -4.0, 4.0)
    eta_away = np.clip(atk[b] - dfn[a], -4.0, 4.0)
    lam = np.exp(eta_home)
    mu = np.exp(eta_away)

    c00 = (x == 0) & (y == 0)
    c01 = (x == 0) & (y == 1)
    c10 = (x == 1) & (y == 0)
    c11 = (x == 1) & (y == 1)

    mejor_rho, mejor_ll = 0.0, -1e18
    for rho in np.arange(-0.25, 0.151, 0.005):
        tau = np.ones_like(lam)
        tau[c00] = 1.0 - lam[c00] * mu[c00] * rho
        tau[c01] = 1.0 + lam[c01] * rho
        tau[c10] = 1.0 + mu[c10] * rho
        tau[c11] = 1.0 - rho
        tau = np.clip(tau, 1e-6, None)
        ll = float(np.sum(w * np.log(tau)))
        if ll > mejor_ll:
            mejor_ll, mejor_rho = ll, float(rho)
    return mejor_rho


# ──────────────────────────────────────────────────────────────────────────
# Entrenamiento / cache
# ──────────────────────────────────────────────────────────────────────────
def entrenar(desde_anio=DESDE_ANIO_DEFAULT, hasta_fecha=None, ref_fecha=None, guardar=True):
    """Ajusta el modelo completo y (opcionalmente) lo cachea en disco."""
    prep = _preparar_datos(desde_anio, hasta_fecha, ref_fecha)
    if prep is None:
        logger.warning("dixon_coles: datos insuficientes para entrenar")
        return None
    arr, idx = prep
    atk, dfn, h = _ajustar_poisson(arr)
    rho = _ajustar_rho(arr, atk, dfn, h)

    modelo = {
        "idx": idx,                 # nombre normalizado → índice
        "atk": atk,
        "dfn": dfn,
        "home_adv": h,
        "rho": rho,
        "n_equipos": arr["n"],
        "n_partidos": int(arr["a"].shape[0]),
        "desde_anio": desde_anio,
        "hasta_fecha": hasta_fecha,
        "fecha_fit": datetime.now().strftime("%Y-%m-%d"),
    }
    if guardar and hasta_fecha is None:
        try:
            os.makedirs("data", exist_ok=True)
            with open(CACHE_PATH, "wb") as f:
                pickle.dump(modelo, f)
            logger.info(
                f"dixon_coles: modelo guardado ({modelo['n_equipos']} equipos, "
                f"{modelo['n_partidos']} partidos, ρ={rho:.3f}, h={h:.3f})"
            )
        except Exception as e:
            logger.warning(f"dixon_coles: no se pudo guardar cache: {e}")
    return modelo


def _modelo_activo(force_refit=False):
    """Devuelve el modelo cacheado (lo entrena/recarga si hace falta)."""
    global _modelo
    if _modelo is not None and not force_refit:
        return _modelo

    if not force_refit and os.path.exists(CACHE_PATH):
        try:
            edad = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_PATH))).days
            if edad < CACHE_DAYS:
                with open(CACHE_PATH, "rb") as f:
                    _modelo = pickle.load(f)
                return _modelo
        except Exception as e:
            logger.warning(f"dixon_coles: cache ilegible ({e}), reentrenando")

    _modelo = entrenar()
    return _modelo


# ──────────────────────────────────────────────────────────────────────────
# Predicción
# ──────────────────────────────────────────────────────────────────────────
def _poisson_col(lam):
    """Vector P(0..MAX_GOLES) para una Poisson(λ)."""
    ks = np.arange(MAX_GOLES + 1)
    return np.exp(-lam) * np.power(lam, ks) / _FACT


def matriz_marcadores(lam_l, lam_v, rho=0.0):
    """Matriz (MAX+1 × MAX+1) de P(marcador = i-j) con corrección τ Dixon-Coles.
    Filas = goles del local, columnas = goles del visitante. Normalizada."""
    lam_l = float(np.clip(lam_l, 0.05, 6.0))
    lam_v = float(np.clip(lam_v, 0.05, 6.0))
    pl = _poisson_col(lam_l)
    pv = _poisson_col(lam_v)
    M = np.outer(pl, pv)
    # Corrección de marcadores bajos
    M[0, 0] *= 1.0 - lam_l * lam_v * rho
    M[0, 1] *= 1.0 + lam_l * rho
    M[1, 0] *= 1.0 + lam_v * rho
    M[1, 1] *= 1.0 - rho
    M = np.clip(M, 0.0, None)
    s = M.sum()
    if s > 0:
        M /= s
    return M


def get_lambdas(local, visitante, neutral=True, modelo=None):
    """(λ_local, λ_visitante) según Dixon-Coles, o None si falta algún equipo."""
    modelo = modelo or _modelo_activo()
    if not modelo:
        return None
    idx = modelo["idx"]
    tl, tv = _resolve(local), _resolve(visitante)
    if tl not in idx or tv not in idx:
        return None
    i, j = idx[tl], idx[tv]
    atk, dfn, h = modelo["atk"], modelo["dfn"], modelo["home_adv"]
    m = 0.0 if neutral else 1.0
    lam_l = math.exp(min(4.0, m * h + atk[i] - dfn[j]))
    lam_v = math.exp(min(4.0, atk[j] - dfn[i]))
    return float(lam_l), float(lam_v)


def predecir(local, visitante, neutral=True, top_n=5, modelo=None):
    """Predicción completa de un partido a partir de la matriz Poisson corregida.

    Devuelve dict con: disponible, xg_local, xg_visit, prob (1X2), over/under,
    btts, marcador_top (lista de {marcador, pct, resultado}) y matriz (para heatmap).
    Si algún equipo no está en el modelo → {disponible: False}.
    """
    modelo = modelo or _modelo_activo()
    lams = get_lambdas(local, visitante, neutral=neutral, modelo=modelo)
    if lams is None:
        return {"disponible": False}
    lam_l, lam_v = lams
    rho = modelo.get("rho", 0.0)
    M = matriz_marcadores(lam_l, lam_v, rho)

    n = M.shape[0]
    p_home = float(np.tril(M, -1).sum())   # i > j
    p_draw = float(np.trace(M))            # i == j
    p_away = float(np.triu(M, 1).sum())    # i < j

    idx_i, idx_j = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    tot = idx_i + idx_j
    p_over15 = float(M[tot > 1].sum())
    p_over25 = float(M[tot > 2].sum())
    p_over35 = float(M[tot > 3].sum())
    p_btts = float(M[(idx_i > 0) & (idx_j > 0)].sum())

    # Top-N marcadores correctos
    plano = [(M[i, j], i, j) for i in range(n) for j in range(n)]
    plano.sort(reverse=True)
    top = []
    for p, i, j in plano[:top_n]:
        res = "LOCAL" if i > j else ("EMPATE" if i == j else "VISITANTE")
        top.append({"marcador": f"{i}-{j}", "pct": round(p * 100, 1), "resultado": res})

    _r = lambda v: round(v * 100, 1)
    return {
        "disponible": True,
        "xg_local": round(lam_l, 2),
        "xg_visit": round(lam_v, 2),
        "rho": round(rho, 3),
        "prob": {"local": _r(p_home), "empate": _r(p_draw), "visitante": _r(p_away)},
        "over_under": {"over_1.5": _r(p_over15), "over_2.5": _r(p_over25),
                       "over_3.5": _r(p_over35), "under_2.5": _r(1 - p_over25)},
        "btts": {"si": _r(p_btts), "no": _r(1 - p_btts)},
        "marcador_top": top,
        "matriz": M.tolist(),
    }


def info():
    """Resumen del modelo activo (para diagnóstico)."""
    m = _modelo_activo()
    if not m:
        return "dixon_coles: sin modelo (datos insuficientes)"
    return (f"dixon_coles: {m['n_equipos']} equipos · {m['n_partidos']} partidos "
            f"· ρ={m['rho']:.3f} · ventaja_local={m['home_adv']:.3f} "
            f"· desde {m['desde_anio']} · fit {m['fecha_fit']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Entrenando Dixon-Coles…")
    entrenar()
    print(info())
    for l, v in [("Argentina", "Austria"), ("Brazil", "Haiti"), ("Mexico", "South Korea")]:
        r = predecir(l, v)
        if not r["disponible"]:
            print(f"\n{l} vs {v}: no disponible")
            continue
        print(f"\n{l} vs {v}  (xG {r['xg_local']} - {r['xg_visit']})")
        print(f"  1X2: L {r['prob']['local']}% | E {r['prob']['empate']}% | V {r['prob']['visitante']}%")
        print("  Top marcadores:", ", ".join(f"{t['marcador']} ({t['pct']}%)" for t in r["marcador_top"]))
