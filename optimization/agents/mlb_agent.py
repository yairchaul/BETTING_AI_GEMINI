"""
MLB Agent - Agente especializado para consultas de MLB optimizadas
"""

import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MLBAgent:
    """
    Agente especializado para consultas de MLB.
    
    Mantiene en contexto:
    - Picks del día cacheados
    - Estadísticas de pitchers/bateadores
    - Análisis precomputados
    """
    
    def __init__(self):
        """Inicializa agente MLB."""
        self.context = {
            'todays_picks': None,
            'last_fetch': None,
            'cached_analyses': {},
            'player_stats': {},
            'team_stats': {},
            'initialized_at': time.time()
        }
        
        # Intentar cargar datos iniciales
        self._load_initial_data()
        
        logger.info("MLBAgent inicializado")
    
    def process(self, query: str, user_context: Optional[Dict] = None) -> Dict:
        """
        Procesa una consulta de MLB.
        
        Args:
            query: Consulta del usuario
            user_context: Contexto adicional (game_pk, etc.)
            
        Returns:
            Respuesta procesada
        """
        if user_context is None:
            user_context = {}
        
        # Clasificar tipo de consulta
        query_type = self._classify_mlb_query(query)
        
        # Procesar según tipo
        if query_type == 'todays_picks':
            return self._process_todays_picks(user_context)
        elif query_type == 'game_analysis':
            return self._process_game_analysis(query, user_context)
        elif query_type == 'player_stats':
            return self._process_player_stats(query, user_context)
        elif query_type == 'hr_picks':
            return self._process_hr_picks(user_context)
        else:
            return self._process_general_query(query, user_context)
    
    def _classify_mlb_query(self, query: str) -> str:
        """Clasifica consultas de MLB."""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ['picks hoy', 'picks today', 'apuestas mlb', 'mlb picks']):
            return 'todays_picks'
        elif any(term in query_lower for term in ['vs', 'contra', 'análisis', 'analysis']):
            return 'game_analysis'
        elif any(term in query_lower for term in ['stats', 'estadisticas', 'pitcher', 'bateador']):
            return 'player_stats'
        elif any(term in query_lower for term in ['home run', 'hr', 'homerun']):
            return 'hr_picks'
        else:
            return 'general'
    
    def _process_todays_picks(self, context: Dict) -> Dict:
        """Procesa consulta de picks del día."""
        # Verificar si necesitamos actualizar
        if self._needs_picks_refresh():
            self._fetch_and_cache_todays_picks()
        
        if self.context['todays_picks']:
            picks = self.context['todays_picks']
            
            # Formatear respuesta
            return {
                'response_type': 'mlb_todays_picks',
                'picks': picks,
                'count': len(picks),
                'last_updated': self.context['last_fetch'],
                'source': 'cache' if self.context['last_fetch'] else 'live'
            }
        else:
            # Fallback a motor original
            return self._fallback_to_original('todays_picks', context)
    
    def _process_game_analysis(self, query: str, context: Dict) -> Dict:
        """Procesa análisis de partido específico."""
        # Extraer equipos de la consulta
        teams = self._extract_teams_from_query(query)
        
        if teams and len(teams) == 2:
            home, away = teams
            
            # Verificar caché
            cache_key = f"{home}_{away}"
            if cache_key in self.context['cached_analyses']:
                cached = self.context['cached_analyses'][cache_key]
                
                # Verificar si es reciente (<10 minutos)
                if time.time() - cached.get('timestamp', 0) < 600:
                    return cached['analysis']
            
            # Generar nuevo análisis
            analysis = self._analyze_game(home, away, context)
            
            # Cachear
            self.context['cached_analyses'][cache_key] = {
                'analysis': analysis,
                'timestamp': time.time()
            }
            
            return analysis
        
        # No se pudieron extraer equipos
        return self._fallback_to_original('game_analysis', context)
    
    def _process_player_stats(self, query: str, context: Dict) -> Dict:
        """Procesa consulta de stats de jugador."""
        # Extraer nombre del jugador
        player_name = self._extract_player_name(query)
        
        if player_name and player_name in self.context['player_stats']:
            stats = self.context['player_stats'][player_name]
            return {
                'response_type': 'player_stats',
                'player': player_name,
                'stats': stats,
                'source': 'cache'
            }
        
        # Buscar en datos disponibles
        # TODO: Integrar con base de datos o API
        
        return {
            'response_type': 'player_stats',
            'player': player_name or 'Desconocido',
            'stats': {},
            'message': 'Stats no disponibles en caché'
        }
    
    def _process_hr_picks(self, context: Dict) -> Dict:
        """Procesa picks de home runs."""
        # Verificar caché de HR picks
        if 'hr_picks' in self.context and self.context['hr_picks']:
            hr_data = self.context['hr_picks']
            
            # Verificar antigüedad
            if time.time() - hr_data.get('timestamp', 0) < 300:  # 5 minutos
                return hr_data['picks']
        
        # Generar HR picks
        hr_picks = self._generate_hr_picks(context)
        
        # Cachear
        self.context['hr_picks'] = {
            'picks': hr_picks,
            'timestamp': time.time()
        }
        
        return hr_picks
    
    def _process_general_query(self, query: str, context: Dict) -> Dict:
        """Procesa consulta general de MLB."""
        # Para consultas generales, usar fallback al motor original
        return self._fallback_to_original('general', context)
    
    def _needs_picks_refresh(self) -> bool:
        """Determina si necesitamos actualizar picks del día."""
        if not self.context['todays_picks']:
            return True
        
        if not self.context['last_fetch']:
            return True
        
        # Actualizar cada 5 minutos
        return time.time() - self.context['last_fetch'] > 300
    
    def _fetch_and_cache_todays_picks(self):
        """Obtiene y cachea picks del día."""
        try:
            # Importar motor MLB original
            from motors.motor_mlb_pro import analizar_mlb_pro_v20
            
            # Obtener partidos de hoy (esto es un placeholder)
            # En implementación real, se obtendrían de scraping o API
            todays_games = self._get_todays_games()
            
            picks = []
            for game in todays_games[:10]:  # Limitar a 10 partidos
                try:
                    analysis = analizar_mlb_pro_v20(game)
                    if analysis and analysis.get('recommendacion') != 'EVITAR':
                        picks.append({
                            'game': f"{game.get('visitante', '')} @ {game.get('local', '')}",
                            'pick': analysis.get('pick'),
                            'confidence': analysis.get('confianza', 0),
                            'stake': analysis.get('stake', 0),
                            'type': analysis.get('tipo_apuesta', 'MONEYLINE'),
                            'reason': analysis.get('razon_decision', '')
                        })
                except Exception as e:
                    logger.debug(f"Error analizando juego: {e}")
            
            self.context['todays_picks'] = picks
            self.context['last_fetch'] = time.time()
            
            logger.info(f"Picks del día actualizados: {len(picks)} picks")
            
        except ImportError as e:
            logger.error(f"No se pudo importar motor MLB: {e}")
            self.context['todays_picks'] = []
            self.context['last_fetch'] = time.time()
    
    def _get_todays_games(self) -> list:
        """Obtiene partidos de hoy (placeholder)."""
        # En implementación real, esto obtendría de scraping
        return [
            {'visitante': 'Yankees', 'local': 'Red Sox', 'game_pk': '12345'},
            {'visitante': 'Dodgers', 'local': 'Giants', 'game_pk': '12346'},
            {'visitante': 'Braves', 'local': 'Mets', 'game_pk': '12347'}
        ]
    
    def _analyze_game(self, home: str, away: str, context: Dict) -> Dict:
        """Analiza un partido específico."""
        try:
            from motors.motor_mlb_pro import analizar_mlb_pro_v20
            
            # Crear objeto de partido
            game = {
                'visitante': away,
                'local': home,
                'game_pk': context.get('game_pk')
            }
            
            # Analizar
            analysis = analizar_mlb_pro_v20(game, game_pk=context.get('game_pk'))
            
            return {
                'response_type': 'game_analysis',
                'home': home,
                'away': away,
                'analysis': analysis,
                'confidence': analysis.get('confianza', 0),
                'pick': analysis.get('pick'),
                'recommendation': analysis.get('recommendacion'),
                'source': 'live_analysis'
            }
            
        except ImportError as e:
            logger.error(f"Error importando motor MLB: {e}")
            return {
                'response_type': 'game_analysis',
                'home': home,
                'away': away,
                'error': 'Motor no disponible',
                'source': 'fallback'
            }
    
    def _generate_hr_picks(self, context: Dict) -> Dict:
        """Genera picks de home runs."""
        try:
            from motors.predictor_hr_corregido import predictor_hr_optimizado
            
            # Obtener equipos de hoy
            todays_games = self._get_todays_games()
            
            hr_picks = []
            for game in todays_games:
                home = game.get('local')
                away = game.get('visitante')
                
                # Obtener predicciones HR para ambos equipos
                for team in [home, away]:
                    try:
                        predictions = predictor_hr_optimizado.obtener_predicciones_para_equipo(
                            team, 
                            game_pk=game.get('game_pk')
                        )
                        
                        for pred in predictions[:2]:  # Top 2 por equipo
                            if pred.get('probabilidad', 0) >= 25:
                                hr_picks.append({
                                    'batter': pred['bateador'],
                                    'team': team,
                                    'probability': pred['probabilidad'],
                                    'stake': pred['stake'],
                                    'vs': pred.get('pitcher_rival', ''),
                                    'reason': f"HR total: {pred.get('hr_total', 0)}"
                                })
                    except Exception as e:
                        logger.debug(f"Error obteniendo HR predictions para {team}: {e}")
            
            return {
                'response_type': 'hr_picks',
                'picks': hr_picks,
                'count': len(hr_picks),
                'source': 'hr_predictor'
            }
            
        except ImportError as e:
            logger.error(f"Error importando predictor HR: {e}")
            return {
                'response_type': 'hr_picks',
                'picks': [],
                'count': 0,
                'error': 'Predictor HR no disponible'
            }
    
    def _extract_teams_from_query(self, query: str) -> Optional[list]:
        """Extrae nombres de equipos de una consulta."""
        # Lista de equipos MLB comunes
        mlb_teams = [
            'Yankees', 'Red Sox', 'Dodgers', 'Giants', 'Cubs', 'Cardinals',
            'Braves', 'Mets', 'Phillies', 'Nationals', 'Marlins', 'Blue Jays',
            'Rays', 'Orioles', 'Guardians', 'White Sox', 'Tigers', 'Royals',
            'Twins', 'Astros', 'Rangers', 'Mariners', 'Athletics', 'Angels',
            'Padres', 'Diamondbacks', 'Rockies', 'Brewers', 'Reds', 'Pirates'
        ]
        
        found_teams = []
        for team in mlb_teams:
            if team.lower() in query.lower():
                found_teams.append(team)
        
        return found_teams if len(found_teams) >= 2 else None
    
    def _extract_player_name(self, query: str) -> Optional[str]:
        """Extrae nombre de jugador de una consulta."""
        # Lista de jugadores conocidos (placeholder)
        known_players = [
            'Aaron Judge', 'Mike Trout', 'Mookie Betts', 'Shohei Ohtani',
            'Ronald Acuña', 'Fernando Tatis', 'Juan Soto', 'Bryce Harper'
        ]
        
        for player in known_players:
            if player.lower() in query.lower():
                return player
        
        return None
    
    def _fallback_to_original(self, query_type: str, context: Dict) -> Dict:
        """Fallback al motor original de MLB."""
        logger.info(f"Fallback a motor original para: {query_type}")
        
        return {
            'response_type': f'mlb_{query_type}',
            'data': {},
            'message': 'Usando motor original (fallback)',
            'source': 'fallback',
            'timestamp': time.time()
        }
    
    def _load_initial_data(self):
        """Carga datos iniciales para el agente."""
        try:
            # Intentar cargar stats de archivos
            import json
            import os
            
            # Stats de jugadores
            stats_file = os.path.join('data', 'player_stats.json')
            if os.path.exists(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    self.context['player_stats'] = json.load(f)
            
            # Stats de equipos
            team_stats_file = os.path.join('data', 'team_stats.json')
            if os.path.exists(team_stats_file):
                with open(team_stats_file, 'r', encoding='utf-8') as f:
                    self.context['team_stats'] = json.load(f)
            
            logger.debug("Datos iniciales cargados para MLBAgent")
            
        except Exception as e:
            logger.debug(f"Error cargando datos iniciales: {e}")
    
    def get_context_info(self) -> Dict:
        """Obtiene información del contexto del agente."""
        return {
            'initialized_at': datetime.fromtimestamp(self.context['initialized_at']).isoformat(),
            'todays_picks_count': len(self.context['todays_picks']) if self.context['todays_picks'] else 0,
            'cached_analyses_count': len(self.context['cached_analyses']),
            'player_stats_count': len(self.context['player_stats']),
            'team_stats_count': len(self.context['team_stats']),
            'last_fetch': datetime.fromtimestamp(self.context['last_fetch']).isoformat() if self.context['last_fetch'] else None,
            'uptime_hours': (time.time() - self.context['initialized_at']) / 3600
        }
    
    def clear_cache(self, cache_type: str = None):
        """Limpia caché del agente."""
        if cache_type == 'picks' or cache_type is None:
            self.context['todays_picks'] = None
            self.context['last_fetch'] = None
        
        if cache_type == 'analyses' or cache_type is None:
            self.context['cached_analyses'] = {}
        
        if cache_type == 'hr_picks' or cache_type is None:
            if 'hr_picks' in self.context:
                del self.context['hr_picks']
        
        logger.info(f"Caché MLB limpiado: {cache_type or 'todo'}")
    
    def warmup(self):
        """Precalienta el agente cargando datos comunes."""
        logger.info("Precalentando MLBAgent...")
        
        # Cargar picks del día
        self._fetch_and_cache_todays_picks()
        
        # Cargar stats comunes
        self._load_initial_data()
        
        logger.info("MLBAgent precalentado")