# -*- coding: utf-8 -*-
"""
CONTEXTO MUNDIAL — nutre a la IA con factores REALES del torneo.

Reúne, por partido:
  • NOTICIAS recientes de ESPN que mencionan a cada equipo (lesiones, polémicas,
    bajas, moral) — p. ej. "Pulisic (calf) out", investigaciones, etc.
  • FORMA reciente (últimos 5: V-E-D y goles) desde la DB.
  • RANKING FIFA aproximado y diferencia de nivel.
  • ESTILO ofensivo/defensivo derivado de goles a favor/en contra.

Devuelve un bloque de texto para inyectar en el prompt del analista IA, de modo
que la decisión no dependa solo de la heurística de goles, sino del CONTEXTO.
"""
import os
import json
import time
import logging
import unicodedata

import requests

logger = logging.getLogger(__name__)

# Fuentes de noticias ESPN relevantes para selecciones / Mundial
_NEWS_URLS = [
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/news",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.worldq.uefa/news",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.worldq.conmebol/news",
]
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_CACHE_PATH = os.path.join("data", "wc_news_cache.json")
_CACHE_TTL = 3 * 3600   # 3 horas
_mem_cache = None        # (timestamp, [articulos])


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "").strip()).encode("ascii", "ignore").decode()
    return t.lower().replace("-", " ").replace(".", "").strip()


def _teams_de_articulo(a: dict) -> set:
    teams = set()
    for c in a.get("categories", []) or []:
        if c.get("type") == "team":
            nombre = c.get("description") or (c.get("team", {}) or {}).get("displayName")
            if nombre:
                teams.add(_norm(nombre))
    return teams


