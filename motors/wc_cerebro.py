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


def calcular_tasas(fase: str = "grupo") -> dict:
    """Devuelve tasas calibradas para el mercado WC en la fase dada."""
    fase_k = _fase_key(fase)
    base = _WC_FASE.get(fase_k, _WC_FASE["grupo"])
    live = _leer_live_wc()

    tasas = {
        "over_1.5": _merge_tasas(base["over_1.5"], live.get("over_1.5", [])),
        "over_2.5": _merge_tasas(base["over_2.5"], live.get("over_2.5", [])),
        "btts":     _merge_tasas(base["btts"],     live.get("btts", [])),
        "local_win": base["local_win"],
        "empate":    base["empate"],
        "away_win":  base["away_win"],
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
    return (
        f"WC 2026 ({fase}): "
        f"Over 1.5 = {tasas['over_1.5']:.0f}% | "
        f"BTTS = {tasas['btts']:.0f}% | "
        f"Over 2.5 = {tasas['over_2.5']:.0f}% | "
        f"Local gana = {tasas['local_win']:.0f}%"
        + (f" · ({n_live} picks WC 2026 resueltos)" if n_live else " · (datos históricos WC 2014-2022)")
    )
