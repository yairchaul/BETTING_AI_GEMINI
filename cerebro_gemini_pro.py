# -*- coding: utf-8 -*-
"""
CEREBRO GEMINI PRO - V3.4 (AUTO-ADAPTATIVO)
Busca y selecciona el modelo disponible automáticamente.
"""

import os
import json
import google.generativeai as genai
import logging

# Configuración de logging según Regla 20
logger = logging.getLogger("BETTING_AI.cerebro")

def get_api_key():
    key = os.environ.get('GEMINI_API_KEY')
    if key: return key
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if 'GEMINI_API_KEY=' in line:
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    except: pass
    return None

class CerebroGeminiPro:
    def __init__(self, api_key=None):
        self.api_key = api_key or get_api_key()
        self.model_name = None
        
        if not self.api_key:
            logger.error("❌ GEMINI_API_KEY no encontrada.")
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai
            self.available_models = []
            
            # --- LÓGICA AUTO-ADAPTATIVA ---
            # Listamos los modelos disponibles en TU cuenta
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    self.available_models.append(m.name)
                    # Preferencia por modelos flash que son más rápidos
                    if 'flash' in m.name:
                        self.model_name = m.name
                        break # Encontró un flash, lo usa y sale
            
            # Si no encontró un flash, agarra el primero que funcione
            if not self.model_name and self.available_models:
                self.model_name = self.available_models[0]
            elif not self.model_name: # No hay modelos disponibles
                logger.error("❌ No se encontraron modelos Gemini disponibles.")
                
            logger.info(f"✅ Motor adaptado automáticamente a: {self.model_name}")
        except Exception as e:
            logger.error(f"❌ Error al auto-detectar modelo: {e}")
            self.client = None

    def test_connection(self):
        """Verifica si la API responde correctamente"""
        try:
            model = self.client.GenerativeModel(self.model_name)
            response = model.generate_content("Ping")
            return response.text is not None
        except:
            return False
    
    def orquestrar_decision_final(self, deporte, partido, resultado_heuristica, resumen_contexto):
        if not self.client or not self.model_name:
            return json.dumps({"error": "No hay modelos disponibles"})
        
        # Merge partido, resultado_heuristica, and resumen_contexto for a comprehensive prompt
        # This ensures all relevant data is available to the prompt builder
        full_context = {
            "partido": partido,
            "resultado_heuristica": resultado_heuristica,
            "resumen_contexto": resumen_contexto
        }

        if deporte == "MLB":
            prompt = self._build_mlb_json_prompt(full_context)
        elif deporte == "NBA":
            prompt = self._build_nba_prompt(full_context)
        elif deporte == "UFC":
            prompt = self._build_ufc_prompt(full_context)
        elif deporte == "FUTBOL":
            prompt = self._build_futbol_prompt(full_context)
        else:
            prompt = f"Analiza este evento de {deporte}: {json.dumps(full_context, ensure_ascii=False)}"
        
        try:
            model = self.client.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            
            res_text = response.text
            # Limpieza de formato Markdown JSON
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```").strip()
            elif "```" in res_text:
                # Si no hay ```json pero sí ```, asumimos que el JSON está dentro del primer bloque
                res_text = res_text.split("```")[0].strip()
            
            return res_text.strip()
        except Exception as e:
            logger.error(f"Error en {self.model_name} al generar contenido: {str(e)}")
            return json.dumps({"error": f"Error en {self.model_name}: {str(e)}"})
    
    def _build_mlb_json_prompt(self, full_context):
        partido = full_context["partido"]
        resultado_heuristica = full_context["resultado_heuristica"]
        resumen = full_context["resumen_contexto"] # Usar el resumen pre-construido

        away = resumen.get("partido", "TBD @ TBD").split(" @ ")[0]
        home = resumen.get("partido", "TBD @ TBD").split(" @ ")[1]
        
        p_away = partido.get("pitchers", {}).get("visitante", {}).get("nombre", "Por anunciar")
        p_home = partido.get("pitchers", {}).get("local", {}).get("nombre", "Por anunciar")
        
        # Asegurarse de que 'Por anunciar' se use si los datos faltan, según la Regla 9
        whip_v = partido.get("whip_v", "N/A")
        whip_l = partido.get("whip_l", "N/A")
        k_v = partido.get("k_proy_v", "N/A")
        k_l = partido.get("k_proy_l", "N/A")
        ou = resumen.get("linea_ou", "N/A") # Usar del resumen para consistencia
        pick = resumen.get("pick_ml", "N/A") # Usar del resumen
        conf = resumen.get("confianza_ml", 50) # Usar del resumen
        handicap_sugerido = resultado_heuristica.get("handicap", "N/A") # Esto podría venir del resultado heurístico
        
        venue = resumen.get("estadio", "TBD")
        clima_info = resumen.get("clima", "N/A")
        temp = clima_info.split(',')[0].replace('°F', '').strip() if '°F' in clima_info else "N/A"
        wind_speed = clima_info.split('Viento ')[1].split('mph')[0].strip() if 'Viento' in clima_info else "N/A"
        wind_dir = clima_info.split('mph ')[1].strip() if 'mph' in clima_info else "N/A"
        
        # Contexto adicional del resumen_contexto (Regla 13)
        hr_info = resumen.get("hr_info", "")
        away_hr_prob = resumen.get("away_team_hr_prob", 0.0)
        home_hr_prob = resumen.get("home_team_hr_prob", 0.0)
        lesiones = ', '.join(resumen.get("lesiones", [])) if resumen.get("lesiones") else "Ninguna"
        ausencias = ', '.join(resumen.get("ausencias", [])) if resumen.get("ausencias") else "Ninguna"
        cambios_alineacion = ', '.join(resumen.get("cambios_alineacion", [])) if resumen.get("cambios_alineacion") else "Ninguno"
        
        # Regla 9: Si los datos del pitcher faltan, indicarlo explícitamente.
        pitcher_away_status = f"{p_away}" if p_away != "Por anunciar" else "Por anunciar (datos insuficientes)"
        pitcher_home_status = f"{p_home}" if p_home != "Por anunciar" else "Por anunciar (datos insuficientes)"
        
        return f"""Eres un analista senior de MLB especializado en apuestas deportivas.
Tu tarea es recibir datos estadisticos y devolver un analisis visual en Markdown.

REGLAS DE FORMATO:
1. Usa tablas de Markdown para las metricas principales.
2. Usa bloques de cita (>) para las conclusiones tecnicas.
3. Usa emojis funcionales: 🟢 valor, 🔴 riesgo, 📈 OVER, 📉 UNDER, ⭐ elite, 🏟️ estadio.
4. Si un dato es 0 (como K/9), indica: "Dato insuficiente para proyeccion".
5. NO digas "None vs None" o "falta informacion". Usa los datos proporcionados.

DATOS DEL PARTIDO:
- 🏟️ {away} @ {home} | Estadio: {venue}
- 🥎 Lanzadores: {pitcher_away_status} vs {pitcher_home_status}
- 📊 WHIP: {whip_v} / {whip_l}
- ☁️ Clima: Temp {temp}°F, Viento {wind_speed}mph ({wind_dir})
- ⚡ K Proyectados: {k_v} / {k_l}
- 🥅 Handicap Sugerido: {handicap_sugerido}
- 📈 O/U: {ou}
- 🎯 Pick Heuristico: {pick} (Confianza: {conf}%)

CONTEXTO ADICIONAL (Regla 13):
- Lesiones de jugadores estrella: {lesiones}
- Ausencias confirmadas: {ausencias}
- Cambios de última hora en alineaciones: {cambios_alineacion}
- Probabilidad HR Visitante: {away_hr_prob:.1f}%
- Probabilidad HR Local: {home_hr_prob:.1f}%
{hr_info}

ESTRUCTURA OBLIGATORIA DE RESPUESTA:

## 🏟️ ANALISIS: {away} @ {home}

### 🎯 DETERMINACION DE APUESTA
| Categoria | Seleccion | Detalle |
|-----------|-----------|---------|
| Pick Principal | [ML/HANDICAP/OVER/UNDER/K/HR] | [Nombre equipo/jugador] |
| Confianza | [0-100]% | Stake: [1u-5u] |
| Valor Detectado | [SI/NO] | [Breve explicacion] |

### 🥎 DUELO DE LANZADORES
> **{p_away}**: WHIP {whip_v}. [Analisis breve, considera si es "Por anunciar"]
> **{p_home}**: WHIP {whip_l}. [Analisis breve, considera si es "Por anunciar"]

### 📊 PROYECCION DE CARRERAS (O/U)
- Linea Casino: {ou}
- Proyeccion Modelo: [TU PROYECCION]
- Veredicto: 📈 OVER / 📉 UNDER / ➡️ NEUTRAL

### 💣 RADAR DE HOME RUNS
| Jugador | Equipo | Prob. HR | Analisis |
|---------|--------|----------|----------|
| [Nombre] | [Eq] | [%] | [Breve] |
### 🎲 VEREDICTO FINAL
> [Conclusion en una frase con la mejor apuesta recomendada, integrando todos los factores, incluyendo lesiones/ausencias y probabilidades de HR.]"""

    def _build_nba_prompt(self, full_context):
        partido = full_context["partido"]
        resultado = full_context["resultado_heuristica"]
        resumen = full_context["resumen_contexto"]

        # Incorporar contexto adicional de lesiones/ausencias/cambios de alineación
        lesiones = ', '.join(resumen.get("lesiones", [])) if resumen.get("lesiones") else "Ninguna"
        ausencias = ', '.join(resumen.get("ausencias", [])) if resumen.get("ausencias") else "Ninguna"
        cambios_alineacion = ', '.join(resumen.get("cambios_alineacion", [])) if resumen.get("cambios_alineacion") else "Ninguno"

        return f"""Eres un analista de la NBA. Analiza el valor del Spread y Over/Under.
        Partido: {partido.get('local')} vs {partido.get('visitante')}
        Líneas: O/U {partido.get('odds', {}).get('over_under')}, Spread {partido.get('odds', {}).get('spread')}
        Confianza Heurística: {resultado.get('confianza')}%
        Prioriza: Fatiga por back-to-back y volumen de triples.

        CONTEXTO ADICIONAL:
        - Lesiones de jugadores estrella: {lesiones}
        - Ausencias confirmadas: {ausencias}
        - Cambios de última hora en alineaciones: {cambios_alineacion}

        Devuelve tu análisis en formato JSON como se especifica en las reglas generales."""

    def _build_ufc_prompt(self, full_context):
        partido = full_context["partido"]
        resultado = full_context["resultado_heuristica"]
        resumen = full_context["resumen_contexto"]

        p1 = partido.get('peleador1', {})
        p2 = partido.get('peleador2', {})

        # Incorporar contexto adicional de lesiones/ausencias/cambios de alineación
        lesiones = ', '.join(resumen.get("lesiones", [])) if resumen.get("lesiones") else "Ninguna"
        ausencias = ', '.join(resumen.get("ausencias", [])) if resumen.get("ausencias") else "Ninguna"
        cambios_alineacion = ', '.join(resumen.get("cambios_alineacion", [])) if resumen.get("cambios_alineacion") else "Ninguno"

        return f"""Analista de MMA. Evalúa choque de estilos.
        Pelea: {p1.get('nombre')} vs {p2.get('nombre')}
        Físico: Alcance {p1.get('alcance')}cm vs {p2.get('alcance')}cm
        Estilo: KO Rate {p1.get('ko_rate')}% vs {p2.get('ko_rate')}%
        Veredicto sobre si llega a la decisión o termina por sumisión/KO.

        CONTEXTO ADICIONAL:
        - Lesiones de peleadores: {lesiones}
        - Ausencias confirmadas: {ausencias}
        - Cambios de última hora: {cambios_alineacion}

        Devuelve tu análisis en formato JSON como se especifica en las reglas generales."""

    def _build_futbol_prompt(self, full_context):
        partido = full_context["partido"]
        resultado = full_context["resultado_heuristica"]
        resumen = full_context["resumen_contexto"]

        # Incorporar contexto adicional de lesiones/ausencias/cambios de alineación
        lesiones = ', '.join(resumen.get("lesiones", [])) if resumen.get("lesiones") else "Ninguna"
        ausencias = ', '.join(resumen.get("ausencias", [])) if resumen.get("ausencias") else "Ninguna"
        cambios_alineacion = ', '.join(resumen.get("cambios_alineacion", [])) if resumen.get("cambios_alineacion") else "Ninguno"

        return f"""Analista de Fútbol Pro. 
        Matchup: {partido.get('home')} vs {partido.get('away')}
        Tendencia Goles: {resultado.get('goles_proyectados')} esperados.
        Analiza valor en Ambos Anotan (BTTS) y Over 2.5.
        
        CONTEXTO ADICIONAL:
        - Lesiones de jugadores clave: {lesiones}
        - Ausencias confirmadas: {ausencias}
        - Cambios de última hora en alineaciones: {cambios_alineacion}

        Devuelve tu análisis en formato JSON como se especifica en las reglas generales."""