# -*- coding: utf-8 -*-
"""Motor Over/Under para MLB — V25 (Clima + Umpire + Lineup integrados)"""

import json
import math
import os
from database_manager import db
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
        "Dodger Stadium": -0.3, "Oracle Park": -0.6, "Petco Park": -0.7, "T-Mobile Park": -0.8,
        "Oakland Coliseum": -0.4, "Tropicana Field": -0.3, "American Family Field": -0.1,
        "Chase Field": 0.3, "PNC Park": -0.2, "Kauffman Stadium": -0.1,
        "Progressive Field": -0.2, "Target Field": -0.1, "Guaranteed Rate Field": 0.1,
        "Angel Stadium": -0.1, "Comerica Park": -0.3, "Nationals Park": 0.0,
        "loanDepot park": -0.4, "Rogers Centre": 0.2,
    }

    # Media de liga y respaldos POR EQUIPO. La DB (get_team_stats_detailed) manda
    # cuando trae forma reciente; si viene vacía (aún sin scrapear), se usa este
    # estático real para NO perder la diferenciación entre equipos. Antes Gemini
    # lo borró y dejó a todos en la media → el modelo no distinguía ofensivas.
    LEAGUE_AVG = {"avg_runs": 4.4, "bullpen_era": 4.2}

    # Media de la tabla estática TEAM_RUNS_AVG (≈4.03). El factor ofensivo debe
    # dividir cada fuente entre SU PROPIA media: antes la tabla estática se
    # dividía entre 4.4 → off_factor quedaba clavado en el piso 0.85 para casi
    # cualquier duelo → sesgo UNDER estructural (backtest: 77% picks UNDER).
    STATIC_RUNS_MEAN = 4.03

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

    BULLPEN_ERA = {
        "New York Yankees": 3.1, "Cleveland Guardians": 3.2, "Los Angeles Dodgers": 3.3,
        "Baltimore Orioles": 3.4, "Seattle Mariners": 3.5, "Atlanta Braves": 3.6,
        "Milwaukee Brewers": 3.7, "Houston Astros": 3.8, "Tampa Bay Rays": 3.9,
        "San Diego Padres": 4.0, "Philadelphia Phillies": 4.1, "Texas Rangers": 4.2,
        "Boston Red Sox": 4.3, "Chicago Cubs": 4.4, "New York Mets": 4.5,
        "Miami Marlins": 4.6, "San Francisco Giants": 4.7, "Arizona Diamondbacks": 4.8,
        "Colorado Rockies": 5.5, "Oakland Athletics": 5.2, "Chicago White Sox": 5.0,
    }

    def _park_bonus(self, venue) -> float:
        """Bono del estadio con match DIFUSO: los feeds traen nombres con
        patrocinador ('UNIQLO Field at Dodger Stadium') que el lookup exacto
        perdía → todos esos juegos quedaban con parque neutro."""
        if not venue:
            return 0.0
        v = str(venue).strip()
        if v in self.PARK_FACTORS:
            return self.PARK_FACTORS[v]
        vl = v.lower()
        for nombre, bono in self.PARK_FACTORS.items():
            if nombre.lower() in vl or vl in nombre.lower():
                return bono
        return 0.0

    def calcular_total(self, partido: dict) -> dict:
        local    = partido.get("local", "")
        visitante = partido.get("visitante", "")
        venue    = partido.get("venue", "Estadio Neutral")
        game_pk  = partido.get("game_pk")

        # Datos dinámicos desde la DB cuando existan; si no, respaldo estático real.
        try:
            stats_l = db.get_team_stats_detailed(local, 'mlb') or {}
            stats_v = db.get_team_stats_detailed(visitante, 'mlb') or {}
        except Exception:
            stats_l, stats_v = {}, {}
        league_avg = self.LEAGUE_AVG

        pitchers  = partido.get("pitchers", {})
        p_local   = pitchers.get("local", {}) if isinstance(pitchers.get("local"), dict) else {}
        p_visit   = pitchers.get("visitante", {}) if isinstance(pitchers.get("visitante"), dict) else {}

        era_l = float(p_local.get("era", 4.50))
        era_v = float(p_visit.get("era", 4.50))

        # 1. Base por lanzadores (65% abridor, 35% bullpen). Bullpen: DB → estático → liga.
        bp_era_l = stats_l.get('bullpen_era') or self.BULLPEN_ERA.get(local, league_avg['bullpen_era'])
        bp_era_v = stats_v.get('bullpen_era') or self.BULLPEN_ERA.get(visitante, league_avg['bullpen_era'])
        carreras_esperadas_l = era_v * 0.65 + bp_era_v * 0.35 # Carreras que se espera anote el local
        carreras_esperadas_v = era_l * 0.65 + bp_era_l * 0.35 # Carreras que se espera anote el visitante
        # ERA solo cuenta carreras LIMPIAS: la suma de ERAs (~8.4) queda corta
        # frente al total real (media 8.94, backtest 926 juegos 2026). El ×1.06
        # repone las carreras sucias; sin él el motor sacaba UNDER 78% de veces.
        carreras_base = (carreras_esperadas_l + carreras_esperadas_v) * 1.06

        # ── 2. Parque ─────────────────────────────────────────────────────────
        bono_estadio = self._park_bonus(venue)

        # ── 3. Factor Ofensivo (forma reciente vs media de liga). Runs: DB → estático → liga.
        # Cada fuente se normaliza contra su propia media (DB→4.4, estático→4.03).
        def _ratio_ofensivo(stats_db, equipo):
            desde_db = stats_db.get('avg_runs_for')
            if desde_db:
                return float(desde_db) / league_avg['avg_runs']
            return self.TEAM_RUNS_AVG.get(equipo, self.STATIC_RUNS_MEAN) / self.STATIC_RUNS_MEAN

        off_factor = _ratio_ofensivo(stats_l, local) * _ratio_ofensivo(stats_v, visitante)
        off_factor = max(0.85, min(1.15, off_factor)) # Acotar para evitar valores extremos

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
            (carreras_base * off_factor) + bono_estadio + bono_clima + bono_umpire - penalizacion_lineup,
            1,
        )

        linea_vegas = float(partido.get("odds", {}).get("over_under", 8.5))

        # ── Segunda opinión: MODELO DE CARRERAS (Dixon-Coles de béisbol) ──────
        # La matriz Poisson de carreras da el total esperado y P(over) de forma
        # coherente con ML y run line. Se mezcla 50/50 con el total heurístico.
        p_over_modelo = None
        try:
            from .mlb_runs_model import predecir as _predecir_runs
            _rm = _predecir_runs(local, visitante, linea_total=linea_vegas)
            if _rm and _rm.get("disponible"):
                total_modelo = _rm.get("total_esperado")
                p_over_modelo = _rm.get("total", {}).get("over")
                if total_modelo:
                    total_proy = round(0.5 * total_proy + 0.5 * float(total_modelo), 1)
        except Exception:
            pass

        diff = round(total_proy - linea_vegas, 1)

        # Confianza HONESTA: los totales MLB 2026 tienen sd REAL 4.5 (backtest
        # 926 juegos con líneas de cierre). Con esa varianza, |diff|=0.8 ⇒ ~57%
        # y |diff|=2 ⇒ ~67% teórico; el viejo 60+12·diff (hasta 85%) era ficción
        # (el motor acertaba ~50-52%). Techo 64%.
        if abs(diff) >= 0.8:
            rec = "OVER" if diff > 0 else "UNDER"
            conf = int(round(100 * 0.5 * (1 + math.erf((abs(diff) / 4.5) / math.sqrt(2)))))
            conf = max(52, min(64, conf))
        else:
            rec, conf = "PASAR", 50

        # Si el modelo de carreras coincide con fuerza, refuerza la confianza
        # (mismo techo honesto: 66).
        if p_over_modelo is not None and rec != "PASAR":
            pm = p_over_modelo if rec == "OVER" else (100 - p_over_modelo)
            conf = int(round(min(66, max(40, 0.5 * conf + 0.5 * pm))))

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
