# -*- coding: utf-8 -*-
import os
import httpx
import asyncio
from dotenv import load_dotenv

async def verificar_deepseek():
    load_dotenv(override=True)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ ERROR: No se encontró DEEPSEEK_API_KEY en el archivo .env")
        return

    print(f"🔍 Probando conexión con DeepSeek (Key: ****{api_key[-4:]})...")
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Responde solo con la palabra: FUNCIONANDO"}],
        "max_tokens": 10
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=20.0)
            
            if response.status_code == 200:
                print(f"✅ ¡ÉXITO! La API responde: {response.json()['choices'][0]['message']['content']}")
            elif response.status_code == 402:
                print("❌ ERROR [402]: Tu cuenta no tiene saldo suficiente. Recarga en platform.deepseek.com")
            else:
                print(f"❌ ERROR HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ EXCEPCIÓN: No se pudo conectar. Verifica tu internet o la URL. Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(verificar_deepseek())