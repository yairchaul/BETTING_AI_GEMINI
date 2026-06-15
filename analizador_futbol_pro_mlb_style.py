# -*- coding: utf-8 -*-
import google.generativeai as genai
import json
import re

class AnalizadorFutbolMLBStyle:
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

    def calcular_matchup(self, ofensiva, defensiva, portero_titular=True):
        # Métrica base
        gf_favor = [p.get('goles_favor', 0) for p in ofensiva]
        gc_contra = [p.get('goles_contra', 0) for p in defensiva]
        
        fuerza_ataque = sum(gf_favor) / len(gf_favor) if gf_favor else 0
        resistencia_defensa = sum(gc_contra) / len(gc_contra) if gc_contra else 0
        
        proyeccion = (fuerza_ataque + resistencia_defensa) / 2
        
        # --- FACTOR PITCHER (PORTERO) ---
        # Si el portero titular NO juega, la defensa proyectada es un 20% más débil
        if not portero_titular:
            proyeccion *= 1.20 
            
        return proyeccion

    def analizar(self, partido, stats_local, stats_visitante):
        # Detectar si los porteros titulares están en la lista de lesionados
        # (Buscamos palabras clave como 'Portero', 'Goalkeeper', 'GK' o nombres específicos)
        portero_l_ok = not any(k in str(stats_local.get('lesionados', [])).lower() for k in ['portero', 'gk', 'goalkeeper'])
        portero_v_ok = not any(k in str(stats_visitante.get('lesionados', [])).lower() for k in ['portero', 'gk', 'goalkeeper'])

        # Proyecciones Estilo MLB
        run_exp_l = self.calcular_matchup(stats_local['ultimos_5'], stats_visitante['ultimos_5'], portero_l_ok)
        run_exp_v = self.calcular_matchup(stats_visitante['ultimos_5'], stats_local['ultimos_5'], portero_v_ok)
        
        # Home Field Advantage (HFA): El local suele rendir un 5-10% mejor
        run_exp_l *= 1.05 
        
        total_proyectado = run_exp_l + run_exp_v
        
        if not self.disponible:
            return {"marcador": f"{run_exp_l:.1f}-{run_exp_v:.1f}", "apuesta": "Calculado sin IA"}

        prompt = f"""
        Analista Sabermétrico: {partido['local']} vs {partido['visitante']}.
        - Proyección Goles Local: {run_exp_l:.2f} (Portero OK: {portero_l_ok})
        - Proyección Goles Visita: {run_exp_v:.2f} (Portero OK: {portero_v_ok})
        - Total de la serie: {total_proyectado:.2f}
        
        Calcula el VALUE. Si el total es > 2.5, recomienda Over. 
        Si un equipo proyecta > 0.7 de diferencia, recomienda Gana (ML).
        
        Responde SOLO JSON: {{"apuesta": "...", "confianza": 0-100, "razon": "..."}}
        """

        try:
            response = self.model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                res = json.loads(match.group(0))
                res['proyeccion_marcador'] = f"{run_exp_l:.1f} - {run_exp_v:.1f}"
                res['alertas'] = "Baja de Portero Detectada" if (not portero_l_ok or not portero_v_ok) else "Porteros OK"
                return res
        except:
            return {"apuesta": "Error", "confianza": 0}
