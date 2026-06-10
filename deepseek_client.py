# deepseek_client.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class DeepSeekClient:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            print("❌ Error: DEEPSEEK_API_KEY no encontrada en el entorno (.env).")
            self.client = None
            return
        
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com/v1"
            )
            # Muestra los últimos 4 dígitos para corroborar cuál se está cargando
            last_digits = self.api_key[-4:] if len(self.api_key) > 4 else "????"
            print(f"✅ Cliente DeepSeek configurado (Key: ****{last_digits})")
        except Exception as e:
            print(f"❌ Error al inicializar cliente DeepSeek: {e}")
            self.client = None
    
    def chat(self, prompt, system=""):
        if not self.client:
            return "DeepSeek no disponible"
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            if "401" in str(e):
                return f"❌ Error 401: La API Key es inválida o ha expirado. Verifica tu cuenta en DeepSeek."
            return f"❌ Error en la comunicación con DeepSeek: {e}"
    
    def analizar_mlb(self, partido):
        prompt = f"""
        Analiza este partido de MLB para apuestas:
        Local: {partido.get('local', '?')}
        Visitante: {partido.get('visitante', '?')}
        Pitcher Local: {partido.get('pitcher_local', 'TBD')}
        Pitcher Visitante: {partido.get('pitcher_visitante', 'TBD')}
        
        Responde en JSON:
        - pick: equipo recomendado
        - confianza: 0-100
        - razon: explicación breve
        """
        return self.chat(prompt, system="Eres un analista de MLB experto en apuestas. Responde SOLO en formato JSON.")

deepseek = DeepSeekClient()

if __name__ == "__main__":
    if deepseek.client:
        respuesta = deepseek.chat("Responde solo OK si funcionas")
        print(f"Respuesta: {respuesta}")
