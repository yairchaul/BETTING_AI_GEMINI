"""
ANALIZADOR FÚTBOL GEMINI MEJORADO - Con análisis de rachas
"""
class AnalizadorFutbolGeminiMejorado:
    def __init__(self, api_key):
        self.api_key = api_key
        self.gemini = None
        try:
            from cerebro_gemini_pro import CerebroGemini
            self.gemini = CerebroGemini(api_key)
        except:
            pass
    
    def analizar(self, partido, stats_local, stats_visit, probabilidades):
        """Analiza partido de fútbol con Gemini"""
        local = partido.get('local', '')
        visitante = partido.get('visitante', '')
        
        if self.gemini:
            try:
                datos = f"Over 2.5: {probabilidades.get('over_25', 0)}% | BTTS: {probabilidades.get('btts', 0)}%"
                return self.gemini.analizar_futbol(local, visitante, stats_local, stats_visit)
            except:
                return "Análisis Gemini no disponible"
        return "Gemini no disponible"
