# -*- coding: utf-8 -*-
import os

class CerebroAnalista:
    def __init__(self, groq_key, gemini_key):
        self.groq_key = groq_key
        self.gemini_key = gemini_key

    def decidir_partido_dudoso(self, equipo, dif, moneyline):
        """
        Si el programa duda (DIF bajo), Groq decide si vale la pena.
        """
        # Prompt para Groq (Llama 3 70B para velocidad)
        prompt = f"Equipo: {equipo}, DIF: {dif}, Cuota: {moneyline}. ¿Es apuesta de valor?"
        
        # Aquí irá la llamada a la API de Groq
        # Si Groq responde que el valor es alto, el programa da LUZ VERDE
        if dif > 1.2: 
            return "LUZ VERDE - Valor detectado por IA"
        return "EVITAR - Riesgo alto"

# La instancia se conectará con tus llaves automáticas
