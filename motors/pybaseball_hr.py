# -*- coding: utf-8 -*-
"""
PYBASEBALL HR ENHANCER — Datos Statcast reales para mejorar el predictor de HRs.

Usa pybaseball (jldbc/pybaseball) para obtener:
  • barrel_rate: % de bolas con exit_velo ≥ 98 mph + ángulo 26-30° (perfectas para HR)
  • hard_hit_pct: % de bolas ≥ 95 mph (contacto duro)
  • xSLG: slugging esperado (indicador de poder)
  • avg_exit_velo: velocidad promedio de salida

Estas métricas REALES del bateador califican si tiene perfil de HR:
  barrel_rate ≥ 10%  → perfil de jonronero élite
  hard_hit_pct ≥ 40% → contacto duro consistente
  xSLG ≥ .500       → slugger de poder

Cache: data/statcast_barrels_{season}.json (7 días)
"""
import json, os, logging, unicodedata
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_CACHE_PATH = "data/statcast_barrels_{season}.json"
_CACHE_DAYS = 7
_DEFAULT_BARREL = 6.5  # promedio MLB


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "").strip()).encode("ascii", "ignore").decode()
    return t.lower().replace(".", "").replace(",", "").strip()


def _nombre_similar(nombre1: str, nombre2: str) -> bool:
    """Detecta si dos nombres son el mismo jugador."""
    n1 = sorted(_norm(nombre1).split())  # orden canónico para comparar
    n2 = sorted(_norm(nombre2).split())
    if not n1 or not n2:
        return False
    # Exacto (ignorando orden)
    if n1 == n2:
        return True
    # Apellido exacto (token más largo) + inicial
    ap1 = max(n1, key=len)
    ap2 = max(n2, key=len)
    if ap1 == ap2 and len(ap1) > 3:
        ini1 = {t[0] for t in n1 if t != ap1}
        ini2 = {t[0] for t in n2 if t != ap2}
        return bool(ini1 & ini2) or not ini1 or not ini2
    return False


def _cache_fresco(path: str) -> bool:
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return (datetime.now() - mtime) < timedelta(days=_CACHE_DAYS)


