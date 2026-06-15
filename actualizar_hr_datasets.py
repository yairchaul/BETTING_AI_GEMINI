# -*- coding: utf-8 -*-
"""
ACTUALIZAR HR DATASETS — regenera hr_datasets_completos.json con datos REALES
de la temporada actual desde la MLB Stats API (bateadores HR + pitchers HR/9).

Mantiene el MISMO formato que consume PredictorHRPro / HRAnalyzer:
  {
    "bateadores": { "Nombre": {"equipo": "NYY", "hr": int, "hr_por_juego": float,
                                "avg": float, "ops": float} },
    "pitchers":   { "Nombre": {"equipo": "LAD", "hr_por_juego": float (HR/9),
                                "hr_permitidos": int} }
  }
"""
import json
import os
import shutil
import requests
from datetime import datetime

try:
    from mapeo_equipos import obtener_abreviatura
except Exception:
    def obtener_abreviatura(n):
        return (n or "")[:3].upper()

HEADERS = {"User-Agent": "Mozilla/5.0"}
ARCHIVO = "hr_datasets_completos.json"


def _season_actual():
    # La temporada MLB suele ser el año en curso
    return datetime.now().year


def _float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def obtener_bateadores(season, limite=150):
    url = (f"https://statsapi.mlb.com/api/v1/stats?stats=season&group=hitting"
           f"&season={season}&sportId=1&limit={limite}&sortStat=homeRuns")
    bateadores = {}
    try:
        d = requests.get(url, headers=HEADERS, timeout=20).json()
        splits = d.get("stats", [{}])[0].get("splits", [])
        for s in splits:
            nombre = s.get("player", {}).get("fullName", "")
            if not nombre:
                continue
            equipo_nombre = s.get("team", {}).get("name", "")
            stat = s.get("stat", {})
            hr = int(_float(stat.get("homeRuns", 0)))
            juegos = int(_float(stat.get("gamesPlayed", 0))) or 1
            if hr <= 0:
                continue
            bateadores[nombre] = {
                "equipo": obtener_abreviatura(equipo_nombre),
                "equipo_nombre": equipo_nombre,
                "hr": hr,
                "hr_por_juego": round(hr / juegos, 3),
                "avg": _float(stat.get("avg", 0.0)),
                "ops": _float(stat.get("ops", 0.0)),
            }
    except Exception as e:
        print(f"⚠️ Error bateadores: {e}")
    return bateadores


def obtener_pitchers(season, limite=150):
    url = (f"https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching"
           f"&season={season}&sportId=1&limit={limite}&sortStat=inningsPitched")
    pitchers = {}
    try:
        d = requests.get(url, headers=HEADERS, timeout=20).json()
        splits = d.get("stats", [{}])[0].get("splits", [])
        for s in splits:
            nombre = s.get("player", {}).get("fullName", "")
            if not nombre:
                continue
            equipo_nombre = s.get("team", {}).get("name", "")
            stat = s.get("stat", {})
            hr9 = _float(stat.get("homeRunsPer9", 0.0))
            ip = _float(stat.get("inningsPitched", 0.0))
            hr_perm = int(_float(stat.get("homeRuns", 0)))
            if hr9 == 0 and ip > 0:
                hr9 = round(hr_perm / ip * 9, 2)
            pitchers[nombre] = {
                "equipo": obtener_abreviatura(equipo_nombre),
                "equipo_nombre": equipo_nombre,
                "hr_por_juego": round(hr9, 2),
                "hr_permitidos": hr_perm,
            }
    except Exception as e:
        print(f"⚠️ Error pitchers: {e}")
    return pitchers


def main():
    season = _season_actual()
    print(f"📥 Descargando HR datasets de la temporada {season}...")
    bateadores = obtener_bateadores(season)
    pitchers = obtener_pitchers(season)

    # Si la temporada actual aún no tiene datos, intentar la anterior
    if not bateadores and season > 2024:
        print(f"⚠️ Sin datos {season}, probando {season-1}...")
        bateadores = obtener_bateadores(season - 1)
        pitchers = obtener_pitchers(season - 1)

    if not bateadores:
        print("❌ No se obtuvieron bateadores. Se conserva el archivo actual.")
        return

    # Respaldo del archivo anterior
    if os.path.exists(ARCHIVO):
        shutil.copy(ARCHIVO, ARCHIVO + ".bak")
        print(f"🗄️ Respaldo creado: {ARCHIVO}.bak")

    data = {
        "actualizado": datetime.now().isoformat(),
        "temporada": season,
        "bateadores": bateadores,
        "pitchers": pitchers,
    }
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(bateadores)} bateadores y {len(pitchers)} pitchers guardados en {ARCHIVO}")
    top = sorted(bateadores.items(), key=lambda x: x[1]["hr"], reverse=True)[:5]
    print("Top 5 HR:")
    for n, v in top:
        print(f"   {n} ({v['equipo']}): {v['hr']} HR · {v['hr_por_juego']}/juego")


if __name__ == "__main__":
    main()
