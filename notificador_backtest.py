# -*- coding: utf-8 -*-
"""
SCRIPT PARA PROCESAR EL HOOK: on-backtest-complete
Ruta: C:\Users\Yair\Desktop\BETTING_AI\scripts\notificador_backtest.py
"""
import json
import os
import time
from datetime import datetime

# Configuración de rutas
PATH_APRENDIZAJE = r"C:\Users\Yair\Desktop\BETTING_AI\data\aprendizaje_semanal.json"
PATH_CONTEXTO = r"C:\Users\Yair\Desktop\BETTING_AI\data\contexto_backtesting.json"

def verificar_condiciones():
    """Verifica si el archivo fue modificado en los últimos 5 minutos"""
    if not os.path.exists(PATH_APRENDIZAJE):
        return False
    
    mtime = os.path.getmtime(PATH_APRENDIZAJE)
    diff_minutos = (time.time() - mtime) / 60
    return diff_minutos <= 5

def ejecutar_notificacion():
    if not verificar_condiciones():
        print("⏭️ Hook omitido: El archivo no es reciente.")
        return

    try:
        # Leer datos de aprendizaje
        with open(PATH_APRENDIZAJE, "r", encoding="utf-8") as f:
            datos = json.load(f)
        
        wr = datos.get("wr_reciente", 0)
        
        # Intentar obtener profit del contexto de backtesting
        profit = "N/A"
        if os.path.exists(PATH_CONTEXTO):
            with open(PATH_CONTEXTO, "r", encoding="utf-8") as f:
                ctx = json.load(f)
                profit = ctx.get("rendimiento_global", {}).get("profit", "0")

        # Formatear mensaje según especificación del Hook
        mensaje = (
            f"📊 Auditoría Semanal Completada.\n"
            f"🔹 Win Rate: {wr}%\n"
            f"🔹 Profit: {profit}u\n"
            f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        # Simulación de envío al panel de Kiro (Output de sistema)
        print("="*40)
        print("🚀 ENVIANDO NOTIFICACIÓN AL DASHBOARD")
        print(mensaje)
        print("="*40)
        
        return True

    except Exception as e:
        print(f"❌ Error al procesar notificación: {e}")
        return False

if __name__ == "__main__":
    ejecutar_notificacion()