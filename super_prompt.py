# -*- coding: utf-8 -*-
"""SUPER PROMPT EVOLUTIVO - Aprende del backtesting"""
import json
import os
from datetime import datetime

class SuperPromptEvolutivo:
    def __init__(self):
        self.ctx = None
        self.cargar_contexto_backtesting()
    
    def cargar_contexto_backtesting(self):
        """Carga datos reales de backtesting para nutrir al prompt"""
        try:
            with open("data/contexto_backtesting.json", "r", encoding="utf-8") as f:
                self.ctx = json.load(f)
        except:
            self.ctx = None
    
    def obtener_lecciones(self):
        """Analiza el historial REAL de backtesting"""
        if self.ctx:
            por_clase = self.ctx.get("por_clase", {})
            lecciones = self.ctx.get("lecciones", [])
            resumen = "BACKTESTING REAL (262 partidos, 20 dias):\n"
            resumen += f"- WR Global: {self.ctx['rendimiento_global']['win_rate']}\n"
            resumen += f"- Profit: {self.ctx['rendimiento_global']['profit']}\n"
            resumen += f"- ELITE: {por_clase.get('ELITE', {}).get('wr', 'N/A')} WR\n"
            resumen += f"- SEGURO: {por_clase.get('SEGURO', {}).get('wr', 'N/A')} WR\n"
            resumen += f"- RESCATE: {por_clase.get('RESCATE', {}).get('wr', 'N/A')} WR\n"
            if lecciones:
                resumen += f"\nLECCIONES: {', '.join(lecciones[:3])}"
            return resumen
        return "Sin historial de backtesting disponible."
    
    def generar_prompt_maestro(self, partido, bateadores):
        """Genera el Super Prompt con contexto de backtesting"""
        away = partido.get("visitante", "TBD")
        home = partido.get("local", "TBD")
        pitchers = partido.get("pitchers", {})
        p_away = pitchers.get("visitante", {}).get("nombre", "TBD")
        p_home = pitchers.get("local", {}).get("nombre", "TBD")
        odds = partido.get("odds", {})
        ml = odds.get("moneyline", {})
        ou = odds.get("over_under", "N/A")
        venue = partido.get("venue", "TBD")
        
        lista_bates = "\n".join([
            f"- {b.get('nombre', b.get('bateador', 'N/A'))}: {b.get('probabilidad', b.get('prob_ia', 0))}% HR"
            for b in (bateadores or [])[:5]
        ]) if bateadores else "Sin candidatos HR"
        
        lecciones = self.obtener_lecciones()
        
        prompt = f"""Eres el nucleo de BETTING_AI NEON V24. Maximiza el Yield.

[DATOS EN TIEMPO REAL]
- Matchup: {away} ({p_away}) @ {home} ({p_home})
- Lineas: ML {ml.get('visitante', 'N/A')} / {ml.get('local', 'N/A')} | O/U {ou}
- Estadio: {venue}

[ANALISIS DE BATEO]
{lista_bates}

[LECCIONES DE BACKTESTING]
{lecciones}

[TAREA]
1. Analiza el matchup de pitchers vs lineups.
2. Cruza probabilidad HR con factor estadio.
3. Evalua si el Moneyline tiene valor real.
4. ELITE y SEGURO son las clases mas rentables (73% WR). Priorizalas.
5. RESCATE solo si el handicap es +3.5.

[RESPUESTA - FORMATO JSON]
{{"decision": "APOSTAR|EVITAR", "pick_final": "Equipo o Over/Under", "stake": "1u-5u", "probabilidad_exito": "0-100", "analisis_tecnico": "Explicacion breve", "hr_recomendado": "Nombre del bateador"}}"""
        
        return prompt
