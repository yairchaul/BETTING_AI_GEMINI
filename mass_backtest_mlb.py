# -*- coding: utf-8 -*-
"""
MASS BACKTEST MLB V2 - Simulación de 30 días (K + HR)
Basado en reglas-mlb.md, protocolo de auditoría y fórmulas indexadas.
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import json
import os

class MassBacktestMLB:
    def __init__(self, days=30):
        self.days = days
        self.results = []
        self.total_units = 0.0
        self.wins = 0
        self.losses = 0
        self.api_base = "https://statsapi.mlb.com/api/v1"

    def fetch_json(self, url):
        try:
            r = requests.get(url, timeout=10)
            return r.json()
        except:
            return None

    def get_pitcher_season_k9(self, p_id, year):
        """Obtiene el K/9 real del pitcher para esa temporada"""
        url = f"{self.api_base}/people/{p_id}/stats?stats=statsSingleSeason&group=pitching&season={year}"
        data = self.fetch_json(url)
        try:
            return float(data["stats"][0]["splits"][0]["stat"]["strikeOutsPer9Inn"])
        except:
            return 0.0

    def get_pitcher_stats(self, p_id, year):
        """Obtiene K/9 y WHIP del pitcher"""
        url = f"{self.api_base}/people/{p_id}/stats?stats=statsSingleSeason&group=pitching&season={year}"
        data = self.fetch_json(url)
        try:
            stat = data["stats"][0]["splits"][0]["stat"]
            return {
                "k9": float(stat.get("strikeOutsPer9Inn", 0)),
                "whip": float(stat.get("whip", 1.20)),
                "hand": data.get("people", [{}])[0].get("pitchHand", {}).get("code", "R")
            }
        except:
            return {"k9": 0.0, "whip": 1.20, "hand": "R"}

    def get_batter_stats_at_date(self, p_id, date_str):
        """Obtiene HR totales y racha de 15 días"""
        year = date_str[:4]
        # Stats de la temporada
        url_season = f"{self.api_base}/people/{p_id}/stats?stats=statsSingleSeason&group=hitting&season={year}"
        # Stats últimos 15 días (aproximado por la API)
        url_recent = f"{self.api_base}/people/{p_id}/stats?stats=lastXGames&group=hitting&limit=15"
        
        data_s = self.fetch_json(url_season)
        data_r = self.fetch_json(url_recent)
        
        try:
            hr_totales = int(data_s["stats"][0]["splits"][0]["stat"].get("homeRuns", 0))
            hr_racha = int(data_r["stats"][0]["splits"][0]["stat"].get("homeRuns", 0))
            return hr_totales, hr_racha
        except:
            return 0, 0

    def run(self):
        print(f"🔍 Iniciando Backtesting Masivo: Últimos {self.days} días")
        print(f"📊 Aplicando reglas de Steering: reglas-mlb.md + mlb-auditoria-pro.md\n")
        
        hoy = datetime.now()
        total_k_units = 0.0
        total_hr_units = 0.0

        for i in range(1, self.days + 1):
            fecha = (hoy - timedelta(days=i)).strftime("%Y-%m-%d")
            print(f"📅 Procesando: {fecha}...", end="\r")
            
            sched_url = f"{self.api_base}/schedule?sportId=1&date={fecha}"
            sched_data = self.fetch_json(sched_url)
            
            if not sched_data or not sched_data.get("dates"): continue
            
            for game in sched_data["dates"][0]["games"]:
                if game["status"]["detailedState"] != "Final": continue
                
                game_pk = game["gamePk"]
                box_url = f"{self.api_base}/game/{game_pk}/boxscore"
                box = self.fetch_json(box_url)
                if not box: continue

                # Analizar abridores de ambos equipos
                for side in ["home", "away"]:
                    p_list = box["teams"][side]["pitchers"]
                    if not p_list: continue
                    
                    p_id = p_list[0]
                    p_info = box["teams"][side]["players"][f"ID{p_id}"]
                    p_name = p_info["person"]["fullName"]
                    k_real = p_info["stats"]["pitching"].get("strikeOuts", 0)
                    
                    # --- DATOS DEL PITCHER ---
                    p_stats = self.get_pitcher_stats(p_id, fecha[:4])
                    k9 = p_stats["k9"]
                    whip = p_stats["whip"]
                    p_hand = p_stats["hand"]

                    if k9 < 4.0: continue 

                    # --- REGLA MLB STEERING: Línea sugerida ---
                    if k9 >= 11.0: line = 6.5
                    elif k9 >= 9.5: line = 5.5
                    elif k9 >= 8.0: line = 4.5
                    else: line = 3.5
                    
                    proyeccion = round((k9 / 9) * 5.8, 1)
                    
                    diff = proyeccion - line
                    k_bet_type = None
                    if diff >= 1.5: k_bet_type = "OVER"
                    elif diff <= -1.5: k_bet_type = "UNDER"

                    if k_bet_type:
                        won = (k_bet_type == "OVER" and k_real > line) or (k_bet_type == "UNDER" and k_real < line)
                        total_k_units += self.record_bet(fecha, p_name, f"K {k_bet_type}", line, k_real, won, is_hr=False)

                    # --- LÓGICA HOME RUNS (Bateadores del equipo rival) ---
                    rival_side = "away" if side == "home" else "home"
                    lineup = box["teams"][rival_side]["players"]
                    
                    for b_id_str, b_data in lineup.items():
                        if "batting" not in b_data["stats"]: continue
                        
                        b_id = b_data["person"]["id"]
                        b_name = b_data["person"]["fullName"]
                        hr_real = b_data["stats"]["batting"].get("homeRuns", 0)
                        
                        hr_totales, racha_15d = self.get_batter_stats_at_date(b_id, fecha)
                        if hr_totales < 5: continue # Solo bateadores con historial

                        # --- FÓRMULA STEERING P_HR ---
                        p_hr = (hr_totales * 1.2) + (racha_15d * 2) - (whip * 5)
                        
                        # Ajuste Bateador Poder vs Zurdo
                        if p_hand == "L" and hr_totales > 15:
                            p_hr += 10 # +10% de confianza base
                        
                        # Umbral de apuesta > 45%
                        if p_hr > 45:
                            won_hr = hr_real > 0
                            total_hr_units += self.record_bet(fecha, b_name, "HR", 0.5, hr_real, won_hr, is_hr=True)
            
            time.sleep(0.2) # Respetar rate limit

        print(f"\n📊 Desglose Unidades: K: {total_k_units:+.2f} | HR: {total_hr_units:+.2f}")
        self.show_summary()

    def record_bet(self, fecha, player, bet, line, real, won, is_hr=False):
        if is_hr:
            # Cuota 3.50 (+250) según protocolo mlb-auditoria-pro.md
            profit = 2.50 if won else -1.0
        else:
            # Cuota 1.90 (-110)
            profit = 0.90 if won else -1.0
            
        self.total_units += profit
        if won: self.wins += 1
        else: self.losses += 1
        self.results.append({
            "fecha": fecha, "player": player, "bet": f"{bet} {line}", 
            "real": real, "res": "✅" if won else "❌", "profit": profit
        })
        return profit

    def show_summary(self):
        print("\n\n" + "="*50)
        print("🏆 RESULTADOS FINALES DEL BACKTESTING")
        print("="*50)
        total = self.wins + self.losses
        wr = (self.wins / total * 100) if total > 0 else 0
        print(f"Picks Analizados: {total}")
        print(f"Win Rate: {wr:.1f}%")
        print(f"Balance Total: {self.total_units:+.2f} Unidades")
        print(f"ROI Estimado: {(self.total_units / total * 100):.1f}%")
        print("="*50)

if __name__ == "__main__":
    tester = MassBacktestMLB(days=30)
    tester.run()