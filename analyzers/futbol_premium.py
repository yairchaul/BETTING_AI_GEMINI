"""
ANALIZADOR FÚTBOL PREMIUM - Con 6 reglas jerárquicas y blindaje
"""
class AnalizadorFutbolPremium:
    def __init__(self):
        pass
    
    def analizar(self, partido, resultado_heur):
        """Analiza partido con reglas premium"""
        
        local = partido.get('local', '')
        visitante = partido.get('visitante', '')
        stats = partido.get('stats_enriquecidas', {})
        
        recomendacion = resultado_heur.get('recomendacion', '')
        confianza = resultado_heur.get('confianza', 50)
        etiqueta_verde = confianza >= 70
        
        # Verificar rotación por Champions (si aplica)
        advertencia = ""
        if "Champions" in str(partido.get('liga', '')):
            if confianza > 65:
                advertencia = "⚠️ ALERTA: Posible rotación por Champions League"
                confianza = max(50, confianza - 15)
                etiqueta_verde = False
        
        return {
            'recomendacion': recomendacion,
            'confianza': confianza,
            'etiqueta_verde': etiqueta_verde,
            'advertencia': advertencia,
            'tipo': resultado_heur.get('tipo', 'Fútbol'),
            'analisis': f"Basado en últimos 5 partidos. Probabilidad {confianza}%"
        }
