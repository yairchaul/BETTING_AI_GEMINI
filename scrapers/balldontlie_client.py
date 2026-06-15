# -*- coding: utf-8 -*-
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True) # Cargar variables de entorno

BASE_URL = "https://api.balldontlie.io/v1" # URL base de la API

class BalldontlieClient:
    def __init__(self):
        self.api_key = os.getenv("BALLDONTLIE_API_KEY")
        self.headers = {"Authorization": self.api_key} if self.api_key else {}
    
    def get_players(self, team_id=None):
        """Obtiene jugadores de un equipo"""
        url = f"{BASE_URL}/players"
        if team_id:
            url += f"?team_ids[]={team_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"data": []}
        except Exception as e:
            print(f"Error Balldontlie: {e}")
            return {"data": []}
    
    def get_player_stats(self, player_id, season="2025"):
        """Obtiene estadísticas de un jugador"""
        url = f"{BASE_URL}/season_averages?season={season}&player_ids[]={player_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    return data["data"][0]
            return {}
        except Exception as e:
            return {}

balldontlie = BalldontlieClient() # Instancia global

if __name__ == "__main__":
    # Prueba simple
    result = balldontlie.get_players(team_id=14)
    print(f"Jugadores Lakers: {len(result.get('data', []))}")
