# -*- coding: utf-8 -*-
"""
WC CEREBRO — Aprende de patrones reales del Mundial y calibra el motor.

Fuente base: martj42/international_results (49K+ partidos WC desde 1872).
Fuente live: data/futbol_backtest_real.json + data/pick_history.json
             (picks WC 2026 resueltos conforme avanza el torneo).

Tasas históricas WC reales (2014 + 2018 + 2022):
  Over 1.5:  73.3%   ← el pick más seguro en WC
  Over 2.5:  50.9%
  BTTS:      39.2%   ← el motor lo sobreestima → debemos penalizarlo
  Local win: 47.7%
  Empate:    21.4%
  Away win:  30.9%
  Avg goles: 2.81

El cerebro devuelve factores de ajuste por mercado que se aplican a la
confianza del motor ANTES de emitir el pick.
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Tasas históricas WC (2014–2022, calculadas sobre 192 partidos finales) ──
_WC_BASE = {
    "over_1.5":  73.3,
    "over_2.5":  50.9,
    "btts":      39.2,
    "local_win": 47.7,
    "empate":    21.4,
    "away_win":  30.9,
    "avg_goles": 2.81,
}

# Tasas por fase (estimadas de patrones históricos WC)
_WC_FASE = {
    "grupo": {
        "over_1.5": 75.0, "over_2.5": 53.0, "btts": 40.5,
        "local_win": 46.0, "empate": 22.0, "away_win": 32.0,
    },
    "octavos": {
        "over_1.5": 73.0, "over_2.5": 50.0, "btts": 38.0,
        "local_win": 50.0, "empate": 20.0, "away_win": 30.0,
    },
    "cuartos": {
        "over_1.5": 70.0, "over_2.5": 47.0, "btts": 37.0,
        "local_win": 52.0, "empate": 18.0, "away_win": 30.0,
    },
    "semi": {
        "over_1.5": 68.0, "over_2.5": 44.0, "btts": 35.0,
        "local_win": 53.0, "empate": 18.0, "away_win": 29.0,
    },
    "final": {
        "over_1.5": 66.0, "over_2.5": 42.0, "btts": 34.0,
        "local_win": 55.0, "empate": 15.0, "away_win": 30.0,
    },
}

_CACHE_PATH = os.path.join("data", "wc_cerebro_cache.json")


def _fase_key(fase: str) -> str:
    f = (fase or "").lower()
    if any(x in f for x in ("cuarto", "quarter")):
        return "cuartos"
    if any(x in f for x in ("semi",)):
        return "semi"
    if any(x in f for x in ("final",)):
        return "final"
    if any(x in f for x in ("octavo", "round of 16")):
        return "octavos"
    return "grupo"


def _leer_live_wc() -> dict:
    """Lee picks WC resueltos del historial para actualizar las tasas."""
    resultados = {"over_1.5": [], "over_2.5": [], "btts": [], "moneyline": []}
    try:
        ph_path = os.path.join("data", "pick_history.json")
        if not os.path.exists(ph_path):
            return resultados
        with open(ph_path, encoding="utf-8") as f:
            picks = json.load(f)
        wc_picks = [
            p for p in picks
            if (p.get("estado") in ("ganado", "perdido"))
            and ("world" in str(p.get("liga", "")).lower()
                 or "wc" in str(p.get("liga", "")).lower()
                 or "mundial" in str(p.get("liga", "")).lower())
        ]
        for p in wc_picks:
            mkt = (p.get("mercado") or "").upper()
            ok = p.get("estado") == "ganado"
            if "1.5" in mkt or "over_1" in mkt.lower():
                resultados["over_1.5"].append(ok)
            elif "2.5" in mkt:
                resultados["over_2.5"].append(ok)
            elif "btts" in mkt.lower():
                resultados["btts"].append(ok)
            elif "moneyline" in mkt.lower() or "1x2" in mkt.lower():
                resultados["moneyline"].append(ok)
    except Exception as e:
        logger.debug(f"wc_cerebro live: {e}")
    return resultados


def _merge_tasas(base: float, live: list, peso_live: float = 0.6) -> float:
    """Mezcla tasa base histórica con datos live del WC 2026."""
    if len(live) < 3:
        return base
    tasa_live = sum(live) / len(live) * 100
    # Más live data → más peso al live
    peso = min(0.85, peso_live + len(live) * 0.02)
    return round(base * (1 - peso) + tasa_live * peso, 1)


# ── Entorno de goles REAL de ESTE Mundial (resultados ya jugados) ───────────
# A diferencia de _leer_live_wc (que mide si los PICKS del motor acertaron), esto
# mide las tasas reales del torneo en curso: ¿cuántos goles, empates y BTTS está
# produciendo ESTE Mundial? Es la señal que el usuario pidió: calibrar con lo que
# de verdad está pasando, no solo con históricos 2014-2022.
_TORNEO_CACHE = {"ts": 0.0, "datos": None}


def _leer_resultados_wc_2026() -> dict:
    """Tasas reales del Mundial en curso desde international_results (torneo
    'FIFA World Cup' del año actual, excluyendo eliminatorias). Cacheado por
    sesión: los resultados solo cambian entre corridas. Devuelve {'n':0} si aún
    no hay suficientes partidos jugados."""
    import time
    if _TORNEO_CACHE["datos"] is not None and (time.time() - _TORNEO_CACHE["ts"]) < 1800:
        return _TORNEO_CACHE["datos"]
    res = {"n": 0}
    try:
        from motors.international_results import _cargar_datos
        anio = str(datetime.now().year)
        partidos = [
            r for r in _cargar_datos()
            if r.get("fecha", "")[:4] == anio
            and "world cup" in str(r.get("torneo", "")).lower()
            and "qualif" not in str(r.get("torneo", "")).lower()
        ]
        n = len(partidos)
        if n >= 5:
            tot = [r["goles_local"] + r["goles_visita"] for r in partidos]
            res = {
                "n": n,
                "over_1.5": round(sum(1 for t in tot if t > 1) / n * 100, 1),
                "over_2.5": round(sum(1 for t in tot if t > 2) / n * 100, 1),
                "btts": round(sum(1 for r in partidos if r["goles_local"] > 0 and r["goles_visita"] > 0) / n * 100, 1),
                "empate": round(sum(1 for r in partidos if r["goles_local"] == r["goles_visita"]) / n * 100, 1),
                "avg_goles": round(sum(tot) / n, 2),
            }
        else:
            res = {"n": n}
    except Exception as e:
        logger.debug(f"wc_cerebro resultados live: {e}")
    _TORNEO_CACHE.update(ts=time.time(), datos=res)
    return res


def factor_goles_torneo() -> float:
    """Multiplicador del nivel de goles de ESTE Mundial vs la media histórica WC
    (2.81). >1 si el torneo es más goleador (sube el xG del modelo y reduce los
    UNDER espurios contra equipos goleadores). Acotado [0.90, 1.18]; 1.0 si aún
    no hay suficientes partidos. Data-driven: lo decide el torneo, no una corazonada."""
    t = _leer_resultados_wc_2026()
    if t.get("n", 0) < 8 or not t.get("avg_goles"):
        return 1.0
    return round(max(0.90, min(1.18, t["avg_goles"] / _WC_BASE["avg_goles"])), 3)


def _blend_torneo(base: float, live_val, n: int, n_full: int = 60) -> float:
    """Mezcla la tasa base (histórica/fase) con la tasa REAL de este Mundial.
    El peso del torneo crece con los partidos jugados (hasta 0.6 cuando la fase
    de grupos está avanzada), porque el entorno propio del torneo manda."""
    if live_val is None or n < 5:
        return base
    peso = min(0.6, n / n_full * 0.6)
    return round(base * (1 - peso) + live_val * peso, 1)


def calcular_tasas(fase: str = "grupo") -> dict:
    """Devuelve tasas calibradas para el mercado WC en la fase dada.

    Tres capas, de más a menos específica: (1) entorno REAL de este Mundial
    (resultados ya jugados) con peso creciente; (2) acierto del motor en sus
    picks resueltos del torneo; (3) base histórica WC 2014-2022 por fase."""
    fase_k = _fase_key(fase)
    base = _WC_FASE.get(fase_k, _WC_FASE["grupo"])
    live = _leer_live_wc()
    torneo = _leer_resultados_wc_2026()
    nT = torneo.get("n", 0)

    def _capa(clave_base, clave_live):
        # 1) entorno real del torneo en curso  2) picks resueltos del motor
        v = _blend_torneo(base[clave_base], torneo.get(clave_base), nT)
        return _merge_tasas(v, live.get(clave_live, []))

    tasas = {
        "over_1.5": _capa("over_1.5", "over_1.5"),
        "over_2.5": _capa("over_2.5", "over_2.5"),
        "btts":     _capa("btts",     "btts"),
        "local_win": base["local_win"],
        "empate":    _blend_torneo(base["empate"], torneo.get("empate"), nT),
        "away_win":  base["away_win"],
        "avg_goles": torneo.get("avg_goles", _WC_BASE["avg_goles"]),
        "n_torneo":  nT,
    }
    return tasas


def factores_ajuste(fase: str = "grupo") -> dict:
    """
    Retorna factores multiplicativos para la confianza del motor.
    factor > 1 = boost, factor < 1 = penaliza.

    El motor usa threshold fijos (BTTS >= 60%).
    Los factores corrigen esos thresholds hacia las tasas reales del WC.
    """
    tasas = calcular_tasas(fase)

    # BTTS: motor threshold 60%, tasa real ~40% → penalizar fuertemente
    f_btts = round(tasas["btts"] / 60.0, 3)  # ~0.65 (penaliza)

    # Over 1.5: motor threshold 55%, tasa real ~73% → boost
    f_over15 = round(tasas["over_1.5"] / 55.0, 3)  # ~1.33 (boost)

    # Over 2.5: motor threshold 60%, tasa real ~51% → ligera penalización
    f_over25 = round(tasas["over_2.5"] / 60.0, 3)  # ~0.85

    # Moneyline local: motor threshold 55%, tasa real ~47% → penalizar
    f_local = round(tasas["local_win"] / 55.0, 3)   # ~0.87

    return {
        "BTTS":        f_btts,
        "OVER_1.5":    f_over15,
        "OVER_2.5":    f_over25,
        "MONEYLINE":   f_local,
        "tasas_reales": tasas,
        "fase": fase,
    }


def ajustar_pick(pick: str, confianza: float, es_torneo: bool, fase: str = "") -> tuple:
    """
    Aplica calibración WC al pick y su confianza.
    Devuelve (confianza_ajustada, nota_calibracion).
    """
    if not es_torneo:
        return confianza, ""

    factores = factores_ajuste(fase)
    tasas = factores["tasas_reales"]
    p = pick.lower()
    nota = ""

    if "btts" in p or "ambos anotan" in p:
        conf_nueva = round(confianza * factores["BTTS"], 1)
        nota = (f"WC: BTTS real {tasas['btts']:.0f}% "
                f"(histórico {_WC_BASE['btts']}%) → confianza ajustada de {confianza:.0f}% a {conf_nueva:.0f}%")
        return conf_nueva, nota

    if "over 1.5" in p:
        # Mezcla hacia la tasa WC (no multiplica) para NO inflar matchups
        # defensivos: 60% confianza del motor (específica del partido) + 40%
        # tasa WC. Así un partido cerrado no termina en 88% artificial.
        conf_nueva = round(min(88, 0.6 * confianza + 0.4 * tasas["over_1.5"]), 1)
        nota = (f"WC: Over 1.5 real {tasas['over_1.5']:.0f}% → confianza {confianza:.0f}% → {conf_nueva:.0f}%")
        return conf_nueva, nota

    if "over 2.5" in p or "over 3.5" in p:
        conf_nueva = round(confianza * factores["OVER_2.5"], 1)
        nota = (f"WC: Over 2.5+ real {tasas['over_2.5']:.0f}% → confianza ajustada a {conf_nueva:.0f}%")
        return conf_nueva, nota

    if "local" in p or "visitante" in p or "gana" in p:
        conf_nueva = round(confianza * factores["MONEYLINE"], 1)
        nota = f"WC: local gana {tasas['local_win']:.0f}% historicamente"
        return conf_nueva, nota

    return confianza, nota


def resumen_wc(fase: str = "grupo") -> str:
    """Resumen texto para mostrar en UI o pasar a Gemini."""
    tasas = calcular_tasas(fase)
    live = _leer_live_wc()
    n_live = sum(len(v) for v in live.values())
    nT = tasas.get("n_torneo", 0)
    base = (
        f"WC 2026 ({fase}): "
        f"Over 1.5 = {tasas['over_1.5']:.0f}% | "
        f"Empate = {tasas['empate']:.0f}% | "
        f"BTTS = {tasas['btts']:.0f}% | "
        f"Over 2.5 = {tasas['over_2.5']:.0f}%"
    )
    if nT >= 5:
        return base + f" · ({nT} partidos jugados de este Mundial, {tasas['avg_goles']:.1f} goles/partido)"
    if n_live:
        return base + f" · ({n_live} picks WC 2026 resueltos)"
    return base + " · (datos históricos WC 2014-2022)"
