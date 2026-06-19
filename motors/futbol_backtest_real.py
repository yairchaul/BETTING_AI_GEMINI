# -*- coding: utf-8 -*-
"""
BACKTEST REAL FÚTBOL — corre el motor jerárquico sobre partidos finalizados
de las ligas principales en los últimos N días y compara el pick contra el
marcador real (Moneyline, Over/Under de goles, BTTS y combinados).

Genera data/futbol_backtest_real.json con la precisión por mercado.
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Ligas que se evaluan por defecto (alta cobertura de resultados en ESPN)
LIGAS_DEFAULT = [
    "FIFA World Cup", "UEFA Champions League", "UEFA Europa League",
    "Copa Libertadores", "Copa Sudamericana",
    "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
    "Eredivisie", "Primeira Liga", "Liga MX", "MLS", "Brazilian Serie A",
    "Argentine Liga Profesional", "Championship",
]

OUT_PATH = os.path.join("data", "futbol_backtest_real.json")


def _grade_pick(pick: str, gl: int, gv: int, local: str, visitante: str):
    """Devuelve (mercado, acierto:bool|None). None = no evaluable (p.ej. HT)."""
    p = (pick or "").lower()
    total = gl + gv

    if not p or "revisar" in p:
        return None, None

    # Over 1.5 HT: no hay marcador de primer tiempo en el scoreboard → no evaluable
    if "ht" in p:
        return None, None

    # Combinado: "Gana X + Over Y"
    if "+" in p and ("over" in p or "under" in p):
        partes = p.split("+")
        gana_ok = None
        if local.lower() in partes[0]:
            gana_ok = gl > gv
        elif visitante.lower() in partes[0]:
            gana_ok = gv > gl
        elif "gana" in partes[0]:
            # favorito por nombre dentro del texto
            gana_ok = gl > gv if local.lower() in p else (gv > gl if visitante.lower() in p else None)
        ou_ok = None
        for ln in (3.5, 2.5, 1.5, 0.5):
            if str(ln) in partes[1]:
                ou_ok = total > ln if "over" in partes[1] else total < ln
                break
        if gana_ok is None or ou_ok is None:
            return "combo", None
        return "combo", (gana_ok and ou_ok)

    # BTTS
    if "btts" in p or "ambos anotan" in p:
        return "btts", (gl > 0 and gv > 0)

    # Favorito anota (Over 0.5 de un equipo)
    if "over 0.5" in p:
        if local.lower() in p:
            return "over_under", gl >= 1
        if visitante.lower() in p:
            return "over_under", gv >= 1
        return "over_under", total >= 1

    # Over/Under total de goles
    for ln in (3.5, 2.5, 1.5):
        if f"over {ln}" in p:
            return "over_under", total > ln
        if f"under {ln}" in p:
            return "over_under", total < ln

    # Moneyline (LOCAL/VISITANTE/Gana X)
    if "local" in p or (local.lower() in p and "gana" in p):
        return "moneyline", gl > gv
    if "visitante" in p or (visitante.lower() in p and "gana" in p):
        return "moneyline", gv > gl

    return None, None


def ejecutar_futbol_backtest_real(dias: int = 10, ligas=None, progreso_cb=None):
    """Corre el motor de fútbol sobre partidos finalizados y mide su precisión."""
    from espn_futbol import ESPN_FUTBOL
    from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico

    ligas = ligas or LIGAS_DEFAULT
    scraper = ESPN_FUTBOL()

    # 1. Recolectar partidos finalizados de cada liga
    finalizados = []
    for i, liga in enumerate(ligas):
        if progreso_cb:
            progreso_cb(i + 1, len(ligas), f"Descargando {liga}...")
        try:
            partidos = scraper.gestor.obtener_partidos(liga, dias_atras=int(dias))
        except Exception as e:
            logger.warning(f"No se pudo cargar {liga}: {e}")
            continue
        for p in partidos:
            if p.get("completado") and p.get("goles_local") is not None and p.get("goles_visitante") is not None:
                finalizados.append(p)

    if not finalizados:
        reporte = {"timestamp": datetime.now().isoformat(), "partidos": 0,
                   "error": "No se encontraron partidos finalizados en el rango."}
        _guardar(reporte)
        return reporte

    # 2. Poblar historial (últimos 5) de todos los equipos involucrados
    if progreso_cb:
        progreso_cb(len(ligas), len(ligas), "Poblando historial de equipos...")
    try:
        scraper.poblar_historial(finalizados)
    except Exception as e:
        logger.warning(f"Poblar historial fútbol: {e}")

    # 3. Correr el motor y graduar
    mercados = {
        "moneyline": {"aciertos": 0, "total": 0},
        "over_under": {"aciertos": 0, "total": 0},
        "btts": {"aciertos": 0, "total": 0},
        "combo": {"aciertos": 0, "total": 0},
    }
    detalle = []
    evaluables = 0

    for j, p in enumerate(finalizados):
        if progreso_cb:
            progreso_cb(j + 1, len(finalizados), f"Analizando {p.get('home')} vs {p.get('away')}")
        local = p.get("home") or p.get("local", "")
        visitante = p.get("away") or p.get("visitante", "")
        try:
            res = analizar_futbol_jerarquico(local, visitante,
                                             es_torneo=p.get("es_torneo", False),
                                             fase=p.get("fase", ""),
                                             liga=p.get("liga", ""))
        except Exception as e:
            logger.debug(f"Motor fútbol falló {local} vs {visitante}: {e}")
            continue

        pick = res.get("pick", "")
        gl = int(p["goles_local"])
        gv = int(p["goles_visitante"])
        mercado, acierto = _grade_pick(pick, gl, gv, local, visitante)
        if mercado is None or acierto is None:
            continue
        evaluables += 1
        mercados[mercado]["total"] += 1
        if acierto:
            mercados[mercado]["aciertos"] += 1
        detalle.append({
            "fecha": str(p.get("fecha_partido") or p.get("fecha") or "")[:10],
            "partido": f"{local} {gl}-{gv} {visitante}",
            "pick": pick, "mercado": mercado,
            "confianza": res.get("confianza", 0),
            "acierto": acierto,
        })

    # 4. Calcular precisiones
    for m in mercados.values():
        m["precision"] = round(m["aciertos"] / m["total"] * 100, 1) if m["total"] else 0.0

    aciertos_glob = sum(m["aciertos"] for m in mercados.values())
    total_glob = sum(m["total"] for m in mercados.values())
    precision_global = round(aciertos_glob / total_glob * 100, 1) if total_glob else 0.0

    reporte = {
        "timestamp": datetime.now().isoformat(),
        "partidos": len(finalizados),
        "evaluados": evaluables,
        "precision_global": precision_global,
        "mercados": mercados,
        "detalle": detalle[:60],
        "ligas": ligas,
        "dias": int(dias),
        # Nota sobre por qué el backtest puede diferir de los picks en vivo:
        # El motor usa el historial de la DB (últimos 5 partidos de cada equipo).
        # Cuando se re-corre sobre partidos pasados, ese historial INCLUYE el
        # partido en cuestión (ya está guardado como resultado), lo que introduce
        # "leakage" de información futura. El pick real mostrado en el día del
        # partido usó el historial de ESE momento — no necesariamente el mismo.
        "nota_metodologia": (
            "Los picks del backtest se generan con el historial actual de la DB, "
            "que incluye resultados posteriores al partido evaluado (leakage). "
            "El pick real del día usó el historial disponible en ese momento. "
            "Por eso puede haber discrepancia entre el pick en vivo y el del backtest."
        ),
    }
    _guardar(reporte)
    logger.info(f"⚽ Backtest fútbol: {evaluables} picks evaluados · {precision_global}% global")
    return reporte


def _guardar(reporte: dict):
    os.makedirs("data", exist_ok=True)
    try:
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(reporte, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"No se pudo guardar el reporte de fútbol: {e}")
