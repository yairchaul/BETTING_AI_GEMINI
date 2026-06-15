# -*- coding: utf-8 -*-
"""
NBA PROPS ANALYZER — V1
Genera props de jugadores (3PM, puntos, rebotes, asistencias) combinando:
  - Stats de DB (player_stats table)
  - PACE y ratings del motor O/U de NBA
  - Matchup defensivo del equipo rival
"""

import logging
from typing import Dict, List, Optional
from utils.database_manager import db

logger = logging.getLogger(__name__)

# ─── Líneas de referencia típicas en books ───────────────────────────────────
DEFAULT_LINES = {
    "tres_pm":    2.5,
    "puntos":    20.5,
    "rebotes":    5.5,
    "asistencias": 4.5,
}

# ─── Equipos con peor defensa en triples (permiten más 3PM al rival) ─────────
DEF_3PM_RANKING = {
    # Valor > 1.0 = mala defensa en 3s, favorece al bateador de triples
    "Sacramento Kings":      1.22, "Charlotte Hornets":   1.20, "Washington Wizards": 1.18,
    "Detroit Pistons":       1.16, "Orlando Magic":       1.04, "Chicago Bulls":      1.04,
    "New Orleans Pelicans":  1.02, "Utah Jazz":           1.01, "Brooklyn Nets":      1.00,
    "Houston Rockets":       0.99, "Toronto Raptors":     0.98, "Dallas Mavericks":   0.97,
    "Phoenix Suns":          0.96, "Los Angeles Lakers":  0.95, "Golden State Warriors": 0.95,
    "Portland Trail Blazers": 0.94, "San Antonio Spurs":  0.93, "Miami Heat":         0.92,
    "Indiana Pacers":        0.92, "Oklahoma City Thunder": 0.91, "Memphis Grizzlies": 0.90,
    "Minnesota Timberwolves": 0.88, "Cleveland Cavaliers": 0.87, "Atlanta Hawks":     0.87,
    "New York Knicks":       0.86, "Milwaukee Bucks":     0.85, "Los Angeles Clippers": 0.84,
    "Denver Nuggets":        0.83, "Boston Celtics":      0.80, "Philadelphia 76ers": 0.79,
}

# ─── Equipos con alto PACE (beneficia volume shooters) ───────────────────────
PACE_TEAM = {
    "Sacramento Kings": 104, "Boston Celtics": 103, "Golden State Warriors": 102,
    "Atlanta Hawks": 101, "Dallas Mavericks": 101, "Indiana Pacers": 101,
    "Oklahoma City Thunder": 100, "Philadelphia 76ers": 100, "Orlando Magic": 99,
    "Los Angeles Lakers": 99, "Houston Rockets": 99, "Minnesota Timberwolves": 98,
    "Miami Heat": 98, "New York Knicks": 97, "Milwaukee Bucks": 97,
    "Cleveland Cavaliers": 97, "Denver Nuggets": 97, "Phoenix Suns": 96,
    "Memphis Grizzlies": 96, "New Orleans Pelicans": 96, "Los Angeles Clippers": 95,
    "Utah Jazz": 95, "Portland Trail Blazers": 95, "Chicago Bulls": 95,
    "Charlotte Hornets": 94, "Toronto Raptors": 94, "Washington Wizards": 93,
    "Brooklyn Nets": 93, "San Antonio Spurs": 93, "Detroit Pistons": 92,
}


