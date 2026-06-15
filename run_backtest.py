# -*- coding: utf-8 -*-
"""
Punto de entrada para ejecutar el backtesting universal del sistema.

Este script invoca el motor de backtesting que:
1. Descarga resultados reales de los últimos días.
2. Cruza esos resultados con los picks 'PENDIENTES' en la base de datos.
3. Actualiza los picks a 'GANADA' o 'PERDIDA'.
4. Calcula y muestra métricas de rendimiento (Win Rate, ROI, Profit).
5. Auto-ajusta los pesos de los motores de análisis para mejorar la precisión futura.
"""

import sys
import os
import logging

# --- Configuración de logging y path ---
# Asegurar que el directorio raíz esté en el path para los imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("="*60)
    logger.info("🚀 INICIANDO BACKTESTER UNIVERSAL")
    logger.info("="*60)

    try:
        from utils.backtester_universal import BacktesterUniversal, inicializar_pesos
        
        # Asegura que el archivo de pesos exista antes de correr el backtest
        inicializar_pesos()
        
        # Crear una instancia y ejecutar el backtest para los últimos 15 días
        backtester = BacktesterUniversal()
        reporte = backtester.ejecutar_backtest_completo(dias=15)
        
        if not reporte:
            logger.error("❌ El backtesting finalizó pero no generó un reporte.")

    except ImportError as e:
        logger.critical(f"❌ Error de importación: No se pudo encontrar el módulo 'backtester_universal'. {e}")
        logger.critical("   Asegúrate de que el archivo 'utils/backtester_universal.py' existe y es correcto.")
    except Exception as e:
        logger.critical(f"❌ Ocurrió un error inesperado durante el backtesting: {e}", exc_info=True)

    logger.info("="*60)
    logger.info("🎉 Proceso de backtesting finalizado.")
    logger.info("="*60)

if __name__ == "__main__":
    main()