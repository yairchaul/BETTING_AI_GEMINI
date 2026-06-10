# Hook: on-backtest-complete

## Evento
Finalización exitosa de la Spec `backtest-semanal`.

## Acción
1. Leer el archivo `C:\Users\Yair\Desktop\BETTING_AI\data\aprendizaje_semanal.json`.
2. Generar un resumen ejecutivo del Win Rate global y Profit.
3. Enviar notificación al canal de chat de Kiro con el mensaje: "📊 Auditoría Semanal Completada. Win Rate: {{wr_reciente}}%. Profit: {{profit}}u".

## Condiciones
Solo se ejecuta si el archivo de aprendizaje fue modificado en los últimos 5 minutos.

## Output
Mensaje de sistema en el panel de control.