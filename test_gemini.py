import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key: {api_key[:15] if api_key else 'NO'}...")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content("Responde solo OK")
        print(f"✅ Gemini funcionando: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ No se encontró API Key en .env")