class NBAPropAnalyzer:
    """Genera candidatos de props NBA con probabilidad estimada."""

    def analizar_props_partido(
        self,
        equipo_local: str,
        equipo_visit: str,
        top_n: int = 5,
    ) -> Dict:
        """
        Retorna los mejores candidatos de props para ambos equipos.

        Returns:
            {
              "tres_pm": [...],
              "puntos":  [...],
              "aviso":   str,
            }
        """
        props_local = self._analizar_equipo(equipo_local, rival=equipo_visit)
        props_visit = self._analizar_equipo(equipo_visit, rival=equipo_local)

        return {
            "local":  equipo_local,
            "visit":  equipo_visit,
            "tres_pm_local":  props_local["tres_pm"][:top_n],
            "tres_pm_visit":  props_visit["tres_pm"][:top_n],
            "puntos_local":   props_local["puntos"][:top_n],
            "puntos_visit":   props_visit["puntos"][:top_n],
            "rebotes_local":  props_local["rebotes"][:top_n],
            "asist_local":    props_local["asistencias"][:top_n],
            "aviso":          "" if (props_local["tres_pm"] or props_visit["tres_pm"]) else "Sin datos en DB — carga stats NBA primero.",
        }

    def _analizar_equipo(self, equipo: str, rival: str) -> Dict:
        jugadores = self._obtener_jugadores(equipo)
        if not jugadores:
            return {"tres_pm": [], "puntos": [], "rebotes": [], "asistencias": []}

        # Factor defensivo del rival en 3s
        def3_rival = DEF_3PM_RANKING.get(rival, 1.0)
        # Factor de pace del equipo
        pace_eq = PACE_TEAM.get(equipo, 98)
        pace_factor = pace_eq / 98.0

        tres_pm_props    = []
        puntos_props     = []
        rebotes_props    = []
        asistencias_props = []

        for j in jugadores:
            nombre = j.get("nombre", "")
            prom_3pm = float(j.get("triples_por_partido", 0))
            prom_pts  = float(j.get("puntos", 0))

            # ── 3PM ──────────────────────────────────────────────────────────
            if prom_3pm >= 0.5:
                adj_3pm = round(prom_3pm * def3_rival * pace_factor, 2)
                linea = DEFAULT_LINES["tres_pm"]
                prob_over = self._prob_poisson(adj_3pm, linea)
                if prob_over >= 45:
                    tres_pm_props.append({
                        "jugador":       nombre,
                        "equipo":        equipo,
                        "prom_3pm":      prom_3pm,
                        "adj_3pm":       adj_3pm,
                        "linea":         linea,
                        "prob_over":     prob_over,
                        "factor_def":    round(def3_rival, 2),
                        "recomendacion": "🔥 OVER 3PM" if prob_over >= 62 else "📊 Considerar OVER 3PM",
                    })

            # ── Puntos ────────────────────────────────────────────────────────
            if prom_pts >= 10:
                adj_pts = round(prom_pts * pace_factor, 1)
                linea_pts = round(prom_pts - 2, 1)
                prob_pts = self._prob_poisson(adj_pts, linea_pts)
                if prob_pts >= 55:
                    puntos_props.append({
                        "jugador":       nombre,
                        "equipo":        equipo,
                        "prom_pts":      prom_pts,
                        "linea":         linea_pts,
                        "prob_over":     prob_pts,
                        "recomendacion": "🔥 OVER Pts" if prob_pts >= 65 else "📊 Considerar OVER Pts",
                    })

        tres_pm_props.sort(key=lambda x: x["prob_over"], reverse=True)
        puntos_props.sort(key=lambda x: x["prob_over"], reverse=True)

        return {
            "tres_pm":      tres_pm_props,
            "puntos":       puntos_props,
            "rebotes":      rebotes_props,
            "asistencias":  asistencias_props,
        }

    def _obtener_jugadores(self, equipo: str) -> List[Dict]:
        try:
            return db.get_top_player_stat(equipo, "three_pm", limit=10, deporte="nba") or []
        except Exception:
            return []

    @staticmethod
    def _prob_poisson(media: float, linea: float) -> float:
        """Probabilidad aproximada de superar `linea` con media Poisson."""
        import math
        if media <= 0:
            return 0.0
        # P(X > linea) ≈ 1 - CDF(floor(linea))
        k = int(linea)
        acum = 0.0
        try:
            for i in range(k + 1):
                acum += (media ** i) * math.exp(-media) / math.factorial(i)
        except (OverflowError, ValueError):
            return 0.0
        return round(max(0.0, min(100.0, (1.0 - acum) * 100)), 1)


# Instancia global
nba_props_analyzer = NBAPropAnalyzer()
