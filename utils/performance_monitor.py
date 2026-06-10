# -*- coding: utf-8 -*-
"""
MONITOR DE RENDIMIENTO - Registro de tiempos de ejecución
Cumple con la Regla 20 (Logging) y Regla 24 (Rutas Windows)
"""
import time
import logging
import os

# Rutas absolutas (Regla 24)
BASE_DIR = r"C:\Users\Yair\Desktop\BETTING_AI"
LOG_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configuración del logger de rendimiento
perf_logger = logging.getLogger("BETTING_AI.Performance")
if not perf_logger.handlers:
    perf_logger.setLevel(logging.INFO)
    log_path = os.path.join(LOG_DIR, "performance.log")
    handler = logging.FileHandler(log_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    handler.setFormatter(formatter)
    perf_logger.addHandler(handler)

class ExecutionTimer:
    """Context manager para medir y registrar el tiempo de ejecución"""
    def __init__(self, task_name):
        self.task_name = task_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        perf_logger.info(f"START | {self.task_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        duration = end_time - self.start_time
        status = "SUCCESS" if exc_type is None else "FAILED"
        perf_logger.info(f"END   | {self.task_name} | Status: {status} | Duration: {duration:.4f}s")
        if exc_type:
            perf_logger.error(f"ERROR | {self.task_name} | {str(exc_val)}")