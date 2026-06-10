# -*- coding: utf-8 -*-
"""
Handler para el Hook on-error
Registra fallos y notifica al usuario.
"""
import os
import logging
from datetime import datetime
import traceback

# Configuración de rutas absolutas (Regla 24)
BASE_DIR = r"c:\Users\Yair\Desktop\BETTING_AI"
LOG_FILE = os.path.join(BASE_DIR, "logs", "error.log")

# Asegurar que la carpeta logs existe
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def init_error_log():
    """Verifica si el archivo de log existe y lo crea si no."""
    if not os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] [ErrorHandler]: Archivo de log de errores inicializado.\n")
        except Exception as e:
            print(f"Fallo crítico al inicializar el archivo de log: {e}")
def registrar_error(modulo_nombre, error_msg, exception=None):
    """Registra el error en el log y simula notificación de chat."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Formatear el traceback si existe
    tb = ""
    if exception:
        tb = "\n" + "".join(traceback.format_exception(None, exception, exception.__traceback__))

    log_entry = f"[{timestamp}] [ERROR] [{modulo_nombre}]: {error_msg}{tb}\n"
    log_entry += "-"*50 + "\n"

    # Escritura en UTF-8 puro (Regla 1)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Fallo crítico al escribir en log: {e}")

    # Simulación de notificación de Chat (Regla 20)
    print("\n" + "!"*30)
    print(f"🚨 ALERTA DE SISTEMA: Fallo en {modulo_nombre}")
    print(f"Mensaje: {error_msg}")
    print("Notificación enviada al Dashboard de Kiro")
    print("!"*30 + "\n")

if __name__ == "__main__":
    # Prueba de error
    init_error_log() # Asegurarse de que el log exista para la prueba
    try:
        x = 1 / 0
    except Exception as e:
        registrar_error("ScriptPrueba", "Error de división por cero", e)