# -*- coding: utf-8 -*-
"""Motor Over/Under para MLB — V25 (Clima + Umpire + Lineup integrados)"""

import json
import os
from .predictor_hr import predictor_hr

_UMPIRES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "inteligencia_umpires.json")
_umpires_cache: dict = {}


def _cargar_umpires() -> dict:
    global _umpires_cache
    if _umpires_cache:
        return _umpires_cache
    try:
        with open(_UMPIRES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _umpires_cache = {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        _umpires_cache = {}
    return _umpires_cache


class MotorOverUnder:
    """Proyecta carreras totales MLB integrando lanzadores, parque, clima y árbitro."""

    PARK_FACTORS = {
        "Coors Field": 1.5, "Great American Ball Park": 1.0, "Yankee Stadium": 0.8,
        "Citizens Bank Park": 0.6, "Fenway Park": 0.4, "Wrigley Field": 0.3,
        "Oriole Park at Camden Yards": 0.3, "Globe Life Field": 0.2,
        "Truist Park": 0.2, "Minute Maid Park": 0.2, "Busch Stadium": -0.2,
        "Dodger Stadium": -0.3, "Oracle Park": -0.6, "Petco Park": -0.7,
        "T-Mobile Park": -0.8, "Oakland Coliseum": -0.4, "Tropicana Field": -0.3,
        "American Family Field": -0.1, "Chase Field": 0.3, "PNC Park": -0.2,
        "Kauffman Stadium": -0.1, "Progressive Field": -0.2, "Target Field": -0.1,
        "Guaranteed Rate Field": 0.1, "Angel Stadium": -0.1, "Comerica Park": -0.3,
        "Nationals Park": 0.0, "loanDepot park": -0.4, "Rogers Centre": 0.2,
    }

    TEAM_RUNS_AVG = {
        "Los Angeles Dodgers": 5.2, "Atlanta Braves": 5.1, "New York Yankees": 4.9,
        "Philadelphia Phillies": 4.8, "Texas Rangers": 4.7, "Houston Astros": 4.6,
        "Boston Red Sox": 4.5, "Chicago Cubs": 4.4, "San Diego Padres": 4.3,
        "Cincinnati Reds": 4.2, "Arizona Diamondbacks": 4.2, "Toronto Blue Jays": 4.1,
        "Seattle Mariners": 4.0, "Tampa Bay Rays": 4.0, "Baltimore Orioles": 4.0,
        "Minnesota Twins": 4.0, "Milwaukee Brewers": 3.9, "Cleveland Guardians": 3.8,
        "San Francisco Giants": 3.8, "Chicago White Sox": 3.7, "Detroit Tigers": 3.7,
        "Miami Marlins": 3.6, "Kansas City Royals": 3.6, "Washington Nationals": 3.6,
        "Colorado Rockies": 3.5, "Oakland Athletics": 3.5, "Pittsburgh Pirates": 3.4,
        "St. Louis Cardinals": 3.4, "New York Mets": 3.3, "Los Angeles Angels": 3.2,
    }

    TEAM_RUNS_ALLOWED = {
        "Atlanta Braves": 3.5, "Los Angeles Dodgers": 3.6, "New York Yankees": 3.7,
        "Philadelphia Phillies": 3.8, "Houston Astros": 3.9, "Baltimore Orioles": 4.0,
        "Seattle Mariners": 4.0, "Cleveland Guardians": 4.1, "Minnesota Twins": 4.1,
        "San Diego Padres": 4.2, "Toronto Blue Jays": 4.2, "Arizona Diamondbacks": 4.3,
        "Texas Rangers": 4.3, "Cincinnati Reds": 4.4, "Boston Red Sox": 4.5,
        "Milwaukee Brewers": 4.5, "Chicago Cubs": 4.6, "Tampa Bay Rays": 4.6,
        "Miami Marlins": 4.7, "San Francisco Giants": 4.7, "Washington Nationals": 4.8,
        "Detroit Tigers": 4.9, "Kansas City Royals": 4.9, "Pittsburgh Pirates": 5.0,
        "St. Louis Cardinals": 5.0, "Chicago White Sox": 5.1, "Colorado Rockies": 5.2,
        "New York Mets": 5.2, "Oakland Athletics": 5.3, "Los Angeles Angels": 5.3,
    }

    def calcular_total(self, partido: dict) -> dict:
        local    = partido.get("local", "")
        visitante = partido.get("visitante", "")
        venue    = partido.get("venue", "Estadio Neutral")
        game_pk  = partido.get("game_pk")

        pitchers  = partido.get("pitchers", {})
        p_local   = pitchers.get("local", {}) if isinstance(pitchers.get("local"), dict) else {}
        p_visit   = pitchers.get("visitante", {}) if isinstance(pitchers.get("visitante"), dict) else {}

        era_l = float(p_local.get("era", 4.50))
        era_v = float(p_visit.get("era", 4.50))

        # ── 1. Base por lanzadores ────────────────────────────────────────────
        carreras_base = (era_l + era_v) / 2 * 0.9

        # ── 2. Parque ─────────────────────────────────────────────────────────
        bono_estadio = self.PARK_FACTORS.get(venue, 0.0)

        # ── 3. Ofensiva / Defensiva ───────────────────────────────────────────
        off_f = (self.TEAM_RUNS_AVG.get(local, 4.0) + self.TEAM_RUNS_AVG.get(visitante, 4.0)) / 8.0
        def_f = 8.0 / (self.TEAM_RUNS_ALLOWED.get(local, 4.0) + self.TEAM_RUNS_ALLOWED.get(visitante, 4.0))

        # ── 4. Clima ──────────────────────────────────────────────────────────
        bono_clima = 0.0
        ajustes_clima = []
        clima = partido.get("clima", {})
        if not clima:
            # Intentar obtener clima del scraper si hay utils disponibles
            try:
                from utils.clima_mlb import ClimaMLB
                clima = ClimaMLB().obtener_clima(venue) or {}
            except Exception:
                clima = {}

        if clima:
            temp      = float(clima.get("temp", 70))
            viento    = float(clima.get("wind_speed", 0))
            viento_dir = clima.get("wind_dir", "None")
            humedad   = float(clima.get("humedad", 50))

            if temp > 88:
                bono_clima += 0.4
                ajustes_clima.append(f"Calor extremo ({temp:.0f}°F) +0.4")
            elif temp > 80:
                bono_clima += 0.2
                ajustes_clima.append(f"Calor moderado ({temp:.0f}°F) +0.2")
            elif temp < 45:
                bono_clima -= 0.5
                ajustes_clima.append(f"Frío extremo ({temp:.0f}°F) -0.5")
            elif temp < 55:
                bono_clima -= 0.3
                ajustes_clima.append(f"Frío moderado ({temp:.0f}°F) -0.3")

            if viento > 15 and viento_dir == "Out":
                bono_clima += 0.7
                ajustes_clima.append(f"Viento fuerte a favor ({viento:.0f}mph Out) +0.7")
            elif viento > 10 and viento_dir == "Out":
                bono_clima += 0.4
                ajustes_clima.append(f"Viento a favor ({viento:.0f}mph Out) +0.4")
            elif viento > 10 and viento_dir == "In":
                bono_clima -= 0.4
                ajustes_clima.append(f"Viento en contra ({viento:.0f}mph In) -0.4")

            if humedad > 75:
                bono_clima += 0.2
                ajustes_clima.append(f"Humedad alta ({humedad:.0f}%) +0.2")

        # ── 5. Árbitro ────────────────────────────────────────────────────────
        bono_umpire = 0.0
        umpire_info = ""
        umpires_db = _cargar_umpires()
        umpire_nombre = partido.get("umpire", "")

        if umpire_nombre and umpire_nombre in umpires_db:
            u = umpires_db[umpire_nombre]
            bono_umpire = float(u.get("run_boost", 0.0))
            over_pct    = float(u.get("over_pct", 50.0))
            zona        = u.get("zona", "media")
            signo = "+" if bono_umpire >= 0 else ""
            umpire_info = (
                f"{umpire_nombre} | zona {zona} | {over_pct:.0f}% OVER historico"
            )
            if bono_umpire != 0:
                ajustes_clima.append(
                    f"Árbitro {umpire_nombre} (zona {zona}) {signo}{bono_umpire:.1f}"
                )

        # ── 6. Penalización lineup ────────────────────────────────────────────
        penalizacion_lineup = 0.0
        ajustes_lineup = []
        if game_pk and predictor_hr:
            activos_l = predictor_hr.obtener_bateadores_activos(local, game_pk)
            activos_v = predictor_hr.obtener_bateadores_activos(visitante, game_pk)

            poder_l = [h for _, h in predictor_hr.bateadores_stats.items()
                       if predictor_hr.normalizar(h.get("equipo", "")) == predictor_hr.normalizar(local)
                       and h.get("hr", 0) >= 10]
            poder_v = [h for _, h in predictor_hr.bateadores_stats.items()
                       if predictor_hr.normalizar(h.get("equipo", "")) == predictor_hr.normalizar(visitante)
                       and h.get("hr", 0) >= 10]

            ausentes_l = [p for p in poder_l
                          if not any(predictor_hr.normalizar(p.get("nombre", "")) in predictor_hr.normalizar(a.get("nombre", ""))
                                     for a in activos_l)]
            ausentes_v = [p for p in poder_v
                          if not any(predictor_hr.normalizar(p.get("nombre", "")) in predictor_hr.normalizar(a.get("nombre", ""))
                                     for a in activos_v)]

            if ausentes_l:
                pen = round(0.2 * len(ausentes_l), 1)
                penalizacion_lineup += pen
                ajustes_lineup.append(f"Faltan {len(ausentes_l)} bateadores de poder en {local} -{pen}")
            if ausentes_v:
                pen = round(0.2 * len(ausentes_v), 1)
                penalizacion_lineup += pen
                ajustes_lineup.append(f"Faltan {len(ausentes_v)} bateadores de poder en {visitante} -{pen}")

        # ── 7. Total proyectado ───────────────────────────────────────────────
        total_proy = round(
            (carreras_base * off_f * def_f) + bono_estadio + bono_clima + bono_umpire - penalizacion_lineup,
            1,
        )

        linea_vegas = float(partido.get("odds", {}).get("over_under", 8.5))
        diff = round(total_proy - linea_vegas, 1)

        if diff >= 0.8:
            rec, conf = "OVER", min(85, 60 + int(diff * 12))
        elif diff <= -0.8:
            rec, conf = "UNDER", min(85, 60 + int(abs(diff) * 12))
        else:
            rec, conf = "PASAR", 50

        return {
            "total_proyectado":  total_proy,
            "proyeccion_total":  total_proy,
            "linea_vegas":       linea_vegas,
            "recomendacion":     rec,
            "confianza":         conf,
            "diferencia":        diff,
            "ajustes_clima":     ajustes_clima,
            "ajustes_lineup":    ajustes_lineup,
            "bono_estadio":      bono_estadio,
            "bono_umpire":       bono_umpire,
            "umpire_info":       umpire_info,
        }


motor_over_under = MotorOverUnder()
