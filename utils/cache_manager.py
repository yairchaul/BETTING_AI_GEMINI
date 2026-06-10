# -*- coding: utf-8 -*-
"""
Cache Manager: limpieza automática de archivos JSON de caché en data/.

Uso desde main_vision_completo.py al arrancar:
    from utils.cache_manager import cleanup_expired_caches
    cleanup_expired_caches()

O desde cualquier parte del código para limpiar un deporte específico:
    cleanup_expired_caches(sport="nba", max_age_days=3)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path("data")

# Archivos cuyo campo de fecha está dentro del JSON (key → campo ISO dentro del JSON)
_CACHE_DATE_FIELDS = {
    "nba_team_stats_cache.json": "ultima_actualizacion",
    "ufc_stats_cache.json": "ultima_actualizacion",
    "hr_datasets_completos.json": None,  # sin campo de fecha → usar mtime del archivo
}


def _file_age_days(path: Path) -> float:
    """Retorna la antigüedad del archivo en días (basado en mtime)."""
    mtime = path.stat().st_mtime
    age_seconds = datetime.now().timestamp() - mtime
    return age_seconds / 86400


def _json_date_age_days(path: Path, date_field: str) -> float | None:
    """
    Retorna la antigüedad en días basada en un campo ISO dentro del JSON.
    Retorna None si no puede leerlo.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get(date_field) if isinstance(data, dict) else None
        if not raw:
            return None
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
        return age
    except Exception:
        return None


def cleanup_expired_caches(
    max_age_days: int = 7,
    sport: str | None = None,
    data_dir: Path | None = None,
) -> list[str]:
    """
    Elimina archivos *_cache.json y hr_*.json de data/ que superen max_age_days.

    Args:
        max_age_days: Antigüedad máxima permitida en días.
        sport: Si se especifica ("nba", "mlb", "ufc"), solo limpia cachés de ese deporte.
        data_dir: Ruta al directorio data/. Por defecto usa data/ relativo al CWD.

    Returns:
        Lista de rutas eliminadas.
    """
    target = data_dir or _DATA_DIR
    if not target.exists():
        return []

    patterns = ["*_cache.json", "hr_*.json"]
    if sport:
        patterns = [f"*{sport.lower()}*cache*.json", f"hr_{sport.lower()}*.json"]

    deleted = []
    for pattern in patterns:
        for cache_file in target.glob(pattern):
            date_field = _CACHE_DATE_FIELDS.get(cache_file.name)

            if date_field is not None:
                age = _json_date_age_days(cache_file, date_field)
                if age is None:
                    age = _file_age_days(cache_file)
            else:
                age = _file_age_days(cache_file)

            if age > max_age_days:
                try:
                    cache_file.unlink()
                    deleted.append(str(cache_file))
                    logger.info(f"[cache_manager] Eliminado {cache_file.name} ({age:.1f} días)")
                except Exception as e:
                    logger.warning(f"[cache_manager] No se pudo eliminar {cache_file}: {e}")

    if deleted:
        logger.info(f"[cache_manager] {len(deleted)} cachés expiradas eliminadas.")
    else:
        logger.debug("[cache_manager] No hay cachés expiradas.")

    return deleted
