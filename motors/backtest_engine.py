# -*- coding: utf-8 -*-
"""
BACKTEST ENGINE — V2
Lee pesos dinámicos de data/pesos_motores.json y clasifica equipos
con datos reales de la base de datos.
"""

import json
import os
import logging
import sqlite3

logger = logging.getLogger(__name__)

PESOS_PATH = os.path.join("data", "pesos_motores.json")
DB_PATH    = os.path.join("data", "betting_stats.db")

PESOS_DEFAULT = {
    "power_factor_ml":               5.0,
    "ml_pitcher_vulnerable_penalty": 0.85,
    "ml_pitcher_novato_penalty":     0.88,
    "ml_racha_fallos_penalty":       0.80,
    "ml_valor_oculto_bonus":         8.0,
    "hr_ou_impact":                  0.015,
}


class backtest_engine:
    """Motor de backtesting y gestión de pesos dinámicos."""

    @staticmethod
    def get_pesos_actuales() -> dict:
        """Lee pesos desde data/pesos_motores.json; usa defaults si no existe."""
        try:
            if os.path.exists(PESOS_PATH):
                with open(PESOS_PATH, encoding="utf-8") as f:
                    pesos = json.load(f)
                # Combinar con defaults para claves faltantes
                merged = PESOS_DEFAULT.copy()
                merged.update({k: v for k, v in pesos.items() if v is not None})
                return merged
        except Exception as e:
            logger.warning(f"No se pudo leer {PESOS_PATH}: {e}")
        return PESOS_DEFAULT.copy()

    @staticmethod
    def get_clasificacion_equipo(equipo: str) -> dict:
        """
        Clasifica un equipo basándose en su historial de picks en la DB.

        Clasificaciones:
          - TRAMPA      : >3 fallos seguidos o win_rate < 35%
          - VALOR_OCULTO: win_rate > 65% con >=4 picks resueltos
          - NORMAL      : cualquier otro caso
        """
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cur  = conn.cursor()
            cur.execute(
                """
                SELECT estado FROM backtesting
                WHERE LOWER(evento) LIKE ?
                ORDER BY id DESC
                LIMIT 10
                """,
                (f"%{equipo.lower()}%",),
            )
            filas = cur.fetchall()
            conn.close()

            if not filas:
                return {"clasificacion": "NORMAL", "tasa_acierto": 0.5, "fallos": 0}

            estados = [f[0] for f in filas if f[0] in ("GANADA", "PERDIDA")]
            if not estados:
                return {"clasificacion": "NORMAL", "tasa_acierto": 0.5, "fallos": 0}

            total   = len(estados)
            ganadas = sum(1 for e in estados if e == "GANADA")
            tasa    = ganadas / total

            # Contar fallos consecutivos desde el pick más reciente
            fallos_consec = 0
            for e in estados:
                if e == "PERDIDA":
                    fallos_consec += 1
                else:
                    break

            if fallos_consec >= 3 or (total >= 4 and tasa < 0.35):
                clasificacion = "TRAMPA"
            elif total >= 4 and tasa > 0.65:
                clasificacion = "VALOR_OCULTO"
            else:
                clasificacion = "NORMAL"

            return {
                "clasificacion": clasificacion,
                "tasa_acierto":  round(tasa, 3),
                "fallos":        fallos_consec,
            }

        except Exception as e:
            logger.debug(f"get_clasificacion_equipo({equipo}): {e}")
            return {"clasificacion": "NORMAL", "tasa_acierto": 0.5, "fallos": 0}
