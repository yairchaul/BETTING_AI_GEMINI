# Reglas de Inferencia Dinámica

## 1. Clima y Proyecciones
- La función `calcular_total` en `motor_over_under.py` TIENE la obligación de llamar a `ClimaMLB.obtener_clima`.
- Si `wind_speed > 12` y `wind_dir == "Out"`, la confianza del OVER sube un 15%.

## 2. Decisión de Handicap vs Moneyline
- Si la confianza del Moneyline es < 65% pero > 55%, Kiro debe sugerir siempre un Handicap de +1.5 para proteger el capital.
- En partidos contra equipos de la lista `EQUIPOS_TRAMPA`, NUNCA sugieras Moneyline, usa siempre Handicap progresivo (+2.5 o +3.5).