def obtener_noticias(force: bool = False) -> list:
    """Lista de noticias {headline, description, published, teams} con caché."""
    global _mem_cache
    ahora = time.time()
    if not force and _mem_cache and ahora - _mem_cache[0] < _CACHE_TTL:
        return _mem_cache[1]
    # Caché en disco
    if not force:
        try:
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                disco = json.load(f)
            if ahora - disco.get("ts", 0) < _CACHE_TTL:
                _mem_cache = (disco["ts"], disco["articulos"])
                return disco["articulos"]
        except Exception:
            pass

    articulos, vistos = [], set()
    for url in _NEWS_URLS:
        try:
            r = requests.get(url, headers=_HEADERS, timeout=12)
            if r.status_code != 200:
                continue
            for a in r.json().get("articles", []):
                h = a.get("headline", "")
                if not h or h in vistos:
                    continue
                vistos.add(h)
                articulos.append({
                    "headline": h,
                    "description": a.get("description", ""),
                    "published": a.get("published", ""),
                    "teams": sorted(_teams_de_articulo(a)),
                })
        except Exception as e:
            logger.debug(f"news {url}: {e}")

    _mem_cache = (ahora, articulos)
    try:
        os.makedirs("data", exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ts": ahora, "articulos": articulos}, f, ensure_ascii=False)
    except Exception:
        pass
    return articulos


def noticias_de_equipo(equipo: str, noticias=None, max_n: int = 3) -> list:
    """Titulares del equipo. Prioriza los asociados por CATEGORÍA (precisos:
    lesiones, alineación, polémicas) sobre los de mera coincidencia de texto
    (más ruidosos: kits, transferencias de club)."""
    nots = noticias if noticias is not None else obtener_noticias()
    eq = _norm(equipo)
    if not eq:
        return []
    por_categoria, por_texto = [], []
    for a in nots:
        if eq in a.get("teams", []):
            por_categoria.append(a)
        elif eq in _norm(a["headline"]) or eq in _norm(a.get("description", "")):
            por_texto.append(a)
    return (por_categoria + por_texto)[:max_n]


def _forma_y_estilo(equipo: str) -> str:
    """Resumen de forma reciente y estilo desde la DB (últimos 5)."""
    try:
        from utils.database_manager import db
        s = db.get_team_stats_detailed(equipo, "soccer")
    except Exception:
        s = None
    if not s or not s.get("goles_favor"):
        return ""
    gf = s.get("goles_favor", [])
    gc = s.get("goles_contra", [])
    n = len(gf)
    v = sum(1 for f, c in zip(gf, gc) if f > c)
    e = sum(1 for f, c in zip(gf, gc) if f == c)
    d = n - v - e
    prom_f = round(sum(gf) / n, 1) if n else 0
    prom_c = round(sum(gc) / n, 1) if n else 0
    estilo = "ofensivo" if prom_f >= 1.8 else ("sólido atrás" if prom_c <= 0.8 else "equilibrado")
    return f"últimos {n}: {v}V-{e}E-{d}D, {prom_f} goles a favor / {prom_c} en contra ({estilo})"


def _ranking(equipo: str) -> int:
    try:
        from motors.futbol_analyzer_jerarquico import _FIFA_RANK
    except Exception:
        return 60
    e = equipo.lower()
    return next((v for k, v in _FIFA_RANK.items() if k.lower() in e or e in k.lower()), 60)


def contexto_partido(local: str, visitante: str, es_torneo: bool = True) -> str:
    """Bloque de texto con noticias, forma, ranking y estilo de ambos equipos.
    Solo se genera para torneos de selecciones (Mundial, etc.); para clubes el
    ranking FIFA no aplica y devolvemos cadena vacía."""
    if not es_torneo:
        return ""
    nots = obtener_noticias()

    # Goleadores de referencia (señal de peligro ofensivo / props)
    try:
        from motors.futbol_props import obtener_goleadores_partido
        goleadores = obtener_goleadores_partido(local, visitante)
    except Exception:
        goleadores = {"local": [], "visitante": []}

    lineas = []
    r_l, r_v = _ranking(local), _ranking(visitante)
    lineas.append(f"Ranking FIFA aprox.: {local} #{r_l} vs {visitante} #{r_v} "
                  f"(dif {abs(r_l - r_v)} -> favorito por ranking: "
                  f"{local if r_l < r_v else visitante}).")

    # Probabilidad del MERCADO (cuotas de-vigueadas) — la 'sabiduría del mercado'
    # de Benter: si el mercado discrepa del modelo, suele saber algo (rotación,
    # lesión). Se inyecta para que la IA calibre su decisión.
    try:
        from motors.mercado_blend import cuotas_1x2
        mkt = cuotas_1x2(local, visitante)
        if mkt:
            lineas.append(f"MERCADO (cuotas {mkt['n_casas']} casas, de-vig): "
                          f"{local} {mkt['local']:.0f}% / Empate {mkt['empate']:.0f}% / "
                          f"{visitante} {mkt['visitante']:.0f}%. Si choca con el heurístico, "
                          f"el mercado puede anticipar rotación/lesión.")
    except Exception:
        pass

    # Situación de grupo / motivación (la lee Gemini para ajustar por interés:
    # ya clasificó y rota, o necesita ganar y ataca → over/BTTS).
    try:
        from motors.contexto_grupo import situacion_grupo
    except Exception:
        situacion_grupo = None

    for equipo in (local, visitante):
        forma = _forma_y_estilo(equipo)
        if forma:
            lineas.append(f"{equipo} — {forma}.")
        if situacion_grupo:
            sg = situacion_grupo(equipo)
            if sg:
                lineas.append(f"SITUACIÓN [{equipo}]: {sg['resumen']}")
        lista_gol = goleadores.get("local" if equipo == local else "visitante", [])
        if lista_gol:
            top = ", ".join(f"{g['jugador']} ({g.get('prob', 0)}% anota)" for g in lista_gol[:2])
            lineas.append(f"Goleadores {equipo}: {top}.")
        for a in noticias_de_equipo(equipo, nots, max_n=2):
            txt = a["headline"]
            if a.get("description"):
                txt += f" — {a['description']}"
            lineas.append(f"NOTICIA [{equipo}]: {txt}")

    if not lineas:
        return ""
    return "CONTEXTO REAL DEL TORNEO (considera lesiones, bajas, moral, polémicas):\n- " + "\n- ".join(lineas)
