# -*- coding: utf-8 -*-
"""
UFC STATS SCRAPER - Datos reales de UFCStats.com con fight details
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os
import unicodedata
from datetime import datetime
import re
try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_OK = True
except ImportError:
    RAPIDFUZZ_OK = False

class UFCStatsScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.cache_file = "data/ufc_stats_cache.json"
        os.makedirs("data", exist_ok=True)
        self.cache = self._load_cache()
        self.caliente_odds_cache = self._load_caliente_odds_cache()
    
    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    def _load_caliente_odds_cache(self):
        odds_file = "data/odds_caliente_ufc.json"
        if os.path.exists(odds_file):
            with open(odds_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    
    def _normalize_name(self, name):
        text = unicodedata.normalize('NFD', name)
        text = text.encode('ascii', 'ignore').decode("utf-8")
        return text.strip().lower().replace(' ', '-')
    
    def _parse_record(self, record_str):
        if not record_str or record_str == 'N/A':
            return {'wins': 0, 'losses': 0, 'draws': 0}
        # Eliminar texto como "Pro" o "Am"
        record_str = re.sub(r'\s*(Pro|Am)\s*', '', record_str, flags=re.IGNORECASE).strip()
        # Si el formato es solo "W-L", asumir 0 draws
        if re.match(r'^\d+-\d+$', record_str):
            record_str += '-0'
        # Si el formato es "W-L-D"
        elif not re.match(r'^\d+-\d+-\d+$', record_str):
            return {'wins': 0, 'losses': 0, 'draws': 0}

        if not record_str:
            return {'wins': 0, 'losses': 0, 'draws': 0}
        parts = record_str.split('-')
        return {
            'wins': int(parts[0]) if len(parts) > 0 else 0,
            'losses': int(parts[1]) if len(parts) > 1 else 0,
            'draws': int(parts[2]) if len(parts) > 2 else 0
        }
    
    def _extract_fight_details(self, fight_url, fighter_name):
        """Extrae estadisticas detalladas de una pelea especifica"""
        try:
            res = requests.get(fight_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            stats = {
                'strikes_landed': 0, 'strikes_attempted': 0,
                'td_landed': 0, 'td_attempted': 0, 'knockdowns': 0
            }
            
            rows = soup.find_all('tr', class_='b-fight-details__table-row')
            
            for row in rows:
                name_cell = row.find('td', class_='b-fight-details__table-col')
                if name_cell:
                    link = name_cell.find('a')
                    if link and fighter_name.lower() in link.get_text(strip=True).lower():
                        cols = row.find_all('td')
                        for i, col in enumerate(cols):
                            text = col.get_text(strip=True)
                            
                            # Strikes
                            if 'of' in text and i == 2:
                                match = re.search(r'(\d+)\s*of\s*(\d+)', text)
                                if match:
                                    stats['strikes_landed'] = int(match.group(1))
                                    stats['strikes_attempted'] = int(match.group(2))
                            
                            # Takedowns
                            if 'of' in text and i == 5:
                                match = re.search(r'(\d+)\s*of\s*(\d+)', text)
                                if match:
                                    stats['td_landed'] = int(match.group(1))
                                    stats['td_attempted'] = int(match.group(2))
                            
                            # Knockdowns
                            if text.isdigit() and i == 1:
                                stats['knockdowns'] = int(text)
                        
                        break
            
            return stats
        except:
            return None
    
    def get_fighter_stats(self, name):
        """Obtiene estadisticas COMPLETAS de un peleador"""
        normalized = self._normalize_name(name)
        
        # Verificar cache (valido por 3 dias)
        if normalized in self.cache:
            cached = self.cache[normalized]
            cached_date = datetime.fromisoformat(cached.get('cached_date', '2000-01-01'))
            if (datetime.now() - cached_date).days < 3:
                print(f"  Usando cache para {name}")
                return cached
        
        print(f"  Buscando {name} en UFCStats...")
        
        stats = {
            'nombre': name,
            'record': 'N/A',
            'wins': 0, 'losses': 0,
            'altura': 0, 'alcance': 0,
            'ko_rate': 0, 'sub_rate': 0,
            'striking_accuracy': 0, 'takedown_accuracy': 0,
            'stance': 'Orthodox',
            'knockdowns_avg': 0,
            'was_koed_recently': False,
            'last_fights': [],
            'slpm': 0.0,
            'str_acc': 0,
            'td_avg': 0.0
        }
        
        try:
            # Buscar en la lista de peleadores
            parts = name.split()
            if len(parts) == 0:
                return stats
            
            last_name = parts[-1]
            letter = last_name[0].lower()
            
            url = f"http://ufcstats.com/statistics/fighters?char={letter}&page=all"
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            rows = soup.find_all('tr')
            fighters_in_page = {} # Nombre: URL

            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 3:
                    link = cols[0].find('a')
                    if link:
                        first_name = cols[0].get_text(strip=True)
                        last_name_col = cols[1].get_text(strip=True)
                        full_name = f"{first_name} {last_name_col}"
                        fighters_in_page[full_name] = link['href']

            profile_url = None
            if fighters_in_page:
                if RAPIDFUZZ_OK:
                    # Usar RapidFuzz para encontrar la mejor coincidencia (umbral 85%)
                    match = process.extractOne(name, fighters_in_page.keys(), scorer=fuzz.WRatio)
                    if match and match[1] >= 85:
                        print(f"    🎯 Coincidencia Fuzzy: {match[0]} ({match[1]:.1f}%)")
                        profile_url = fighters_in_page[match[0]]
                else:
                    # Fallback simple si no está instalado
                    for fn, url_f in fighters_in_page.items():
                        if name.lower() in fn.lower() or fn.lower() in name.lower():
                            profile_url = url_f
                            break
            
            if not profile_url:
                print(f"    No encontrado en UFCStats")
                stats['cached_date'] = datetime.now().isoformat()
                self.cache[normalized] = stats
                self._save_cache()
                return stats
            
            # Obtener perfil completo
            res = requests.get(profile_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Record
            record_span = soup.find('span', class_='b-content__title-record')
            if record_span:
                record_text = record_span.get_text(strip=True)
                match = re.search(r'Record:\s*(\d+)-(\d+)-(\d+)', record_text)
                if match:
                    stats['record'] = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    stats['wins'] = int(match.group(1))
                    stats['losses'] = int(match.group(2))
                    print(f"    Record: {stats['record']}")
            
            # Altura y alcance
            bio_div = soup.find('div', class_='b-list__info-box')
            if bio_div:
                for li in bio_div.find_all('li'):
                    text = li.get_text(strip=True)
                    if 'Height:' in text:
                        match = re.search(r"Height:\s*(\d+)'\s*(\d+)?\"?", text)
                        if match:
                            feet = int(match.group(1))
                            inches = int(match.group(2)) if match.group(2) else 0
                            stats['altura'] = int((feet * 30.48) + (inches * 2.54))
                    elif 'Reach:' in text:
                        match = re.search(r'Reach:\s*(\d+\.?\d*)\"?', text)
                        if match:
                            stats['alcance'] = int(float(match.group(1)) * 2.54)
                    elif 'STANCE:' in text:
                        stance = text.replace('STANCE:', '').strip()
                        stats['stance'] = stance if stance else 'Orthodox'
            
            # Historial de peleas
            fight_rows = soup.find_all('tr', class_='b-fight-details__table-row')
            
            # Reiniciar contadores para promedios
            total_strikes_landed = 0
            total_strikes_attempted = 0
            total_td_landed = 0
            total_td_attempted = 0
            total_control_time = 0 # Nuevo: tiempo de control
            total_sig_strikes_per_min = 0 # Nuevo: SLpM
            total_knockdowns = 0
            ko_wins = 0
            sub_wins = 0
            total_wins = 0
            fights_analyzed = 0
            
            for row in fight_rows[:10]:
                cols = row.find_all('td')
                if len(cols) >= 8:
                    result_cell = cols[0]
                    result_text = result_cell.get_text(strip=True).lower()
                    is_win = 'win' in result_text
                    method_cell = cols[7]
                    method_text = method_cell.get_text(strip=True).upper()
                    
                    # Detectar si la última pelea fue una derrota por KO/TKO
                    if fights_analyzed == 0 and not is_win and (stats['wins'] + stats['losses'] > 0): # Solo si tiene al menos una pelea
                        if 'KO' in method_text or 'TKO' in method_text:
                            stats['was_koed_recently'] = True

                    if is_win:
                        total_wins += 1
                        if 'KO' in method_text or 'TKO' in method_text:
                            ko_wins += 1
                        elif 'SUB' in method_text:
                            sub_wins += 1
                    
                    fight_link = cols[0].find('a')
                    if fight_link and fight_link.get('href'):
                        fight_url = fight_link['href']
                        # Extraer detalles de la pelea (strikes, takedowns, etc.)
                        fight_stats = self._extract_fight_details(fight_url, name) 
                        
                        if fight_stats:
                            total_strikes_landed += fight_stats.get('strikes_landed', 0)
                            total_strikes_attempted += fight_stats.get('strikes_attempted', 0)
                            total_td_landed += fight_stats.get('td_landed', 0)
                            total_td_attempted += fight_stats.get('td_attempted', 0)
                            total_control_time += fight_stats.get('control_time', 0)
                            total_sig_strikes_per_min += fight_stats.get('slpm', 0)
                            total_knockdowns += fight_stats.get('knockdowns', 0)
                            fights_analyzed += 1
                            stats['last_fights'].append({ # Guardar un resumen de la pelea
                                'oponente': cols[2].get_text(strip=True),
                                'resultado': result_text,
                                'metodo': method_text,
                                'ronda': cols[8].get_text(strip=True),
                                'tiempo': cols[9].get_text(strip=True)
                            })
                    
                    time.sleep(0.3)
            
            # Calcular promedios
            if fights_analyzed > 0:
                if total_strikes_attempted > 0:
                    stats['striking_accuracy'] = round(total_strikes_landed / total_strikes_attempted, 2)
                if total_td_attempted > 0:
                    stats['takedown_accuracy'] = round(total_td_landed / total_td_attempted, 2)
                stats['knockdowns_avg'] = round(total_knockdowns / fights_analyzed, 1)
                stats['control_time_avg'] = round(total_control_time / fights_analyzed, 1)
                stats['slpm_avg'] = round(total_sig_strikes_per_min / fights_analyzed, 1)
            
            if total_wins > 0:
                stats['ko_rate'] = round(ko_wins / total_wins, 2)
                stats['sub_rate'] = round(sub_wins / total_wins, 2)
            
            print(f"    KO Rate: {int(stats['ko_rate']*100)}%")
            print(f"    SLpM Avg: {stats['slpm_avg']:.1f}")
            print(f"    Control Time Avg: {stats['control_time_avg']:.1f} min")
            
        except Exception as e:
            print(f"    Error: {e}")
        
        stats['cached_date'] = datetime.now().isoformat()
        self.cache[normalized] = stats
        self._save_cache()
        return stats

    def get_ufc_odds_caliente(self):
        """Retorna las odds de UFC de Caliente.mx desde el caché"""
        # Este método asume que las odds ya fueron scrapeadas y guardadas
        # por un scraper de Caliente específico para UFC.
        # Por ahora, devuelve el caché cargado en __init__
        return self.caliente_odds_cache


    
    def get_rankings(self):
        """Obtiene rankings P4P"""
        rankings = []
        try:
            url = "http://ufcstats.com/rankings"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', class_='b-list__table')
                if table:
                    rows = table.find_all('tr')[1:16]
                    for i, row in enumerate(rows, 1):
                        cols = row.find_all('td')
                        if len(cols) > 1:
                            name = cols[1].text.strip()
                            rankings.append({'rank': i, 'name': name})
        except:
            pass
        return rankings

if __name__ == "__main__":
    scraper = UFCStatsScraper()
    test = scraper.get_fighter_stats("Jon Jones")
    print(json.dumps(test, indent=2, default=str))