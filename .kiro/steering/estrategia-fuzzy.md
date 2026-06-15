# Protocolo de Resolución de Nombres

## 1. Prioridad de Mapeo
- Siempre intentar coincidencia exacta primero.
- Si falla, usar `fuzz.WRatio` con un umbral de 85%.
- Si el score es entre 70% y 84%, marcar el dato como "Sujeto a revisión" en el Dashboard.

## 2. Casos Especiales
- Nombres con "Jr", "Sr" o acentos deben ser normalizados eliminando dichos caracteres antes del proceso de RapidFuzz.
- En MLB, si el nombre del lanzador no coincide, intentar buscar por `Abreviatura_Equipo + Dorsal` si está disponible.