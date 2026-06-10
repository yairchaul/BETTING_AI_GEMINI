# -*- coding: utf-8 -*-
"""
MOTOR UFC PRO - REDUNDANTE
Este archivo ha sido unificado en 'motors/ufc_analyzer.py'.
Se mantiene como wrapper para no romper dependencias legacy.
"""
from motors.ufc_analyzer import UFCAnalyzer

class MotorUFCPro(UFCAnalyzer):
    def __init__(self):
        super().__init__()