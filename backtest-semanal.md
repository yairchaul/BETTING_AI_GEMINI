# Spec: backtest-semanal

## Descripción
Ejecuta el proceso de auditoría automática de los picks generados durante la semana, cruza con resultados reales y actualiza el motor de aprendizaje.

## Disparador
Schedule: `0 0 * * 0` (Todos los domingos a medianoche)

## Pre-requisitos
- Archivo `C:\Users\Yair\Desktop\BETTING_AI\data\predicciones_log.json` debe existir.
- Conexión activa a internet para consulta de MLB API.

## Pasos
1. **Recolección**: Leer `predicciones_log.json` filtrando registros de los últimos 7 días.
2. **Sincronización**: Consultar resultados oficiales mediante `C:\Users\Yair\Desktop\BETTING_AI\scrapers\espn_mlb.py` (modo histórico).
3. **Cálculo**: Ejecutar script de auditoría para obtener ROI y efectividad por tramos de confianza.
4. **Detección**: Identificar equipos con racha de fallos >= 3 para marcarlos como "Equipos Trampa".
5. **Reporte**: Generar `C:\Users\Yair\Desktop\BETTING_AI\data\backtest_semanal.md` con tablas de rendimiento.
6. **Persistencia**: Actualizar `C:\Users\Yair\Desktop\BETTING_AI\data\aprendizaje_semanal.json` con los nuevos pesos y equipos trampa detectados.

## Post-condiciones
- `data/aprendizaje_semanal.json` actualizado.
- Notificación de resumen enviada a través de `on-backtest-complete`.

## Manejo de errores
- Si falla la API de resultados, reintentar en 1 hora.
- Si el log está vacío, abortar y registrar "Sin datos para auditar" en `logs/system.log`.