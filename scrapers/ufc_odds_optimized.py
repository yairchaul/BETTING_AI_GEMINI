# -*- coding: utf-8 -*-
"""
UFC ODDS OPTIMIZADO - BestFightOdds
"""
import requests
from bs4 import BeautifulSoup

class UFCOddsOptimized:
    def __init__(self):
        self.url = "https://www.bestfightodds.com/"
        self.headers = {"User-Agent": "Mozilla/5.0"}
    
    def get_odds(self):
        try:
            res = requests.get(self.url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.content, "html.parser")
            odds = {}
            rows = soup.select("tr")
            for row in rows:
                fighters = row.select("th")
                prices = row.select("td")
                if len(fighters) >= 2 and len(prices) >= 2:
                    f1 = fighters[0].get_text(strip=True)
                    f2 = fighters[1].get_text(strip=True)
                    o1 = prices[0].get_text(strip=True)
                    o2 = prices[1].get_text(strip=True)
                    odds[f1] = o1
                    odds[f2] = o2
            return odds
        except:
            return {}
