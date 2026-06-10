"""
Configuración del Sistema de Optimización de Tokens
"""

import os
from datetime import timedelta

# Configuración de Caché
CACHE_CONFIG = {
    'mlb_picks': {
        'ttl': 300,  # 5 minutos
        'strategy': 'time_based',
        'invalidation_triggers': ['lineup_change', 'pitcher_change', 'weather_change'],
        'max_entries': 100
    },
    'mlb_analysis': {
        'ttl': 600,  # 10 minutos
        'strategy': 'game_based',
        'invalidation_triggers': ['odds_change', 'lineup_release'],
        'max_entries': 50
    },
    'ufc_fight': {
        'ttl': 600,  # 10 minutos
        'strategy': 'event_based',
        'invalidation_triggers': ['odds_change', 'weight_in', 'injury'],
        'max_entries': 30
    },
    'ufc_event': {
        'ttl': 1800,  # 30 minutos
        'strategy': 'time_based',
        'invalidation_triggers': ['card_change'],
        'max_entries': 10
    },
    'futbol_predictions': {
        'ttl': 900,  # 15 minutos
        'strategy': 'accuracy_based',
        'invalidation_triggers': ['lineup_change', 'weather_change', 'odds_change'],
        'max_entries': 50
    },
    'futbol_hierarchical': {
        'ttl': 1200,  # 20 minutos
        'strategy': 'league_based',
        'invalidation_triggers': ['lineups_released', 'stadium_factor_change'],
        'max_entries': 20
    },
    'nba_picks': {
        'ttl': 300,  # 5 minutos
        'strategy': 'time_based',
        'invalidation_triggers': ['injury_report', 'lineup_change'],
        'max_entries': 50
    }
}

# Configuración de Plantillas
TEMPLATE_CONFIG = {
    'mlb_pick': {
        'format': 'compact',
        'max_tokens': 120,
        'fields': ['pick', 'confidence', 'stake', 'reason_short', 'power_factor'],
        'emoji_mapping': {
            'high_confidence': '🔥',      # >70%
            'medium_confidence': '✅',    # 50-70%
            'low_confidence': '📊',       # 30-50%
            'avoid': '❌'                 # <30%
        }
    },
    'ufc_fight': {
        'format': 'comparison',
        'max_tokens': 180,
        'fields': ['fighter1', 'fighter2', 'heuristic_pick', 'ai_pick', 'edge_rating'],
        'show_stats': ['record', 'age', 'reach', 'ko_rate']
    },
    'futbol_hierarchical': {
        'format': 'hierarchical',
        'max_tokens': 220,
        'hierarchy': ['over_1.5_1t', 'over_3.5', 'btts', 'over_2.5', 'moneyline', 'handicap'],
        'max_picks': 3
    },
    'general_summary': {
        'format': 'summary',
        'max_tokens': 150,
        'fields': ['best_pick', 'confidence', 'expected_value', 'stake'],
        'include_emoji': True
    }
}

# Configuración de Agentes
AGENT_CONFIG = {
    'mlb': {
        'context_ttl': 3600,  # 1 hora
        'max_context_size': 50000,  # ~50KB
        'precomputation_schedule': 'hourly',
        'cached_datasets': ['hr_stats', 'pitcher_stats', 'team_stats']
    },
    'ufc': {
        'context_ttl': 7200,  # 2 horas
        'max_context_size': 30000,  # ~30KB
        'precomputation_schedule': 'event_based',
        'cached_datasets': ['fighter_stats', 'event_stats']
    },
    'futbol': {
        'context_ttl': 5400,  # 1.5 horas
        'max_context_size': 80000,  # ~80KB
        'precomputation_schedule': 'every_15_min',
        'cached_datasets': ['league_stats', 'team_stats', 'player_stats']
    },
    'nba': {
        'context_ttl': 3600,  # 1 hora
        'max_context_size': 40000,  # ~40KB
        'precomputation_schedule': 'hourly',
        'cached_datasets': ['player_stats', 'team_stats', 'injury_reports']
    }
}

# Configuración de Métricas
METRICS_CONFIG = {
    'target_efficiency': 0.7,  # 70% eficiencia (info/tokens)
    'alert_threshold': 0.5,    # Alertar si eficiencia < 50%
    'max_tokens_per_query': 800,
    'min_cache_hit_rate': 0.6,  # 60% mínimo de cache hits
    'sampling_rate': 0.1,      # Muestrear 10% de consultas para análisis detallado
    'retention_days': 30       # Mantener métricas por 30 días
}

# Configuración de Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, 'data', 'optimization_cache')
METRICS_DIR = os.path.join(BASE_DIR, 'data', 'optimization_metrics')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'optimization', 'templates')

# Crear directorios si no existen
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(METRICS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Configuración de Precomputación
PRECOMPUTATION_SCHEDULE = {
    'hourly': [
        'mlb_todays_picks',
        'nba_todays_picks',
        'general_stats_update'
    ],
    'every_15_min': [
        'futbol_predictions',
        'odds_update_check'
    ],
    'event_based': [
        'ufc_event_analysis',
        'mlb_lineup_changes'
    ],
    'daily': [
        'historical_stats',
        'trend_analysis',
        'cache_cleanup'
    ]
}

# Umbrales de Optimización
OPTIMIZATION_THRESHOLDS = {
    'min_confidence_for_cache': 0.4,      # 40% confianza mínima para cachear
    'max_response_time_cache': 2.0,       # 2 segundos máximo para respuestas cacheadas
    'min_information_density': 0.3,       # 30% densidad mínima de información
    'compression_target': 0.6,            # Comprimir 40% del texto original
    'template_efficiency_gain': 0.4       # 40% mejora con plantillas vs texto libre
}

# Configuración de Logging
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': os.path.join(BASE_DIR, 'logs', 'optimization.log'),
    'max_size_mb': 10,
    'backup_count': 5
}

# Clasificación de Consultas
QUERY_CLASSIFICATION = {
    'mlb': [
        r'(picks|apuestas|predicciones).*(mlb|baseball|beisbol)',
        r'(mlb).*(hoy|today|ayer|yesterday)',
        r'(home run|hr).*(hoy|today)',
        r'(pitcher|lanzador).*(stats|estadisticas)',
        r'(análisis|analysis).*(vs|contra)'
    ],
    'ufc': [
        r'(ufc|mma).*(análisis|analysis|predicciones)',
        r'(pelea|fight).*(ufc|mma)',
        r'(evento|event).*(ufc)',
        r'(ko|knockout).*(predicción|prediction)'
    ],
    'futbol': [
        r'(fútbol|futbol|soccer).*(predicciones|apuestas)',
        r'(liga|league).*(premier|la liga|serie a|bundesliga)',
        r'(over|under|btts).*(hoy|today)',
        r'(handicap|hándicap).*(fútbol|futbol)'
    ],
    'nba': [
        r'(nba|basketball|baloncesto).*(picks|apuestas)',
        r'(player|jugador).*(props|propuestas)',
        r'(over|under).*(points|puntos)'
    ]
}

# Mapeo de consultas a plantillas
QUERY_TO_TEMPLATE = {
    'mlb_picks': 'mlb_pick',
    'mlb_analysis': 'mlb_pick',
    'ufc_fight': 'ufc_fight',
    'ufc_event': 'ufc_fight',
    'futbol_predictions': 'futbol_hierarchical',
    'futbol_hierarchical': 'futbol_hierarchical',
    'nba_picks': 'general_summary',
    'general_query': 'general_summary'
}