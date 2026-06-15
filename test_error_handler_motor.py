# -*- coding: utf-8 -*-
"""
Script de prueba para validar el Error Handler en motores.
Cumple con la Regla 24: Rutas compatibles con Windows.
"""
import os
import sys

# Asegurar que la raíz del proyecto esté en el path para las importaciones
BASE_DIR = r"C:\Users\Yair\Desktop\BETTING_AI"
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from utils.error_handler import registrar_error

def motor_simulado_fallido():
    """Simula una función de un motor que falla inesperadamente."""
    print("🚀 Iniciando motor simulado para prueba de error...")
    try:
        # Forzar un error manual
        resultado = 10 / 0
    except Exception as e:
        # Llamar al handler centralizado
        registrar_error("MotorPruebaSimulada", "Error crítico provocado en cálculo matemático", e)
        print("✅ registrar_error ejecutado satisfactoriamente.")

if __name__ == "__main__":
    motor_simulado_fallido()
    
    # Verificación física del log
    log_path = os.path.join(BASE_DIR, "logs", "error.log")
    if os.path.exists(log_path):
        print(f"📄 Verificando registro en: {log_path}")
        with open(log_path, "r", encoding="utf-8") as f:
            contenido = f.read()
            if "MotorPruebaSimulada" in contenido:
                print("⭐ PRUEBA EXITOSA: El error fue capturado y registrado correctamente en el log.")
            else:
                print("❌ PRUEBA FALLIDA: El error no se encuentra en el archivo de log.")