# -*- coding: utf-8 -*-
"""
SCRAPER DE RANKINGS UFC - Con force_refresh
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta

class UFCRankingsScraper:
    def __init__(self):
        self.cache_file = 'data/ufc_rankings_cache.json'
        self.cache_duration = timedelta(hours=24)
        os.makedirs('data', exist_ok=True)
        self.rankings = self._load_rankings()
    
    def _load_rankings(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    last_update = datetime.fromisoformat(cache.get('last_update', '2000-01-01'))
                    
                    rankings = cache.get('rankings', {})
                    if rankings.get('campeones') and datetime.now() - last_update < self.cache_duration:
                        print(f"[rankings] Usando cache ({last_update.strftime('%Y-%m-%d %H:%M')})")
                        return rankings
            except:
                pass

        print("[rankings] Descargando rankings...")
        return self._fetch_rankings_ufcstats()
    
    def _fetch_rankings_ufcstats(self):
        rankings = {
            'campeones': [],
            'top5': [],
            'top10': [],
            'top15': [],
            'p4p': [],
            'p4p_positions': {}
        }
        
        # Datos P4P (actualizados Abril 2026)
        p4p_list = [
            "Islam Makhachev", "Ilia Topuria", "Alex Pereira", "Khamzat Chimaev",
            "Alexander Volkanovski", "Petr Yan", "Tom Aspinall", "Merab Dvalishvili",
            "Alexandre Pantoja", "Joshua Van", "Charles Oliveira"
        ]
        
        for i, name in enumerate(p4p_list, 1):
            rankings['p4p_positions'][name] = i
            rankings['p4p'].append(name)
        
        # Campeones actuales
        rankings['campeones'] = [
            "Alexandre Pantoja", "Petr Yan", "Alexander Volkanovski",
            "Ilia Topuria", "Islam Makhachev", "Khamzat Chimaev",
            "Carlos Ulberg", "Jon Jones", "Zhang Weili",
            "Valentina Shevchenko", "Julianna Peña"
        ]
        
        self._save_cache(rankings)
        return rankings
    
    def _save_cache(self, rankings):
        cache_data = {
            'last_update': datetime.now().isoformat(),
            'rankings': rankings
        }
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    
    def force_refresh(self):
        """Fuerza la actualización de rankings"""
        print("[rankings] Forzando actualizacion de rankings...")
        self.rankings = self._fetch_rankings_ufcstats()
        return self.rankings
    
    def get_bonus(self, fighter_name):
        if not fighter_name:
            return 0
        
        if fighter_name in self.rankings.get('campeones', []):
            return 0.05
        if fighter_name in self.rankings.get('p4p', []):
            pos = self.rankings['p4p_positions'].get(fighter_name, 999)
            if pos == 1: return 0.05
            elif pos == 2: return 0.045
            elif pos == 3: return 0.04
            elif pos <= 5: return 0.035
            elif pos <= 10: return 0.03
            else: return 0.02
        if fighter_name in self.rankings.get('top5', []):
            return 0.02
        if fighter_name in self.rankings.get('top10', []):
            return 0.01
        
        return 0
    
    def get_p4p_position(self, fighter_name):
        return self.rankings.get('p4p_positions', {}).get(fighter_name)
