# -*- coding: utf-8 -*-
"""
MOTOR HIBRIDO UNIVERSAL V24
Gemini -> Groq -> Motor Local (fallback automatico)
"""

import streamlit as st

class MotorHibridoUniversal:
    """Motor que une Gemini + Groq + Heuristico con fallback"""
    
    def __init__(self):
        self.modo_backup = False
        self.cache = {}
    
    def analizar(self, deporte, datos_partido, resultado_heuristico):
        """Analisis hibrido con fallback automatico"""
        
        gemini_ok = hasattr(st.session_state, 'gemini') and st.session_state.gemini
        groq_ok = hasattr(st.session_state, 'groq') and st.session_state.groq
        
        # 1. Intentar Gemini
        if gemini_ok:
            try:
                resultado = st.session_state.gemini.orquestrar_decision_final(
                    deporte, datos_partido, resultado_heuristico
                )
                return {
                    "pick": resultado.get("pick", resultado_heuristico.get("pick", "N/A")),
                    "confianza": self._fusionar(resultado_heuristico.get("confianza", 50), resultado.get("confianza", 50)),
                    "fuente": "🤖 Gemini",
                    "metodo": resultado.get("metodo", "Hibrido")
                }
            except:
                pass
        
        # 2. Intentar Groq
        if groq_ok:
            try:
                resultado = st.session_state.groq.analyze_fight(
                    datos_partido.get("peleador1", {}).get("nombre", ""),
                    datos_partido.get("peleador1", {}).get("record", "0-0"),
                    50, 0, 180, 180,
                    datos_partido.get("peleador2", {}).get("nombre", ""),
                    datos_partido.get("peleador2", {}).get("record", "0-0"),
                    50, 0, 180, 180,
                    "N/A", "N/A"
                )
                if resultado and resultado[0]:
                    return {
                        "pick": resultado[0].get("winner", resultado_heuristico.get("pick", "N/A")),
                        "confianza": resultado[0].get("confidence", resultado_heuristico.get("confianza", 50)),
                        "fuente": "⚡ Groq",
                        "metodo": resultado[0].get("method", "Rapido")
                    }
            except:
                pass
        
        # 3. Fallback local
        self.modo_backup = True
        return {
            "pick": resultado_heuristico.get("pick", "N/A"),
            "confianza": resultado_heuristico.get("confianza", 50),
            "fuente": "🏠 Local",
            "metodo": "Heuristico"
        }
    
    def _fusionar(self, conf_h, conf_ia):
        return int(conf_ia * 0.6 + conf_h * 0.4)
    
    def analizar_mlb(self, p, pick, conf):
        return self.analizar("MLB", p, {"pick": pick, "confianza": conf})
    
    def analizar_ufc(self, c, stats_p1, stats_p2):
        return self.analizar("UFC", c, {
            "pick": c.get("peleador1", {}).get("nombre", "P1"),
            "confianza": max(stats_p1.get("ko_rate", 0.5), stats_p2.get("ko_rate", 0.5)) * 100
        })
    
    def analizar_nba(self, p, resultado):
        return self.analizar("NBA", p, {"pick": resultado.get("recomendacion", "N/A"), "confianza": resultado.get("confianza", 50)})
