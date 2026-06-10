# -*- coding: utf-8 -*-
"""ANALISTA TOTAL - Gemini/Groq con TODOS los datos"""
import json
import os
from datetime import datetime
import numpy as np # Necesario para np.mean
from collections import Counter # Necesario para Counter
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Definir la ruta base del proyecto para asegurar rutas absolutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class AnalistaTotal:
    """Usa Gemini o Groq para analizar TODOS los datos disponibles"""
    
    def __init__(self, gemini_client=None, groq_client=None, deepseek_client=None, new_ai_client=None, selected_model="Votación (Todas las IAs)"):
        self.gemini = gemini_client # Cliente para Gemini
        self.groq = groq_client # Cliente para Groq
        self.deepseek = deepseek_client # Cliente para DeepSeek
        self.new_ai = new_ai_client # Cliente para NewAI
        self.selected_model = selected_model # Modelo de IA seleccionado
        self.cargar_contexto() # Carga el contexto al inicializar
    
    def cargar_contexto(self): # Carga el contexto desde archivos JSON
        """Carga todo el contexto disponible"""
        self.contexto = {}
        
        # Tendencias Over/Under
        try:
            path = os.path.join(BASE_DIR, "data", "tendencias_over_under.json")
            with open(path, "r", encoding="utf-8") as f:
                self.contexto["tendencias_ou"] = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Archivo no encontrado: {path}")
        except Exception as e:
            logger.error(f"Error al cargar tendencias_ou: {e}")
        
        # Aprendizaje semanal
        try:
            path = os.path.join(BASE_DIR, "data", "aprendizaje_semanal.json")
            with open(path, "r", encoding="utf-8") as f:
                self.contexto["aprendizaje"] = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Archivo no encontrado: {path}")
        except Exception as e:
            logger.error(f"Error al cargar aprendizaje_semanal: {e}")
        
        # Umbrales dinámicos
        try:
            path = os.path.join(BASE_DIR, "data", "umbrales_dinamicos.json")
            with open(path, "r", encoding="utf-8") as f:
                self.contexto["umbrales"] = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Archivo no encontrado: {path}")
        except Exception as e:
            logger.error(f"Error al cargar umbrales_dinamicos: {e}")
        
        # Umpires
        try:
            path = os.path.join(BASE_DIR, "data", "umpires_db.json")
            with open(path, "r", encoding="utf-8") as f:
                self.contexto["umpires"] = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Archivo no encontrado: {path}")
        except Exception as e:
            logger.error(f"Error al cargar umpires_db: {e}")
        
        # Estadios
        try:
            path = os.path.join(BASE_DIR, "data", "estadios_db.json")
            with open(path, "r", encoding="utf-8") as f:
                self.contexto["estadios"] = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Archivo no encontrado: {path}")
        except Exception as e:
            logger.error(f"Error al cargar estadios_db: {e}")
        
        # HR datos
        try:
            path = os.path.join(BASE_DIR, "hr_datasets_completos.json")
            with open(path, "r", encoding="utf-8") as f:
                self.contexto["hr_data"] = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Archivo no encontrado: {path}")
        except Exception as e:
            logger.error(f"Error al cargar hr_datasets_completos.json: {e}")
    
    def analizar_partido_completo(self, partido, resultado_heurístico, candidatos_hr, clima=None):
        """
        Análisis COMPLETO con todos los datos disponibles
        """
        # Construir resumen del contexto
        resumen = self._construir_resumen(partido, resultado_heurístico, candidatos_hr, clima)
        deporte = resumen.get('deporte', 'MLB') # Asumir MLB si no se especifica
        
        ia_results = []

        # Ejecutar IA(s) según la selección
        if self.selected_model == "Gemini" and self.gemini:
            try:
                ia_results.append(self._analizar_con_gemini(deporte, partido, resultado_heurístico, resumen))
            except Exception as e:
                logger.error(f"Gemini falló: {e}")
        elif self.selected_model == "Groq" and self.groq:
            try:
                ia_results.append(self._analizar_con_groq(deporte, partido, resultado_heurístico, resumen))
            except Exception as e:
                logger.error(f"Groq falló: {e}")
        elif self.selected_model == "DeepSeek" and self.deepseek:
            try:
                ia_results.append(self._analizar_con_deepseek(deporte, partido, resultado_heurístico, resumen))
            except Exception as e:
                logger.error(f"DeepSeek falló: {e}")
        elif self.selected_model == "NewAI" and self.new_ai:
            try:
                ia_results.append(self._analizar_con_new_ai(deporte, partido, resultado_heurístico, resumen))
            except Exception as e:
                logger.error(f"NewAI falló: {e}")
        elif self.selected_model == "Votación (Todas las IAs)":
            if self.gemini:
                try:
                    ia_results.append(self._analizar_con_gemini(deporte, partido, resultado_heurístico, resumen))
                except Exception as e:
                    logger.error(f"Gemini falló: {e}")
            if self.groq:
                try:
                    ia_results.append(self._analizar_con_groq(deporte, partido, resultado_heurístico, resumen))
                except Exception as e:
                    logger.error(f"Groq falló: {e}")
            if self.deepseek:
                try:
                    ia_results.append(self._analizar_con_deepseek(deporte, partido, resultado_heurístico, resumen))
                except Exception as e:
                    logger.error(f"DeepSeek falló: {e}")
            if self.new_ai:
                try:
                    ia_results.append(self._analizar_con_new_ai(deporte, partido, resultado_heurístico, resumen))
                except Exception as e:
                    logger.error(f"NewAI falló: {e}")
        
        if ia_results:
            voted_result = self._sistema_de_votacion(ia_results, resultado_heurístico)
            # Añadir los resultados individuales para visualización
            voted_result['individual_ia_results'] = ia_results
            return voted_result
        
        # Fallback si ninguna IA responde o si se selecciona "Heurístico"
        return resultado_heurístico # Retorna el resultado heurístico directamente
    
    def _construir_resumen(self, partido, resultado, candidatos, clima):
        """Construye resumen para la IA"""
        deporte = "MLB" # Default, ajustar si es necesario
        if "peleador1" in partido: deporte = "UFC"
        elif "records" in partido: deporte = "NBA"
        elif "liga" in partido: deporte = "FUTBOL"

        away = partido.get("visitante", "?")
        home = partido.get("local", "?")
        
        # Para UFC, los nombres de los peleadores son el "equipo"
        if deporte == "UFC":
            away = partido.get("peleador1", {}).get("nombre", "?")
            home = partido.get("peleador2", {}).get("nombre", "?")

        venue = partido.get("venue", "TBD")
        ou_line = partido.get("odds", {}).get("over_under", "N/A")
        
        # Datos heurísticos
        pick_ml = resultado.get("pick", "")
        conf_ml = resultado.get("confianza", 50)
        diff = float(resultado.get("diff", 0))
        
        # Tendencias
        equipos_trampa = self.contexto.get("aprendizaje", {}).get("equipos_trampa", [])
        dia_semana = datetime.now().weekday()
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
        # Factor día O/U
        factor_dia = 1.0
        tendencias_ou = self.contexto.get("tendencias_ou", {})
        if tendencias_ou.get("factores_dia"):
            dia_str = str(dia_semana)
            if dia_str in tendencias_ou["factores_dia"]:
                factor_dia = tendencias_ou["factores_dia"][dia_str].get("factor", 1.0)
        
        # Candidatos HR
        hr_info = ""
        if candidatos:
            mejor = candidatos[0]
            hr_info = f"Top candidato HR: {mejor.get('nombre', 'N/A')} ({mejor.get('probabilidad', 0)}%)"
        
        # Placeholder para probabilidades de HR por equipo (Regla 16)
        # Esto debería ser alimentado por el orquestador o un módulo de HR más avanzado
        away_team_hr_prob = 0.0
        home_team_hr_prob = 0.0
        if isinstance(candidatos, dict) and 'away_team_hr_prob' in candidatos:
            away_team_hr_prob = candidatos['away_team_hr_prob']
            home_team_hr_prob = candidatos['home_team_hr_prob']
        elif self.contexto.get("hr_data") and away != "?" and home != "?":
            # Intento de inferir de hr_data si está estructurado por equipo
            # Asumiendo hr_data = {'TeamName': {'hr_prob': 0.X}}
            # La estructura actual de hr_data no soporta esto directamente sin un cálculo previo.
            pass # Esto requeriría un módulo PredictorHR para calcular.

        
        # Clima
        clima_info = ""
        if clima:
            clima_info = f"{clima.get('temp', 70)}°F, Viento {clima.get('wind_speed', 0)}mph {clima.get('wind_dir', 'None')}"
        
        return {
            "partido": f"{away} @ {home}",
            "estadio": venue,
            "linea_ou": ou_line,
            "pick_ml": pick_ml,
            "confianza_ml": conf_ml,
            "diff": diff,
            "equipos_trampa": equipos_trampa,
            "dia": dias[dia_semana],
            "factor_dia_ou": factor_dia,
            "hr_info": hr_info,
            "clima": clima_info,
            "pick_en_trampa": pick_ml in equipos_trampa,
            "zona_trampa": 10 <= diff < 15,
            "deporte": deporte, # Añadir el deporte al resumen
            "away_team_hr_prob": away_team_hr_prob, # Probabilidad HR equipo visitante
            "home_team_hr_prob": home_team_hr_prob, # Probabilidad HR equipo local
            # Placeholder para contexto adicional (Regla 13)
            "lesiones": partido.get("lesiones", []),
            "ausencias": partido.get("ausencias", []),
            "cambios_alineacion": partido.get("cambios_alineacion", [])
        }
    
    def _analizar_con_gemini(self, deporte, partido_original, resultado_heuristico, resumen_contexto):
        """Análisis profundo con Gemini"""
        prompt = f"""
        ANALISTA DE {deporte.upper()} EXPERTO - DECISIÓN FINAL
        
        PARTIDO: {resumen_contexto['partido']}
        ESTADIO: {resumen_contexto['estadio']}
        LÍNEA O/U: {resumen_contexto['linea_ou']}
        DÍA: {resumen_contexto['dia']}
        
        DATOS DEL MODELO:
        - Pick Moneyline: {resumen_contexto['pick_ml']} (Confianza: {resumen_contexto['confianza_ml']}%)
        - Diferencia de Win%: {resumen_contexto['diff']:.1f}%
        - ¿Es equipo trampa?: {'SÍ ⚠️' if resumen_contexto['pick_en_trampa'] else 'No'}
        - ¿Zona trampa (10-15%)?: {'SÍ ⚠️' if resumen_contexto['zona_trampa'] else 'No'}
        
        FACTORES EXTERNOS:
        - Factor día O/U: {resumen_contexto['factor_dia_ou']}x
        - Clima: {resumen_contexto['clima']}
        - {resumen_contexto['hr_info']}
        - Probabilidad HR Visitante: {resumen_contexto['away_team_hr_prob']:.1f}%
        - Probabilidad HR Local: {resumen_contexto['home_team_hr_prob']:.1f}%
        - Lesiones/Ausencias: {', '.join(resumen_contexto['lesiones'] + resumen_contexto['ausencias'])}
        - Cambios de Alineación: {', '.join(resumen_contexto['cambios_alineacion'])}
        
        TAREA:
        1. Evalúa si el Moneyline es confiable o hay que buscar alternativa
        2. Si el equipo es trampa o está en zona trampa, recomienda EVITAR
        3. Si el O/U tiene valor (factor día + clima), recomienda OVER/UNDER
        4. Si hay candidato HR fuerte (>40%) y pitcher vulnerable, recomienda HR
        5. Da tu recomendación final en JSON:
        
        {{"tipo_apuesta": "MONEYLINE|HANDICAP|OVER/UNDER|HOME_RUN|EVITAR",
          "pick": "...",
          "confianza": 0-100,
          "stake": "1u|2u|3u|0u",
          "razon": "explica en una frase por qué esta es la mejor opción"}}
        """
        try:
            # Usar el resumen_contexto para el prompt, pero pasar partido_original y resultado_heuristico
            # para que el cerebro_gemini_pro pueda construir el prompt específico del deporte, incluyendo el resumen.
            respuesta_json_str = self.gemini.orquestrar_decision_final(deporte, partido_original, resultado_heuristico, resumen_contexto)
            return json.loads(respuesta_json_str)
        except Exception as e:
            logger.error(f"Error en _analizar_con_gemini: {e}")
            return {"error": f"Gemini falló: {e}"}

    def _analizar_con_groq(self, deporte, partido_original, resultado_heuristico, resumen_contexto):
        """Análisis rápido con Groq (especialmente para UFC)"""
        if deporte == "UFC":
            # Para UFC, Groq tiene un motor especializado
            p1_data = partido_original.get('peleador1', {})
            p2_data = partido_original.get('peleador2', {})
            
            # Aquí necesitarías extraer todos los parámetros que GroqUFCEngine.analyze_fight espera
            # Esto es un ejemplo simplificado, deberías pasar los datos reales de s1 y s2
            groq_result, _ = self.groq.analyze_fight(
                p1_data.get('nombre', ''), p1_data.get('record', ''), p1_data.get('ko_rate', 0), p1_data.get('sub_rate', 0), p1_data.get('altura', 0), p1_data.get('alcance', 0),
                p2_data.get('nombre', ''), p2_data.get('record', ''), p2_data.get('ko_rate', 0), p2_data.get('sub_rate', 0), p2_data.get('altura', 0), p2_data.get('alcance', 0),
                odds_p1=p1_data.get('odds', 'N/A'), odds_p2=p2_data.get('odds', 'N/A')
            )
            if groq_result:
                return {
                    "pick": groq_result.get('winner'),
                    "confianza": groq_result.get('confidence'),
                    "stake": "3u" if groq_result.get('confidence', 0) >= 70 else "2u",
                    "razon": groq_result.get('reason'),
                    "mercado": "MONEYLINE"
                }
            return {"error": "Groq UFC falló"}
        else:
            # Para otros deportes, usar un prompt general si Groq no tiene un motor específico
            try:
                if hasattr(self.groq, 'orquestrar_decision_final'):
                    respuesta_json_str = self.groq.orquestrar_decision_final(deporte, partido_original, resultado_heuristico, resumen_contexto)
                    return json.loads(respuesta_json_str)
                else:
                    return {"error": "Groq no tiene implementado orquestrar_decision_final para este deporte"}
            except Exception as e:
                logger.error(f"Error en _analizar_con_groq: {e}")
                return {"error": f"Groq falló: {e}"}

    def _analizar_con_deepseek(self, deporte, partido_original, resultado_heuristico, resumen_contexto):
        """Análisis con DeepSeek"""
        # Prompt optimizado para DeepSeek R1 (Reasoner) para forzar razonamiento en cadena
        thinking_prompt = f"""
        [SYSTEM: DEEPSEEK R1 STRATEGIC REASONING]
        Analiza el valor de apuesta para {deporte}. 
        Datos: {resumen_contexto['partido']}
        Heurística: {resumen_contexto['pick_ml']} ({resumen_contexto['confianza_ml']}%)
        Factores: Clima {resumen_contexto['clima']}, Lesiones {resumen_contexto['lesiones']}
        
        INSTRUCCIONES:
        1. Contrasta la probabilidad heurística con los factores externos.
        2. Si el clima o las bajas afectan la tendencia, ajusta el pick.
        3. Devuelve tu decisión final en formato JSON.
        
        {{
          "tipo_apuesta": "MONEYLINE|HANDICAP|OVER/UNDER|HOME_RUN|EVITAR",
          "pick": "...",
          "confianza": 0-100,
          "stake": "1u|2u|3u",
          "razon": "Explicación lógica breve"
        }}
        """
        try:
            # Usamos orquestrar_decision_final pero pasando el prompt de razonamiento si es R1
            # Si tu clase CerebroDeepSeek ya maneja esto, asegúrate de que el modelo sea 'deepseek-reasoner'
            respuesta_json_str = self.deepseek.orquestrar_decision_final(deporte, partido_original, resultado_heuristico, thinking_prompt)
            return json.loads(respuesta_json_str)
        except Exception as e:
            logger.error(f"Error en _analizar_con_deepseek: {e}")
            return {"error": f"DeepSeek falló: {e}"}

    def _analizar_con_new_ai(self, deporte, partido_original, resultado_heuristico, resumen_contexto):
        """Análisis con el nuevo modelo de IA"""
        try:
            respuesta_json_str = self.new_ai.orquestrar_decision_final(deporte, partido_original, resultado_heuristico)
            return json.loads(respuesta_json_str)
        except Exception as e:
            logger.error(f"Error en _analizar_con_new_ai: {e}")
            return {"error": f"NewAI falló: {e}"}

    def _sistema_de_votacion(self, ia_results, resultado_heuristico):
        """Implementa un sistema de votación para el pick final"""
        picks = []
        confianzas = []
        razones = []

        for res in ia_results:
            if isinstance(res, dict) and "pick" in res and "confianza" in res:
                picks.append(res["pick"])
                confianzas.append(res["confianza"])
                razones.append(res.get("razon", ""))
        
        if not picks:
            logger.warning("No se obtuvieron picks de las IAs para la votación.")
            return resultado_heuristico

        # Votación simple: el pick más frecuente
        pick_final_list = Counter(picks).most_common(1)
        pick_final = pick_final_list[0][0] if pick_final_list else resultado_heuristico.get("pick", "N/A")
        
        # Confianza promedio de los picks que votaron por el pick_final
        avg_conf = np.mean([c for p, c in zip(picks, confianzas) if p == pick_final]) if picks else 0
        # Razón: combinar las razones o tomar la más relevante
        razon_final = f"Consenso IA: {pick_final}. Razones: {'; '.join(set(razones))}"
        
        # Determinar stake basado en la confianza final
        stake = "0u" # Confianza < 55%
        if avg_conf >= 75: stake = "3u" # PICK ÉLITE
        elif avg_conf >= 65: stake = "2u"
        elif avg_conf >= 55: stake = "1u"

        return {
            "recomendacion": pick_final,
            "confianza": int(round(avg_conf, 0)), # Redondear a entero
            "pick": pick_final,
            "decision": "APOSTAR", # O "VOTACION"
            "tipo_apuesta": "MONEYLINE", # Esto podría ser más dinámico
            "handicap": None,
            "stake": stake,
            "razon": razon_final,
            "fuente_ia": "Votación IA"
        }
    
    def _decision_por_reglas(self, resumen):
        """Decisión por reglas basadas en todo el contexto"""
        pick = resumen['pick_ml']
        diff = resumen['diff']
        conf = resumen['confianza_ml']
        away_hr_prob = resumen['away_team_hr_prob']
        home_hr_prob = resumen['home_team_hr_prob']
        clima_info = resumen['clima']
        ou_line = resumen['linea_ou']
        
        # Regla 1: Equipo trampa → EVITAR
        if resumen['pick_en_trampa']:
            logger.info(f"Regla 1 activada: {pick} es equipo trampa.")
            return {
                "tipo_apuesta": "EVITAR",
                "pick": "N/A",
                "confianza": 0,
                "stake": "0u",
                "razon": f"⚠️ {pick} es equipo trampa esta semana"
            }
        
        # Regla 2: Zona trampa → EVITAR
        if resumen['zona_trampa'] and conf < 55: # Solo si la confianza heurística es baja
            logger.info(f"Regla 2 activada: {pick} en zona trampa con baja confianza heurística.")
            return {
                "tipo_apuesta": "EVITAR",
                "pick": "N/A",
                "confianza": 0,
                "stake": "0u",
                "razon": f"⚠️ Diff {diff:.1f}% en zona trampa (10-15%)"
            }
        
        # Aplicar Regla 16: Correlación HR -> O/U -> ML
        adjusted_conf = conf
        adjusted_ou_pick = None
        
        # Si HR% > 50% en un equipo -> OVER +0.5 carreras y Moneyline +5%
        if away_hr_prob > 0.50 or home_hr_prob > 0.50:
            logger.info(f"Regla 16 activada: Alta probabilidad de HR ({away_hr_prob*100:.1f}% / {home_hr_prob*100:.1f}%).")
            adjusted_conf += 5 # Aumentar confianza del Moneyline
            # Asumiendo que el pick heurístico ya tiene un O/U, lo forzamos a OVER
            adjusted_ou_pick = f"OVER {ou_line + 0.5}" if isinstance(ou_line, (int, float)) else "OVER"
            
        # Si ambos equipos tienen HR% > 45% -> OVER forzoso
        if away_hr_prob > 0.45 and home_hr_prob > 0.45:
            logger.info(f"Regla 16 activada: Ambos equipos con alta probabilidad de HR ({away_hr_prob*100:.1f}% / {home_hr_prob*100:.1f}%). Forzando OVER.")
            adjusted_ou_pick = f"OVER {ou_line}" if isinstance(ou_line, (int, float)) else "OVER"
            
        # Si HR% > 60% -> Aumentar confianza del Moneyline +10%
        if away_hr_prob > 0.60 or home_hr_prob > 0.60:
            logger.info(f"Regla 16 activada: Probabilidad de HR muy alta ({away_hr_prob*100:.1f}% / {home_hr_prob*100:.1f}%). Aumentando confianza ML.")
            adjusted_conf += 10

        # Aplicar Regla 12: Factores Climáticos y de Estadio (simplificado para _decision_por_reglas)
        # Esto es una simplificación; la IA debería hacer un análisis más profundo
        if "lluvia" in clima_info.lower() or "viento fuerte" in clima_info.lower():
            logger.info(f"Regla 12 activada: Clima extremo detectado ({clima_info}).")
            # Clima extremo favorece a equipos con mejor bullpen o pitchers terrestres (no podemos determinar aquí)
            # Podríamos reducir la confianza si el pick es muy dependiente del bateo
            if "Out" in clima_info and (away_hr_prob > 0.4 or home_hr_prob > 0.4): # Viento hacia afuera y HR prob alta
                logger.info("Regla 12: Viento hacia afuera con alta prob HR. Ajustando O/U a OVER.")
                adjusted_ou_pick = f"OVER {ou_line + 0.5}" if isinstance(ou_line, (int, float)) else "OVER"
            elif "In" in clima_info: # Viento hacia adentro
                logger.info("Regla 12: Viento hacia adentro. Ajustando O/U a UNDER.")
                adjusted_ou_pick = f"UNDER {ou_line - 0.5}" if isinstance(ou_line, (int, float)) else "UNDER"

        # Asegurar que la confianza ajustada no exceda 100
        adjusted_conf = min(100, adjusted_conf)

        # Determinar stake basado en la confianza ajustada (Regla 15)
        stake = "0u" # Confianza < 55%
        if adjusted_conf >= 75: stake = "3u" # PICK ÉLITE
        elif adjusted_conf >= 65: stake = "2u"
        elif adjusted_conf >= 55: stake = "1u"

        # Regla 3: Diff alto + confianza alta → MONEYLINE (usando confianza ajustada)
        if diff >= 15 and adjusted_conf >= 55:
            logger.info(f"Regla 3 activada: Diff alto ({diff:.1f}%) con buena confianza ({adjusted_conf}%).")
            return {
                "tipo_apuesta": "MONEYLINE",
                "pick": pick,
                "confianza": int(round(adjusted_conf, 0)),
                "stake": stake,
                "razon": f"Diff alto ({diff:.1f}%) con buena confianza. {('HR correlación aplicada.' if adjusted_conf > conf else '')}"
            }
        
        # Regla 4: Factor día O/U favorable → OVER/UNDER
        factor_dia = resumen['factor_dia_ou']
        if factor_dia > 1.05 or adjusted_ou_pick: # Priorizar si hay un pick O/U ajustado por HR/Clima
            logger.info(f"Regla 4 activada: Factor día O/U favorable ({factor_dia}x) o pick O/U ajustado.")
            return {
                "tipo_apuesta": "OVER/UNDER",
                "pick": adjusted_ou_pick if adjusted_ou_pick else f"OVER {resumen['linea_ou']}",
                "confianza": int(round(min(100, 65 + (factor_dia - 1.05)*100), 0)), # Ajustar confianza por factor
                "stake": "2u", # Asumiendo que un factor favorable ya da 2u
                "razon": f"Factor día favorable ({resumen['dia']}: {factor_dia}x). {('Correlación HR/Clima aplicada.' if adjusted_ou_pick else '')}"
            }
        
        # Regla 5: RESCATE con +3.5
        if diff >= 2:
            logger.info(f"Regla 5 activada: Diff suficiente para rescate ({diff:.1f}%).")
            return {
                "tipo_apuesta": "HANDICAP",
                "pick": f"{pick} +3.5",
                "confianza": int(round(min(100, adjusted_conf + 5), 0)),
                "stake": stake, # Usar el stake ajustado
                "razon": "Handicap +3.5 para más protección"
            }
        
        # Regla 6: Nada confiable → EVITAR
        logger.info("Regla 6 activada: Ninguna regla de apuesta se cumplió. Evitando pick.")
        return {
            "tipo_apuesta": "EVITAR",
            "pick": "N/A",
            "confianza": 0,
            "stake": "0u",
            "razon": "Confianza insuficiente en todas las opciones"
        }

# Prueba
if __name__ == "__main__":
    # Configurar un logger para la prueba
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    partido = {"visitante": "NYY", "local": "BOS", "venue": "Fenway", "odds": {"over_under": 8.5}}
    resultado = {"pick": "NYY", "confianza": 65, "diff": 12}
    candidatos = [{"nombre": "Judge", "probabilidad": 40}]
    
    decision = at.analizar_partido_completo(partido, resultado, candidatos)
    print(json.dumps(decision, indent=2, ensure_ascii=False))
