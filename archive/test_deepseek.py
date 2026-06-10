# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

key = os.getenv("DEEPSEEK_API_KEY")
print(f"🔍 Diagnosticando API Key de DeepSeek...")
print(f"🔑 Key cargada del .env termina en: ****{key[-4:] if key else 'NO ENCONTRADA'}")

if not key:
    print("❌ ERROR: No se encontró la variable DEEPSEEK_API_KEY en el archivo .env")
else:
    client = OpenAI(api_key=key, base_url="https://api.deepseek.com/v1")
    try:
        print("📡 Enviando solicitud de prueba a DeepSeek...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Responde solo OK"}],
            max_tokens=5
        )
        print(f"✅ ¡ÉXITO! La llave es válida. Respuesta: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ FALLO DE AUTENTICACIÓN: {e}")