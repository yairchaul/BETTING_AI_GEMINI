# -*- coding: utf-8 -*-
"""
GROQ ENGINE CON AUTO-APRENDIZAJE
Velocidad + adaptación automática
"""
import json

class GroqEngineAprendizaje:
    def __init__(self, groq_client=None):
        self.groq = groq_client
        self.umbrales_dinamicos = {
            "elite_diff_min": 15,
            "seguro_diff_min": 5,
            "rescate_diff_min": 2,
        }
        self.cargar_umbrales()
    
    def cargar_umbrales(self):
        try:
            with open("data/aprendizaje_semanal.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            from analizador_tendencias import AnalizadorTendencias
            at = AnalizadorTendencias()
            self.umbrales_dinamicos = at.obtener_umbrales_dinamicos()
        except:
            pass
    
    def analizar_rapido(self, partido, resultado_heuristico):
        """
        Análisis rápido con Groq + reglas de aprendizaje
        """
        pick = resultado_heuristico.get('pick', '')
        conf = resultado_heuristico.get('confianza', 50)
        diff = resultado_heuristico.get('diff', 0)
        
        # Aplicar umbrales dinámicos
        if diff >= self.umbrales_dinamicos.get("elite_diff_min", 15):
            nivel, stake = "ELITE", 3
        elif diff >= self.umbrales_dinamicos.get("seguro_diff_min", 5) and conf >= 55:
            nivel, stake = "SEGURO", 2
        elif diff >= self.umbrales_dinamicos.get("rescate_diff_min", 2):
            nivel, stake = "RESCATE", 1
        else:
            nivel, stake = "EVITAR", 0
        
        # Si Groq está disponible, usarlo para validación rápida
        if self.groq and hasattr(self.groq, 'analizar_rapido'):
            try:
                resultado_groq = self.groq.analizar_rapido("MLB", partido, {"pick": pick, "confianza": conf})
                if resultado_groq:
                    return {
                        "pick": resultado_groq.get("pick", pick),
                        "confianza": resultado_groq.get("confianza", conf),
                        "nivel": nivel,
                        "stake": stake,
                        "fuente": "Groq + Auto-aprendizaje"
                    }
            except:
                pass
        
        return {
            "pick": pick,
            "confianza": conf,
            "nivel": nivel,
            "stake": stake,
            "fuente": "Auto-aprendizaje (reglas)"
        }
    
    def actualizar_umbrales(self, nuevos_umbrales):
        """Actualiza umbrales basados en backtesting"""
        self.umbrales_dinamicos.update(nuevos_umbrales)
        
        import os
        os.makedirs("data", exist_ok=True)
        with open("data/umbrales_dinamicos.json", "w", encoding="utf-8") as f:
            json.dump(self.umbrales_dinamicos, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Umbrales dinámicos actualizados: {self.umbrales_dinamicos}")

# Prueba
if __name__ == "__main__":
    ge = GroqEngineAprendizaje()
    
    partido = {"visitante": "New York Yankees", "local": "Texas Rangers"}
    resultado = {"pick": "New York Yankees", "confianza": 65, "diff": 12}
    
    decision = ge.analizar_rapido(partido, resultado)
    print(f"Decisión: {decision}")
