# -*- coding: utf-8 -*-
"""SCRAPER MASIVO - Últimos 10 días de resultados MLB"""
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json

class MLBResultadosScraper:
    def __init__(self, dias=10):
        self.dias = dias
        self.resultados = []
    
    def scrape_ultimos_dias(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()
            
            for i in range(self.dias):
                fecha = datetime.now() - timedelta(days=i+1)
                fecha_str = fecha.strftime("%Y%m%d")
                url = f"https://www.espn.com.mx/beisbol/mlb/calendario/_/fecha/{fecha_str}"
                
                print(f"\n📅 Procesando {fecha.strftime('%Y-%m-%d')}...")
                
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Buscar todas las tablas de resultados
                    tables = soup.find_all('table')
                    juegos_dia = []
                    
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            row_text = row.get_text()
                            
                            # Buscar patrones de resultado (ej: "BOS 8, DET 6" o "NYY 7, KC 0")
                            score_pattern = r'([A-Z]{3})\s*(\d+)\s*,\s*([A-Z]{3})\s*(\d+)'
                            match = re.search(score_pattern, row_text)
                            
                            if match:
                                away_abbr = match.group(1)
                                away_score = match.group(2)
                                home_abbr = match.group(3)
                                home_score = match.group(4)
                                
                                # Mapeo de abreviaturas a nombres completos
                                team_names = {
                                    'DET': 'Detroit Tigers', 'BOS': 'Boston Red Sox',
                                    'NYY': 'New York Yankees', 'KC': 'Kansas City Royals',
                                    'HOU': 'Houston Astros', 'CLE': 'Cleveland Guardians',
                                    'CIN': 'Cincinnati Reds', 'TB': 'Tampa Bay Rays',
                                    'STL': 'St. Louis Cardinals', 'MIA': 'Miami Marlins',
                                    'ATL': 'Atlanta Braves', 'WSH': 'Washington Nationals',
                                    'BAL': 'Baltimore Orioles', 'PHI': 'Philadelphia Phillies',
                                    'CHC': 'Chicago Cubs', 'LAD': 'Los Angeles Dodgers',
                                    'COL': 'Colorado Rockies', 'TOR': 'Toronto Blue Jays',
                                    'LAA': 'Los Angeles Angels', 'ATH': 'Athletics',
                                    'SEA': 'Seattle Mariners', 'SF': 'San Francisco Giants',
                                    'MIL': 'Milwaukee Brewers', 'PIT': 'Pittsburgh Pirates',
                                    'NYM': 'New York Mets', 'MIN': 'Minnesota Twins',
                                    'TEX': 'Texas Rangers', 'ARI': 'Arizona Diamondbacks',
                                    'SD': 'San Diego Padres', 'CHW': 'Chicago White Sox'
                                }
                                
                                away_team = team_names.get(away_abbr, away_abbr)
                                home_team = team_names.get(home_abbr, home_abbr)
                                
                                # Determinar ganador
                                if int(away_score) > int(home_score):
                                    winner = away_team
                                    loser = home_team
                                    margin = int(away_score) - int(home_score)
                                else:
                                    winner = home_team
                                    loser = away_team
                                    margin = int(home_score) - int(away_score)
                                
                                # Extraer pitchers (buscar en celdas)
                                cells = row.find_all('td')
                                winning_pitcher = None
                                losing_pitcher = None
                                
                                for cell in cells:
                                    cell_text = cell.get_text()
                                    if 'Ganado' in cell_text:
                                        winning_pitcher = cell_text.replace('Ganado', '').strip()
                                    if 'Perdido' in cell_text:
                                        losing_pitcher = cell_text.replace('Perdido', '').strip()
                                
                                juego = {
                                    'fecha': fecha.strftime('%Y-%m-%d'),
                                    'away': away_team,
                                    'home': home_team,
                                    'away_score': int(away_score),
                                    'home_score': int(home_score),
                                    'winner': winner,
                                    'loser': loser,
                                    'margin': margin,
                                    'winning_pitcher': winning_pitcher,
                                    'losing_pitcher': losing_pitcher,
                                    'total_runs': int(away_score) + int(home_score)
                                }
                                
                                juegos_dia.append(juego)
                                print(f"   ✅ {away_team} @ {home_team}: {away_score}-{home_score} (Ganó: {winner})")
                    
                    self.resultados.extend(juegos_dia)
                    print(f"   📊 {len(juegos_dia)} juegos encontrados")
                    
                except Exception as e:
                    print(f"   ❌ Error: {str(e)[:50]}")
            
            browser.close()
        
        return self.resultados
    
    def guardar_json(self, filename="resultados_10_dias.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Resultados guardados en {filename}")
    
    def generar_reporte(self):
        if not self.resultados:
            return {}
        
        total_juegos = len(self.resultados)
        home_wins = sum(1 for r in self.resultados if r['winner'] == r['home'])
        away_wins = total_juegos - home_wins
        
        avg_margin = sum(r['margin'] for r in self.resultados) / total_juegos
        avg_total_runs = sum(r['total_runs'] for r in self.resultados) / total_juegos
        
        # Rachas por equipo
        team_streaks = {}
        for r in self.resultados:
            winner = r['winner']
            loser = r['loser']
            
            if winner not in team_streaks:
                team_streaks[winner] = {'wins': 0, 'losses': 0, 'last_10': []}
            if loser not in team_streaks:
                team_streaks[loser] = {'wins': 0, 'losses': 0, 'last_10': []}
            
            team_streaks[winner]['wins'] += 1
            team_streaks[loser]['losses'] += 1
            team_streaks[winner]['last_10'].append('W')
            team_streaks[loser]['last_10'].append('L')
        
        return {
            'total_juegos': total_juegos,
            'home_wins': home_wins,
            'away_wins': away_wins,
            'home_win_pct': round(home_wins / total_juegos * 100, 1),
            'avg_margin': round(avg_margin, 1),
            'avg_total_runs': round(avg_total_runs, 1),
            'team_streaks': team_streaks
        }

if __name__ == "__main__":
    scraper = MLBResultadosScraper(dias=10)
    resultados = scraper.scrape_ultimos_dias()
    scraper.guardar_json()
    
    reporte = scraper.generar_reporte()
    print("\n📊 REPORTE DE LOS ÚLTIMOS 10 DÍAS:")
    print(f"   Total juegos: {reporte['total_juegos']}")
    print(f"   Victorias local: {reporte['home_wins']} ({reporte['home_win_pct']}%)")
    print(f"   Victorias visitante: {reporte['away_wins']}")
    print(f"   Margen promedio: {reporte['avg_margin']} carreras")
    print(f"   Total carreras promedio: {reporte['avg_total_runs']}")
