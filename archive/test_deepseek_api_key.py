# -*- coding: utf-8 -*-
"""
Script para verificar la funcionalidad de la API Key de DeepSeek cargada desde .env.
"""
import os
from dotenv import load_dotenv
from update_env import validar_key_deepseek # Importa la función de validación existente

# Carga las variables de entorno del archivo .env
load_dotenv()

def test_deepseek_key_from_env():
    """
    Obtiene la API Key de DeepSeek del archivo .env y la valida.
    """
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

    if not deepseek_api_key:
        print("❌ DEEPSEEK_API_KEY no encontrada en el archivo .env.")
        print("Asegúrate de que tu archivo .env contenga una línea como: DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        return False

    print(f"\n--- Probando la API Key de DeepSeek cargada del .env (últimos 4 dígitos: ****{deepseek_api_key[-4:]}) ---")
    return validar_key_deepseek(deepseek_api_key)

if __name__ == "__main__":
    test_deepseek_key_from_env()