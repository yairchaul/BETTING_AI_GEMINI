# -*- coding: utf-8 -*-

def obtener_factor_altitud(ciudad):
    """
    Retorna un multiplicador de fatiga basado en la altitud de la ciudad.
    Ciudades con > 1000m afectan significativamente el cardio.
    """
    ciudades_altas = {
        "Mexico City": 2240,
        "Denver": 1609,
        "Salt Lake City": 1288,
        "Albuquerque": 1619,
        "Bogota": 2640,
        "Quito": 2850
    }
    
    altitud = ciudades_altas.get(ciudad, 0)
    if altitud > 2000:
        return 1.25  # Impacto crítico
    elif altitud > 1000:
        return 1.15  # Impacto alto
    return 1.0