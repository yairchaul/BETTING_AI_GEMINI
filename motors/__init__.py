# -*- coding: utf-8 -*-
"""
Paquete de Motores de Análisis para BETTING_AI V24.
Expone funciones y clases principales de los motores de análisis.
"""

# ==================== MOTORES GENERALES ====================
try:
    from .motor_momentum import MotorMomentumProfesional
except ImportError:
    MotorMomentumProfesional = None

try:
    from .motor_decision_inteligente import MotorDecisionInteligente
except ImportError:
    MotorDecisionInteligente = None

try:
    from .motor_memoria import MotorMemoria
except ImportError:
    MotorMemoria = None

# ==================== MOTORES NBA ====================
try:
    # Importar desde el archivo correcto
    from .analizar_nba_pro_v17 import analizar_nba_pro_v17
except ImportError:
    try:
        from .motor_nba_pro_v17 import analizar_nba_pro_v17
    except ImportError:
        analizar_nba_pro_v17 = None

try:
    from .motor_nba_over_under import MotorNBAOverUnder
except ImportError:
    MotorNBAOverUnder = None

# ==================== MOTORES MLB ====================
try:
    from .motor_mlb_pro import analizar_mlb_pro_v20
except ImportError:
    try:
        from .motor_mlb_completo import analizar_mlb_pro_v20
    except ImportError:
        try:
            # Último fallback: importar directamente
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from motor_mlb import analizar_mlb_pro_v20
        except ImportError:
            analizar_mlb_pro_v20 = None

try:
    from .motor_over_under import MotorOverUnder
except ImportError:
    MotorOverUnder = None

try:
    from .motor_lanzadores import obtener_analisis_lanzadores, motor_lanzadores
except ImportError:
    obtener_analisis_lanzadores, motor_lanzadores = None, None

try:
    from .predictor_hr import PredictorHR
except ImportError:
    try:
        from .hr_analyzer_v24_1 import HRAnalyzerUnificado as PredictorHR
    except ImportError:
        PredictorHR = None

try:
    from .predictor_ponches import PredictorPonches
except ImportError:
    PredictorPonches = None

try:
    from .mlb_stats_api import obtener_whip_cacheado, obtener_k9_cacheado
except ImportError:
    obtener_whip_cacheado, obtener_k9_cacheado = None, None

# ==================== MOTORES UFC ====================
try:
    from .ufc_analyzer import UFCAnalyzer
except ImportError:
    UFCAnalyzer = None

# ==================== MOTORES FÚTBOL ====================
try:
    from .futbol_analyzer_jerarquico import analizar_futbol_jerarquico
except ImportError:
    analizar_futbol_jerarquico = None

# ==================== MOTOR PARLAYS ====================
try:
    from .parlay_engine import ParlayEngine
except ImportError:
    ParlayEngine = None

# ==================== EXPORTACIONES ====================
__all__ = [
    # Generales
    'MotorMomentumProfesional',
    'MotorDecisionInteligente',
    'MotorMemoria',
    # NBA
    'analizar_nba_pro_v17',
    'MotorNBAOverUnder',
    # MLB
    'analizar_mlb_pro_v20',
    'MotorOverUnder',
    'obtener_analisis_lanzadores',
    'motor_lanzadores',
    'PredictorHR',
    'PredictorPonches',
    'obtener_whip_cacheado',
    'obtener_k9_cacheado',
    # UFC
    'UFCAnalyzer',
    # Fútbol
    'analizar_futbol_jerarquico',
    # Parlays
    'ParlayEngine',
]
