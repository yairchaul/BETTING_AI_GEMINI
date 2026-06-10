# Spec: mantenimiento-sistema

## Descripción
Optimización de la base de datos SQLite y purga de archivos de registro (logs) antiguos para prevenir degradación de rendimiento y saturación de almacenamiento.

## Disparador
Schedule: `0 3 1 * *` (El primer día de cada mes a las 3:00 AM)

## Pre-requisitos
- Acceso de escritura a la carpeta `C:\Users\Yair\Desktop\BETTING_AI\data\`.
- Acceso de escritura a la carpeta `C:\Users\Yair\Desktop\BETTING_AI\logs\`.

## Pasos
1. **DB Vacuum**: Ejecutar comando `VACUUM` en `betting_stats.db` para reconstruir el archivo de base de datos y liberar espacio.
2. **DB Indexing**: Re-indexar tablas principales (`backtesting`, `predicciones`) para optimizar consultas de búsqueda.
3. **Purga de Datos**: Eliminar registros de la tabla `backtesting` con antigüedad superior a 180 días.
4. **Limpieza de Logs**: Eliminar archivos dentro de `C:\Users\Yair\Desktop\BETTING_AI\logs\` que tengan más de 30 días de antigüedad.
5. **Rotación**: Renombrar `error.log` actual a `error.log.old` y crear uno nuevo vacío.

## Post-condiciones
- Tamaño del archivo `.db` reducido.
- Logs antiguos eliminados.
- Registro de mantenimiento exitoso en `system.log`.

## Manejo de errores
- Si la base de datos está bloqueada (Locked), reintentar 3 veces con intervalos de 5 minutos.
- Si falla la purga de archivos, notificar a través del hook `on-error`.