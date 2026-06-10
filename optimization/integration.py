"""
Integration Module - Conecta el sistema de optimización con BETTING_AI existente
"""

import logging
from typing import Dict, Optional, Any
import streamlit as st

from .manager import optimization_manager

logger = logging.getLogger(__name__)


def get_mlb_analysis_optimized(game_pk: str = None, game_data: Dict = None) -> Dict:
    """
    Obtiene análisis de MLB optimizado usando el sistema de optimización.
    
    Args:
        game_pk: ID del juego (opcional)
        game_data: Datos del juego (opcional)
        
    Returns:
        Análisis optimizado
    """
    try:
        # Preparar contexto
        context = {}
        if game_pk:
            context['game_pk'] = game_pk
        
        if game_data:
            context['game_data'] = game_data
            context['home'] = game_data.get('local')
            context['away'] = game_data.get('visitante')
        
        # Construir query
        if 'home' in context and 'away' in context:
            query = f"mlb analysis {context['away']} vs {context['home']}"
        elif game_pk:
            query = f"mlb analysis game {game_pk}"
        else:
            query = "mlb analysis"
        
        # Procesar con optimizador
        response = optimization_manager.process_query(query, context)
        
        # Extraer respuesta principal
        if 'response' in response:
            return response['response']
        else:
            return response
            
    except Exception as e:
        logger.error(f"Error en análisis MLB optimizado: {e}")
        
        # Fallback al motor original
        return _fallback_to_original_mlb(game_pk, game_data)


def get_ufc_analysis_optimized(event_id: str = None, fight_data: Dict = None) -> Dict:
    """
    Obtiene análisis de UFC optimizado.
    
    Args:
        event_id: ID del evento (opcional)
        fight_data: Datos de la pelea (opcional)
        
    Returns:
        Análisis optimizado
    """
    try:
        # Preparar contexto
        context = {}
        if event_id:
            context['event_id'] = event_id
        
        if fight_data:
            context['fight_data'] = fight_data
            context['fighter1'] = fight_data.get('peleador1', {}).get('nombre')
            context['fighter2'] = fight_data.get('peleador2', {}).get('nombre')
        
        # Construir query
        if 'fighter1' in context and 'fighter2' in context:
            query = f"ufc analysis {context['fighter1']} vs {context['fighter2']}"
        elif event_id:
            query = f"ufc analysis event {event_id}"
        else:
            query = "ufc analysis"
        
        # Procesar con optimizador
        response = optimization_manager.process_query(query, context)
        
        # Extraer respuesta principal
        if 'response' in response:
            return response['response']
        else:
            return response
            
    except Exception as e:
        logger.error(f"Error en análisis UFC optimizado: {e}")
        
        # Fallback al motor original
        return _fallback_to_original_ufc(event_id, fight_data)


def get_futbol_predictions_optimized(league: str = None, match_data: Dict = None) -> Dict:
    """
    Obtiene predicciones de fútbol optimizadas.
    
    Args:
        league: Nombre de la liga (opcional)
        match_data: Datos del partido (opcional)
        
    Returns:
        Predicciones optimizadas
    """
    try:
        # Preparar contexto
        context = {}
        if league:
            context['league'] = league
        
        if match_data:
            context['match_data'] = match_data
            context['home'] = match_data.get('local')
            context['away'] = match_data.get('visitante')
        
        # Construir query
        if league:
            query = f"futbol predictions {league}"
        elif 'home' in context and 'away' in context:
            query = f"futbol analysis {context['away']} vs {context['home']}"
        else:
            query = "futbol predictions"
        
        # Procesar con optimizador
        response = optimization_manager.process_query(query, context)
        
        # Extraer respuesta principal
        if 'response' in response:
            return response['response']
        else:
            return response
            
    except Exception as e:
        logger.error(f"Error en predicciones fútbol optimizadas: {e}")
        
        # Fallback al motor original
        return _fallback_to_original_futbol(league, match_data)


