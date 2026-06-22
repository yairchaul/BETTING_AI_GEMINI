# -*- coding: utf-8 -*-
"""
Integración con martj42/international_results:
~50 000 partidos internacionales 1872–2024.

Fuente: https://github.com/martj42/international_results
CSV columns: date, home_team, away_team, home_score, away_score, tournament, city, country, neutral

Provee:
  head_to_head(local, visitante)  → estadísticas H2H históricas
  historial_mundial(equipo)       → rendimiento histórico en Copas del Mundo
  forma_reciente(equipo, n)       → últimos N partidos internacionales
  analizar_h2h(local, visitante)  → resumen texto para Gemini/display
"""
import os
import csv
import logging
import requests
import unicodedata
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

CSV_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
CACHE_PATH = os.path.join("data", "international_results.csv")
CACHE_DAYS = 7  # refrescar semanalmente

_cache_data = None  # lista de dicts en memoria


# ── Normalización de nombres ─────────────────────────────────────────────────

def _norm(name: str) -> str:
    t = unicodedata.normalize('NFD', (name or '').strip()).encode('ascii', 'ignore').decode()
    return t.lower().replace('-', ' ').replace('.', '').strip()


# Aliases: variante común (FIFA o español) → nombre normalizado tal como
# aparece en el CSV de martj42. OJO: martj42 usa nombres comunes en inglés
# ("south korea", "czech republic", "ivory coast", "united states"), NO los
# nombres estilo FIFA. Mapear al nombre REAL del dataset o el lookup falla.
_ALIASES = {
    # Corea (dataset: "south korea")
    "korea republic": "south korea",
    "corea del sur": "south korea",
    "corea": "south korea",
    "corea del norte": "north korea",
    # Estados Unidos (dataset: "united states")
    "usa": "united states",
    "estados unidos": "united states",
    "eeuu": "united states",
    "ee uu": "united states",
    # Irán
    "ir iran": "iran",
    # Costa de Marfil (dataset: "ivory coast")
    "cote d ivoire": "ivory coast",
    "costa de marfil": "ivory coast",
    # Chequia (dataset: "czech republic")
    "czechia": "czech republic",
    "chequia": "czech republic",
    "republica checa": "czech republic",
    # Macedonia (dataset: "north macedonia")
    "macedonia": "north macedonia",
    # Cabo Verde (dataset: "cape verde")
    "cabo verde": "cape verde",
    # Congo RD (dataset: "dr congo")
    "congo dr": "dr congo",
    "rd congo": "dr congo",
    "rdc": "dr congo",
    # Traducciones ES → EN comunes (los feeds dan inglés, pero el usuario
    # puede teclear en español)
    "paises bajos": "netherlands",
    "holanda": "netherlands",
    "alemania": "germany",
    "inglaterra": "england",
    "francia": "france",
    "espana": "spain",
    "belgica": "belgium",
    "brasil": "brazil",
    "croacia": "croatia",
    "suiza": "switzerland",
    "japon": "japan",
    "marruecos": "morocco",
    "arabia saudita": "saudi arabia",
    "arabia saudi": "saudi arabia",
    "catar": "qatar",
}


def _resolve(name: str) -> str:
    n = _norm(name)
    return _ALIASES.get(n, n)


# ── Descarga y carga del CSV ─────────────────────────────────────────────────

