"""
Optimization Manager - Componente central del sistema de optimización
"""

import re
import time
import logging
from typing import Dict, Optional, Any, Tuple
from datetime import datetime

from .config import (
    CACHE_CONFIG, TEMPLATE_CONFIG, AGENT_CONFIG, METRICS_CONFIG,
    QUERY_CLASSIFICATION, QUERY_TO_TEMPLATE, OPTIMIZATION_THRESHOLDS
)
from .cache import CacheCoordinator
from .templates import TemplateRenderer
from .metrics import TokenMonitor

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptimizationManager:
    """
    Manager principal que coordina toda la optimización de tokens.
    
    Responsabilidades:
    1. Clasificar consultas del usuario
    2. Coordinar caché (hit/miss)
    3. Dispatchear a agentes especializados
    4. Aplicar plantillas de optimización
    5. Registrar métricas
    """
    
    def __init__(self):
        """Inicializar todos los componentes del sistema."""
        logger.info("Inicializando OptimizationManager...")
        
        # Componentes del sistema
        self.cache = CacheCoordinator()
        self.templates = TemplateRenderer()
        self.metrics = TokenMonitor()
        
        # Agentes especializados (lazy loading)
        self._agents = {}
        
        # Estadísticas
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_processing_time': 0,
            'total_tokens_saved': 0
        }
        
        logger.info("OptimizationManager inicializado correctamente")
    
    def process_query(self, query: str, context: Optional[Dict] = None) -> Dict:
        """
        Procesa una consulta optimizando el uso de tokens.
        
        Args:
            query: Consulta del usuario
            context: Contexto adicional (game_pk, event_id, etc.)
            
        Returns:
            Dict con respuesta optimizada
        """
        start_time = time.time()
        self.stats['total_queries'] += 1
        
        # Preparar contexto
        if context is None:
            context = {}
        
        # 1. Clasificar la consulta
        query_type, query_subtype = self._classify_query(query, context)
        logger.debug(f"Consulta clasificada: {query_type}.{query_subtype}")
        
        # 2. Verificar caché
        cache_key = self._generate_cache_key(query_type, query_subtype, context)
        cached_response = self.cache.get(cached_key=cache_key)
        
        if cached_response:
            self.stats['cache_hits'] += 1
            logger.debug(f"Cache HIT para {cache_key}")
            
            # Formatear respuesta cacheada
            response = self._format_cached_response(cached_response, query_type)
            response['from_cache'] = True
            response['cache_age'] = time.time() - cached_response.get('timestamp', 0)
            
            # Registrar métricas
            processing_time = time.time() - start_time
            self._update_stats(response, processing_time, cached=True)
            
            return response
        
        # 3. Cache MISS - procesar consulta
        self.stats['cache_misses'] += 1
        logger.debug(f"Cache MISS para {cache_key}")
        
        # 4. Obtener agente especializado
        agent = self._get_agent(query_type)
        
        # 5. Procesar con agente
        raw_response = agent.process(query, context)
        
        # 6. Optimizar respuesta
        optimized_response = self._optimize_response(
            raw_response, query_type, query_subtype
        )
        
        # 7. Determinar si cachear
        should_cache = self._should_cache(query_type, raw_response, optimized_response)
        if should_cache:
            cache_data = {
                'data': optimized_response,
                'query_type': query_type,
                'query_subtype': query_subtype,
                'context': context,
                'timestamp': time.time()
            }
            self.cache.set(cache_key, cache_data, query_type)
            logger.debug(f"Respuesta cacheada: {cache_key}")
        
        # 8. Formatear respuesta final
        final_response = self._format_response(optimized_response, query_type)
        final_response['from_cache'] = False
        final_response['cache_key'] = cache_key if should_cache else None
        
        # 9. Registrar métricas
        processing_time = time.time() - start_time
        self._update_stats(final_response, processing_time, cached=False)
        
        logger.info(f"Consulta procesada: {query_type}.{query_subtype} "
                   f"en {processing_time:.2f}s")
        
        return final_response
    
    def _classify_query(self, query: str, context: Dict) -> Tuple[str, str]:
        """
        Clasifica la consulta en tipo y subtipo.
        
        Returns:
            Tuple (query_type, query_subtype)
        """
        query_lower = query.lower().strip()
        
        # Verificar patrones por deporte
        for sport, patterns in QUERY_CLASSIFICATION.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    # Determinar subtipo basado en contenido específico
                    subtype = self._determine_subtype(query_lower, sport, context)
                    return sport, subtype
        
        # Consulta general no clasificada
        return 'general', 'query'
    
    def _determine_subtype(self, query: str, sport: str, context: Dict) -> str:
        """Determina el subtipo específico de consulta."""
        if sport == 'mlb':
            if 'picks' in query or 'apuestas' in query or 'predicciones' in query:
                return 'picks'
            elif 'vs' in query or 'contra' in query or 'análisis' in query:
                return 'analysis'
            elif 'home run' in query or 'hr' in query:
                return 'hr_picks'
            elif 'pitcher' in query or 'lanzador' in query:
                return 'pitcher_stats'
        
        elif sport == 'ufc':
            if 'evento' in query or 'event' in query:
                return 'event'
            elif 'pelea' in query or 'fight' in query:
                return 'fight'
            elif 'ko' in query or 'knockout' in query:
                return 'ko_prediction'
        
        elif sport == 'futbol':
            if 'over' in query or 'under' in query or 'btts' in query:
                return 'predictions'
            elif 'liga' in query or 'league' in query:
                return 'league_predictions'
            elif 'handicap' in query or 'hándicap' in query:
                return 'handicap'
        
        elif sport == 'nba':
            if 'picks' in query or 'apuestas' in query:
                return 'picks'
            elif 'player' in query or 'jugador' in query:
                return 'player_props'
        
        return 'general'
    
    def _generate_cache_key(self, query_type: str, query_subtype: str, context: Dict) -> str:
        """Genera clave única para caché."""
        # Base key
        key_parts = [query_type, query_subtype]
        
        # Agregar contexto relevante
        if 'game_pk' in context:
            key_parts.append(f"game_{context['game_pk']}")
        if 'event_id' in context:
            key_parts.append(f"event_{context['event_id']}")
        if 'league' in context:
            key_parts.append(context['league'])
        if 'team' in context:
            key_parts.append(context['team'])
        
        # Agregar timestamp para granularidad horaria
        hour_key = datetime.now().strftime("%Y%m%d%H")
        key_parts.append(hour_key)
        
        return "_".join(key_parts)
    
    def _get_agent(self, query_type: str):
        """Obtiene agente especializado (lazy loading)."""
        if query_type not in self._agents:
            # Lazy loading del agente
            try:
                if query_type == 'mlb':
                    from .agents.mlb_agent import MLBAgent
                    self._agents['mlb'] = MLBAgent()
                elif query_type == 'ufc':
                    from .agents.ufc_agent import UFCAgent
                    self._agents['ufc'] = UFCAgent()
                elif query_type == 'futbol':
                    from .agents.futbol_agent import FutbolAgent
                    self._agents['futbol'] = FutbolAgent()
                elif query_type == 'nba':
                    from .agents.nba_agent import NBAAgent
                    self._agents['nba'] = NBAAgent()
                else:
                    # Agente general por defecto
                    from .agents.general_agent import GeneralAgent
                    self._agents['general'] = GeneralAgent()
            except ImportError as e:
                logger.error(f"Error cargando agente {query_type}: {e}")
                # Fallback a agente general
                from .agents.general_agent import GeneralAgent
                self._agents[query_type] = GeneralAgent()
        
        return self._agents.get(query_type, self._agents.get('general'))
    
    def _optimize_response(self, raw_response: Dict, query_type: str, query_subtype: str) -> Dict:
        """Aplica optimizaciones a la respuesta cruda."""
        # 1. Determinar plantilla a usar
        template_key = f"{query_type}_{query_subtype}"
        if template_key not in QUERY_TO_TEMPLATE:
            template_key = f"{query_type}_general"
        
        template_name = QUERY_TO_TEMPLATE.get(template_key, 'general_summary')
        
        # 2. Aplicar plantilla
        if template_name in TEMPLATE_CONFIG:
            optimized = self.templates.render(template_name, raw_response)
        else:
            # Fallback: usar compresión básica
            optimized = self._compress_response(raw_response)
        
        # 3. Calcular métricas de optimización
        original_tokens = self._estimate_tokens(str(raw_response))
        optimized_tokens = self._estimate_tokens(str(optimized))
        
        if original_tokens > 0:
            compression_ratio = 1 - (optimized_tokens / original_tokens)
            optimized['optimization_metrics'] = {
                'original_tokens': original_tokens,
                'optimized_tokens': optimized_tokens,
                'compression_ratio': round(compression_ratio, 3),
                'tokens_saved': original_tokens - optimized_tokens
            }
        
        return optimized
    
    def _compress_response(self, response: Dict) -> Dict:
        """Compresión básica de respuesta."""
        compressed = response.copy()
        
        # Acortar textos largos
        for key, value in compressed.items():
            if isinstance(value, str) and len(value) > 100:
                compressed[key] = value[:97] + "..."
            elif isinstance(value, dict):
                compressed[key] = self._compress_response(value)
            elif isinstance(value, list) and len(value) > 5:
                compressed[key] = value[:5]  # Limitar listas largas
        
        return compressed
    
    def _should_cache(self, query_type: str, raw_response: Dict, optimized_response: Dict) -> bool:
        """Determina si una respuesta debe ser cacheada."""
        # 1. Verificar configuración para este tipo
        if query_type not in CACHE_CONFIG:
            return False
        
        config = CACHE_CONFIG[query_type]
        
        # 2. Verificar confianza mínima
        confidence = raw_response.get('confidence', 0)
        if confidence < OPTIMIZATION_THRESHOLDS['min_confidence_for_cache']:
            logger.debug(f"No cachear: confianza {confidence} < umbral")
            return False
        
        # 3. Verificar calidad de la respuesta
        if 'error' in raw_response or 'exception' in raw_response:
            logger.debug("No cachear: respuesta contiene error")
            return False
        
        # 4. Verificar si es una respuesta válida para cachear
        if not self._is_cacheable_response(raw_response):
            logger.debug("No cachear: respuesta no es cacheable")
            return False
        
        # 5. Verificar tamaño de respuesta
        response_size = len(str(optimized_response).encode('utf-8'))
        if response_size > 1024 * 1024:  # 1MB
            logger.debug(f"No cachear: respuesta muy grande ({response_size} bytes)")
            return False
        
        return True
    
    def _is_cacheable_response(self, response: Dict) -> bool:
        """Verifica si una respuesta es adecuada para caché."""
        required_fields = ['response', 'timestamp']
        for field in required_fields:
            if field not in response:
                return False
        
        # Verificar que la respuesta no sea un error
        if isinstance(response.get('response'), dict) and 'error' in response['response']:
            return False
        
        return True
    
    def _format_cached_response(self, cached_data: Dict, query_type: str) -> Dict:
        """Formatea una respuesta cacheada."""
        response = cached_data['data'].copy()
        response['cached_at'] = cached_data['timestamp']
        response['query_type'] = query_type
        
        # Agregar indicador de caché
        response['_meta'] = {
            'source': 'cache',
            'age_seconds': time.time() - cached_data['timestamp'],
            'original_query_type': cached_data.get('query_type', 'unknown')
        }
        
        return response
    
    def _format_response(self, optimized_response: Dict, query_type: str) -> Dict:
        """Formatea respuesta final para el usuario."""
        response = optimized_response.copy()
        
        # Agregar metadatos
        response['_meta'] = {
            'source': 'live',
            'processed_at': datetime.now().isoformat(),
            'query_type': query_type,
            'system': 'token_optimization_v1'
        }
        
        # Asegurar formato consistente
        if 'response' not in response:
            response['response'] = response
        
        return response
    
    def _update_stats(self, response: Dict, processing_time: float, cached: bool):
        """Actualiza estadísticas del sistema."""
        # Actualizar tiempo promedio de procesamiento
        total_time = self.stats['avg_processing_time'] * (self.stats['total_queries'] - 1)
        self.stats['avg_processing_time'] = (total_time + processing_time) / self.stats['total_queries']
        
        # Actualizar tokens ahorrados
        if 'optimization_metrics' in response:
            tokens_saved = response['optimization_metrics'].get('tokens_saved', 0)
            self.stats['total_tokens_saved'] += tokens_saved
        
        # Loggear estadísticas cada 100 consultas
        if self.stats['total_queries'] % 100 == 0:
            self._log_system_stats()
    
    def _log_system_stats(self):
        """Loggea estadísticas del sistema."""
        cache_hit_rate = (self.stats['cache_hits'] / self.stats['total_queries']) * 100
        
        logger.info(f"=== Sistema de Optimización - Estadísticas ===")
        logger.info(f"Total consultas: {self.stats['total_queries']}")
        logger.info(f"Cache hits: {self.stats['cache_hits']} ({cache_hit_rate:.1f}%)")
        logger.info(f"Cache misses: {self.stats['cache_misses']}")
        logger.info(f"Tiempo promedio: {self.stats['avg_processing_time']:.2f}s")
        logger.info(f"Tokens ahorrados: {self.stats['total_tokens_saved']}")
        logger.info(f"==============================================")
    
    def _estimate_tokens(self, text: str) -> int:
        """Estima número de tokens en un texto (aproximación simple)."""
        # Aproximación: 1 token ≈ 4 caracteres en inglés, ~2.5 en español
        if not text:
            return 0
        
        # Contar palabras y ajustar para español
        words = len(text.split())
        chars = len(text)
        
        # Estimación conservadora para español
        tokens_from_words = words * 1.3  # Español tiene palabras más largas
        tokens_from_chars = chars / 2.5  # ~2.5 chars por token en español
        
        return int(max(tokens_from_words, tokens_from_chars))
    
    def get_system_stats(self) -> Dict:
        """Retorna estadísticas del sistema."""
        stats = self.stats.copy()
        
        # Calcular métricas derivadas
        if stats['total_queries'] > 0:
            stats['cache_hit_rate'] = (stats['cache_hits'] / stats['total_queries']) * 100
            stats['cache_miss_rate'] = (stats['cache_misses'] / stats['total_queries']) * 100
        else:
            stats['cache_hit_rate'] = 0
            stats['cache_miss_rate'] = 0
        
        # Agentes cargados
        stats['loaded_agents'] = list(self._agents.keys())
        
        # Estado del caché
        stats['cache_status'] = self.cache.get_status()
        
        return stats
    
    def clear_cache(self, query_type: Optional[str] = None):
        """Limpia el caché, opcionalmente por tipo de consulta."""
        self.cache.clear(query_type)
        logger.info(f"Caché limpiado{' para ' + query_type if query_type else ''}")
    
    def warmup_cache(self):
        """Precalienta el caché con datos comunes."""
        logger.info("Precalentando caché...")
        
        # TODO: Implementar precalentamiento basado en patrones de uso
        # Por ahora solo log
        logger.info("Precalentamiento completado (placeholder)")
    
    def health_check(self) -> Dict:
        """Realiza check de salud del sistema."""
        health = {
            'status': 'healthy',
            'components': {},
            'issues': []
        }
        
        # Check caché
        cache_health = self.cache.health_check()
        health['components']['cache'] = cache_health
        if cache_health['status'] != 'healthy':
            health['issues'].append(f"Cache: {cache_health.get('message', 'Unknown error')}")
        
        # Check agentes
        agent_count = len(self._agents)
        health['components']['agents'] = {
            'status': 'healthy' if agent_count > 0 else 'warning',
            'loaded_count': agent_count,
            'loaded_agents': list(self._agents.keys())
        }
        if agent_count == 0:
            health['issues'].append("No hay agentes cargados")
        
        # Check métricas
        health['components']['metrics'] = {
            'status': 'healthy',
            'total_queries': self.stats['total_queries'],
            'cache_hit_rate': self.stats.get('cache_hit_rate', 0)
        }
        
        # Determinar estado general
        if len(health['issues']) > 2:
            health['status'] = 'unhealthy'
        elif len(health['issues']) > 0:
            health['status'] = 'degraded'
        
        return health