# -*- coding: utf-8 -*-
"""
MLB ANALYZER REAL - Solo jugadores del lineup
"""
from scrapers.mlb_scraper_real import MLBScraperReal

class MLBAnalyzerReal:
    def __init__(self):
        self.scraper = MLBScraperReal()
    
    def analyze_game(self, game):
        game_id = game.get("game_id")
        if not game_id:
            return {"away_hr": [], "home_hr": []}
        
        lineup = self.scraper.get_lineup(game_id)
        resultado = {"away_hr": [], "home_hr": []}
        
        # AWAY
        for player in lineup.get("away", [])[:9]:
            stats = self.scraper.get_player_hr_stats(player)
            if stats.get("ab", 0) > 20:
                resultado["away_hr"].append({
                    "nombre": player,
                    "prob": stats["hr_rate"]
                })
        
        # HOME
        for player in lineup.get("home", [])[:9]:
            stats = self.scraper.get_player_hr_stats(player)
            if stats.get("ab", 0) > 20:
                resultado["home_hr"].append({
                    "nombre": player,
                    "prob": stats["hr_rate"]
                })
        
        # Ordenar y tomar top 2
        resultado["away_hr"] = sorted(resultado["away_hr"], key=lambda x: x["prob"], reverse=True)[:2]
        resultado["home_hr"] = sorted(resultado["home_hr"], key=lambda x: x["prob"], reverse=True)[:2]
        
        return resultado