def cargar_statcast_barrels(season: int = None) -> dict:
    """
    Descarga o carga desde cache los barrel rates de la temporada actual.
    Retorna {nombre_jugador: {barrel_rate, hard_hit_pct, xslg, avg_exit_velo, player_id}}.
    """
    if season is None:
        season = datetime.now().year

    cache_path = _CACHE_PATH.format(season=season)

    if _cache_fresco(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    try:
        import pybaseball as pb
        pb.cache.enable()

        # Barrel rate + exit velo por bateador (temporada completa)
        logger.info(f"Descargando Statcast barrels {season}...")
        df = pb.statcast_batter_exitvelo_barrels(season, minBBE=20)

        data = {}
        for _, row in df.iterrows():
            nombre = str(row.get("last_name, first_name", "") or row.get("player_name", ""))
            if not nombre:
                continue
            # El formato viene "Apellido, Nombre" → normalizar a "Nombre Apellido"
            if "," in nombre:
                partes = nombre.split(",", 1)
                nombre = f"{partes[1].strip()} {partes[0].strip()}"

            data[_norm(nombre)] = {
                "nombre_display": nombre,
                "barrel_rate": float(row.get("brl_percent", 0) or 0),
                "hard_hit_pct": float(row.get("hard_hit_percent", 0) or 0),
                "avg_exit_velo": float(row.get("avg_exit_velocity", 0) or 0),
                "player_id": int(row.get("player_id", 0) or 0),
            }

        # Complementar con expected stats (xSLG, xwOBA)
        try:
            df_exp = pb.statcast_batter_expected_stats(season, minPA=50)
            for _, row in df_exp.iterrows():
                nombre = str(row.get("last_name, first_name", "") or row.get("player_name", ""))
                if not nombre:
                    continue
                if "," in nombre:
                    partes = nombre.split(",", 1)
                    nombre = f"{partes[1].strip()} {partes[0].strip()}"
                key = _norm(nombre)
                if key in data:
                    data[key]["xslg"] = float(row.get("xslg", 0) or 0)
                    data[key]["xwoba"] = float(row.get("xwoba", 0) or 0)
                    data[key]["ba"] = float(row.get("ba", 0) or 0)
                else:
                    data[key] = {
                        "nombre_display": nombre,
                        "barrel_rate": 0, "hard_hit_pct": 0, "avg_exit_velo": 0,
                        "player_id": int(row.get("player_id", 0) or 0),
                        "xslg": float(row.get("xslg", 0) or 0),
                        "xwoba": float(row.get("xwoba", 0) or 0),
                    }
        except Exception as e_exp:
            logger.debug(f"xStats fallback: {e_exp}")

        # Guardar cache
        os.makedirs("data", exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        logger.info(f"Statcast barrels: {len(data)} jugadores guardados en cache")
        return data

    except Exception as e:
        logger.warning(f"pybaseball barrel descarga falló: {e}")
        return {}


# Singleton en memoria durante la sesión
_BARRELS_CACHE: dict = {}


def get_barrel_stats(nombre_jugador: str, season: int = None) -> dict:
    """
    Devuelve métricas Statcast de un bateador.
    Retorna dict con barrel_rate, hard_hit_pct, avg_exit_velo, xslg o vacío si no encontrado.
    """
    global _BARRELS_CACHE
    if not _BARRELS_CACHE:
        _BARRELS_CACHE = cargar_statcast_barrels(season)

    if not _BARRELS_CACHE:
        return {}

    clave = _norm(nombre_jugador)

    # Búsqueda exacta
    if clave in _BARRELS_CACHE:
        return _BARRELS_CACHE[clave]

    # Búsqueda por similitud de nombre
    for key, stats in _BARRELS_CACHE.items():
        if _nombre_similar(nombre_jugador, key):
            return stats

    return {}


def factor_hr_statcast(nombre_jugador: str) -> tuple[float, str]:
    """
    Calcula un factor multiplicador de probabilidad HR basado en datos Statcast.

    Retorna (factor, nota) donde:
      factor > 1.0: jugador tiene perfil de HR por encima del promedio
      factor < 1.0: jugador tiene perfil de contacto débil
      factor = 1.0: sin datos o perfil promedio
    """
    stats = get_barrel_stats(nombre_jugador)
    if not stats:
        return 1.0, ""

    barrel = stats.get("barrel_rate", _DEFAULT_BARREL)
    hard = stats.get("hard_hit_pct", 35)
    velo = stats.get("avg_exit_velo", 88)
    xslg = stats.get("xslg", 0.420)

    # Factor barrel (referencia: 6.5% promedio MLB)
    factor_barrel = barrel / _DEFAULT_BARREL

    # Factor hard hit (referencia: 35% promedio)
    factor_hard = hard / 35.0 if hard else 1.0

    # Factor velocidad (referencia: 88 mph promedio)
    factor_velo = velo / 88.0 if velo > 50 else 1.0

    # Factor xSLG (referencia: .420 promedio)
    factor_xslg = xslg / 0.420 if xslg else 1.0

    # Combinar: barrel tiene más peso (40%), luego hard hit (30%), velo (20%), xslg (10%)
    factor_total = (
        factor_barrel * 0.40
        + factor_hard * 0.30
        + factor_velo * 0.20
        + factor_xslg * 0.10
    )

    # Nota explicativa
    nivel = "ÉLITE" if barrel >= 12 else "POWER" if barrel >= 8 else "PROMEDIO" if barrel >= 5 else "CONTACTO"
    nota = (
        f"Statcast {stats.get('nombre_display', nombre_jugador)}: "
        f"Barrel {barrel:.1f}% ({nivel}) · "
        f"Hard Hit {hard:.1f}% · "
        f"Exit Velo {velo:.1f} mph"
    )
    if xslg:
        nota += f" · xSLG {xslg:.3f}"

    return round(factor_total, 3), nota


def top_sluggers_statcast(n: int = 10) -> list[dict]:
    """
    Retorna los top N sluggers de la temporada por barrel_rate.
    Útil para identificar bateadores con mayor perfil de HR sin depender del historial de la DB.
    """
    global _BARRELS_CACHE
    if not _BARRELS_CACHE:
        _BARRELS_CACHE = cargar_statcast_barrels()
    if not _BARRELS_CACHE:
        return []

    lista = [
        {"nombre": v.get("nombre_display", k), **v}
        for k, v in _BARRELS_CACHE.items()
        if v.get("barrel_rate", 0) > 0
    ]
    lista.sort(key=lambda x: x.get("barrel_rate", 0), reverse=True)
    return lista[:n]
