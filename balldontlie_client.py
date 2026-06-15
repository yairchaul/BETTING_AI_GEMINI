# balldontlie_client.py
import requests
import json

class BalldontlieClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.balldontlie.io/v1"
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
    
    def get_teams(self):
        """Obtener lista de equipos"""
        response = requests.get(f"{self.base_url}/teams", headers=self.headers)
        return response.json()
    
    def get_players(self, team_id=None, per_page=100):
        """Obtener jugadores de un equipo"""
        url = f"{self.base_url}/players?per_page={per_page}"
        if team_id:
            url += f"&team_ids[]={team_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_player_stats(self, player_id, season="2025"):
        """Obtener estadísticas de un jugador"""
        url = f"{self.base_url}/season_averages?season={season}&player_ids[]={player_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_today_games(self):
        """Obtener partidos de hoy"""
        response = requests.get(f"{self.base_url}/games?dates[]=2025-05-20", headers=self.headers)
        return response.json()
    
    def get_player_props(self, player_id):
        """Obtener proyecciones de jugador (triples, puntos, etc.)"""
        # Nota: Balldontlie no tiene props directamente
        # Calculamos desde promedios
        stats = self.get_player_stats(player_id)
        if stats.get('data') and len(stats['data']) > 0:
            return {
                "pts": stats['data'][0].get('pts', 0),
                "ast": stats['data'][0].get('ast', 0),
                "reb": stats['data'][0].get('reb', 0),
                "fg3_pct": stats['data'][0].get('fg3_pct', 0),
                "fg3a": stats['data'][0].get('fg3a', 0)  # Intentos de triple
            }
        return None

# Instancia global
balldontlie = BalldontlieClient("c0da27f9-394d-473f-aae3-f8e0b48f27ef")

if __name__ == "__main__":
    # Probar conexión
    teams = balldontlie.get_teams()
    print(f"✅ Conectado: {len(teams.get('data', []))} equipos cargados")
