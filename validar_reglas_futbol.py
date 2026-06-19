# -*- coding: utf-8 -*-
"""
Validación de la ruta DB de analizar_futbol_jerarquico tras corregir:
  - Regla 1: OVER 1.5 HT = P(2+ goles en 1ª parte) vía Poisson
             (usa HT real si existe; si no, estima desde el total FT · 0.45).
  - Regla 7: combinado Gana+Over SOLO si Moneyline y Over ambos ≥ 60%.

Inyecta escenarios sintéticos en historial_equipos y comprueba el pick.
Uso:  python validar_reglas_futbol.py
"""
import os
import sqlite3
from datetime import datetime, timedelta

from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico

DB = os.path.join("data", "betting_stats.db")


def _reset(equipos):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    for e in equipos:
        cur.execute("DELETE FROM historial_equipos WHERE nombre_equipo = ? AND deporte='soccer'", (e,))
    conn.commit()
    conn.close()


def _insertar(equipo, partidos):
    """partidos: lista de (favor, ht, contra)."""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    for i, (favor, ht, contra) in enumerate(partidos):
        fecha = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        cur.execute(
            "INSERT INTO historial_equipos (nombre_equipo, deporte, puntos_favor, puntos_ht, puntos_contra, fecha) VALUES (?,?,?,?,?,?)",
            (equipo, "soccer", favor, ht, contra, fecha))
    conn.commit()
    conn.close()


def escenario(nombre, local, visit, datos_l, datos_v, espera):
    _reset([local, visit])
    _insertar(local, datos_l)
    _insertar(visit, datos_v)
    res = analizar_futbol_jerarquico(local, visit)
    pick = res.get("pick", "")
    regla = res.get("regla", "?")
    conf = res.get("confianza", 0)
    ok = espera.lower() in pick.lower()
    print(f"[{'OK ' if ok else 'XX '}] {nombre}")
    print(f"       pick={pick!r}  regla={regla}  conf={conf}%  (esperaba ~ {espera!r})")
    return ok


if __name__ == "__main__":
    print("=" * 70)
    print("VALIDACIÓN REGLAS 1 y 7 (ruta DB)")
    print("=" * 70)
    res = []

    # A) Regla 1 con HT REAL: empates con 2 goles al HT cada uno → P(2+ HT) alta
    #    (empates ⇒ ML=0%, no se dispara el combinado: aísla la Regla 1)
    res.append(escenario(
        "A · Regla 1 (HT real, 2+ goles 1ª parte)",
        "Alpha FC", "Beta United",
        [(2, 2, 2)] * 5, [(2, 2, 2)] * 5,
        espera="OVER 1.5 HT"))

    # B) Regla 1 ESTIMADA (sin HT, empates muy goleadores): FT alto → estima HT
    #    (empates ⇒ ML=0%, aísla la Regla 1 del combinado)
    res.append(escenario(
        "B · Regla 1 (estimada desde FT, sin datos HT)",
        "Gamma SC", "Delta City",
        [(2, 0, 2)] * 5, [(3, 0, 3)] * 5,
        espera="OVER 1.5 HT"))

    # C) Regla 7 POSITIVO: local gana siempre (ML>60%) y muchos goles (Over>60%)
    #    favor alto + victorias 5/5 → combinado Gana + Over
    res.append(escenario(
        "C · Regla 7 (ML y Over ambos ≥60% → combinado)",
        "Omega FC", "Weak Town",
        [(4, 0, 0)] * 5, [(0, 0, 3)] * 5,
        espera="+"))

    # D) Regla 7 NEGATIVO: gana parejo (ML ~ bajo) → NO debe salir combinado
    _reset(["Even One", "Even Two"])
    _insertar("Even One", [(1, 0, 1), (2, 0, 2), (0, 0, 0), (1, 0, 1), (2, 0, 1)])
    _insertar("Even Two", [(1, 0, 1), (1, 0, 1), (2, 0, 2), (0, 0, 1), (1, 0, 1)])
    res_d = analizar_futbol_jerarquico("Even One", "Even Two")
    no_combo = "+" not in res_d.get("pick", "")
    print(f"[{'OK ' if no_combo else 'XX '}] D · Regla 7 NO dispara (ML insuficiente)")
    print(f"       pick={res_d.get('pick')!r}  regla={res_d.get('regla')}  conf={res_d.get('confianza')}%  (esperaba SIN '+')")
    res.append(no_combo)

    # limpieza
    _reset(["Alpha FC", "Beta United", "Gamma SC", "Delta City",
            "Omega FC", "Weak Town", "Even One", "Even Two"])

    print("-" * 70)
    print(f"RESULTADO: {sum(res)}/{len(res)} escenarios OK")
    print("=" * 70)
