# -*- coding: utf-8 -*-
"""MÓDULO DE WHIP REAL - MLB Stats API"""
import requests

def obtener_whip_pitcher_real(nombre_pitcher):
    """Busca el WHIP 2026 de un pitcher en la API oficial de MLB"""
    if not nombre_pitcher or nombre_pitcher == "TBD":
        return 1.25
    
    try:
        # 1. Buscar ID del jugador por nombre
        search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={nombre_pitcher}"
        resp = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        
        if not resp.get("people"):
            return 1.25
        
        p_id = resp["people"][0]["id"]
        
        # 2. Consultar Stats de temporada actual
        stats_url = f"https://statsapi.mlb.com/api/v1/people/{p_id}/stats?stats=statsSingleSeason&group=pitching&season=2026"
        stats_resp = requests.get(stats_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        
        # Extraer WHIP
        splits = stats_resp["stats"][0]["splits"]
        if splits:
            whip = splits[0]["stat"].get("whip", 1.25)
            return float(whip)
        
        return 1.25
    except:
        return 1.25

# Cache para no repetir llamadas
_cache_whip = {}

def obtener_whip_cacheado(nombre):
    if nombre not in _cache_whip:
        _cache_whip[nombre] = obtener_whip_pitcher_real(nombre)
    return _cache_whip[nombre]
