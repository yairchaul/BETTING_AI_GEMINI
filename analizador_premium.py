# -*- coding: utf-8 -*-
"""
ANALIZADOR PREMIUM V24
Deteccion de contradicciones + Power Rating + Alertas
"""

class AnalizadorPremiumProfesional:
    """Fusion avanzada con alertas de contradiccion"""
    
    def __init__(self):
        self.alertas = []
    
    def analizar(self, resultado_heuristico, stats=None):
        """Analisis premium con deteccion de riesgos"""
        
        conf = resultado_heuristico.get("confianza", 50)
        pick = resultado_heuristico.get("pick", "N/A")
        
        # Power rating
        power = self._power_rating(stats)
        
        # Fusion
        conf_final = int((conf + power) / 2)
        
        # Alertas
        alertas = self._detectar_alertas(conf, stats)
        
        # Recomendacion final
        if conf_final >= 80:
            nivel, color, stake = "🔥 ELITE", "#10b981", "3u"
        elif conf_final >= 65:
            nivel, color, stake = "⭐ SEGURO", "#3b82f6", "2u"
        elif conf_final >= 50:
            nivel, color, stake = "🟡 MODERADO", "#f59e0b", "1u"
        else:
            nivel, color, stake = "❌ EVITAR", "#ef4444", "0u"
        
        return {
            "pick_final": pick,
            "confianza": conf_final,
            "nivel": nivel,
            "color": color,
            "stake": stake,
            "alertas": alertas,
            "metodo": "Motor Hibrido (Gemini/Groq + Heuristico)"
        }
    
    def _power_rating(self, stats):
        if not stats: return 50
        rating = 50
        if stats.get("racha_ganados", 0) > 3: rating += 10
        if stats.get("racha_perdidos", 0) > 3: rating -= 10
        if stats.get("lesionados", 0) > 2: rating -= 15
        return max(0, min(100, rating))
    
    def _detectar_alertas(self, confianza, stats):
        alertas = []
        if not stats: return alertas
        racha = str(stats.get("racha", ""))
        if confianza > 70 and "P" in racha:
            alertas.append("🚨 Confianza alta pero racha negativa")
        if confianza < 30 and "G" in racha:
            alertas.append("⚠️ Oportunidad: Baja confianza pero buena racha")
        if stats.get("lesionados", 0) > 3:
            alertas.append("🏥 +3 lesionados")
        return alertas