def _descargar_csv() -> bool:
    try:
        r = requests.get(CSV_URL, timeout=40, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            os.makedirs("data", exist_ok=True)
            with open(CACHE_PATH, 'w', encoding='utf-8', newline='') as f:
                f.write(r.text)
            logger.info("international_results: CSV descargado correctamente")
            return True
    except Exception as e:
        logger.warning(f"international_results: no se pudo descargar CSV: {e}")
    return False


def _cargar_datos() -> list:
    global _cache_data
    if _cache_data is not None:
        return _cache_data

    cache_ok = False
    if os.path.exists(CACHE_PATH):
        age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_PATH))).days
        cache_ok = age < CACHE_DAYS

    if not cache_ok:
        _descargar_csv()

    if not os.path.exists(CACHE_PATH):
        logger.warning("international_results: sin datos locales disponibles")
        _cache_data = []
        return _cache_data

    filas = []
    try:
        with open(CACHE_PATH, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    filas.append({
                        'fecha': row['date'],
                        'local_raw': row['home_team'],
                        'visita_raw': row['away_team'],
                        'local': _norm(row['home_team']),
                        'visita': _norm(row['away_team']),
                        'goles_local': int(row['home_score'] or 0),
                        'goles_visita': int(row['away_score'] or 0),
                        'torneo': row.get('tournament', ''),
                        'neutral': (row.get('neutral', 'FALSE') or 'FALSE').upper() == 'TRUE',
                    })
                except (ValueError, KeyError):
                    continue
    except Exception as e:
        logger.warning(f"international_results: error leyendo CSV: {e}")

    _cache_data = filas
    logger.info(f"international_results: {len(filas):,} partidos cargados")
    return _cache_data


def disponible() -> bool:
    """True si los datos están cargados (local o descarga OK)."""
    return len(_cargar_datos()) > 0


# ── Funciones de análisis ────────────────────────────────────────────────────

def head_to_head(local: str, visitante: str, n: int = 30, solo_wc: bool = False) -> dict:
    """H2H histórico entre dos selecciones (últimos N enfrentamientos)."""
    datos = _cargar_datos()
    la = _resolve(local)
    va = _resolve(visitante)

    partidos = []
    for row in datos:
        rl, rv = row['local'], row['visita']
        es_match = (rl == la and rv == va) or (rl == va and rv == la)
        if not es_match:
            continue
        if solo_wc and 'world cup' not in row['torneo'].lower():
            continue
        partidos.append(row)

    partidos = sorted(partidos, key=lambda x: x['fecha'], reverse=True)[:n]

    if not partidos:
        return {'total': 0}

    gana_la = gana_va = empates = 0
    gf_la = gf_va = 0
    ultimos = []

    for p in partidos:
        if p['local'] == la:
            g, c = p['goles_local'], p['goles_visita']
            swap = False
        else:
            g, c = p['goles_visita'], p['goles_local']
            swap = True
        gf_la += g
        gf_va += c
        if g > c:
            gana_la += 1
        elif c > g:
            gana_va += 1
        else:
            empates += 1
        if len(ultimos) < 5:
            hl, hv = (p['local_raw'], p['visita_raw']) if not swap else (p['visita_raw'], p['local_raw'])
            ultimos.append({
                'fecha': p['fecha'],
                'local': hl, 'visitante': hv,
                'resultado': f"{g}-{c}",
                'torneo': p['torneo'],
            })

    total = len(partidos)
    return {
        'total': total,
        'gana_local': gana_la, 'empates': empates, 'gana_visita': gana_va,
        'pct_local': round(gana_la / total * 100, 1),
        'pct_empate': round(empates / total * 100, 1),
        'pct_visita': round(gana_va / total * 100, 1),
        'avg_goles_local': round(gf_la / total, 2),
        'avg_goles_visita': round(gf_va / total, 2),
        'avg_total': round((gf_la + gf_va) / total, 2),
        'ultimos': ultimos,
    }


def historial_mundial(equipo: str, desde_anio: int = 1990) -> dict:
    """Rendimiento en Copas del Mundo desde `desde_anio`."""
    datos = _cargar_datos()
    eq = _resolve(equipo)

    partidos_wc = []
    for row in datos:
        if 'world cup' not in row['torneo'].lower():
            continue
        if row['fecha'][:4] < str(desde_anio):
            continue
        if row['local'] == eq or row['visita'] == eq:
            partidos_wc.append(row)

    if not partidos_wc:
        return {'total_wc': 0}

    gana = empata = pierde = gf = gc = 0
    for p in partidos_wc:
        if p['local'] == eq:
            g, c = p['goles_local'], p['goles_visita']
        else:
            g, c = p['goles_visita'], p['goles_local']
        gf += g; gc += c
        if g > c:
            gana += 1
        elif g == c:
            empata += 1
        else:
            pierde += 1

    total = len(partidos_wc)
    return {
        'total_wc': total,
        'ganados': gana, 'empatados': empata, 'perdidos': pierde,
        'goles_favor': gf, 'goles_contra': gc,
        'win_rate_wc': round(gana / total * 100, 1),
        'puntos_prom': round((gana * 3 + empata) / total, 2),
    }


def forma_reciente(equipo: str, n: int = 10, solo_torneos: bool = False) -> dict:
    """Últimos N partidos internacionales (opcionalmente solo torneos oficiales)."""
    datos = _cargar_datos()
    eq = _resolve(equipo)

    partidos = []
    for row in sorted(datos, key=lambda x: x['fecha'], reverse=True):
        if row['local'] != eq and row['visita'] != eq:
            continue
        if solo_torneos and row['torneo'].lower() in ('friendly',):
            continue
        partidos.append(row)
        if len(partidos) >= n:
            break

    if not partidos:
        return {'total': 0}

    gana = empata = pierde = gf = gc = 0
    for p in partidos:
        if p['local'] == eq:
            g, c = p['goles_local'], p['goles_visita']
        else:
            g, c = p['goles_visita'], p['goles_local']
        gf += g; gc += c
        if g > c:
            gana += 1
        elif g == c:
            empata += 1
        else:
            pierde += 1

    total = len(partidos)
    return {
        'total': total,
        'ganados': gana, 'empatados': empata, 'perdidos': pierde,
        'goles_favor': gf, 'goles_contra': gc,
        'avg_gf': round(gf / total, 2), 'avg_gc': round(gc / total, 2),
        'win_rate': round(gana / total * 100, 1),
    }


def analizar_h2h(local: str, visitante: str) -> str:
    """Texto resumen H2H + historial WC para contexto de Gemini."""
    h2h = head_to_head(local, visitante, n=20)
    h2h_wc = head_to_head(local, visitante, n=10, solo_wc=True)
    wc_l = historial_mundial(local)
    wc_v = historial_mundial(visitante)
    forma_l = forma_reciente(local, n=10, solo_torneos=True)
    forma_v = forma_reciente(visitante, n=10, solo_torneos=True)

    lines = [f"=== DATOS HISTÓRICOS: {local} vs {visitante} ==="]

    if h2h.get('total', 0):
        lines.append(
            f"H2H últimos {h2h['total']} partidos: "
            f"{local} gana {h2h['pct_local']}% | empate {h2h['pct_empate']}% | "
            f"{visitante} gana {h2h['pct_visita']}%"
        )
        lines.append(
            f"Promedio goles: {local} {h2h['avg_goles_local']} - {h2h['avg_goles_visita']} {visitante} "
            f"(total/partido: {h2h['avg_total']})"
        )
        if h2h.get('ultimos'):
            lines.append("Últimos 5 enfrentamientos:")
            for u in h2h['ultimos']:
                lines.append(f"  {u['fecha']} | {u['local']} {u['resultado']} {u['visitante']} ({u['torneo']})")
    else:
        lines.append("Sin enfrentamientos directos en el registro histórico.")

    if h2h_wc.get('total', 0):
        lines.append(
            f"En Mundiales: {local} gana {h2h_wc['pct_local']}% | "
            f"empate {h2h_wc['pct_empate']}% | {visitante} gana {h2h_wc['pct_visita']}%"
        )

    if wc_l.get('total_wc', 0):
        lines.append(
            f"\nHistorial WC {local} (desde 1990): "
            f"W{wc_l['ganados']} E{wc_l['empatados']} L{wc_l['perdidos']} | "
            f"WR {wc_l['win_rate_wc']}% | {wc_l['goles_favor']} GF - {wc_l['goles_contra']} GC"
        )
    if wc_v.get('total_wc', 0):
        lines.append(
            f"Historial WC {visitante} (desde 1990): "
            f"W{wc_v['ganados']} E{wc_v['empatados']} L{wc_v['perdidos']} | "
            f"WR {wc_v['win_rate_wc']}% | {wc_v['goles_favor']} GF - {wc_v['goles_contra']} GC"
        )

    if forma_l.get('total', 0):
        lines.append(
            f"\nForma reciente {local}: "
            f"{forma_l['ganados']}G {forma_l['empatados']}E {forma_l['perdidos']}P | "
            f"{forma_l['avg_gf']} GF/partido"
        )
    if forma_v.get('total', 0):
        lines.append(
            f"Forma reciente {visitante}: "
            f"{forma_v['ganados']}G {forma_v['empatados']}E {forma_v['perdidos']}P | "
            f"{forma_v['avg_gf']} GF/partido"
        )

    return "\n".join(lines)
