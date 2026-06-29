# -*- coding: utf-8 -*-
"""MOTOR DE DECISIÓN INTELIGENTE - Elige la mejor apuesta"""
import json
import os
import logging
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

from clima_mlb import ClimaMLB
from backtesting_auto_aprendizaje import BacktestingAutoAprendizaje

class MotorDecisionInteligente:
    """Elige automáticamente la mejor apuesta con Auto-Aprendizaje de fallos"""

    def __init__(self):
        self.cargar_datos()
        self.clima_engine = ClimaMLB()
        self.backtesting_auto = BacktestingAutoAprendizaje()
    
    def cargar_datos(self):
        try:
            with open("data/tendencias_over_under.json", "r", encoding="utf-8") as f:
                self.tendencias_ou = json.load(f)
        except:
            self.tendencias_ou = {}
        
        try:
            with open("data/aprendizaje_semanal.json", "r", encoding="utf-8") as f:
                self.aprendizaje = json.load(f)
        except:
            self.aprendizaje = {}
        
        try:
            with open("hr_datasets_completos.json", "r", encoding="utf-8") as f:
                self.hr_data = json.load(f)
        except:
            self.hr_data = {"bateadores": {}, "pitchers": {}}

        self.log_fallos = []
        log_path = "data/aprendizaje_fallos.log"
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    self.log_fallos = f.readlines()[-100:] # Analizar últimos 100 fallos
            except: pass

        try:
            from motors.motor_momentum import MotorMomentumProfesional
            self.motor_momentum = MotorMomentumProfesional()
        except ImportError: self.motor_momentum = None
    
    def decidir_mejor_apuesta(self, partido, resultado_heurístico, candidatos_hr, clima=None):
        """
        Analiza todas las opciones y elige la mejor apuesta
        
        Retorna:
        {
            "tipo_apuesta": "MONEYLINE|HANDICAP|OVER/UNDER|HOME RUN",
            "pick": "...",
            "confianza": 0-100,
            "razon": "...",
            "stake": "1u-3u"
        }
        """
        puntuaciones = {}
        
        # 1. Evaluar MONEYLINE
        diff = resultado_heurístico.get("diff", 0)
        conf_ml = resultado_heurístico.get("confianza", 50)
        pick_ml = resultado_heurístico.get("pick", "")
        
        # --- AUTO-APRENDIZAJE: Penalización por fallos previos ---
        ocurrencias = 0   # definir SIEMPRE (se usa abajo aunque log_fallos esté vacío)
        if self.log_fallos:
            ocurrencias = sum(1 for line in self.log_fallos if pick_ml.lower() in line.lower())
            if ocurrencias > 0:
                castigo = min(30, ocurrencias * 7) # -7% por cada fallo registrado
                conf_ml -= castigo
                punt_ml_ajuste = -(castigo / 2)
            else: punt_ml_ajuste = 0
        else: punt_ml_ajuste = 0

        # Puntuación Moneyline
        if diff >= 15:
            punt_ml = 85 + punt_ml_ajuste
        elif diff >= 7 and diff < 10:
            punt_ml = 75 + punt_ml_ajuste
        elif diff >= 5:
            punt_ml = 60 + punt_ml_ajuste
        elif diff >= 2:
            punt_ml = 50 + punt_ml_ajuste
        else:
            punt_ml = 30 + punt_ml_ajuste
        
        # Penalizar equipos trampa
        equipos_trampa = self.aprendizaje.get("equipos_trampa", [])
        if pick_ml in equipos_trampa:
            punt_ml = 0
        
        puntuaciones["MONEYLINE"] = {
            "puntuacion": punt_ml,
            "pick": pick_ml,
            "confianza": conf_ml,
            "razon": (f"Diff: {diff:.1f}% | Confianza: {conf_ml}%" +
                      (" | momentum activo" if self.motor_momentum else "") +
                      (f" | Penalizado por {ocurrencias} fallos previos" if ocurrencias > 0 else "") +
                      (f" | Equipo trampa detectado" if pick_ml in equipos_trampa else "")
                     )
        }
        
        # --- 2. Evaluar HANDICAP (Dinámico según confianza) ---
        ou_line = partido.get("odds", {}).get("over_under", 8.5)
        try:
            ou_line = float(ou_line)
        except:
            ou_line = 8.5
        
        # Handicap +1.5 (cubre 76.8% de partidos)
        handicap_value = 1.5
        if conf_ml >= 70: # Si ML es casi seguro, Handicap +1.5 es muy seguro
            punt_hand = 85
            handicap_value = 1.5
        elif conf_ml >= 55: # Si ML es moderado, Handicap +2.5 es más seguro
            punt_hand = 70
            handicap_value = 2.5
        elif conf_ml >= 45: # Si ML es bajo, Handicap +3.5 para rescate
            punt_hand = 55
            handicap_value = 3.5
        else: # Si ML es muy bajo, no hay valor en Handicap
            punt_hand = 20
            handicap_value = "N/A"
        
        puntuaciones["HANDICAP"] = {
            "puntuacion": punt_hand,
            "pick": f"{pick_ml} +{handicap_value}" if handicap_value != "N/A" else "N/A",
            "confianza": min(95, conf_ml + 15), # Handicap siempre da más confianza que ML directo
            "razon": f"Handicap +{handicap_value} para proteger capital en {pick_ml}"
        }
        
        # --- 3. Evaluar OVER/UNDER (Integrando Clima y Momentum) ---
        dia_semana = datetime.now().weekday()
        factor_dia = 1.0
        
        if self.tendencias_ou.get("factores_dia"):
            dia_str = str(dia_semana)
            if dia_str in self.tendencias_ou["factores_dia"]:
                factor_dia = self.tendencias_ou["factores_dia"][dia_str].get("factor", 1.0)
        
        # Obtener proyección de MotorOverUnder (que ya integra clima)
        try:
            from motors.motor_over_under import MotorOverUnder
            mou = MotorOverUnder()
            # Necesitamos pasarle los datos de runs promedio de los equipos
            # Asumiendo que partido ya tiene 'away_avg_runs' y 'home_avg_runs'
            ou_analysis = mou.calcular_total(partido)
            proyeccion = ou_analysis["total_proyectado"]
            ou_conf = ou_analysis["confianza"]
            ou_razon = ", ".join(ou_analysis["ajustes"])
        except Exception as e:
            logger.error(f"Error en MotorOverUnder: {e}")
            proyeccion = ou_line # Fallback
            ou_conf = 50
            ou_razon = "Error al calcular O/U"

        if clima:
            viento = clima.get("wind_speed", 0)
            if viento > 12:
                proyeccion += 1.5
            elif viento > 8:
                proyeccion += 0.8
        
        # --- JERARQUÍA V24 para OVER/UNDER ---
        if proyeccion >= ou_line + 0.75 and ou_conf >= 75: # ÉLITE Over (ajustado)
            punt_ou = 90
            pick_ou = f"OVER {ou_line}"
        elif proyeccion <= ou_line - 0.75 and ou_conf >= 75: # ÉLITE Under
            punt_ou = 90
            pick_ou = f"UNDER {ou_line}"
        elif proyeccion >= ou_line + 0.25 and ou_conf >= 60: # SEGURO Over
            punt_ou = 75
            pick_ou = f"OVER {ou_line}"
        elif proyeccion <= ou_line - 0.25 and ou_conf >= 60: # SEGURO Under
            punt_ou = 75
            pick_ou = f"UNDER {ou_line}"
        else: # RESCATE / NEUTRAL
            punt_ou = 50
            pick_ou = f"OVER/UNDER {ou_line} (NEUTRAL)"
        
        puntuaciones["OVER/UNDER"] = {
            "puntuacion": punt_ou,
            "pick": pick_ou,
            "confianza": ou_conf,
            "razon": ou_razon
        }
        
        # --- 4. Evaluar HOME RUN (Usando HRAnalyzerUnificado) ---
        if candidatos_hr:
            mejor_hr = candidatos_hr[0]
            prob_hr = mejor_hr.get("probabilidad", 0) 
            p_rival = mejor_hr.get("pitcher_rival", "TBD")
            
            # --- JERARQUÍA BASADA EN BACKTEST V2 (Rentabilidad > 45%) ---
            if prob_hr >= 72: # ÉLITE HR
                punt_hr = 95
            elif prob_hr >= 60: # ALTA HR
                punt_hr = 85
            elif prob_hr >= 45: # MEDIA HR (Umbral mínimo de apuesta)
                punt_hr = 75
            elif prob_hr >= 30: # BAJA HR
                punt_hr = 55
            else: # NO RENTABLE
                punt_hr = 20

            puntuaciones["HOME RUN"] = {
                "puntuacion": punt_hr,
                "pick": f"HR {mejor_hr.get('nombre', 'N/A')}",
                "confianza": prob_hr,
                "razon": f"{mejor_hr.get('nombre', '')} ({prob_hr}% prob) vs {p_rival}"
            }
        else:
            puntuaciones["HOME RUN"] = {
                "puntuacion": 0,
                "pick": "N/A",
                "confianza": 0,
                "razon": "Sin candidatos HR"
            }
        
        
        # 🛡️ Validar contra reglas de auto-aprendizaje
        # Esto se puede integrar aquí si BacktestingAutoAprendizaje devuelve una penalización
        # Por ahora, asumimos que la confianza ya fue ajustada por MotorMomentumProfesional

        # 5. ELEGIR LA MEJOR OPCIÓN
        mejor = max(puntuaciones.items(), key=lambda x: x[1]["puntuacion"])
        tipo_apuesta = mejor[0]
        datos = mejor[1]
        
        # Determinar stake
        if datos["puntuacion"] >= 80:
            stake = "ÉLITE (3u)"
        elif datos["puntuacion"] >= 65:
            stake = "SEGURO (2u)"
        elif datos["puntuacion"] >= 50:
            stake = "RESCATE (1u)"
        else:
            stake = "0u (EVITAR)"
        
        return {
            "tipo_apuesta": tipo_apuesta,
            "pick": datos["pick"],
            "confianza": datos["confianza"],
            "puntuacion": datos["puntuacion"],
            "razon": datos["razon"],
            "stake": stake,
            "todas_opciones": {k: {"punt": v["puntuacion"], "pick": v["pick"]} for k, v in puntuaciones.items()}
        }

# Prueba
if __name__ == "__main__":
    motor = MotorDecisionInteligente()
    
    partido = {
        "visitante": "New York Yankees",
        "local": "Tampa Bay Rays",
        "odds": {"over_under": 8.0}
    }
    
    resultado = {
        "pick": "New York Yankees",
        "confianza": 65,
        "diff": 12
    }
    
    candidatos = [
        {"nombre": "Aaron Judge", "probabilidad": 45, "pitcher_rival": "Kevin Gausman"}
    ]
    
    decision = motor.decidir_mejor_apuesta(partido, resultado, candidatos)
    
    print("🧠 DECISIÓN INTELIGENTE:")
    print(f"   Mejor apuesta: {decision['tipo_apuesta']}")
    print(f"   Pick: {decision['pick']}")
    print(f"   Confianza: {decision['confianza']}%")
    print(f"   Stake: {decision['stake']}")
    print(f"   Razón: {decision['razon']}")
    print(f"\n   Todas las opciones evaluadas:")
    for tipo, datos in decision["todas_opciones"].items():
        emoji = "✅" if tipo == decision["tipo_apuesta"] else "  "
        print(f"   {emoji} {tipo}: {datos['punt']}/100 → {datos['pick']}")
