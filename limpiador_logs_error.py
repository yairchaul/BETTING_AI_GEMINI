# -*- coding: utf-8 -*-
import os
import sys

# Forzar salida UTF-8 para evitar fallos al imprimir en consola Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def limpiar_archivos_log():
    log_dir = r"C:\Users\Yair\Desktop\BETTING_AI\logs"
    if not os.path.exists(log_dir):
        return

    print("🧹 Limpiando errores de codificación en archivos de log...")
    for archivo in os.listdir(log_dir):
        if archivo.endswith(".log") or archivo.endswith(".txt"):
            ruta = os.path.join(log_dir, archivo)
            try:
                # Leer como binario para evitar errores de decodificación iniciales
                with open(ruta, 'rb') as f:
                    contenido_binario = f.read()
                
                # Decodificar ignorando caracteres corruptos y re-codificar en UTF-8 puro
                contenido_limpio = contenido_binario.decode('utf-8', errors='ignore')
                
                with open(ruta, 'w', encoding='utf-8') as f:
                    f.write(contenido_limpio)
                print(f"✅ Log saneado: {archivo}")
            except Exception as e:
                print(f"⚠️ No se pudo procesar {archivo}: {e}")

if __name__ == "__main__":
    limpiar_archivos_log()