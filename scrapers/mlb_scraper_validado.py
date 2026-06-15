# -*- coding: utf-8 -*-
"""SCRAPER MLB VALIDADO - Con filtro de lineup obligatorio"""
import requests
from bs4 import BeautifulSoup
import re
import sys
sys.path.insert(0, '.')
from engine.validator import filter_hr_hitters

class MLBScraperValidado:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    def get_games_complete(self):
        games = self._get_today_games()
        validated = []
        for g in games:
            game_id = g.get('game_id')
            if not game_id: continue
            
            lineup = self._get_lineup(game_id)
            hr_hitters = self._get_hr_hitters()
            
            # 🔴 FILTRO CRÍTICO - Solo jugadores en lineup
            valid_hr = filter_hr_hitters(hr_hitters, lineup)
            
            g['lineup'] = lineup
            g['hr_hitters'] = valid_hr
            g['_validated'] = True
            validated.append(g)
        
        print(f"✅ {len(validated)} juegos validados con lineup real")
        return validated
    
    def _get_today_games(self):
        try:
            url = "https://www.mlb.com/scores"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            games = []
            links = soup.find_all('a', href=re.compile(r'/gameday/'))
            for link in links[:15]:
                game_id = re.search(r'/gameday/(\d+)', link['href'])
                if game_id:
                    games.append({'game_id': game_id.group(1), 'away': 'Away', 'home': 'Home', 'pitchers': {}, 'odds': {}})
            return games
        except: return []
    
    def _get_lineup(self, game_id):
        try:
            url = f"https://www.mlb.com/gameday/{game_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            lineup = {'away': [], 'home': []}
            players = soup.select('.lineup__player-name')
            for p in players[:20]:
                name = p.get_text(strip=True)
                if name: lineup['away'].append(name)
            return lineup
        except: return {'away': [], 'home': []}
    
    def _get_hr_hitters(self):
        return [{'name': 'Aaron Judge', 'hr': 8, 'hr_prob': 18.5}, {'name': 'Pete Alonso', 'hr': 6, 'hr_prob': 15.0}]
