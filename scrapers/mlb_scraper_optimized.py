# -*- coding: utf-8 -*-
"""
MLB SCRAPER OPTIMIZADO - 1 request por fuente
"""
import requests
from bs4 import BeautifulSoup
import re

class MLBScraperOptimized:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    def get_today_games(self):
        """Obtiene juegos del día"""
        try:
            url = "https://www.mlb.com/scores"
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.content, "html.parser")
            games = []
            links = soup.find_all("a", href=re.compile(r"/gameday/"))
            for l in links[:15]:
                href = l["href"]
                game_id = re.search(r"/gameday/(\d+)", href)
                if game_id:
                    games.append({
                        "game_id": game_id.group(1),
                        "url": "https://www.mlb.com" + href
                    })
            return games
        except:
            return []
    
    def get_lineup(self, game_id):
        """Obtiene lineup de un juego"""
        try:
            url = f"https://www.mlb.com/gameday/{game_id}"
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.content, "html.parser")
            lineup = {"away": [], "home": []}
            players = soup.select(".lineup__player-name")
            for p in players[:20]:
                name = p.get_text(strip=True)
                if name:
                    lineup["away"].append(name)
            return lineup
        except:
            return {"away": [], "home": []}
    
    def get_hr_leaders(self):
        """Obtiene líderes HR en UNA SOLA request"""
        try:
            url = "https://www.mlb.com/stats/home-runs"
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.content, "html.parser")
            data = {}
            rows = soup.find_all("tr")
            for r in rows[:100]:
                cols = r.find_all("td")
                if len(cols) > 3:
                    name = cols[1].get_text(strip=True)
                    try:
                        hr = int(cols[3].get_text(strip=True))
                        data[name] = hr
                    except:
                        pass
            return data
        except:
            return {}
    
    def get_pitchers(self):
        """Obtiene pitchers probables"""
        try:
            url = "https://www.mlb.com/es/probable-pitchers"
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.content, "html.parser")
            pitchers = []
            matchups = soup.select(".probable-pitchers__matchup")
            for m in matchups:
                away = m.select_one(".probable-pitchers__pitcher--away")
                home = m.select_one(".probable-pitchers__pitcher--home")
                pitchers.append({
                    "away": away.get_text(strip=True) if away else "N/A",
                    "home": home.get_text(strip=True) if home else "N/A"
                })
            return pitchers
        except:
            return []
    
    def get_top_hr(self, lineup, hr_data):
        """Filtra top HR del lineup"""
        players = []
        for p in lineup[:9]:
            if p in hr_data:
                hr = hr_data[p]
                prob = min(round((hr / 50) * 15, 1), 25)
                players.append({"nombre": p, "hr": hr, "probabilidad": prob})
        return sorted(players, key=lambda x: x["probabilidad"], reverse=True)[:2]
    
    def get_games_complete(self):
        """Pipeline completo - optimizado"""
        games = self.get_today_games()
        if not games:
            return []
        
        hr_data = self.get_hr_leaders()
        pitchers = self.get_pitchers()
        
        result = []
        for i, g in enumerate(games[:8]):
            lineup = self.get_lineup(g["game_id"])
            away_top = self.get_top_hr(lineup.get("away", []), hr_data)
            home_top = self.get_top_hr(lineup.get("home", []), hr_data)
            
            result.append({
                "game_id": g["game_id"],
                "away_team": f"Away {i+1}",
                "home_team": f"Home {i+1}",
                "away": f"Away {i+1}",
                "home": f"Home {i+1}",
                "top_hr_away": away_top,
                "top_hr_home": home_top,
                "pitchers": pitchers[i] if i < len(pitchers) else {"away": "N/A", "home": "N/A"},
                "time": "TBD",
                "away_record": "0-0",
                "home_record": "0-0"
            })
        return result
