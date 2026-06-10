import json
import asyncio
import sys
import requests
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Leer el comando de Continue
    stdin = sys.stdin.read()
    try:
        request = json.loads(stdin)
    except:
        print(json.dumps({"error": "Entrada JSON no válida"}))
        return

    tool_name = request.get("params", {}).get("name", "")

    if tool_name == "chat_groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print(json.dumps({"error": "GROQ_API_KEY no encontrada en .env"}))
            return
        prompt = request["params"]["arguments"]["prompt"]
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}
        )
        result = response.json()["choices"][0]["message"]["content"]
        print(json.dumps({"result": result}))

    elif tool_name == "chat_deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print(json.dumps({"error": "DEEPSEEK_API_KEY no encontrada en .env"}))
            return
        prompt = request["params"]["arguments"]["prompt"]
        
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]},
                timeout=30
            )
            data = response.json()
            if "choices" in data:
                result = data["choices"][0]["message"]["content"]
                print(json.dumps({"result": result}))
            else:
                print(json.dumps({"error": f"API Error: {data.get('error', data)}"}))
        except Exception as e:
            print(json.dumps({"error": f"Excepción en servidor: {str(e)}"}))

    else:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))

if __name__ == "__main__":
    asyncio.run(main())
