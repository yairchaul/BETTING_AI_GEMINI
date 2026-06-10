# -*- coding: utf-8 -*-
"""
Scraper de K/9 para pitchers MLB del dia usando MLB Stats API.
Genera data/stats_lanzadores_hoy.json con K/9 y avg_innings de cada pitcher.
"""
import json
import os
from datetime import datetime

try:
    import statsapi
except ImportError:
    statsapi = None

CACHE_FILE = "data/stats_lanzadores_hoy.json"
CACHE_TTL_HOURS = 4  # Renovar cada 4 horas


def obtener_pitchers_hoy():
    """Obtiene los pitchers probables del dia desde MLB Stats API."""
    if not statsapi:
        return {}
    
    try:
        # Obtener schedule del dia
        today = datetime.now().strftime('%m/%d/%Y')
        schedule = statsapi.schedule(date=today)
        
        pitchers = {}
        for game in schedule:
            # Pitcher local
            home_pitcher = game.get('home_probable_pitcher', '')
            away_pitcher = game.get('away_probable_pitcher', '')
            home_team = game.get('home_name', '')
            away_team = game.get('away_name', '')
            
            if home_pitcher and home_pitcher != 'TBD':
                stats = _get_pitcher_k9(home_pitcher)
                if stats:
                    pitchers[home_team] = {
                        'nombre': home_pitcher,
                        'k9': stats.get('k9', 0),
                        'era': stats.get('era', 0),
                        'avg_innings': stats.get('avg_innings', 5.5),
                        'whip': stats.get('whip', 1.35)
                    }
            
            if away_pitcher and away_pitcher != 'TBD':
                stats = _get_pitcher_k9(away_pitcher)
                if stats:
                    pitchers[away_team] = {
                        'nombre': away_pitcher,
                        'k9': stats.get('k9', 0),
                        'era': stats.get('era', 0),
                        'avg_innings': stats.get('avg_innings', 5.5),
                        'whip': stats.get('whip', 1.35)
                    }
        
        return pitchers
    except Exception as e:
        print(f"Error obteniendo pitchers del dia: {e}")
        return {}


def _get_pitcher_k9(pitcher_name):
    """Obtiene K/9 de un pitcher desde la API."""
    try:
        results = statsapi.lookup_player(pitcher_name)
        if not results:
            return None
        
        player_id = results[0]['id']
        stats = statsapi.player_stat_data(player_id, group="pitching", type="season")
        
        if stats and 'stats' in stats:
            for stat_group in stats['stats']:
                if 'stats' in stat_group:
                    s = stat_group['stats']
                    k9 = float(s.get('strikeoutsPer9Inn', 0))
                    era = float(s.get('era', 0))
                    whip = float(s.get('whip', 1.35))
                    ip = float(s.get('inningsPitched', 0))
                    games = int(s.get('gamesStarted', 1)) or 1
                    avg_innings = round(ip / games, 1) if games > 0 else 5.5
                    
                    return {
                        'k9': round(k9, 1),
                        'era': round(era, 2),
                        'whip': round(whip, 2),
                        'avg_innings': avg_innings
                    }
        return None
    except Exception as e:
        print(f"  Error K/9 para {pitcher_name}: {e}")
        return None


def actualizar_stats_lanzadores():
    """Actualiza el archivo de stats de lanzadores si esta desactualizado."""
    os.makedirs("data", exist_ok=True)
    
    # Verificar cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if '_timestamp' in data:
                ts = datetime.fromisoformat(data['_timestamp'])
                hours_old = (datetime.now() - ts).total_seconds() / 3600
                if hours_old < CACHE_TTL_HOURS:
                    # Cache valido, no actualizar
                    return data
        except:
            pass
    
    print("[MLB] Actualizando stats de lanzadores...")
    pitchers = obtener_pitchers_hoy()
    
    if pitchers:
        pitchers['_timestamp'] = datetime.now().isoformat()
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(pitchers, f, indent=2, ensure_ascii=False)
        print(f"[MLB] {len(pitchers) - 1} pitchers actualizados")
    
    return pitchers


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    result = actualizar_stats_lanzadores()
    print(f"\nResultado: {len(result) - 1 if result else 0} pitchers")
    for k, v in result.items():
        if k != '_timestamp':
            print(f"  {k}: {v.get('nombre', 'N/A')} - K/9: {v.get('k9', 0)}")
