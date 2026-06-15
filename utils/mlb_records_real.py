# -*- coding: utf-8 -*-
import requests
import pandas as pd
from cachetools import cached, TTLCache

# Caché de 6 horas para no saturar ESPN y ser rápidos
cache = TTLCache(maxsize=1, ttl=21600)

@cached(cache)
def scraping_records_mlb():
    """Busca Standings reales de MLB 2026"""
    try:
        url = "https://www.espn.com/mlb/standings/_/group/overall"
        tablas = pd.read_html(url)
        equipos = tablas[0]
        stats = tablas[1]
        
        records = {}
        for i in range(len(equipos)):
            nombre = ''.join([char for char in equipos.iloc[i, 0] if not char.isdigit()]).replace('x - ', '').replace('y - ', '').strip()
            wins = int(stats.iloc[i, 0])
            losses = int(stats.iloc[i, 1])
            records[nombre] = {"wins": wins, "losses": losses}
        return records
    except:
        return None

def get_record(team_name):
    data = scraping_records_mlb()
    if not data: return {"wins": 10, "losses": 10}
    team_name = team_name.lower()
    for key in data:
        if key.lower() in team_name or team_name in key.lower():
            return data[key]
    return {"wins": 10, "losses": 10}

def get_diff(away, home):
    away_rec = get_record(away)
    home_rec = get_record(home)
    return abs(home_rec["wins"] - away_rec["wins"])

def get_confianza(away, home):
    away_rec = get_record(away)
    home_rec = get_record(home)
    total = away_rec["wins"] + home_rec["wins"]
    if total == 0: return 50
    return int(max(home_rec["wins"]/total, away_rec["wins"]/total) * 100)

def get_pick(away, home):
    a = get_record(away); h = get_record(home)
    return home if h["wins"] >= a["wins"] else away
