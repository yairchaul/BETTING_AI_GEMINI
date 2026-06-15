import os

# CONFIGURACIÓN
SALIDA = "CODIGO_COMPLETO_NEON.html"
# Solo carpetas con código real
CARPETAS_OK = ['scrapers', 'analyzers', 'motores', 'visuals', '.'] 
EXTENSIONES_OK = ['.py', '.css', '.html']
IGNORAR = ['__pycache__', '.git', '.venv', 'node_modules', 'data', '_OLD', '_PARA_BORRAR']

html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>NEON CODE VIEWER</title>
    <style>
        body {{ background: #0e1117; color: #00ff41; font-family: monospace; padding: 20px; }}
        .file-box {{ border: 1px solid #00ff41; margin-bottom: 30px; border-radius: 8px; overflow: hidden; }}
        .file-name {{ background: #1a1f2a; padding: 10px; font-weight: bold; border-bottom: 1px solid #00ff41; }}
        pre {{ margin: 0; padding: 15px; overflow-x: auto; color: #e6edf3; background: #000; }}
    </style>
</head>
<body>
    <h1>🚀 ESTRUCTURA DE CÓDIGO: BETTING_AI_NEON</h1>
    {contenido}
</body>
</html>
"""

def generar():
    cuerpo = ""
    for root, dirs, files in os.walk("."):
        # Ignorar carpetas basura
        dirs[:] = [d for d in dirs if d not in IGNORAR and not d.startswith('.')]
        
        for file in files:
            if any(file.endswith(ext) for ext in EXTENSIONES_OK):
                ruta = os.path.join(root, file)
                try:
                    with open(ruta, 'r', encoding='utf-8') as f:
                        codigo = f.read().replace('<', '&lt;').replace('>', '&gt;')
                        cuerpo += f'<div class="file-box"><div class="file-name">{ruta}</div><pre>{codigo}</pre></div>'
                        print(f"Incluido: {ruta}")
                except:
                    continue

    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(html_template.format(contenido=cuerpo))
    print(f"\n✅ LISTO! Archivo creado: {SALIDA}")

if __name__ == "__main__":
    generar()
