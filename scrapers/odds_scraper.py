# -*- coding: utf-8 -*-
"""
SCRAPER DE CUOTAS — Caliente.mx (Playtech sportsbook)

Caliente renderiza en el servidor los eventos EN VIVO y destacados con sus
cuotas dentro de bloques `div.expander.event` → `button.price` (decimal en
`span.price.dec`). Las cuotas de PRE-JUEGO completas cargan por JavaScript, así
que con requests obtenemos de forma fiable lo que viene server-side (live +
destacados). Para cobertura total de pre-juego, combinar con The Odds API
(scrapers/odds_api.py), que ya está integrado.

Estructura confirmada (jun-2026):
  div.expander.event.sport-XXXX
    a  -> "Away Team(Pitcher) @ Home Team(Pitcher)"  (o "A vs B" en fútbol)
    button.price.mkt-{id}.seln-{id}.ev-{id}
       span.price.dec -> cuota decimal
       texto -> "Under ( 2.5 ) 23/20 2.15 +115"

Devuelve:
  get_caliente_markets(url)  -> [ {away, home, en_vivo, mercados:{moneyline, total, run_line}} ]
  get_mlb_odds_caliente()    -> { 'Equipo Normalizado': cuota_decimal_moneyline }  (retrocompat)
"""
import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

try:
    from utils.mapeo_equipos import normalizar_equipo
except Exception:
    def normalizar_equipo(x):
        return (x or "").strip()

_BASE = "https://sports.caliente.mx/es_MX"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}

# Tokens de cuota al final del texto del botón (fraccionaria, decimal, americana)
_RE_FRAC = re.compile(r"\b\d+/\d+\b")
_RE_DEC = re.compile(r"\b\d+\.\d{1,3}\b")
_RE_AMER = re.compile(r"[+-]\d{2,5}\b")
_RE_LINEA = re.compile(r"\(?\s*([+-]?\d+(?:\.\d+)?)\s*\)?")


def _limpiar_equipo(nombre: str) -> str:
    """Quita el pitcher entre paréntesis y normaliza: 'Toronto(Gausman)' -> 'Toronto'."""
    return re.sub(r"\s*\([^)]*\)", "", nombre or "").strip()


def _label_seleccion(texto_btn: str) -> str:
    """Extrae el nombre de la selección quitando los tokens de cuota del final."""
    t = texto_btn
    for rx in (_RE_AMER, _RE_DEC, _RE_FRAC):
        t = rx.sub("", t)
    return re.sub(r"\s+", " ", t).strip(" -·|")


def _decimal_de_boton(btn) -> float:
    dec_el = btn.select_one("span.price.dec, span.dec")
    if dec_el:
        m = _RE_DEC.search(dec_el.get_text(strip=True))
        if m:
            try:
                return float(m.group())
            except ValueError:
                pass
    # respaldo: primer decimal en el texto del botón
    m = _RE_DEC.search(btn.get_text(" ", strip=True))
    return float(m.group()) if m else 0.0


def _parse_evento(ev) -> dict:
    """Convierte un bloque div.expander.event en {away, home, en_vivo, mercados}."""
    # Título: el <a> que contiene '@' (béisbol) o ' vs ' (fútbol)
    titulo_el = next((a for a in ev.find_all("a")
                      if a.get_text(strip=True) and ("@" in a.get_text() or " vs " in a.get_text().lower())), None)
    if not titulo_el:
        return {}
    titulo = titulo_el.get_text(" ", strip=True)
    if "@" in titulo:
        partes = titulo.split("@", 1)        # Away @ Home (convención MLB)
        away, home = _limpiar_equipo(partes[0]), _limpiar_equipo(partes[1])
    elif " vs " in titulo.lower():
        partes = re.split(r"\s+vs\s+", titulo, flags=re.I)
        away, home = _limpiar_equipo(partes[0]), _limpiar_equipo(partes[1]) if len(partes) > 1 else ""
    else:
        return {}

    en_vivo = bool(ev.select_one(".live, .in-play, [class*='live']")) or bool(re.search(r"\d{1,2}:\d{2}", titulo_el.parent.get_text() if titulo_el.parent else ""))

    # Agrupar outcomes por mercado (clase mkt-{id})
    mercados_raw = {}
    for btn in ev.select("button.price"):
        mkt = next((c for c in btn.get("class", []) if c.startswith("mkt-")), None)
        if not mkt:
            continue
        dec = _decimal_de_boton(btn)
        if dec <= 1.0:
            continue
        label = _label_seleccion(btn.get_text(" ", strip=True))
        mercados_raw.setdefault(mkt, []).append({"label": label, "cuota": dec})

    moneyline, total, run_line = {}, {}, {}
    for mkt, outs in mercados_raw.items():
        labels = " ".join(o["label"].lower() for o in outs)
        if "over" in labels or "under" in labels or "más" in labels or "menos" in labels:
            # Total (Over/Under). Línea del primer label.
            for o in outs:
                lado = "over" if ("over" in o["label"].lower() or "más" in o["label"].lower()) else "under"
                m = _RE_LINEA.search(o["label"])
                if m and "linea" not in total:
                    total["linea"] = float(m.group(1))
                total[lado] = o["cuota"]
        elif any(re.search(r"[+-]\d+\.5", o["label"]) for o in outs):
            # Run line / hándicap (+1.5 / -1.5)
            for o in outs:
                m = re.search(r"([+-]\d+\.5)", o["label"])
                if m:
                    run_line[m.group(1)] = o["cuota"]
        elif len(outs) in (2, 3):
            # Moneyline: outcomes con nombre de equipo (o empate)
            for o in outs:
                ln = o["label"].lower()
                if away and (_limpiar_equipo(away).lower()[:6] in ln or ln[:6] in away.lower()):
                    moneyline["away"] = o["cuota"]
                elif home and (_limpiar_equipo(home).lower()[:6] in ln or ln[:6] in home.lower()):
                    moneyline["home"] = o["cuota"]
                elif "empate" in ln or "draw" in ln or ln in ("x",):
                    moneyline["draw"] = o["cuota"]

    return {"away": away, "home": home, "en_vivo": en_vivo,
            "mercados": {"moneyline": moneyline, "total": total, "run_line": run_line}}


