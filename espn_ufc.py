# -*- coding: utf-8 -*-
"""
ESPN UFC - Scraper de cartelera.

Estrategia:
  1. Consulta el scoreboard de ESPN (evento mas cercano).
  2. Si ese evento YA TERMINO (status == 'post'), busca automaticamente
     el PROXIMO evento en el calendario y lo trae (cartelera siguiente).
  3. Devuelve la lista de combates con nombre, record y cuota (si existe).
"""
import requests
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"


class ESPN_UFC:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # ------------------------------------------------------------------ #
    # API publica
    # ------------------------------------------------------------------ #
    def get_events(self):
        """Devuelve la cartelera UFC vigente (o la proxima si la actual ya termino)."""
        try:
            data = self.session.get(SCOREBOARD_URL, timeout=12).json()
            events = data.get('events', [])

            # Eventos del scoreboard que NO han terminado (pre / in progress)
            vigentes = [e for e in events if not self._evento_terminado(e)]

            if vigentes:
                fights = self._parse_scoreboard_events(vigentes)
                if fights:
                    logger.info(f"✅ {len(fights)} combates UFC (cartelera vigente)")
                    return fights

            # Todos terminados -> buscar la PROXIMA cartelera en el calendario
            logger.info("ℹ️ El evento actual ya termino. Buscando la proxima cartelera...")
            fights = self._get_next_event_from_calendar(data)
            if fights:
                logger.info(f"✅ {len(fights)} combates UFC (proxima cartelera)")
                return fights

            # Si no hubo proximo, al menos devolver el ultimo scoreboard parseado
            fights = self._parse_scoreboard_events(events)
            return fights or self._get_fallback_fights()

        except Exception as e:
            logger.error(f"Error ESPN UFC: {e}")
            return self._get_fallback_fights()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _evento_terminado(event: dict) -> bool:
        """True si el evento (o todas sus peleas) ya finalizo."""
        status = event.get('status', {}).get('type', {})
        if status.get('completed') is True:
            return True
        if status.get('state') == 'post':
            return True
        # Si no hay status a nivel evento, revisar las competiciones
        comps = event.get('competitions', [])
        if comps:
            estados = [c.get('status', {}).get('type', {}).get('state') for c in comps]
            estados = [s for s in estados if s]
            if estados and all(s == 'post' for s in estados):
                return True
        return False

    def _parse_scoreboard_events(self, events: list) -> list:
        """Parsea eventos con el formato 'site API' (scoreboard)."""
        all_fights = []
        for event in events:
            event_name = event.get('name', 'UFC Event')
            event_date = event.get('date', '')[:10]

            for comp in event.get('competitions', []):
                competitors = comp.get('competitors', [])
                if len(competitors) < 2:
                    continue
                p1, p2 = competitors[0], competitors[1]
                p1_name = p1.get('athlete', {}).get('displayName', '')
                p2_name = p2.get('athlete', {}).get('displayName', '')
                if not p1_name or not p2_name:
                    continue

                odds = comp.get('odds', [{}])[0] if comp.get('odds') else {}
                all_fights.append({
                    'evento': event_name,
                    'fecha': event_date,
                    'peleador1': {
                        'nombre': p1_name,
                        'record': self._record_summary(p1),
                        'odds': self._odds_value(odds, 'awayTeamOdds'),
                    },
                    'peleador2': {
                        'nombre': p2_name,
                        'record': self._record_summary(p2),
                        'odds': self._odds_value(odds, 'homeTeamOdds'),
                    },
                })
        return all_fights

    @staticmethod
    def _record_summary(competitor: dict) -> str:
        recs = competitor.get('records')
        if recs and isinstance(recs, list):
            return recs[0].get('summary', 'N/A')
        return 'N/A'

    @staticmethod
    def _odds_value(odds: dict, side: str) -> str:
        if not odds:
            return 'N/A'
        val = odds.get(side, {})
        if isinstance(val, dict):
            return str(val.get('value', val.get('moneyLine', 'N/A')))
        return 'N/A'

    # ------------------------------------------------------------------ #
    # Proxima cartelera (core API via calendario)
    # ------------------------------------------------------------------ #
    def _get_next_event_from_calendar(self, scoreboard_data: dict) -> list:
        """Busca en el calendario el proximo evento futuro y trae su cartelera."""
        try:
            calendar = scoreboard_data.get('leagues', [{}])[0].get('calendar', [])
            now = datetime.now(timezone.utc)

            futuros = []
            for c in calendar:
                sd = c.get('startDate')
                if not sd:
                    continue
                try:
                    fecha = datetime.fromisoformat(sd.replace('Z', '+00:00'))
                except ValueError:
                    continue
                if fecha > now:
                    futuros.append((fecha, c))

            if not futuros:
                return []

            futuros.sort(key=lambda x: x[0])
            _, prox = futuros[0]
            ref = prox.get('event', {}).get('$ref', '')
            if not ref:
                return []
            ref = ref.replace('.pvt', '.com').replace('http://', 'https://')

            ev = self.session.get(ref, timeout=12).json()
            return self._parse_core_event(ev)
        except Exception as e:
            logger.warning(f"No se pudo obtener la proxima cartelera: {e}")
            return []

    def _parse_core_event(self, ev: dict) -> list:
        """Parsea un evento del 'core API' (con $ref a atletas y records)."""
        event_name = ev.get('name', 'UFC Event')
        event_date = (ev.get('date', '') or '')[:10]
        event_id = ev.get('id', '')
        comps = ev.get('competitions', [])

        # Ordenar: Main Card antes que Prelims y, dentro de cada segmento, el
        # estelar primero (matchNumber == 1 es el headliner). El id del segmento
        # 'Main Card' (173) es menor que 'Prelims' (174).
        def _orden(c):
            seg = c.get('cardSegment', {}) or {}
            try:
                seg_id = int(seg.get('id', 999))
            except (TypeError, ValueError):
                seg_id = 999
            return (seg_id, c.get('matchNumber', 999) or 999)
        comps.sort(key=_orden)

        # Recolectar todas las $ref de atletas/records y resolverlas en paralelo
        refs = set()
        for comp in comps:
            for cmp in comp.get('competitors', []):
                a = cmp.get('athlete', {}).get('$ref')
                r = cmp.get('record', {}).get('$ref')
                if a:
                    refs.add(a)
                if r:
                    refs.add(r)

        resueltas = self._fetch_refs_parallel(refs)

        fights = []
        for comp in comps:
            competitors = comp.get('competitors', [])
            if len(competitors) < 2:
                continue
            lados = []
            for cmp in competitors:
                a_ref = cmp.get('athlete', {}).get('$ref')
                r_ref = cmp.get('record', {}).get('$ref')
                ath = resueltas.get(a_ref, {}) if a_ref else {}
                rec = resueltas.get(r_ref, {}) if r_ref else {}
                nombre = ath.get('displayName') or ath.get('fullName') or ''
                items = rec.get('items', []) if isinstance(rec, dict) else []
                record = items[0].get('summary', 'N/A') if items else 'N/A'
                lados.append({'nombre': nombre, 'record': record})

            if len(lados) < 2 or not lados[0]['nombre'] or not lados[1]['nombre']:
                continue

            # Cuotas (moneyline) si ESPN ya las publico para esta pelea
            o1, o2 = self._fetch_odds_competicion(event_id, comp.get('id', ''))

            fights.append({
                'evento': event_name,
                'fecha': event_date,
                'peleador1': {'nombre': lados[0]['nombre'], 'record': lados[0]['record'], 'odds': o1},
                'peleador2': {'nombre': lados[1]['nombre'], 'record': lados[1]['record'], 'odds': o2},
            })
        return fights

    def _fetch_odds_competicion(self, event_id: str, comp_id: str):
        """Devuelve (odds_p1, odds_p2) moneyline desde ESPN si estan disponibles."""
        if not event_id or not comp_id:
            return 'N/A', 'N/A'
        url = (f"https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/events/"
               f"{event_id}/competitions/{comp_id}/odds?lang=en&region=us")
        try:
            data = self.session.get(url, timeout=8).json()
            items = data.get('items', [])
            if not items:
                return 'N/A', 'N/A'
            o = items[0]
            away = (o.get('awayTeamOdds', {}) or {}).get('moneyLine')
            home = (o.get('homeTeamOdds', {}) or {}).get('moneyLine')
            # peleador1 = order 2 (away), peleador2 = order 1 (home) en el core API
            return (str(away) if away is not None else 'N/A',
                    str(home) if home is not None else 'N/A')
        except Exception:
            return 'N/A', 'N/A'

    def _fetch_refs_parallel(self, refs) -> dict:
        """Resuelve un conjunto de URLs $ref en paralelo."""
        out = {}

        def _fetch(url):
            try:
                u = url.replace('.pvt', '.com').replace('http://', 'https://')
                return url, self.session.get(u, timeout=10).json()
            except Exception:
                return url, {}

        if not refs:
            return out
        with ThreadPoolExecutor(max_workers=10) as ex:
            for url, data in ex.map(_fetch, list(refs)):
                out[url] = data
        return out

    def _get_fallback_fights(self):
        """Combates de respaldo."""
        return [
            {
                'evento': 'UFC Fight Night',
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'peleador1': {'nombre': 'Peleador 1', 'record': '0-0', 'odds': 'N/A'},
                'peleador2': {'nombre': 'Peleador 2', 'record': '0-0', 'odds': 'N/A'},
            }
        ]
