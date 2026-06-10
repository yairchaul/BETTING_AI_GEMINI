"""
General Agent - Agente para consultas no especializadas
"""

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GeneralAgent:
    """
    Agente general para consultas que no son específicas de un deporte.
    
    Funciona como fallback y para consultas generales del sistema.
    """
    
    def __init__(self):
        """Inicializa agente general."""
        self.context = {
            'initialized_at': time.time(),
            'recent_queries': [],
            'common_responses': self._load_common_responses()
        }
        
        logger.info("GeneralAgent inicializado")
    
    def process(self, query: str, user_context: Optional[Dict] = None) -> Dict:
        """
        Procesa una consulta general.
        
        Args:
            query: Consulta del usuario
            user_context: Contexto adicional
            
        Returns:
            Respuesta procesada
        """
        if user_context is None:
            user_context = {}
        
        # Registrar consulta
        self._log_query(query, user_context)
        
        # Clasificar consulta
        query_type = self._classify_general_query(query)
        
        # Procesar según tipo
        if query_type == 'help':
            return self._process_help_query()
        elif query_type == 'system_status':
            return self._process_system_status()
        elif query_type == 'optimization_info':
            return self._process_optimization_info()
        elif query_type == 'cache_info':
            return self._process_cache_info()
        elif query_type == 'common_query':
            return self._process_common_query(query)
        else:
            return self._process_unknown_query(query)
    
    def _classify_general_query(self, query: str) -> str:
        """Clasifica consultas generales."""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ['ayuda', 'help', 'qué puedes hacer', 'comandos']):
            return 'help'
        elif any(term in query_lower for term in ['estado', 'status', 'salud', 'health']):
            return 'system_status'
        elif any(term in query_lower for term in ['optimización', 'optimization', 'tokens', 'eficiencia']):
            return 'optimization_info'
        elif any(term in query_lower for term in ['caché', 'cache', 'almacenamiento']):
            return 'cache_info'
        elif any(resp['pattern'] in query_lower for resp in self.context['common_responses']):
            return 'common_query'
        else:
            return 'unknown'
    
    def _process_help_query(self) -> Dict:
        """Procesa consulta de ayuda."""
        help_text = """
🎯 **SISTEMA DE OPTIMIZACIÓN DE TOKENS**

**Consultas frecuentes optimizadas:**
- `picks mlb hoy` - Picks de MLB del día (caché 5min)
- `análisis [equipo1] vs [equipo2]` - Análisis específico
- `home runs hoy` - Predicciones HR
- `mejores apuestas fútbol` - Modelo jerárquico
- `análisis ufc` - Peleas UFC

**Comandos del sistema:**
- `estado sistema` - Estado y métricas
- `optimización info` - Estadísticas de tokens
- `limpiar caché` - Limpia caché
- `agentes cargados` - Lista agentes activos

**Deportes soportados:** MLB, UFC, Fútbol, NBA
**Caché:** Inteligente con TTLs específicos
**Plantillas:** Respuestas optimizadas
        """
        
        return {
            'response_type': 'help',
            'text': help_text.strip(),
            'sections': ['frequent_queries', 'system_commands', 'sports_supported'],
            'source': 'general_agent'
        }
    
    def _process_system_status(self) -> Dict:
        """Procesa consulta de estado del sistema."""
        # Esta información vendría del OptimizationManager
        # Por ahora, información básica
        
        status = {
            'system': 'BETTING_AI Optimization System',
            'version': '1.0.0',
            'status': 'operational',
            'components': {
                'optimization_manager': 'active',
                'cache_system': 'active',
                'template_renderer': 'active',
                'token_monitor': 'active'
            },
            'agents_loaded': ['MLB', 'General'],  # Placeholder
            'uptime_seconds': int(time.time() - self.context['initialized_at']),
            'timestamp': time.time()
        }
        
        return {
            'response_type': 'system_status',
            'status': status,
            'source': 'general_agent'
        }
    
    def _process_optimization_info(self) -> Dict:
        """Procesa consulta de información de optimización."""
        # Placeholder - en implementación real, obtendría del TokenMonitor
        
        info = {
            'optimization_techniques': [
                'Caché inteligente por tipo de consulta',
                'Plantillas optimizadas por deporte',
                'Agentes especializados',
                'Compresión de respuestas',
                'Monitoreo de tokens'
            ],
            'targets': {
                'max_tokens_per_query': 800,
                'min_cache_hit_rate': 60,
                'target_efficiency': 0.7
            },
            'current_status': 'collecting_metrics',  # Placeholder
            'recommendations': [
                'Usar consultas específicas para mejor caché',
                'Revisar picks en horarios de actualización',
                'Usar comandos cortos para respuestas rápidas'
            ]
        }
        
        return {
            'response_type': 'optimization_info',
            'info': info,
            'source': 'general_agent'
        }
    
    def _process_cache_info(self) -> Dict:
        """Procesa consulta de información de caché."""
        # Placeholder
        
        cache_info = {
            'types': {
                'mlb_picks': {'ttl': '5 minutos', 'strategy': 'time_based'},
                'ufc_analysis': {'ttl': '10 minutos', 'strategy': 'event_based'},
                'futbol_predictions': {'ttl': '15 minutos', 'strategy': 'accuracy_based'}
            },
            'management': {
                'cleanup': 'automatic (LRU)',
                'persistence': 'enabled',
                'max_entries_per_type': 100
            },
            'commands': [
                'limpiar caché mlb',
                'limpiar caché ufc',
                'limpiar caché futbol',
                'limpiar todo el caché'
            ]
        }
        
        return {
            'response_type': 'cache_info',
            'cache': cache_info,
            'source': 'general_agent'
        }
    
    def _process_common_query(self, query: str) -> Dict:
        """Procesa consulta común con respuesta predefinida."""
        query_lower = query.lower()
        
        for common in self.context['common_responses']:
            if common['pattern'] in query_lower:
                return {
                    'response_type': 'common_response',
                    'text': common['response'],
                    'pattern': common['pattern'],
                    'category': common.get('category', 'general'),
                    'source': 'predefined'
                }
        
        # No se encontró patrón exacto
        return self._process_unknown_query(query)
    
    def _process_unknown_query(self, query: str) -> Dict:
        """Procesa consulta desconocida."""
        return {
            'response_type': 'unknown_query',
            'text': f"Consulta no reconocida: '{query}'\n\nUsa 'ayuda' para ver comandos disponibles.",
            'query': query,
            'suggestion': 'Intenta usar consultas más específicas o usa el comando de ayuda.',
            'source': 'general_agent'
        }
    
    def _log_query(self, query: str, context: Dict):
        """Registra consulta para análisis."""
        log_entry = {
            'query': query[:100],  # Limitar longitud
            'timestamp': time.time(),
            'context_keys': list(context.keys()) if context else [],
            'agent': 'general'
        }
        
        self.context['recent_queries'].append(log_entry)
        
        # Mantener solo las últimas 100 consultas
        if len(self.context['recent_queries']) > 100:
            self.context['recent_queries'] = self.context['recent_queries'][-100:]
    
    def _load_common_responses(self) -> list:
        """Carga respuestas comunes predefinidas."""
        return [
            {
                'pattern': 'hola',
                'response': '¡Hola! Soy el sistema de optimización de BETTING_AI. ¿En qué puedo ayudarte?',
                'category': 'greeting'
            },
            {
                'pattern': 'gracias',
                'response': '¡De nada! ¿Algo más en lo que pueda ayudarte?',
                'category': 'greeting'
            },
            {
                'pattern': 'qué deportes',
                'response': 'Soporto MLB (béisbol), UFC (MMA), Fútbol y NBA (baloncesto). Cada uno tiene agentes especializados.',
                'category': 'info'
            },
            {
                'pattern': 'cómo funciona',
                'response': 'Uso caché inteligente, plantillas optimizadas y agentes especializados para reducir tokens y acelerar respuestas.',
                'category': 'info'
            },
            {
                'pattern': 'mejores picks',
                'response': 'Para picks específicos, consulta por deporte: "picks mlb hoy", "mejores apuestas fútbol", etc.',
                'category': 'guidance'
            },
            {
                'pattern': 'actualizar',
                'response': 'Los datos se actualizan automáticamente. MLB cada 5min, UFC cada 10min, Fútbol cada 15min.',
                'category': 'info'
            }
        ]
    
    def get_agent_info(self) -> Dict:
        """Obtiene información del agente."""
        return {
            'name': 'GeneralAgent',
            'purpose': 'Procesar consultas generales y no especializadas',
            'initialized': self.context['initialized_at'],
            'recent_queries_count': len(self.context['recent_queries']),
            'common_responses_count': len(self.context['common_responses']),
            'categories_covered': list(set(r.get('category', 'general') for r in self.context['common_responses']))
        }
    
    def get_query_stats(self, time_range: str = '1h') -> Dict:
        """
        Obtiene estadísticas de consultas.
        
        Args:
            time_range: '1h', '24h', '7d'
        """
        # Calcular cutoff
        cutoff = time.time() - self._time_range_to_seconds(time_range)
        
        # Filtrar consultas recientes
        recent = [q for q in self.context['recent_queries'] if q['timestamp'] >= cutoff]
        
        # Analizar
        query_types = {}
        for query in recent:
            qtype = self._classify_general_query(query['query'])
            query_types[qtype] = query_types.get(qtype, 0) + 1
        
        return {
            'time_range': time_range,
            'total_queries': len(recent),
            'by_type': query_types,
            'unique_queries': len(set(q['query'] for q in recent)),
            'avg_query_length': sum(len(q['query']) for q in recent) / len(recent) if recent else 0
        }
    
    def _time_range_to_seconds(self, time_range: str) -> int:
        """Convierte rango de tiempo a segundos."""
        if time_range == '1h':
            return 3600
        elif time_range == '24h':
            return 86400
        elif time_range == '7d':
            return 7 * 86400
        else:
            return 3600  # Default 1h
    
    def add_common_response(self, pattern: str, response: str, category: str = 'custom') -> bool:
        """
        Agrega una respuesta común personalizada.
        
        Args:
            pattern: Patrón a buscar en consultas
            response: Respuesta a devolver
            category: Categoría de la respuesta
            
        Returns:
            True si se agregó exitosamente
        """
        try:
            self.context['common_responses'].append({
                'pattern': pattern.lower(),
                'response': response,
                'category': category,
                'added_at': time.time()
            })
            
            logger.info(f"Respuesta común agregada: {pattern}")
            return True
            
        except Exception as e:
            logger.error(f"Error agregando respuesta común: {e}")
            return False
    
    def remove_common_response(self, pattern: str) -> bool:
        """
        Remueve una respuesta común.
        
        Args:
            pattern: Patrón a remover
            
        Returns:
            True si se removió exitosamente
        """
        initial_count = len(self.context['common_responses'])
        
        self.context['common_responses'] = [
            r for r in self.context['common_responses']
            if r['pattern'] != pattern.lower()
        ]
        
        removed = initial_count - len(self.context['common_responses'])
        
        if removed > 0:
            logger.info(f"Respuesta común removida: {pattern}")
            return True
        else:
            logger.warning(f"No se encontró respuesta común con patrón: {pattern}")
            return False