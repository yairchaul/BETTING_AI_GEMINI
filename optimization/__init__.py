"""
Sistema de Optimización de Tokens para BETTING_AI
Módulo principal para reducir consumo de tokens en consultas recurrentes
"""

__version__ = "1.0.0"
__author__ = "BETTING_AI Team"

from .manager import OptimizationManager
from .cache import CacheCoordinator
from .templates import TemplateRenderer
from .metrics import TokenMonitor

# Instancia global del sistema de optimización
optimization_manager = OptimizationManager()

__all__ = [
    'OptimizationManager',
    'CacheCoordinator', 
    'TemplateRenderer',
    'TokenMonitor',
    'optimization_manager'
]