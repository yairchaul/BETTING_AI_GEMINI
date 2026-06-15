# -*- coding: utf-8 -*-
import json
import os
import re
from deepseek_client import deepseek # Assuming deepseek is an instance of DeepSeekClient
from cliente_ia import chat_groq # Import Groq chat function

def ejecutar_analisis_rendimiento():
    print("🚀 Iniciando análisis de rendimiento con DeepSeek R1 (Free)...")
    
    path_backtesting = os.path.join("data", "backtesting_results.json")
    if not os.path.exists(path_backtesting):
        print("❌ No se encontró el archivo de datos. Ejecuta primero la exportación.")
        return

    with open(path_backtesting, "r", encoding="utf-8") as f:
        datos = json.load(f)

    # Prompt para DeepSeek
    deepseek_prompt = f"""
    Analiza estos resultados de apuestas y devuelve un resumen ejecutivo en JSON.
    Datos: {json.dumps(datos[:20], ensure_ascii=False)} 
    
    Formato requerido:
    {{
        "precision_global": "X%",
        "mejor_deporte": "Nombre",
        "peor_deporte": "Nombre",
        "conclusión": "Breve análisis estratégico"
    }}
    """
    
    # Prompt para Groq (incluyendo la persona en el mensaje de usuario)
    groq_fallback_prompt = f"""
    Eres un experto analista estadístico de apuestas.
    Analiza estos resultados de apuestas y devuelve un resumen ejecutivo en JSON.
    Datos: {json.dumps(datos[:20], ensure_ascii=False)}
    
    Formato requerido:
    {{
        "precision_global": "X%",
        "mejor_deporte": "Nombre",
        "peor_deporte": "Nombre",
        "conclusión": "Breve análisis estratégico"
    }}
    """
    
    print("📡 Enviando datos a DeepSeek R1...")
    respuesta = deepseek.chat(deepseek_prompt, system="Eres un experto analista estadístico de apuestas.")
    
    # Manejo de error de saldo o conexión
    if "❌ Error 402" in respuesta: # Específicamente el error de saldo
        print(respuesta)
        print("⚠️ DeepSeek devolvió Error 402 (Saldo Insuficiente). Intentando con Groq como respaldo...")
        print("📡 Enviando datos a Groq (Llama 3)...")
        respuesta = chat_groq(groq_fallback_prompt) # Usar el prompt adaptado para Groq
        if "Error" in respuesta: # Si Groq también falla
            print(f"❌ Groq también falló: {respuesta}")
            return None
    elif "❌ Error" in respuesta: # Otros errores de DeepSeek
        print(respuesta)
        return None

    # Intentar limpiar y guardar
    try:
        # Extraer JSON usando Regex para mayor robustez
        json_match = re.search(r'```json\s*(.*?)\s*```', respuesta, re.DOTALL)
        if json_match:
            respuesta = json_match.group(1)
        else:
            # Si no hay bloques markdown, buscar el primer objeto JSON {...}
            json_match = re.search(r'(\{.*\})', respuesta, re.DOTALL)
            if json_match:
                respuesta = json_match.group(1)
        
        resultado_final = json.loads(respuesta)
        path_output = os.path.join("data", "analisis_ia_rendimiento.json")
        
        with open(path_output, "w", encoding="utf-8") as f:
            json.dump(resultado_final, f, indent=4, ensure_ascii=False)
            
        print(f"✅ Análisis completado y guardado en: {path_output}")
        return resultado_final
    except Exception as e:
        print(f"❌ Error al procesar respuesta: {e}")
        print("Respuesta recibida:", respuesta)
        return None

if __name__ == "__main__":
    ejecutar_analisis_rendimiento()