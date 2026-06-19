# -*- coding: utf-8 -*-
"""
PARLAY LOG — Lee / resuelve / estadísticas de parlay_history.json.

Kiro's _guardar_parlay() ya escribe en data/parlay_history.json; este módulo
provee las funciones de lectura, auto-resolve y estadísticas que la UI necesita.
"""
import json, os, logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
_PATH = os.path.join("data", "parlay_history.json")


def _cargar() -> list:
    if not os.path.exists(_PATH):
        return []
    try:
        with open(_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _guardar(log: list):
    os.makedirs("data", exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(log[-500:], f, ensure_ascii=False, indent=1)


# ─── Lectura ─────────────────────────────────────────────────────────────────

def historial(dias: int = 14) -> list:
    """Parlays de los últimos N días, más recientes primero."""
    fecha_min = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    log = _cargar()
    return sorted(
        [e for e in log if e.get("fecha", "") >= fecha_min],
        key=lambda x: x.get("id", ""), reverse=True,
    )


def stats_parlays() -> dict:
    """Estadísticas globales de todos los parlays resueltos."""
    log = _cargar()
    resueltos = [e for e in log if e.get("estado") not in (None, "pendiente")]
    totales = len(resueltos)
    ganados  = sum(1 for e in resueltos if e["estado"] == "ganado")
    perdidos = sum(1 for e in resueltos if e["estado"] == "perdido")
    parciales = sum(1 for e in resueltos if e["estado"] == "parcial")

    roi = 0.0
    for e in resueltos:
        if e["estado"] == "ganado":
            roi += e.get("cuota", 2.0) - 1
        else:
            roi -= 1

    por_tipo: dict = {}
    for e in resueltos:
        t = e.get("tipo", "OTRO")
        if t not in por_tipo:
            por_tipo[t] = {"total": 0, "ganados": 0, "perdidos": 0, "parciales": 0}
        por_tipo[t]["total"] += 1
        key = e["estado"] if e["estado"] in ("ganados", "perdidos", "parciales") else e["estado"] + "s"
        por_tipo[t][key] = por_tipo[t].get(key, 0) + 1

    return {
        "total":     totales,
        "ganados":   ganados,
        "perdidos":  perdidos,
        "parciales": parciales,
        "pendientes": sum(1 for e in log if e.get("estado") in (None, "pendiente")),
        "win_rate":  round(ganados / totales * 100, 1) if totales else 0.0,
        "roi":       round(roi / totales * 100, 1) if totales else 0.0,
        "por_tipo":  por_tipo,
    }


# ─── Auto-resolve ─────────────────────────────────────────────────────────────

def resolver_parlay_por_id(pid: str, estado: str, legs_ganadas: int = None):
    """Marca manualmente el resultado de un parlay (estado = ganado/perdido/parcial)."""
    log = _cargar()
    for e in log:
        if e.get("id") == pid:
            e["estado"] = estado
            if legs_ganadas is not None:
                e["legs_ganadas"] = legs_ganadas
            _guardar(log)
            return True
    return False


def auto_resolver_con_picks(pick_resultados: dict) -> int:
    """
    Cruza legs de parlays pendientes con un mapa {pick_texto_lower: bool}.
    Marca automáticamente parlays cuando TODOS sus legs tienen resultado conocido.

    Retorna el número de parlays resueltos en esta llamada.
    """
    log = _cargar()
    resueltos = 0
    cambios = False

    for entry in log:
        if entry.get("estado") not in (None, "pendiente"):
            continue
        legs = entry.get("legs", [])
        legs_r: list[bool | None] = []
        todos_conocidos = True

        for leg in legs:
            pick_key = leg.get("pick", "").strip().lower()
            evento_key = leg.get("evento", "").strip().lower()
            resultado_leg = None

            for k, v in pick_resultados.items():
                kn = k.lower()
                if kn in pick_key or pick_key in kn:
                    resultado_leg = v
                    break
                # También intentar match por evento
                if evento_key and (kn in evento_key or evento_key in kn):
                    resultado_leg = v
                    break

            if resultado_leg is None:
                todos_conocidos = False
                break
            legs_r.append(resultado_leg)

        if todos_conocidos and legs_r:
            ganadas = sum(1 for r in legs_r if r)
            total = len(legs_r)
            entry["estado"] = "ganado" if ganadas == total else (
                "parcial" if ganadas > 0 else "perdido"
            )
            entry["legs_ganadas"] = ganadas
            entry["legs_totales"] = total
            resueltos += 1
            cambios = True

    if cambios:
        _guardar(log)
    return resueltos