def get_caliente_markets(url: str = None, deporte: str = "MLB", sport_filter: str = None) -> list:
    """Eventos de Caliente con sus mercados (ML / total / run line).

    sport_filter: si se indica (p.ej. 'BASE' béisbol, 'FOOT' fútbol), solo
    devuelve eventos de ese deporte (la clase del evento es 'sport-XXXX').
    Evita que el fútbol en vivo contamine la lista de MLB."""
    url = url or f"{_BASE}/{deporte}"
    eventos = []
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning(f"Caliente {url} -> {r.status_code}")
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        for ev in soup.select("div.expander.event"):
            if sport_filter:
                clases = ev.get("class", [])
                if not any(c.upper() == f"SPORT-{sport_filter.upper()}" for c in clases):
                    continue
            d = _parse_evento(ev)
            if d and d.get("home") and d.get("away"):
                m = d["mercados"]
                if m["moneyline"] or m["total"] or m["run_line"]:
                    eventos.append(d)
    except Exception as e:
        logger.error(f"Error scrapeando Caliente ({url}): {e}")
    return eventos


def get_mlb_odds_caliente() -> dict:
    """Retrocompat: { 'Equipo Normalizado': cuota_decimal_moneyline }.
    Solo eventos de béisbol (sport-BASE), no fútbol en vivo de la misma página."""
    odds_map = {}
    for ev in get_caliente_markets(deporte="MLB", sport_filter="BASE"):
        ml = ev["mercados"].get("moneyline", {})
        if ml.get("home"):
            odds_map[normalizar_equipo(ev["home"])] = ml["home"]
        if ml.get("away"):
            odds_map[normalizar_equipo(ev["away"])] = ml["away"]
    return odds_map


def get_soccer_odds_caliente(url: str = None) -> dict:
    """Cuotas reales de FÚTBOL de Caliente (1X2 + total) por evento.
    El fútbol sí se renderiza server-side, así que esto trae cuotas reales
    útiles para el EV de las apuestas del Mundial.
    Retorna { 'local__visitante': {moneyline:{home,draw,away}, total:{...}} }."""
    url = url or f"{_BASE}/Futbol"
    out = {}
    for ev in get_caliente_markets(url=url, sport_filter="FOOT"):
        clave = f"{normalizar_equipo(ev['home'])}__{normalizar_equipo(ev['away'])}"
        out[clave] = {"home": ev["home"], "away": ev["away"],
                      "moneyline": ev["mercados"]["moneyline"],
                      "total": ev["mercados"]["total"]}
    return out


if __name__ == "__main__":
    import json
    print("=== Caliente MLB (sport-BASE) ===")
    evs = get_caliente_markets(deporte="MLB", sport_filter="BASE")
    print(f"{len(evs)} eventos de beisbol con cuotas")
    for e in evs[:6]:
        print(json.dumps(e, ensure_ascii=False))
    print("\n=== moneyline MLB (retrocompat) ===")
    print(json.dumps(get_mlb_odds_caliente(), ensure_ascii=False))
    print("\n=== Caliente FUTBOL (1X2 + total) ===")
    sf = get_soccer_odds_caliente()
    print(f"{len(sf)} partidos de futbol con cuotas")
    for k, v in list(sf.items())[:6]:
        print(f"  {v['home']} vs {v['away']}: ML={v['moneyline']} TOTAL={v['total']}")
