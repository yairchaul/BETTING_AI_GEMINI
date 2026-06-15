# -*- coding: utf-8 -*-
import sqlite3
import requests
import json
import os
from datetime import datetime

def registrar_fallo_estadio_favorable(jugador, estadio, fecha):
    ruta = "data/hr_fails_favorable_parks.json"
    fails = []
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            fails = json.load(f)
    
    fails.append({
        "jugador": jugador,
        "estadio": estadio,
        "fecha": fecha,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(fails, f, indent=2, ensure_ascii=False)

def auditar_home_runs():
    print("🔍 Audidando candidatos a Home Run...")
    conn = sqlite3.connect("data/betting_stats.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, fecha, jugador FROM hr_candidates_history WHERE resultado = 'PENDIENTE'")
    pendientes = cursor.fetchall()
    
    if not pendientes:
        print("✅ No hay candidatos de HR pendientes.")
        return

    cache_boxscores = {}

    for row_id, fecha, jugador in pendientes:
        # Necesitamos el gamePk. En producción, lo ideal es guardarlo en la tabla.
        # Por ahora, buscamos el schedule de esa fecha.
        if fecha not in cache_boxscores:
            url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}"
            games = requests.get(url).json().get("dates", [{}])[0].get("games", [])
            cache_boxscores[fecha] = games

        conecto = False
        mano_pitcher = "R" # Default
        estadio_actual = "Desconocido"

        for game in cache_boxscores[fecha]:
            game_id = game["gamePk"]
            estadio_actual = game.get("venue", {}).get("name", "TBD")
            box = requests.get(f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore").json()
            
            # Buscar al jugador en ambos equipos
            for side in ["home", "away"]:
                players = box["teams"][side]["players"]
                for p_id, p_info in players.items():
                    # Extraer mano del pitcher si es el rival
                    if pitcher_rival.lower() in p_info["person"]["fullName"].lower():
                        mano_pitcher = p_info["person"].get("pitchHand", {}).get("code", "R")

                    if jugador.lower() in p_info["person"]["fullName"].lower():
                        hr_count = p_info["stats"]["batting"].get("homeRuns", 0)
                        if hr_count > 0: conecto = True
        
        nuevo_estado = "GANADA" if conecto else "PERDIDA"

        # Lógica de detección de estadios favorables (Factores > 1.10)
        estadios_faborables = ["Coors Field", "Great American Ball Park", "Yankee Stadium", "Guaranteed Rate Field"]
        if nuevo_estado == "PERDIDA" and estadio_actual in estadios_faborables:
            print(f"   ⚠️ Fallo en estadio favorable detectado: {jugador} en {estadio_actual}")
            registrar_fallo_estadio_favorable(jugador, estadio_actual, fecha)

        cursor.execute("UPDATE hr_candidates_history SET resultado = ?, pitcher_mano = ? WHERE id = ?", (nuevo_estado, mano_pitcher, row_id))
        print(f"   ⚾ {jugador} vs {pitcher_rival} ({mano_pitcher}): {nuevo_estado}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    auditar_home_runs()