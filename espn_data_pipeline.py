# -*- coding: utf-8 -*-
"""
ESPN DATA PIPELINE - Extracción de datos de ESPN con TODAS las cuotas
"""
import requests
import streamlit as st
from datetime import datetime

class ESPNDataPipeline:
    def __init__(self):
        self.base_url = "https://site.web.api.espn.com/apis/site/v2/sports"
        self.ligas_codigos = {
            "México - Liga MX": "mex.1",
            "UEFA - Champions League": "uefa.champions",
            "UEFA - Europa League": "uefa.europa",
            "UEFA - Europa Conference League": "uefa.europa.conf",
            "La Liga": "esp.1",
            "Inglaterra - Premier League": "eng.1",
            "Bundesliga 1": "ger.1",
            "Serie A": "ita.1",
            "Ligue 1": "fra.1",
            "Holanda - Eredivisie": "ned.1",
            "Portugal - Primeira Liga": "por.1",
            "México - Liga de Expansión MX": "mex.2",
            "Eliminatorias UEFA": "fifa.worldq.uefa",
            "México - Liga MX Femenil": "mex.women",
            "CONCACAF Champions Cup": "concacaf.champions",
            "Copa Libertadores": "conmebol.libertadores",
            "Copa Sudamericana": "conmebol.sudamericana",
            "Brasil - Serie A": "bra.1",
            "Argentina - Liga Profesional": "arg.1",
            "MLS - Major League Soccer": "usa.1",
        }
    
    def get_nba_games_with_odds(self):
        try:
            fecha = datetime.now().strftime("%Y%m%d")
            url = f"{self.base_url}/basketball/nba/scoreboard?dates={fecha}&limit=100"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                partidos = []
                for event in data.get('events', []):
                    competition = event['competitions'][0]
                    competitors = competition['competitors']
                    if len(competitors) >= 2:
                        home = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
                        away = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])
                        odds_data = self._extract_nba_odds(competition)
                        lideres_local, lideres_visit = self._extract_nba_leaders(competitors)
                        partidos.append({
                            'id': event.get('id'),
                            'local': home['team']['displayName'],
                            'visitante': away['team']['displayName'],
                            'fecha': event.get('date', '')[:10],
                            'hora': competition.get('date', '')[-8:] if competition.get('date') else '',
                            'estado': competition.get('status', {}).get('type', 'scheduled'),
                            'records': {
                                'local': home.get('records', [{}])[0].get('summary', '0-0') if home.get('records') else '0-0',
                                'visitante': away.get('records', [{}])[0].get('summary', '0-0') if away.get('records') else '0-0'
                            },
                            'odds': odds_data,
                            'lideres': {
                                'local': lideres_local,
                                'visitante': lideres_visit
                            }
                        })
                return partidos
            return self._get_mock_nba_data()
        except:
            return self._get_mock_nba_data()

    def _extract_nba_odds(self, competition):
        odds_data = {
            'moneyline': {'local': 'N/A', 'visitante': 'N/A'},
            'spread': {'valor': 0, 'local_odds': 'N/A', 'visitante_odds': 'N/A'},
            'totales': {'linea': 0, 'over_odds': 'N/A', 'under_odds': 'N/A'}
        }
        if 'odds' in competition and competition['odds']:
            odds = competition['odds'][0]
            if 'homeTeamOdds' in odds and odds['homeTeamOdds']:
                odds_data['moneyline']['local'] = odds['homeTeamOdds'].get('american', 'N/A')
            if 'awayTeamOdds' in odds and odds['awayTeamOdds']:
                odds_data['moneyline']['visitante'] = odds['awayTeamOdds'].get('american', 'N/A')
            odds_data['spread']['valor'] = odds.get('spread', 0)
            odds_data['totales']['linea'] = odds.get('overUnder', 0)
        return odds_data

    def _extract_nba_leaders(self, competitors):
        lideres_local, lideres_visit = [], []
        for i, comp in enumerate(competitors):
            if 'leaders' in comp:
                for lider in comp['leaders']:
                    if lider.get('name') in ['pointsPerGame', 'assistsPerGame', 'reboundsPerGame']:
                        for jugador in lider.get('leaders', []):
                            stats = {
                                'nombre': jugador['athlete']['displayName'],
                                'categoria': lider['name'],
                                'valor': jugador['displayValue'],
                                'equipo': comp['team']['displayName']
                            }
                            if i == 0: lideres_local.append(stats)
                            else: lideres_visit.append(stats)
        return lideres_local, lideres_visit

    def _get_mock_nba_data(self):
        return [{'id': 'mock1', 'local': 'Hornets', 'visitante': 'Magic', 'fecha': '2026-04-27', 'hora': '19:00', 'estado': 'scheduled', 'records': {'local': '0-0', 'visitante': '0-0'}, 'odds': {'moneyline': {'local': '-110', 'visitante': '-110'}, 'spread': {'valor': 0, 'local_odds': '-110', 'visitante_odds': '-110'}, 'totales': {'linea': 220, 'over_odds': '-110', 'under_odds': '-110'}}, 'lideres': {'local': [], 'visitante': []}}]

    def get_soccer_games_today(self, liga_nombre):
        codigo = self.ligas_codigos.get(liga_nombre)
        if not codigo: return []
        try:
            url = f"{self.base_url}/soccer/{codigo}/scoreboard"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                partidos = []
                for event in response.json().get('events', []):
                    comp = event['competitions'][0]
                    partidos.append({
                        'id': event.get('id'),
                        'liga': liga_nombre,
                        'local': comp['competitors'][0]['team']['displayName'],
                        'visitante': comp['competitors'][1]['team']['displayName'],
                        'fecha': event.get('date', '')[:10]
                    })
                return partidos
        except: return []
        return []

    def get_ufc_events(self):
        try:
            url = f"{self.base_url}/mma/ufc/scoreboard"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                combates = []
                for event in response.json().get('events', []):
                    for competition in event.get('competitions', []):
                        comps = competition.get('competitors', [])
                        if len(comps) >= 2:
                            combates.append({
                                'id': event.get('id'),
                                'evento': event.get('name', 'UFC'),
                                'fecha': event.get('date', '')[:10],
                                'peleador1': {'nombre': comps[0]['athlete']['displayName'], 'record': comps[0].get('record', '0-0'), 'pais': 'N/A'},
                                'peleador2': {'nombre': comps[1]['athlete']['displayName'], 'record': comps[1].get('record', '0-0'), 'pais': 'N/A'}
                            })
                return combates
        except: return []
        return []
