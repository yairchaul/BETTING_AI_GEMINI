# Hook: on-error

## Evento
Excepción detectada en cualquier script `.py` del proyecto.

## Acción
1. Capturar el traceback del error.
2. Escribir en `C:\Users\Yair\Desktop\BETTING_AI\logs\error.log` con timestamp.
3. Notificar al usuario: "🚨 Error detectado en el módulo {{module_name}}. Revisa los logs inmediatamente."

## Condiciones
Ejecución inmediata ante cualquier salida de error (stderr).

## Output
Registro en log y alerta visual.