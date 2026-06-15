# -*- coding: utf-8 -*-
"""
ANALIZADOR UFC HEURÍSTICO - OBSOLETO
Este archivo ha sido reemplazado por la lógica unificada en 'ufc_analyzer.py'.
"""
from .ufc_analyzer import UFCAnalyzer

class AnalizadorUFCHuristico(UFCAnalyzer):
    def __init__(self):
        super().__init__()
    # Mantiene compatibilidad con llamadas antiguas si fuera necesario
