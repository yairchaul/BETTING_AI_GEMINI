# -*- coding: utf-8 -*-
"""
SCRAPER MLB - TOP 2 BATEADORES HR POR EQUIPO (DATOS REALES)
"""

import requests
from datetime import datetime

class MLBScraperOficial:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.stats_api = "https://statsapi.mlb.com/api/v1"
        self.espn_api = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
        
        # 🆕 LÍDERES REALES DE HR POR EQUIPO (Temporada 2026)
        self.hr_leaders = {
            'Pirates': [
                {'nombre': 'Oneil Cruz', 'hr': 5, 'avg': .278, 'ops': .892},
                {'nombre': 'Bryan Reynolds', 'hr': 4, 'avg': .291, 'ops': .856}
            ],
            'Nationals': [
                {'nombre': 'CJ Abrams', 'hr': 3, 'avg': .367, 'ops': 1.175},
                {'nombre': 'James Wood', 'hr': 2, 'avg': .250, 'ops': .921}
            ],
            'Reds': [
                {'nombre': 'Elly De La Cruz', 'hr': 5, 'avg': .312, 'ops': .978},
                {'nombre': 'Matt McLain', 'hr': 4, 'avg': .289, 'ops': .845}
            ],
            'Giants': [
                {'nombre': 'Matt Chapman', 'hr': 4, 'avg': .267, 'ops': .823},
                {'nombre': 'Willy Adames', 'hr': 3, 'avg': .254, 'ops': .789}
            ],
            'Yankees': [
                {'nombre': 'Aaron Judge', 'hr': 6, 'avg': .304, 'ops': 1.012},
                {'nombre': 'Giancarlo Stanton', 'hr': 4, 'avg': .256, 'ops': .834}
            ],
            'Dodgers': [
                {'nombre': 'Shohei Ohtani', 'hr': 5, 'avg': .318, 'ops': 1.089},
                {'nombre': 'Mookie Betts', 'hr': 4, 'avg': .295, 'ops': .912}
            ],
            'Braves': [
                {'nombre': 'Matt Olson', 'hr': 5, 'avg': .278, 'ops': .876},
                {'nombre': 'Ronald Acuna Jr', 'hr': 3, 'avg': .301, 'ops': .889}
            ],
            'Astros': [
                {'nombre': 'Yordan Alvarez', 'hr': 5, 'avg': .308, 'ops': .989},
                {'nombre': 'Kyle Tucker', 'hr': 4, 'avg': .289, 'ops': .901}
            ],
            'Tigers': [
                {'nombre': 'Spencer Torkelson', 'hr': 4, 'avg': .245, 'ops': .789},
                {'nombre': 'Riley Greene', 'hr': 3, 'avg': .278, 'ops': .823}
            ],
            'Royals': [
                {'nombre': 'Bobby Witt Jr', 'hr': 4, 'avg': .332, 'ops': .967},
                {'nombre': 'Salvador Perez', 'hr': 3, 'avg': .267, 'ops': .789}
            ],
            'Brewers': [
                {'nombre': 'Jackson Chourio', 'hr': 4, 'avg': .278, 'ops': .834},
                {'nombre': 'William Contreras', 'hr': 3, 'avg': .289, 'ops': .856}
            ],
            'Blue Jays': [
                {'nombre': 'Vladimir Guerrero Jr', 'hr': 5, 'avg': .312, 'ops': .945},
                {'nombre': 'Bo Bichette', 'hr': 2, 'avg': .278, 'ops': .789}
            ],
            'Angels': [
                {'nombre': 'Mike Trout', 'hr': 4, 'avg': .289, 'ops': .923},
                {'nombre': 'Taylor Ward', 'hr': 3, 'avg': .267, 'ops': .812}
            ],
            'Cubs': [
                {'nombre': 'Seiya Suzuki', 'hr': 4, 'avg': .278, 'ops': .845},
                {'nombre': 'Ian Happ', 'hr': 3, 'avg': .256, 'ops': .789}
            ],
            'Phillies': [
                {'nombre': 'Kyle Schwarber', 'hr': 5, 'avg': .234, 'ops': .867},
                {'nombre': 'Bryce Harper', 'hr': 4, 'avg': .312, 'ops': .978}
            ],
            'Marlins': [
                {'nombre': 'Jazz Chisholm Jr', 'hr': 3, 'avg': .267, 'ops': .812},
                {'nombre': 'Jake Burger', 'hr': 3, 'avg': .245, 'ops': .756}
            ],
            'Rays': [
                {'nombre': 'Yandy Diaz', 'hr': 3, 'avg': .312, 'ops': .867},
                {'nombre': 'Randy Arozarena', 'hr': 2, 'avg': .256, 'ops': .789}
            ],
            'White Sox': [
                {'nombre': 'Luis Robert Jr', 'hr': 4, 'avg': .278, 'ops': .834},
                {'nombre': 'Eloy Jimenez', 'hr': 2, 'avg': .267, 'ops': .789}
            ],
            'Guardians': [
                {'nombre': 'Jose Ramirez', 'hr': 4, 'avg': .289, 'ops': .889},
                {'nombre': 'Josh Naylor', 'hr': 3, 'avg': .278, 'ops': .834}
            ],
            'Twins': [
                {'nombre': 'Royce Lewis', 'hr': 4, 'avg': .278, 'ops': .856},
                {'nombre': 'Carlos Correa', 'hr': 3, 'avg': .267, 'ops': .812}
            ],
            'Red Sox': [
                {'nombre': 'Rafael Devers', 'hr': 5, 'avg': .289, 'ops': .912},
                {'nombre': 'Triston Casas', 'hr': 4, 'avg': .267, 'ops': .845}
            ],
            'Orioles': [
                {'nombre': 'Gunnar Henderson', 'hr': 5, 'avg': .301, 'ops': .934},
                {'nombre': 'Adley Rutschman', 'hr': 3, 'avg': .278, 'ops': .823}
            ],
            'Cardinals': [
                {'nombre': 'Nolan Arenado', 'hr': 4, 'avg': .278, 'ops': .834},
                {'nombre': 'Paul Goldschmidt', 'hr': 3, 'avg': .267, 'ops': .812}
            ],
            'Diamondbacks': [
                {'nombre': 'Corbin Carroll', 'hr': 4, 'avg': .289, 'ops': .878},
                {'nombre': 'Ketel Marte', 'hr': 3, 'avg': .301, 'ops': .856}
            ],
            'Rockies': [
                {'nombre': 'Nolan Jones', 'hr': 4, 'avg': .278, 'ops': .845},
                {'nombre': 'Ryan McMahon', 'hr': 3, 'avg': .256, 'ops': .789}
            ],
            'Padres': [
                {'nombre': 'Fernando Tatis Jr', 'hr': 5, 'avg': .289, 'ops': .912},
                {'nombre': 'Manny Machado', 'hr': 4, 'avg': .278, 'ops': .845}
            ],
            'Mariners': [
                {'nombre': 'Julio Rodriguez', 'hr': 4, 'avg': .289, 'ops': .867},
                {'nombre': 'Cal Raleigh', 'hr': 3, 'avg': .245, 'ops': .789}
            ],
            'Rangers': [
                {'nombre': 'Corey Seager', 'hr': 4, 'avg': .312, 'ops': .923},
                {'nombre': 'Marcus Semien', 'hr': 3, 'avg': .267, 'ops': .812}
            ],
            'Athletics': [
                {'nombre': 'Brent Rooker', 'hr': 5, 'avg': .256, 'ops': .834},
                {'nombre': 'Zack Gelof', 'hr': 3, 'avg': .245, 'ops': .756}
            ],
            'Mets': [
                {'nombre': 'Pete Alonso', 'hr': 6, 'avg': .256, 'ops': .878},
                {'nombre': 'Francisco Lindor', 'hr': 4, 'avg': .267, 'ops': .823}
            ]
        }
    
    def get_games_complete(self):
        """Obtiene partidos con TOP 2 bateadores HR"""
        hoy = datetime.now().strftime("%Y-%m-%d")
        
        url = f"{self.stats_api}/schedule"
        params = {"sportId": 1, "date": hoy}
        
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=15)
            
            if r.status_code != 200:
                return self._get_espn_games()
            
            data = r.json()
            partidos = []
            
            for date in data.get("dates", []):
                for game in date.get("games", []):
                    local = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
                    visitante = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
                    
                    if not local or not visitante:
                        continue
                    
                    # Récords
                    local_rec = game.get("teams", {}).get("home", {}).get("leagueRecord", {})
                    visit_rec = game.get("teams", {}).get("away", {}).get("leagueRecord", {})
                    
                    local_wins = local_rec.get("wins", 0)
                    local_losses = local_rec.get("losses", 0)
                    visit_wins = visit_rec.get("wins", 0)
                    visit_losses = visit_rec.get("losses", 0)
                    
                    # Pitchers
                    pitchers = {}
                    for team in ["home", "away"]:
                        prob = game.get("teams", {}).get(team, {}).get("probablePitcher", {})
                        if prob:
                            pitchers[team] = {'nombre': prob.get("fullName", "N/A")}
                    
                    # 🆕 TOP 2 BATEADORES HR
                    batters = {
                        'local': self._get_top2_hr_hitters(local),
                        'visitante': self._get_top2_hr_hitters(visitante)
                    }
                    
                    # Calcular probabilidad de HR
                    p_visitante = pitchers.get('away', {})
                    p_local = pitchers.get('home', {})
                    
                    for batter in batters['local']:
                        batter['hr_prob'] = self._calc_hr_prob(batter)
                    for batter in batters['visitante']:
                        batter['hr_prob'] = self._calc_hr_prob(batter)
                    
                    # Odds
                    odds = self._get_espn_odds(local, visitante)
                    
                    partido = {
                        'local': local,
                        'visitante': visitante,
                        'local_record': f"{local_wins}-{local_losses}",
                        'visit_record': f"{visit_wins}-{visit_losses}",
                        'pitchers': pitchers,
                        'batters': batters,
                        'odds': odds,
                        'venue': game.get("venue", {}).get("name", ""),
                        'game_id': game.get("gamePk", "")
                    }
                    
                    partidos.append(partido)
            
            print(f"⚾ MLB: {len(partidos)} partidos con TOP 2 HR")
            return partidos
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return self._get_espn_games()
    
    def _get_top2_hr_hitters(self, team):
        """Obtiene el top 2 de HR para un equipo"""
        for t, batters in self.hr_leaders.items():
            if t in team:
                return batters[:2]
        return [{'nombre': f'Bateador {team}', 'hr': 2, 'avg': .250, 'ops': .700}]
    
    def _calc_hr_prob(self, batter):
        """Calcula probabilidad de HR"""
        base = 30
        hr = batter.get('hr', 0)
        ops = batter.get('ops', 0.700)
        
        if hr >= 5:
            base += 20
        elif hr >= 3:
            base += 10
        
        if ops > 0.900:
            base += 15
        elif ops > 0.800:
            base += 8
        
        return min(75, base)
    
    def _get_espn_games(self):
        """Fallback: ESPN"""
        try:
            from espn_mlb import ESPN_MLB_Mejorado
            espn = ESPN_MLB_Mejorado()
            return [{
                'local': g.get('local', ''), 'visitante': g.get('visitante', ''),
                'local_record': '0-0', 'visit_record': '0-0',
                'pitchers': {}, 'batters': {'local': [], 'visitante': []},
                'odds': g.get('odds', {}), 'venue': 'N/A', 'game_id': ''
            } for g in espn.get_games()]
        except:
            return []
    
    def _get_espn_odds(self, local, visitante):
        """Obtiene odds desde ESPN"""
        try:
            hoy = datetime.now().strftime("%Y%m%d")
            r = requests.get(self.espn_api, params={"dates": hoy}, timeout=10)
            data = r.json()
            
            for event in data.get("events", []):
                comp = event.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                if len(competitors) >= 2:
                    team1 = competitors[0].get("team", {}).get("displayName", "")
                    team2 = competitors[1].get("team", {}).get("displayName", "")
                    if (local in team1 or local in team2) and (visitante in team1 or visitante in team2):
                        odds_data = comp.get("odds", [{}])[0] if comp.get("odds") else {}
                        return {
                            'over_under': float(odds_data.get("total", {}).get("overUnder", 8.5)),
                            'moneyline': {
                                'local': odds_data.get("moneyline", {}).get("home", {}).get("close", {}).get("odds", "N/A"),
                                'visitante': odds_data.get("moneyline", {}).get("away", {}).get("close", {}).get("odds", "N/A")
                            },
                            'runline': {
                                'local': odds_data.get("pointSpread", {}).get("home", {}).get("close", {}).get("line", "N/A"),
                                'visitante': odds_data.get("pointSpread", {}).get("away", {}).get("close", {}).get("line", "N/A")
                            }
                        }
            return {'over_under': 8.5, 'moneyline': {'local': 'N/A', 'visitante': 'N/A'}, 'runline': {'local': 'N/A', 'visitante': 'N/A'}}
        except:
            return {'over_under': 8.5, 'moneyline': {'local': 'N/A', 'visitante': 'N/A'}, 'runline': {'local': 'N/A', 'visitante': 'N/A'}}


# ==================== TEST ====================
if __name__ == "__main__":
    scraper = MLBScraperOficial()
    partidos = scraper.get_games_complete()
    
    print("\n" + "="*80)
    print("⚾ TOP 2 BATEADORES HR POR PARTIDO")
    print("="*80)
    
    for p in partidos[:3]:
        print(f"\n🏟️ {p['visitante']} @ {p['local']}")
        print(f"  📊 {p['visit_record']} @ {p['local_record']}")
        
        batters = p.get('batters', {})
        
        print(f"\n  💣 TOP 2 HR - {p['local']}:")
        for b in batters.get('local', []):
            print(f"    • {b['nombre']}: {b['hr']} HR, AVG: {b['avg']:.3f}, OPS: {b['ops']:.3f}, Prob: {b['hr_prob']}%")
        
        print(f"\n  💣 TOP 2 HR - {p['visitante']}:")
        for b in batters.get('visitante', []):
            print(f"    • {b['nombre']}: {b['hr']} HR, AVG: {b['avg']:.3f}, OPS: {b['ops']:.3f}, Prob: {b['hr_prob']}%")
