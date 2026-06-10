# -*- coding: utf-8 -*-
"""MOTOR DE DECISIÓN CON MEMORIA - Aprende de resultados anteriores"""
import json
import os

class MotorDecisionMemoria:
    def __init__(self):
        self.archivo_resultados = "resultados_reales_15dias.json"
        self.cargar_equipos_trampa()
    
    def cargar_equipos_trampa(self):
        """Carga equipos trampa desde aprendizaje semanal"""
        try:
            with open("data/aprendizaje_semanal.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            self.equipos_trampa = data.get("equipos_trampa", [])
        except:
            self.equipos_trampa = []
    
    def obtener_decision_con_memoria(self, partido, datos_heuristica):
        """
        Toma decisión considerando el historial de resultados.
        Si el equipo ha fallado recientemente, recomienda EVITAR.
        """
        from analizador_tendencias import AnalizadorTendencias
        
        at = AnalizadorTendencias()
        analisis = at.analizar_tendencias()
        
        equipos_peligrosos = analisis.get("equipos_trampa", [])
        pick_sugerido = datos_heuristica.get("pick", "")
        
        # REGLA 1: Bloquear equipos trampa detectados
        if pick_sugerido in equipos_peligrosos:
            return {
                "decision": "EVITAR",
                "confianza_ajustada": 0,
                "razon": f"🚨 DINÁMICO: {pick_sugerido} detectado como equipo trampa (WR < 35% en 15d)",
                "nivel": "❌ EVITAR",
                "stake": "0u"
            }
        
        # REGLA 2: Zona trampa (diff 10-15%)
        diff = datos_heuristica.get("diff", 0)
        if 10 <= diff < 15:
            return {
                "decision": "EVITAR",
                "confianza_ajustada": 0,
                "razon": f"⚠️ Zona trampa detectada (diff {diff}% entre 10-15%)",
                "nivel": "❌ EVITAR",
                "stake": "0u"
            }
        
        # REGLA 3: Factor día
        from datetime import datetime
        dia = datetime.now().weekday()
        confianza = datos_heuristica.get("confianza", 50)
        factor_dia = 1.0
        
        if dia == 6:  # Domingo
            factor_dia = 0.85
        elif dia == 3:  # Jueves
            factor_dia = 0.90
        
        confianza_ajustada = confianza * factor_dia
        
        # REGLA 4: Clasificar según diff y confianza
        from analizador_tendencias import AnalizadorTendencias
        at = AnalizadorTendencias()
        umbrales = at.obtener_umbrales_dinamicos()
        
        if diff >= umbrales.get("elite_diff_min", 15) or (diff >= umbrales.get("elite_diff_alt", 7) and diff < 10):
            nivel, stake = "🔥 ELITE", "3u"
        elif diff >= umbrales.get("seguro_diff_min", 5) and confianza_ajustada >= 55:
            nivel, stake = "⭐ SEGURO", "2u"
        elif diff >= umbrales.get("rescate_diff_min", 2):
            nivel, stake = "🛡️ RESCATE", "1u"
        else:
            nivel, stake = "❌ EVITAR", "0u"
        
        return {
            "decision": "APOSTAR" if stake != "0u" else "EVITAR",
            "confianza_ajustada": round(confianza_ajustada, 1),
            "razon": f"✅ Pick validado con umbrales dinámicos (diff: {diff}%)",
            "nivel": nivel,
            "stake": stake
        }
    
    def guardar_resultado(self, partido, pick, ganador, resultado):
        """Guarda resultado para aprendizaje futuro"""
        import os
        os.makedirs("data", exist_ok=True)
        
        resultado_nuevo = {
            "fecha": __import__('datetime').datetime.now().strftime("%Y-%m-%d"),
            "visitante": partido.get("visitante", ""),
            "local": partido.get("local", ""),
            "pick": pick,
            "ganador": ganador,
            "resultado": resultado
        }
        
        # Cargar existentes
        try:
            with open(self.archivo_resultados, "r", encoding="utf-8") as f:
                resultados = json.load(f)
        except:
            resultados = []
        
        resultados.append(resultado_nuevo)
        
        with open(self.archivo_resultados, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Resultado guardado: {pick} → {resultado}")

# Instancia global
motor_memoria = MotorDecisionMemoria()
