# -*- coding: utf-8 -*-
import os
from openai import OpenAI

def validar_key_deepseek(api_key):
    """Verifica si la API Key es válida haciendo una consulta mínima a DeepSeek."""
    print(f"📡 Validando API Key: ****{api_key[-4:]}...")
    try:
        # DeepSeek es compatible con el cliente de OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        # Realizamos una petición mínima de 1 token para no gastar cuota
        client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1
        )
        print("✅ API Key validada con éxito.")
        return True
    except Exception as e:
        print(f"❌ La validación falló: {e}")
        return False

def actualizar_variable_env(ruta_env, clave, nuevo_valor):
    lineas = []
    encontrada = False
    
    if os.path.exists(ruta_env):
        with open(ruta_env, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
    
    nuevas_lineas = []
    for linea in lineas:
        if linea.strip().startswith(f"{clave}="):
            nuevas_lineas.append(f"{clave}={nuevo_valor}\n")
            encontrada = True
        else:
            nuevas_lineas.append(linea)
            
    if not encontrada:
        nuevas_lineas.append(f"{clave}={nuevo_valor}\n")
        
    with open(ruta_env, 'w', encoding='utf-8') as f:
        f.writelines(nuevas_lineas)

if __name__ == "__main__":
    ruta = r"c:\Users\Yair\Desktop\BETTING_AI\.env"
    nueva_key = "***REMOVED_SECRET***"
    
    # Solo actualizamos si la llave es válida
    if validar_key_deepseek(nueva_key):
        actualizar_variable_env(ruta, "DEEPSEEK_API_KEY", nueva_key)
        print(f"✅ Archivo .env actualizado con éxito en: {ruta}")
    else:
        print("⚠️ No se actualizó el archivo .env porque la llave no es válida.")