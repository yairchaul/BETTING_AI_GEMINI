# -*- coding: utf-8 -*-
import pandas as pd
import json
import os

def auditar_bitacora():
    """Cruza la bitácora maestra con los resultados reales de los últimos 15 días."""
    bitacora_path = "data/bitacora_maestra.csv"
    resultados_path = "data/resultados_reales_15dias.json"
    
    if not os.path.exists(bitacora_path) or not os.path.exists(resultados_path):
        return

    df = pd.read_csv(bitacora_path)
    with open(resultados_path, "r", encoding="utf-8") as f:
        reales = json.load(f)

    def verificar_acierto(row):
        if str(row['Resultado_Real']).lower() != 'pendiente':
            return row['acierto']
            
        # Buscar partido en resultados reales (MLB)
        for r in reales:
            if row['Evento'] == f"{r['visitante']} vs {r['local']}":
                ganador_real = r['ganador']
                # Comparación flexible para el pick (evita errores por nombres largos)
                apuesta_str = str(row['Apuesta']).lower()
                ganador_str = str(ganador_real).lower()
                acierto = ganador_str in apuesta_str or apuesta_str in ganador_str
                return acierto
        return row['acierto']

    df['acierto'] = df.apply(verificar_acierto, axis=1)
    # Actualizar estado de pendiente a resultado real
    df.loc[df['Resultado_Real'].astype(str).str.lower() == 'pendiente', 'Resultado_Real'] = "Procesado"
    
    df.to_csv(bitacora_path, index=False)
    print("✅ Bitácora Maestra auditada automáticamente.")

if __name__ == "__main__":
    auditar_bitacora()