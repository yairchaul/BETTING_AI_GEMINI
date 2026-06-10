# -*- coding: utf-8 -*-
"""AUDITOR DE RESULTADOS - Cierra picks pendientes usando ESPN Scoreboard"""
import requests
import sqlite3
import os
import json
from datetime import datetime
from database_manager import db

def auditar_picks():
    print("🔍 Iniciando auditoría de picks pendientes...")
    
    # Asegurar existencia del log de aprendizaje
    log_path = "data/aprendizaje_fallos.log"
    if not os.path.exists("data"): os.makedirs("data")
    if not os.path.exists(log_path):
        with open(log_path, "w", encoding="utf-8") as f: f.write("--- LOG DE APRENDIZAJE BETTING_AI ---\n")

    try:
        conn = sqlite3.connect("data/betting_stats.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, fecha, deporte, evento, pick FROM backtesting WHERE estado = 'PENDIENTE'")
        pendientes = cursor.fetchall()
        
        if not pendientes:
            print("✅ No hay picks pendientes por auditar.")
            return

        # Diccionario para cachear resultados de ESPN por fecha para no repetir requests
        cache_resultados = {}

        for p_id, fecha, deporte, evento, pick in pendientes:
            # Formatear fecha para ESPN API (YYYYMMDD)
            fecha_espn = fecha.replace("-", "")
            sport_path = "baseball/mlb" if deporte == "MLB" else "basketball/nba"
            
            if fecha_espn not in cache_resultados:
                # Usamos ESPN para Score y MLB API para Boxscore (HR)
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard?dates={fecha_espn}"
                
                resp = requests.get(url).json()
                cache_resultados[fecha_espn] = resp.get("events", [])

            # Buscar el partido específico en los eventos de ESPN
            juego_finalizado = False
            ganador_real = None
            
            for event in cache_resultados[fecha_espn]:
                name = event.get("name", "")
                status = event.get("status", {}).get("type", {}).get("state", "")
                
                if status == "post game" or status == "final":
                    # Comparación difusa de nombres
                    if any(word.lower() in name.lower() for word in evento.split() if len(word) > 4):
                        juego_finalizado = True
                        # Determinar ganador
                        competitors = event["competitions"][0]["competitors"]
                        winner_comp = next((c for c in competitors if c.get("winner") == True), None)
                        if winner_comp:
                            ganador_real = winner_comp["team"]["displayName"]
                        break
            
            if juego_finalizado and ganador_real:
                # Normalizar nombres para comparación
                es_acierto = pick.lower() in ganador_real.lower() or ganador_real.lower() in pick.lower()
                nuevo_estado = "GANADA" if es_acierto else "PERDIDA"
                
                # --- LÓGICA DE AUTO-APRENDIZAJE ---
                if nuevo_estado == "PERDIDA":
                    with open(log_path, "a", encoding="utf-8") as f:
                        extra = " [🚩 LANZADOR VULNERABLE]" if "🚩" in pick else ""
                        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] FALLO: {evento} | Pick: {pick}{extra} | Ganó: {ganador_real}\n")

                cursor.execute("UPDATE backtesting SET estado = ? WHERE id = ?", (nuevo_estado, p_id))
                print(f"✅ Pick {p_id} ({evento}): {nuevo_estado} (Ganó: {ganador_real})")
            else:
                print(f"⏳ El juego {evento} aún no termina o no se encontró.")

        conn.commit()
        conn.close()
        print("🚀 Auditoría completada.")

    except Exception as e:
        print(f"❌ Error en auditoría: {e}")

if __name__ == "__main__":
    auditar_picks()