# -*- coding: utf-8 -*-
"""
CEREBRO DEEPSEEK - Cliente para la API de DeepSeek (compatible con OpenAI)
"""

import os
import json
from openai import OpenAI # DeepSeek es compatible con la API de OpenAI
from dotenv import load_dotenv

load_dotenv() # Cargar variables de entorno al inicio

class CerebroDeepSeek:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        self.model_name = "deepseek-chat" # O el modelo específico que quieras usar
        self.client = None

        if not self.api_key:
            print("❌ DEEPSEEK_API_KEY no encontrada.")
            return

        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com/v1" # Endpoint de la API de DeepSeek
            )
            print(f"✅ DeepSeek listo con modelo: {self.model_name}")
        except Exception as e:
            print(f"❌ Error al conectar con DeepSeek: {e}")
            self.client = None

    def _get_system_persona(self):
        return """Eres el 'Analista Deportivo BETTING_AI', un experto senior en apuestas con acceso a datos en tiempo real. 
Tu objetivo es maximizar el ROI. Tu formato de respuesta DEBE ser siempre este JSON:
{
  "pick": "recomendación exacta",
  "confianza": 0-100,
  "stake": 1-3,
  "razon": "explicación técnica breve",
  "mercado": "MONEYLINE|OVER_UNDER|STRIKEOUTS|HOME_RUN|BTTS|HANDICAP"
}"""

    def orquestrar_decision_final(self, deporte, partido, resultado_heuristica, custom_prompt=None):
        if not self.client:
            return json.dumps({"error": "DeepSeek no disponible"})

        # Si viene un prompt personalizado (como el de razonamiento R1), lo priorizamos
        if custom_prompt:
            prompt_content = custom_prompt
        elif deporte == "MLB":
            prompt_content = self._build_mlb_json_prompt(partido, resultado_heuristica)
        elif deporte == "NBA":
            prompt_content = self._build_nba_prompt(partido, resultado_heuristica)
        elif deporte == "UFC":
            prompt_content = self._build_ufc_prompt(partido, resultado_heuristica)
        elif deporte == "FUTBOL":
            prompt_content = self._build_futbol_prompt(partido, resultado_heuristica)
        else:
            prompt_content = f"Analiza este evento de {deporte}: {partido}. Resultado previo: {resultado_heuristica}"

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self._get_system_persona()},
                    {"role": "user", "content": prompt_content}
                ],
                temperature=0.0,
                max_tokens=500
            )
            res_text = response.choices[0].message.content
            
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
                res_text = res_text.split("```")[1].strip()
            
            return res_text.strip()
        except Exception as e:
            return json.dumps({"error": f"Error en DeepSeek: {str(e)}"})

    # Métodos _build_mlb_json_prompt, _build_nba_prompt, etc. (copiados de cerebro_gemini_pro.py)
    # Estos prompts deben ser consistentes con la persona definida en _get_system_persona
    def _build_mlb_json_prompt(self, partido, resultado):
        persona = self._get_system_persona()
        return f"""{persona}
        
        MLB Matchup: {partido.get('visitante')} @ {partido.get('local')}
        Pitchers: {partido.get('pitchers', {}).get('visitante', {}).get('nombre', 'TBD')} vs {partido.get('pitchers', {}).get('local', {}).get('nombre', 'TBD')}
        Líneas: O/U {partido.get('odds', {}).get('over_under')}, ML {partido.get('odds', {}).get('moneyline')}
        Heurística: {resultado.get('recomendacion')} (Confianza: {resultado.get('confianza')}%)
        Clima: Temp {partido.get('clima', {}).get('temp', 'N/A')}°F, Viento {partido.get('clima', {}).get('wind_speed', 'N/A')}mph ({partido.get('clima', {}).get('wind_dir', 'N/A')})
        Game ID: {partido.get('game_pk', 'N/A')}
        Prioridad MLB: STRIKEOUTS > HOME_RUN > MONEYLINE.
        Analiza el valor basándote en la racha reciente y el clima."""

    def _build_nba_prompt(self, partido, resultado):
        persona = self._get_system_persona()
        return f"""{persona}
        
        NBA Matchup: {partido.get('local')} vs {partido.get('visitante')}
        Records: {partido.get('records', {}).get('local')} vs {partido.get('records', {}).get('visitante')}
        Heurística: {resultado.get('recomendacion')}
        Prioridad NBA: HÁNDICAP > OVER/UNDER > MONEYLINE.
        Aplica ajuste por localía (+5%) y fatiga."""

    def _build_ufc_prompt(self, partido, resultado):
        persona = self._get_system_persona()
        p1 = partido.get('peleador1', {})
        p2 = partido.get('peleador2', {})
        return f"""{persona}
        
        UFC Fight: {p1.get('nombre')} vs {p2.get('nombre')}
        Stats P1: Record {p1.get('record')}, Alcance {p1.get('alcance')}cm, SLpM {p1.get('slpm')}
        Stats P2: Record {p2.get('record')}, Alcance {p2.get('alcance')}cm, SLpM {p2.get('slpm')}
        Heurística: {resultado.get('recomendacion')}
        Prioridad UFC: MONEYLINE > MÉTODO DE FINALIZACIÓN.
        Penaliza si diferencia edad > 10 años."""

    def _build_futbol_prompt(self, partido, resultado):
        persona = self._get_system_persona()
        return f"""{persona}
        
        Soccer Matchup: {partido.get('home')} vs {partido.get('away')}
        Ligas: {partido.get('liga')}
        Estadísticas: Proy Goles {resultado.get('goles_proyectados')}
        Heurística: {resultado.get('recomendacion')}
        Prioridad Fútbol: OVER 1.5 1T > OVER 3.5 > BTTS > OVER 2.5 > MONEYLINE."""