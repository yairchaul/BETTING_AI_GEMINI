<#
.SYNOPSIS
    Script de PowerShell para automatizar la ejecución de la Spec 'mantenimiento-sistema'.
    Realiza la optimización de la base de datos SQLite y la purga de logs antiguos.

.DESCRIPTION
    Este script realiza las siguientes tareas:
    1. Ejecuta VACUUM y REINDEX en la base de datos SQLite 'betting_stats.db'.
    2. Elimina registros de la tabla 'backtesting' con más de 180 días de antigüedad.
    3. Elimina archivos de log en la carpeta 'logs' con más de 30 días de antigüedad.
    4. Rota el archivo 'error.log'.
    Registra todas las acciones y errores en 'logs/system.log'.

.NOTES
    Requiere 'sqlite3.exe' en el PATH del sistema o especificar su ruta completa.
    Asegúrate de tener permisos de escritura en las carpetas 'data' y 'logs'.
#>

# --- Configuración de Rutas ---
$BETTING_AI_ROOT = "C:\Users\Yair\Desktop\BETTING_AI"
$DATA_DIR = Join-Path $BETTING_AI_ROOT "data"
$LOGS_DIR = Join-Path $BETTING_AI_ROOT "logs"
$DB_PATH = Join-Path $DATA_DIR "betting_stats.db"
$SYSTEM_LOG = Join-Path $LOGS_DIR "system.log"
$ERROR_LOG = Join-Path $LOGS_DIR "error.log"
$SQLITE_EXE = "sqlite3.exe" # Asegúrate de que sqlite3.exe esté en tu PATH o especifica la ruta completa, e.g., "C:\sqlite\sqlite3.exe"

# --- Funciones de Ayuda ---
function Write-Log {
    Param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $SYSTEM_LOG -Value $LogEntry
    Write-Host $LogEntry
}

function Execute-SQLiteCommand {
    Param(
        [string]$Command,
        [string]$Description
    )
    Write-Log "Ejecutando: $Description"
    try {
        $result = & $SQLITE_EXE $DB_PATH $Command 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "SQLite command failed: $result"
        }
        Write-Log "✅ $Description completado."
    } catch {
        Write-Log "❌ Error al ejecutar $Description: $($_.Exception.Message)" -Level "ERROR"
        # Aquí podrías invocar el hook on-error si tu sistema Kiro lo permite desde PowerShell
    }
}

# --- Inicio del Mantenimiento ---
Write-Log "Iniciando mantenimiento del sistema BETTING_AI..."

# 1. DB Vacuum
Execute-SQLiteCommand "VACUUM;" "Optimización de la base de datos (VACUUM)"

# 2. DB Indexing (asumiendo tablas 'backtesting' y 'predicciones')
Execute-SQLiteCommand "REINDEX backtesting;" "Re-indexando tabla 'backtesting'"
Execute-SQLiteCommand "REINDEX predicciones;" "Re-indexando tabla 'predicciones'"

# 3. Purga de Datos Antiguos (más de 180 días)
$dateThreshold = (Get-Date).AddDays(-180).ToString("yyyy-MM-dd HH:mm:ss")
Execute-SQLiteCommand "DELETE FROM backtesting WHERE fecha < '$dateThreshold';" "Eliminando registros antiguos de 'backtesting' (más de 180 días)"

# 4. Limpieza de Logs Antiguos (más de 30 días)
Write-Log "Limpiando archivos de log antiguos (más de 30 días) en $LOGS_DIR..."
Get-ChildItem -Path $LOGS_DIR -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Log "✅ Limpieza de logs completada."

# 5. Rotación de error.log
if (Test-Path $ERROR_LOG) {
    $oldErrorLog = Join-Path $LOGS_DIR ("error.log." + (Get-Date -Format "yyyyMMddHHmmss"))
    Move-Item -Path $ERROR_LOG -Destination $oldErrorLog -Force -ErrorAction SilentlyContinue
    New-Item -Path $ERROR_LOG -ItemType File -Force | Out-Null
    Write-Log "✅ error.log rotado a $oldErrorLog y nuevo error.log creado."
} else {
    Write-Log "⚠️ error.log no encontrado para rotar."
}

Write-Log "Mantenimiento del sistema BETTING_AI finalizado."