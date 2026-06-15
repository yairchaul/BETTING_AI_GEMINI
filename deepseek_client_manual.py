# deepseek_client_manual.py
from openai import OpenAI

DEEPSEEK_API_KEY = "***REMOVED_SECRET***"

class DeepSeekClient:
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            print("❌ DEEPSEEK_API_KEY no encontrada")
            self.client = None
            return
        
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1"
        )
        print("✅ DeepSeek cliente listo")
    
    def chat(self, prompt):
        if not self.client:
            return "DeepSeek no disponible"
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

deepseek = DeepSeekClient()

if __name__ == "__main__":
    if deepseek.client:
        respuesta = deepseek.chat("Responde solo OK si funcionas")
        print(f"Respuesta: {respuesta}")