def get_todays_picks_optimized(sport: str = None) -> Dict:
    """
    Obtiene picks del día optimizados.
    
    Args:
        sport: Deporte específico ('mlb', 'ufc', 'futbol', 'nba')
        
    Returns:
        Picks optimizados
    """
    try:
        # Preparar contexto
        context = {}
        
        # Construir query
        if sport:
            query = f"{sport} picks today"
        else:
            query = "todays picks all sports"
        
        # Procesar con optimizador
        response = optimization_manager.process_query(query, context)
        
        # Extraer respuesta principal
        if 'response' in response:
            return response['response']
        else:
            return response
            
    except Exception as e:
        logger.error(f"Error en picks del día optimizados: {e}")
        
        # Fallback
        return {
            'response_type': 'todays_picks',
            'sport': sport or 'all',
            'picks': [],
            'error': 'Sistema de optimización no disponible',
            'source': 'fallback'
        }


def get_system_metrics() -> Dict:
    """
    Obtiene métricas del sistema de optimización.
    
    Returns:
        Métricas del sistema
    """
    try:
        # Estadísticas del manager
        stats = optimization_manager.get_system_stats()
        
        # Salud del sistema
        health = optimization_manager.health_check()
        
        # Métricas de token monitor
        # (Nota: En implementación completa, esto vendría del TokenMonitor)
        
        return {
            'optimization_system': {
                'status': 'active',
                'stats': stats,
                'health': health
            },
            'timestamp': 'TODO: agregar timestamp'
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas del sistema: {e}")
        
        return {
            'optimization_system': {
                'status': 'error',
                'error': str(e)
            }
        }


def clear_optimization_cache(cache_type: str = None) -> Dict:
    """
    Limpia el caché del sistema de optimización.
    
    Args:
        cache_type: Tipo específico a limpiar (opcional)
        
    Returns:
        Resultado de la operación
    """
    try:
        optimization_manager.clear_cache(cache_type)
        
        return {
            'success': True,
            'cache_type': cache_type or 'all',
            'message': f"Caché {'de ' + cache_type if cache_type else ''}limpiado exitosamente"
        }
        
    except Exception as e:
        logger.error(f"Error limpiando caché: {e}")
        
        return {
            'success': False,
            'cache_type': cache_type,
            'error': str(e)
        }


def warmup_optimization_system() -> Dict:
    """
    Precalienta el sistema de optimización.
    
    Returns:
        Resultado del precalentamiento
    """
    try:
        optimization_manager.warmup_cache()
        
        return {
            'success': True,
            'message': 'Sistema de optimización precalentado',
            'components_warmed': ['cache', 'agents']
        }
        
    except Exception as e:
        logger.error(f"Error precalentando sistema: {e}")
        
        return {
            'success': False,
            'error': str(e)
        }


# Funciones de fallback a motores originales
def _fallback_to_original_mlb(game_pk: str = None, game_data: Dict = None) -> Dict:
    """Fallback al motor MLB original."""
    try:
        from motors.motor_mlb_pro import analizar_mlb_pro_v20
        
        if game_data:
            analysis = analizar_mlb_pro_v20(game_data, game_pk=game_pk)
        else:
            # Datos de ejemplo para fallback
            analysis = {
                'response_type': 'mlb_analysis',
                'source': 'original_fallback',
                'message': 'Usando motor original (fallback)',
                'data': {}
            }
        
        return analysis
        
    except ImportError as e:
        logger.error(f"Error importando motor MLB original: {e}")
        
        return {
            'response_type': 'mlb_analysis',
            'source': 'error',
            'error': 'Motor MLB no disponible',
            'data': {}
        }


def _fallback_to_original_ufc(event_id: str = None, fight_data: Dict = None) -> Dict:
    """Fallback al motor UFC original."""
    try:
        # Importar motor UFC (ajustar según implementación real)
        # from motors.ufc_analyzer import analizar_ufc
        
        # Placeholder
        return {
            'response_type': 'ufc_analysis',
            'source': 'original_fallback',
            'message': 'Motor UFC original (placeholder)',
            'data': {}
        }
        
    except ImportError as e:
        logger.error(f"Error importando motor UFC original: {e}")
        
        return {
            'response_type': 'ufc_analysis',
            'source': 'error',
            'error': 'Motor UFC no disponible',
            'data': {}
        }


def _fallback_to_original_futbol(league: str = None, match_data: Dict = None) -> Dict:
    """Fallback al motor fútbol original."""
    try:
        # Importar motor fútbol (ajustar según implementación real)
        # from motors.futbol_analyzer_jerarquico import analizar_futbol
        
        # Placeholder
        return {
            'response_type': 'futbol_predictions',
            'source': 'original_fallback',
            'message': 'Motor fútbol original (placeholder)',
            'data': {}
        }
        
    except ImportError as e:
        logger.error(f"Error importando motor fútbol original: {e}")
        
        return {
            'response_type': 'futbol_predictions',
            'source': 'error',
            'error': 'Motor fútbol no disponible',
            'data': {}
        }


# Funciones de integración con Streamlit
def setup_streamlit_integration():
    """Configura integración con Streamlit."""
    try:
        # Agregar estado de optimización a session_state si no existe
        if 'optimization' not in st.session_state:
            st.session_state.optimization = {
                'enabled': True,
                'cache_hits': 0,
                'cache_misses': 0,
                'last_reset': 'never'
            }
        
        # Agregar callbacks para botones
        # (Esto se integraría con la UI existente)
        
        logger.info("Integración Streamlit configurada")
        
    except Exception as e:
        logger.error(f"Error configurando integración Streamlit: {e}")


def get_optimization_status_for_ui() -> Dict:
    """Obtiene estado de optimización para mostrar en UI."""
    try:
        stats = optimization_manager.get_system_stats()
        
        # Calcular métricas para UI
        total_queries = stats.get('total_queries', 0)
        cache_hits = stats.get('cache_hits', 0)
        cache_misses = stats.get('cache_misses', 0)
        
        if total_queries > 0:
            cache_hit_rate = (cache_hits / total_queries) * 100
        else:
            cache_hit_rate = 0
        
        return {
            'enabled': True,
            'total_queries': total_queries,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'cache_hit_rate': round(cache_hit_rate, 1),
            'avg_processing_time': round(stats.get('avg_processing_time', 0), 3),
            'total_tokens_saved': stats.get('total_tokens_saved', 0),
            'agents_loaded': stats.get('loaded_agents', []),
            'cache_status': stats.get('cache_status', {})
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estado para UI: {e}")
        
        return {
            'enabled': False,
            'error': str(e)
        }


# Funciones para debugging
def debug_optimization_query(query: str, context: Dict = None) -> Dict:
    """
    Depura una consulta de optimización (para testing).
    
    Args:
        query: Consulta a depurar
        context: Contexto adicional
        
    Returns:
        Información detallada de depuración
    """
    if context is None:
        context = {}
    
    try:
        # Procesar consulta con logging detallado
        import io
        import sys
        
        # Capturar logs
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        
        # Agregar handler temporal
        root_logger = logging.getLogger()
        original_level = root_logger.level
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)
        
        try:
            # Procesar consulta
            response = optimization_manager.process_query(query, context)
            
            # Obtener logs
            log_contents = log_capture.getvalue()
            
            # Información de depuración
            debug_info = {
                'query': query,
                'context': context,
                'response': response,
                'logs': log_contents,
                'stats': optimization_manager.get_system_stats(),
                'cache_key': response.get('cache_key'),
                'from_cache': response.get('from_cache', False)
            }
            
            return debug_info
            
        finally:
            # Restaurar configuración de logging
            root_logger.removeHandler(handler)
            root_logger.setLevel(original_level)
            
    except Exception as e:
        return {
            'error': str(e),
            'query': query,
            'context': context
        }