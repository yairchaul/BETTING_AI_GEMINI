# -*- coding: utf-8 -*-
import google.generativeai as genai
import json
import re
from datetime import datetime

class AnalizadorFutbolPremium:
    """
    MOTOR PREMIUM: Basado en Sabermetrics de MLB aplicado al Fútbol.
    Incluye: Factor Portero, Ventaja de Localía y Fatiga de Calendario.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.disponible = False
        try:
            if api_key and api_key != "TU_API_KEY_AQUÍ":
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.disponible = True
        except:
            self.model = None

    def _calcular_fatiga(self, stats_equipo):
        # Si el último partido fue hace menos de 4 días, penaliza la ofensiva un 10%
        # (Simula el cansancio del bullpen o de los abridores en MLB)
        try:
            ultimo_partido = stats_equipo.get('fecha_ultimo', "")
            if ultimo_partido:
                fecha_p = datetime.strptime(ultimo_partido, "%Y-%m-%d")
                dias_descanso = (datetime.now() - fecha_p).days
                return 0.90 if dias_descanso < 4 else 1.0
        except:
            pass
        return 1.0

    def analizar(self, partido, stats_local, stats_visitante):
        # 1. Identificar Porteros (Factor Pitcher)
        baja_portero_l = any(k in str(stats_local.get('lesionados', [])).lower() for k in ['portero', 'gk', 'goalkeeper'])
        baja_portero_v = any(k in str(stats_visitante.get('lesionados', [])).lower() for k in ['portero', 'gk', 'goalkeeper'])

        # 2. Calcular Cruce (Ataque vs Defensa)
        def calcular_run_exp(ataque, defensa, es_local, tiene_portero):
            gf = [p.get('goles_favor', 0) for p in ataque.get('ultimos_5', [])]
            gc = [p.get('goles_contra', 0) for p in defensa.get('ultimos_5', [])]
            
            base = ( (sum(gf)/5 if gf else 0) + (sum(gc)/5 if gc else 0) ) / 2
            
            # Aplicar modificadores
            if es_local: base *= 1.05  # Home Field Adv
            if not tiene_portero: base *= 1.15 # Penalización por falta de 'Pitcher' titular
            
            # Aplicar Fatiga
            base *= self._calcular_fatiga(ataque)
            
            return base

        exp_l = calcular_run_exp(stats_local, stats_visitante, True, not baja_portero_l)
        exp_v = calcular_run_exp(stats_visitante, stats_local, False, not baja_portero_v)
        
        total = exp_l + exp_v

        if not self.disponible:
            return {"apuesta": "ERROR_IA", "marcador_proyectado": f"{exp_l:.1f}-{exp_v:.1f}"}

        # 3. Prompt Sabermétrico para Gemini
        prompt = f"""
        SABERMETRICS FOOTBALL ANALYSIS:
        Matchup: {partido['local']} vs {partido['visitante']}
        - Proyección Goles Local: {exp_l:.2f}
        - Proyección Goles Visita: {exp_v:.2f}
        - Total Proyectado: {total:.2f}
        - Alerta Portero: {'BAJA LOCAL' if baja_portero_l else 'OK'} / {'BAJA VISITA' if baja_portero_v else 'OK'}

        Instrucción: Si el total es > 2.7, recomienda Over 2.5. Si la diferencia es > 0.8, recomienda el favorito.
        Responde SOLO JSON: {{"apuesta": "...", "confianza": 0-100, "razon": "..."}}
        """

        try:
            response = self.model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                res = json.loads(match.group(0))
                res['marcador_ia'] = f"{exp_l:.1f} - {exp_v:.1f}"
                res['tipo'] = 'SABERMETRICS_PREMIUM'
                return res
        except:
            return {"apuesta": "Error en IA", "confianza": 0}
