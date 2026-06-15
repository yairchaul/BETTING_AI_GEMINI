# -*- coding: utf-8 -*-
"""
MLB SCRAPER - Datos reales de MLB.com
Extrae: Lineup, pitchers probables, stats de HR
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

class MLBScraperReal:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def get_today_games(self):
        """Obtiene partidos del día con IDs"""
        try:
            url = "https://www.mlb.com/scores"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            games = []
            # Buscar enlaces a gameday
            game_links = soup.find_all('a', href=re.compile(r'/gameday/'))
            
            for link in game_links[:10]:
                game_url = "https://www.mlb.com" + link['href']
                game_id = re.search(r'/gameday/(\d+)', game_url)
                
                if game_id:
                    games.append({
                        'game_id': game_id.group(1),
                        'url': game_url
                    })
            
            return games
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def get_lineup(self, game_id):
        """Obtiene lineup real del partido"""
        try:
            url = f"https://www.mlb.com/gameday/{game_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            lineup = {'away': [], 'home': []}
            
            # Extraer lineups del HTML
            away_players = soup.find_all('div', class_='lineup__player--away')
            home_players = soup.find_all('div', class_='lineup__player--home')
            
            for player in away_players:
                name = player.find('span', class_='lineup__player-name')
                if name:
                    lineup['away'].append(name.get_text(strip=True))
            
            for player in home_players:
                name = player.find('span', class_='lineup__player-name')
                if name:
                    lineup['home'].append(name.get_text(strip=True))
            
            return lineup
        except:
            return {'away': [], 'home': []}
    
    def get_player_hr_stats(self, player_name):
        """Obtiene stats de HR de un jugador"""
        try:
            # Buscar en la página de stats
            search_name = player_name.lower().replace(' ', '-')
            url = f"https://www.mlb.com/player/{search_name}"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraer HR de la tabla de stats
            hr_elem = soup.find('td', {'data-stat': 'homeRuns'})
            ab_elem = soup.find('td', {'data-stat': 'atBats'})
            
            hr = int(hr_elem.get_text(strip=True)) if hr_elem else 0
            ab = int(ab_elem.get_text(strip=True)) if ab_elem else 1
            
            return {
                'hr': hr,
                'ab': ab,
                'hr_rate': round((hr / ab) * 100, 1) if ab > 0 else 0
            }
        except:
            return {'hr': 0, 'ab': 0, 'hr_rate': 0}
    
    def get_probable_pitchers(self):
        """Obtiene pitchers probables"""
        try:
            url = "https://www.mlb.com/es/probable-pitchers"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            pitchers = []
            matchups = soup.find_all('div', class_='probable-pitchers__matchup')
            
            for m in matchups:
                away = m.find('div', class_='probable-pitchers__pitcher--away')
                home = m.find('div', class_='probable-pitchers__pitcher--home')
                
                pitchers.append({
                    'away': away.get_text(strip=True) if away else 'N/A',
                    'home': home.get_text(strip=True) if home else 'N/A'
                })
            
            return pitchers
        except:
            return []
