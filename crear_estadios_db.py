# -*- coding: utf-8 -*-
"""BASE DE DATOS DE ESTADIOS - Ballpark Factors"""
import json

ESTADIOS = {
    "Coors Field": {"factor_hr": 1.35, "factor_runs": 1.30, "altitud": 5280, "viento_factor": 1.2},
    "Great American Ball Park": {"factor_hr": 1.25, "factor_runs": 1.15, "altitud": 550, "viento_factor": 1.1},
    "Yankee Stadium": {"factor_hr": 1.15, "factor_runs": 1.05, "altitud": 30, "viento_factor": 1.0},
    "Fenway Park": {"factor_hr": 1.05, "factor_runs": 1.10, "altitud": 20, "viento_factor": 0.9},
    "Dodger Stadium": {"factor_hr": 0.85, "factor_runs": 0.90, "altitud": 340, "viento_factor": 0.8},
    "Petco Park": {"factor_hr": 0.80, "factor_runs": 0.85, "altitud": 15, "viento_factor": 0.7},
    "Oracle Park": {"factor_hr": 0.75, "factor_runs": 0.80, "altitud": 10, "viento_factor": 1.3},
    "Wrigley Field": {"factor_hr": 1.10, "factor_runs": 1.05, "altitud": 600, "viento_factor": 1.4},
    "Progressive Field": {"factor_hr": 0.95, "factor_runs": 1.00, "altitud": 650, "viento_factor": 0.9},
    "Target Field": {"factor_hr": 0.85, "factor_runs": 0.90, "altitud": 840, "viento_factor": 0.8},
    "Globe Life Field": {"factor_hr": 1.05, "factor_runs": 1.05, "altitud": 550, "viento_factor": 1.0},
    "Rogers Centre": {"factor_hr": 1.00, "factor_runs": 1.00, "altitud": 250, "viento_factor": 0.0},
    "PNC Park": {"factor_hr": 0.90, "factor_runs": 0.95, "altitud": 730, "viento_factor": 1.1},
    "Rate Field": {"factor_hr": 1.05, "factor_runs": 1.00, "altitud": 600, "viento_factor": 1.0},
    "Dodger Stadium": {"factor_hr": 0.85, "factor_runs": 0.90, "altitud": 340, "viento_factor": 0.8},
}

with open("data/estadios_db.json", "w", encoding="utf-8") as f:
    json.dump(ESTADIOS, f, indent=2, ensure_ascii=False)

print(f"✅ Base de estadios creada: {len(ESTADIOS)} parques")
