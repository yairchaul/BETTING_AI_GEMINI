# Reglas de Integridad de Datos Dinámicos

## 1. Validación MLB
- Prohibido realizar análisis de K (Ponches) si el valor de `k9` es 0. 
- En caso de detectar `TBD` en lanzadores, Gemini debe sugerir "Esperar Lineups Oficiales".

## 2. Validación UFC
- El análisis debe cruzar obligatoriamente `SLpM` y `Reach`. 
- Si los datos de `ufc_stats_cache.json` tienen más de 7 días, disparar alerta de actualización.

## 3. Automatización (Hooks)
- Al detectar un cambio en `resultados_finales_corregidos.json`, se debe re-ejecutar `motor_decision_inteligente.py`.
- Cada pick generado debe tener un ID único vinculado a la tabla `backtesting`.