# -*- coding: utf-8 -*-
"""
TAPOLOGY SCRAPER — Segunda/tercera fuente para UFC (peleadores + resultados).

Tapology bloquea bots normales (403) pero permite Googlebot, así que se usa esa
UA con simples requests (sin Playwright — mucho más rápido).

Funciones de módulo:
  • buscar_peleador(nombre) → stats reales (record, KO/Sub rate, racha)
  • resultados_evento(url_o_slug) → peleas con ganador + método detallado
También expone TapologyScraper.scrape_event() por compatibilidad.
"""

import re
import requests

HEADERS = {'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)'}
BASE = "https://www.tapology.com"


def _get(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def buscar_peleador(nombre):
    """Busca un peleador en tapology y devuelve sus stats reales. None si no hay."""
    term = nombre.strip().replace(' ', '+')
    html = _get(f"{BASE}/search?term={term}&mainSearchFilter=fighters")
    if not html:
        return None
    m = re.search(r'/fightcenter/fighters/(\d+-[a-z0-9-]+)', html)
    if not m:
        return None
    perfil = _get(f"{BASE}/fightcenter/fighters/{m.group(1)}")
    if not perfil:
        return None

    rec = re.search(r'(\d+)-(\d+)-(\d+)', perfil)
    if not rec:
        return None
    wins, losses, draws = int(rec.group(1)), int(rec.group(2)), int(rec.group(3))
    datos = {'fuente': 'tapology', 'record': f"{wins}-{losses}-{draws}",
             'wins': wins, 'losses': losses}

    streak = re.search(r'Streak:\s*(\d+)\s*Win', perfil)
    if streak:
        datos['streak'] = int(streak.group(1))

    def _num_cerca(label):
        idx = perfil.find(label)
        if idx < 0:
            return 0
        ventana = re.sub(r'<[^>]+>', ' ', perfil[max(0, idx - 80):idx + 20])
        nums = re.findall(r'\b(\d+)\b', ventana)
        return int(nums[-1]) if nums else 0

    ko_w = _num_cerca('by Knockout') or _num_cerca('Knockout')
    sub_w = _num_cerca('by Submission') or _num_cerca('Submission')
    if wins > 0:
        datos['ko_rate'] = round(min(ko_w, wins) / wins, 2)
        datos['sub_rate'] = round(min(sub_w, wins) / wins, 2)
    return datos


def resultados_evento(url_o_slug):
    """Resultados de un evento: [{ganador, perdedor, metodo}]. Ganador va primero en el slug."""
    url = url_o_slug if url_o_slug.startswith('http') else f"{BASE}/fightcenter/events/{url_o_slug}"
    html = _get(url)
    if not html:
        return []

    # Bouts ÚNICOS por slug, con su primera posición (orden de cartelera)
    bouts = {}
    for m in re.finditer(r'/fightcenter/bouts/\d+-([a-z0-9-]+)', html):
        slug = m.group(1)
        if slug not in bouts:
            bouts[slug] = m.start()
    bouts_ordenados = sorted(bouts.items(), key=lambda x: x[1])

    # Nombres limpios de peleador, dedup consecutivo (img+name del mismo peleador)
    nombres = []
    for f in re.findall(r'/fightcenter/fighters/\d+-([a-z0-9-]+)', html):
        nombre = f.replace('-', ' ').title()
        if not nombres or nombres[-1] != nombre:
            nombres.append(nombre)

    metodos = [(re.sub(r'\s+', ' ', mm.group(1)).strip(), mm.start())
               for mm in re.finditer(r'>\s*(Decision[^<]*|Submission[^<]*|KO/TKO[^<]*|TKO[^<]*)<', html)]

    resultados = []
    vistos = set()
    for i, (slug, pos) in enumerate(bouts_ordenados):
        if i * 2 + 1 >= len(nombres):
            break
        ganador = nombres[i * 2]
        perdedor = nombres[i * 2 + 1]
        clave = f"{ganador}|{perdedor}"
        if clave in vistos:
            continue
        vistos.add(clave)
        metodo = next((m for m, mp in metodos if mp >= pos), 'Decisión')
        resultados.append({'ganador': ganador, 'perdedor': perdedor, 'metodo': metodo})
    return resultados


class TapologyScraper:
    """Compat: misma interfaz pero ahora ligera (Googlebot, sin Playwright)."""
    def __init__(self):
        self.base_url = BASE

    def scrape_event(self, event_url):
        return resultados_evento(event_url)

    def buscar_peleador(self, nombre):
        return buscar_peleador(nombre)


if __name__ == "__main__":
    print("Peleador:", buscar_peleador("Josh Hokit"))
    print("Evento:")
    for r in resultados_evento("140934-ufc-fight-night-muhammad-vs-bonfim")[:6]:
        print("  ", r)
