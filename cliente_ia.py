# cliente_ia.py
import requests
import json

# Configuración
GROQ_API_KEY = "***REMOVED_SECRET***"
DEEPSEEK_API_KEY = "***REMOVED_SECRET***"

def chat_groq(mensaje):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": mensaje}], "temperature": 0.3}
    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

def chat_deepseek(mensaje):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": mensaje}], "temperature": 0.3}
    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

if __name__ == "__main__":
    print("Probando Groq:", chat_groq("Responde OK"))
    print("Probando DeepSeek:", chat_deepseek("Responde OK"))
