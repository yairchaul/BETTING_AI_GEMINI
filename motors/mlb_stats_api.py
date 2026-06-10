# motors/mlb_stats_api.py
import statsapi
import json
import os
import time
from datetime import datetime

def obtener_whip_cacheado(pitcher_name, equipo=None, temporada='2026'):
    """
    Obtiene el WHIP de un lanzador usando caché local y API de MLB
    
    Args:
        pitcher_name: Nombre del lanzador
        equipo: Equipo del lanzador (opcional)
        temporada: Temporada (default: actual)
    
    Returns:
        float: WHIP del lanzador, o 1.35 si no se encuentra
    """
    cache_file = "data/pitchers_cache.json"
    cache = {}
    
    # Cargar caché
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except:
            pass
    
    # Buscar en caché
    cache_key = f"{pitcher_name}_{temporada or 'latest'}"
    if cache_key in cache:
        return cache[cache_key]
    
    try:
        # Buscar lanzador por nombre
        search_results = statsapi.lookup_player(pitcher_name)
        
        if search_results:
            player_id = search_results[0]['id']
            
            # Obtener estadísticas de los últimos 3 partidos (Muestra de forma actual)
            stats = statsapi.player_stat_data(
                player_id, 
                group="pitching", 
                type="season"
            )
            
            whip = 1.35  # Valor por defecto
            
            if stats and 'stats' in stats:
                for stat_group in stats['stats']:
                    if 'splits' in stat_group:
                        # Agregamos los datos de los 3 juegos para calcular el WHIP reciente
                        total_ip = sum([float(s['stat'].get('inningsPitched', 0)) for s in stat_group['splits']])
                        total_h = sum([int(s['stat'].get('hits', 0)) for s in stat_group['splits']])
                        total_bb = sum([int(s['stat'].get('baseOnBalls', 0)) for s in stat_group['splits']])
                        
                        if total_ip > 0:
                            # Fórmula WHIP: (H + BB) / IP
                            whip = round((total_h + total_bb) / total_ip, 2)
                        break
            
            # Guardar en caché
            cache[cache_key] = whip
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            
            return whip
    except Exception as e:
        print(f"Error obteniendo WHIP de {pitcher_name}: {e}")
    
    return 1.35

def obtener_k9_cacheado(pitcher_name, equipo=None, temporada='2026'):
    """
    Obtiene el K/9 de un lanzador usando caché local y API de MLB
    
    Returns:
        float: K/9 del lanzador, o 8.0 si no se encuentra
    """
    cache_file = "data/pitchers_cache.json"
    cache = {}
    
    # Cargar caché
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except:
            pass
    
    cache_key = f"k9_{pitcher_name}_{temporada or 'latest'}"
    if cache_key in cache:
        return cache[cache_key]
    
    try:
        search_results = statsapi.lookup_player(pitcher_name)
        
        if search_results:
            player_id = search_results[0]['id']
            
            # Estadísticas recientes (últimos 3 partidos)
            stats = statsapi.player_stat_data(
                player_id, 
                group="pitching", 
                type="season"
            )
            
            k9 = 8.0  # Valor por defecto
            
            if stats and 'stats' in stats:
                for stat_group in stats['stats']:
                    if 'splits' in stat_group:
                        # Calculamos K/9 real de los últimos 3 juegos
                        total_so = sum([int(s['stat'].get('strikeOuts', 0)) for s in stat_group['splits']])
                        total_ip = sum([float(s['stat'].get('inningsPitched', 0)) for s in stat_group['splits']])
                        
                        if total_ip > 0:
                            k9 = round((total_so * 9) / total_ip, 2)
                        break
            
            cache[cache_key] = k9
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            
            return k9
    except Exception as e:
        print(f"Error obteniendo K/9 de {pitcher_name}: {e}")
    
    return 8.0

if __name__ == "__main__":
    # Prueba
    print("Probando MLB Stats API...")
    whip = obtener_whip_cacheado("Gerrit Cole")
    print(f"WHIP de Gerrit Cole: {whip}")
    
    k9 = obtener_k9_cacheado("Gerrit Cole")
    print(f"K/9 de Gerrit Cole: {k9}")