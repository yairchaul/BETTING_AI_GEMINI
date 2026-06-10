# Hook: on-data-update

## Evento
Modificación del archivo `C:\Users\Yair\Desktop\BETTING_AI\data\scraper_results.json`.

## Acción
Disparar automáticamente la ejecución de la Spec `analizar-jornada-completa`.

## Condiciones
Solo si el tamaño del archivo es mayor a 10KB (evita disparos por archivos corruptos o vacíos).

## Output
Inicio de análisis en tiempo real.