# -*- coding: utf-8 -*-
"""
ESPN UFC - Scraper garantizado
"""
import requests
import logging

logger = logging.getLogger(__name__)

class ESPN_UFC:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    def get_events(self):
        """Obtiene cartelera UFC desde ESPN"""
        try:
            url = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            
            events = data.get('events', [])
            if not events:
                logger.warning("No hay eventos UFC")
                return []
            
            all_fights = []
            
            for event in events:
                event_name = event.get('name', 'UFC Event')
                event_date = event.get('date', '')[:10]
                
                for comp in event.get('competitions', []):
                    competitors = comp.get('competitors', [])
                    if len(competitors) >= 2:
                        p1 = competitors[0]
                        p2 = competitors[1]
                        
                        p1_records = p1.get('records', [])
                        p2_records = p2.get('records', [])

                        p1_streak = next((r.get('summary', '') for r in p1_records if r.get('type') == 'streak'), 'N/A')
                        p2_streak = next((r.get('summary', '') for r in p2_records if r.get('type') == 'streak'), 'N/A')
                        
                        p1_name = p1.get('athlete', {}).get('displayName', '')
                        p2_name = p2.get('athlete', {}).get('displayName', '')
                        
                        if p1_name and p2_name:
                            odds = comp.get('odds', [{}])[0] if comp.get('odds') else {}
                            
                            fight = {
                                'evento': event_name,
                                'fecha': event_date,
                                'peleador1': {
                                    'nombre': p1_name,
                                    'record': next((r.get('summary', '0-0-0') for r in p1_records if r.get('type') == 'total'), '0-0-0'),
                                    'streak': p1_streak,
                                    'odds': odds.get('awayTeamOdds', {}).get('value', 'N/A') if odds else 'N/A'
                                },
                                'peleador2': {
                                    'nombre': p2_name,
                                    'record': next((r.get('summary', '0-0-0') for r in p2_records if r.get('type') == 'total'), '0-0-0'),
                                    'streak': p2_streak,
                                    'odds': odds.get('homeTeamOdds', {}).get('value', 'N/A') if odds else 'N/A'
                                }
                            }
                            all_fights.append(fight)
            
            logger.info(f"✅ {len(all_fights)} combates UFC cargados")
            return all_fights
            
        except Exception as e:
            logger.error(f"Error ESPN UFC: {e}")
            return self._get_fallback_fights()
    
    def _get_fallback_fights(self):
        """Combates de respaldo"""
        return [
            {
                'evento': 'UFC Fight Night',
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'peleador1': {'nombre': 'Peleador 1', 'record': '0-0', 'odds': 'N/A'},
                'peleador2': {'nombre': 'Peleador 2', 'record': '0-0', 'odds': 'N/A'}
            }
        ]

# Import para fallback
from datetime import datetime