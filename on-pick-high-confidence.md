# Hook: on-pick-high-confidence

## Evento
Generación de una nueva entrada en `predicciones_log.json`.

## Acción
Si `confianza` > 75, enviar el pick a la tabla de `BACKTESTING_ELITE` en la DB y disparar alerta sonora/visual en el dashboard.

## Condiciones
`pick.confianza >= 75` AND `pick.estado == 'PENDIENTE'`.

## Output
Marcado de pick como ÉLITE en la interfaz de usuario.