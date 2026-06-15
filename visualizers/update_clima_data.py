# -*- coding: utf-8 -*-
from utils.clima_mlb import ClimaMLB

print("--- ACTUALIZANDO DATOS DE CLIMA ---")
try:
    clima_engine = ClimaMLB()
    # En una implementación real, aquí se llamarían a los métodos para forzar la actualización.
    print("✅ (Simulación) Motor de clima invocado para actualizar caché.")
except Exception as e:
    print(f"❌ Error al actualizar clima: {e}")