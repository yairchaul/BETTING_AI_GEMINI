# -*- coding: utf-8 -*-
"""
UFC STATS SCRAPER V3 - Fuente: ESPN MMA API (gratuita, sin key)

UFCStats.com añadió protección anti-bot (challenge JavaScript), por lo que la
fuente principal ahora es ESPN:
  - search v2          → encontrar el athlete_id del peleador
  - athlete bio        → altura, peso, alcance, postura, edad, récord, KO/SUB
  - core statistics    → SLpM, precisión de golpeo, TD avg/acc, sub avg
  - overview + status  → historial: tiempo de pelea, racha, derrota por KO reciente

Mantiene la misma clase/método (UFCStatsScraper.get_fighter_stats) y el mismo
esquema de salida para no romper main, renderers ni el analyzer.
"""

import requests
import re
import time
import json
import os
import unicodedata

try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_OK = True
except ImportError:
    RAPIDFUZZ_OK = False

from database_manager import db

_SEARCH_URL = "https://site.web.api.espn.com/apis/search/v2"
_BIO_URL = "https://site.web.api.espn.com/apis/common/v3/sports/mma/ufc/athletes/{aid}"
_CORE_STATS_URL = "https://sports.core.api.espn.com/v2/sports/mma/athletes/{aid}/statistics"
_OVERVIEW_URL = "https://site.web.api.espn.com/apis/common/v3/sports/mma/ufc/athletes/{aid}/overview"
_COMP_URL = "https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/events/{eid}/competitions/{cid}"

_UFC_COM_URL = "https://www.ufc.com/athlete/{slug}"


class UFCStatsScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        os.makedirs("data", exist_ok=True)
        self.caliente_odds_cache = self._load_caliente_odds_cache()

    def _load_caliente_odds_cache(self):
        odds_file = "data/odds_caliente_ufc.json"
        if os.path.exists(odds_file):
            with open(odds_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _normalize_name(self, name):
        text = unicodedata.normalize('NFD', name)
        text = text.encode('ascii', 'ignore').decode("utf-8")
        return text.strip().lower().replace(' ', '-')

    def _get_json(self, url, timeout=12):
        try:
            res = requests.get(url, headers=self.headers, timeout=timeout)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
        return None

    # ──────────────────────────────────────────────────────────────────────
    # ESPN: BÚSQUEDA E IDENTIFICACIÓN
    # ──────────────────────────────────────────────────────────────────────

    def _find_athlete_id(self, name):
        """Busca el athlete_id de MMA en ESPN. uid formato 's:3301~a:<id>'.

        Si hay homónimos (ej. dos 'Steve Garcia'), desempata prefiriendo al
        peleador activo con más victorias.
        """
        data = self._get_json(f"{_SEARCH_URL}?query={requests.utils.quote(name)}&limit=10")
        if not data:
            return None

        candidatos = []          # lista de (displayName, id) — admite homónimos
        for grp in data.get('results', []):
            if grp.get('type') != 'player':
                continue
            for item in grp.get('contents', []):
                uid = item.get('uid', '')
                if 's:3301' not in uid:          # 3301 = MMA
                    continue
                m = re.search(r'a:(\d+)', uid)
                if m:
                    candidatos.append((item.get('displayName', ''), m.group(1)))

        if not candidatos:
            return None

        def _similitud(disp):
            if RAPIDFUZZ_OK:
                return fuzz.WRatio(name, disp)
            d, n = disp.lower(), name.lower()
            return 100 if (n in d or d in n) else 0

        puntuados = sorted(
            ((_similitud(d), d, aid) for d, aid in candidatos), reverse=True
        )
        mejor_sim = puntuados[0][0]
        if mejor_sim < 80:
            return None

        finalistas = [(d, aid) for sim, d, aid in puntuados if sim >= mejor_sim - 5]
        if len(finalistas) == 1:
            print(f"    Match ESPN: {finalistas[0][0]} ({mejor_sim:.0f}%)")
            return finalistas[0][1]

        # Homónimos: elegir al activo con más victorias
        mejor_id, mejor_puntaje, mejor_disp = None, -1, ''
        for disp, aid in finalistas[:4]:
            bio = self._get_json(_BIO_URL.format(aid=aid)) or {}
            a = bio.get('athlete', {})
            wins = 0
            for s in a.get('statsSummary', {}).get('statistics', []):
                if s.get('name') == 'wins-losses-draws':
                    mm = re.match(r'(\d+)', s.get('displayValue', '0'))
                    wins = int(mm.group(1)) if mm else 0
            puntaje = (1000 if a.get('active') else 0) + wins
            if puntaje > mejor_puntaje:
                mejor_puntaje, mejor_id, mejor_disp = puntaje, aid, disp
        print(f"    Match ESPN (desambiguado entre {len(finalistas)}): {mejor_disp} -> id {mejor_id}")
        return mejor_id

    # ──────────────────────────────────────────────────────────────────────
    # ESPN: BIO + CAREER STATS + HISTORIAL
    # ──────────────────────────────────────────────────────────────────────

    def _parse_bio(self, aid, stats):
        """Bio: altura, peso, alcance, postura, edad, récord y conteos KO/SUB."""
        data = self._get_json(_BIO_URL.format(aid=aid))
        if not data:
            return
        a = data.get('athlete', {})

        if a.get('displayHeight'):
            stats['altura'] = a['displayHeight']             # ej. 5' 11"
        if a.get('displayWeight'):
            stats['peso'] = a['displayWeight']               # ej. 145 lbs
        if a.get('displayReach'):
            stats['alcance'] = a['displayReach']             # ej. 72.5"
        if a.get('stance'):
            stance = a['stance']
            stance_txt = stance.get('text', '') if isinstance(stance, dict) else str(stance)
            if stance_txt and stance_txt != '--':
                stats['stance'] = stance_txt
        if a.get('age'):
            stats['edad'] = int(a['age'])
        if a.get('weightClass'):
            wc = a['weightClass']
            stats['division'] = wc.get('text', '') if isinstance(wc, dict) else str(wc)
        if a.get('headshot'):
            hs = a['headshot']
            stats['photo'] = hs.get('href', '') if isinstance(hs, dict) else str(hs)

        ko_wins = sub_wins = ko_losses = 0
        for s in a.get('statsSummary', {}).get('statistics', []):
            nombre_stat = s.get('name', '')
            valor = s.get('displayValue', '')
            if nombre_stat == 'wins-losses-draws':
                m = re.match(r'(\d+)-(\d+)-(\d+)', valor)
                if m:
                    stats['record'] = valor
                    stats['wins'] = int(m.group(1))
                    stats['losses'] = int(m.group(2))
            elif nombre_stat == 'tkos-tkoLosses':
                m = re.match(r'(\d+)-(\d+)', valor)
                if m:
                    ko_wins, ko_losses = int(m.group(1)), int(m.group(2))
            elif nombre_stat == 'submissions-submissionLosses':
                m = re.match(r'(\d+)-(\d+)', valor)
                if m:
                    sub_wins = int(m.group(1))

        if stats.get('wins', 0) > 0:
            stats['ko_rate'] = round(ko_wins / stats['wins'], 2)
            stats['sub_rate'] = round(sub_wins / stats['wins'], 2)
        stats['ko_losses'] = ko_losses

    def _parse_career_stats(self, aid, stats):
        """Cuadro de carrera: SLpM, precisión, TD avg/acc, sub avg."""
        data = self._get_json(_CORE_STATS_URL.format(aid=aid))
        career = stats['estadisticas_carrera']
        if not data:
            return
        for cat in data.get('splits', {}).get('categories', []):
            for s in cat.get('stats', []):
                n, v = s.get('name'), s.get('value', 0) or 0
                if n == 'strikeLPM':
                    career['sig_strikes_landed_per_min'] = round(v, 2)
                elif n == 'strikeAccuracy':
                    career['sig_strike_accuracy'] = round(v, 1)      # %
                elif n == 'takedownAvg':
                    career['td_avg_per_15min'] = round(v, 2)
                elif n == 'takedownAccuracy':
                    career['td_accuracy'] = round(v, 1)              # %
                elif n == 'submissionAvg':
                    career['sub_avg_per_15min'] = round(v, 2)

    def _parse_fight_history(self, aid, stats, max_fights=5):
        """Últimas peleas vía overview: tiempo promedio, racha, KO reciente."""
        data = self._get_json(_OVERVIEW_URL.format(aid=aid))
        if not data:
            return
        uids = data.get('fightHistory', []) or []

        tiempos = []
        racha = 0
        racha_activa = True
        completadas = 0

        for uid in uids[:max_fights]:
            m = re.search(r'e:(\d+)~c:(\d+)', str(uid))
            if not m:
                continue
            comp = self._get_json(_COMP_URL.format(eid=m.group(1), cid=m.group(2)))
            if not comp:
                continue

            es_ganador = None
            for cc in comp.get('competitors', []):
                if str(cc.get('id')) == str(aid):
                    es_ganador = bool(cc.get('winner', False))
                    break
            if es_ganador is None:
                continue

            status_ref = comp.get('status', {}).get('$ref', '')
            status = self._get_json(status_ref) if status_ref else None
            if not status or not status.get('type', {}).get('completed', False):
                continue

            completadas += 1
            metodo = status.get('result', {}).get('displayName', '')
            ronda = int(status.get('period', 0) or 0)
            reloj = status.get('displayClock', '0:00')

            # Tiempo total de pelea en minutos
            m_t = re.match(r'(\d+):(\d+)', str(reloj))
            if ronda > 0 and m_t:
                tiempos.append((ronda - 1) * 5 + int(m_t.group(1)) + int(m_t.group(2)) / 60)

            # Racha de victorias (peleas más recientes primero)
            if racha_activa:
                if es_ganador:
                    racha += 1
                else:
                    racha_activa = False

            # ¿Su derrota más reciente fue por KO/TKO?
            if completadas == 1 and not es_ganador and re.search(r'KO|TKO', metodo, re.IGNORECASE):
                stats['was_koed_recently'] = True

            if len(stats['last_fights']) < 5:
                stats['last_fights'].append({
                    'oponente': '',
                    'resultado': 'win' if es_ganador else 'loss',
                    'metodo': metodo,
                    'ronda': str(ronda),
                    'tiempo': str(reloj),
                    'fecha': comp.get('date', '')[:10],
                })
            time.sleep(0.1)

        stats['streak'] = racha
        if tiempos:
            stats['estadisticas_carrera']['avg_fight_time'] = round(sum(tiempos) / len(tiempos), 2)

    # ──────────────────────────────────────────────────────────────────────
    # SEGUNDA FUENTE: ufc.com (datos reales, no inventados)
    # ──────────────────────────────────────────────────────────────────────

    def _scrape_ufc_com(self, name):
        """Extrae datos REALES de ufc.com/athlete/<slug>. None si no encuentra."""
        slug = self._normalize_name(name)  # ya devuelve 'josh-hokit'
        try:
            r = requests.get(_UFC_COM_URL.format(slug=slug), headers=self.headers, timeout=12)
            if r.status_code != 200:
                return None
            t = r.text
        except Exception:
            return None

        def _num_antes_de(label):
            idx = t.find(label)
            if idx < 0:
                return None
            antes = re.sub(r'<[^>]+>', ' ', t[max(0, idx - 160):idx])
            nums = re.findall(r'\b(\d+\.?\d*)\b', antes)
            return float(nums[-1]) if nums else None

        # Record (formato '9-0-0 (W-L-D)')
        m_rec = re.search(r'(\d+)-(\d+)-(\d+)\s*\(', t)
        if not m_rec:
            return None
        wins, losses, draws = int(m_rec.group(1)), int(m_rec.group(2)), int(m_rec.group(3))

        datos = {'fuente': 'ufc.com', 'record': f"{wins}-{losses}-{draws}",
                 'wins': wins, 'losses': losses}

        # Físicos: tomar el primer número DESPUÉS del label (con tags en medio)
        def _num_despues_de(label):
            idx = t.find(label)
            if idx < 0:
                return None
            despues = re.sub(r'<[^>]+>', ' ', t[idx + len(label):idx + len(label) + 120])
            nums = re.findall(r'(\d+\.?\d*)', despues)
            return float(nums[0]) if nums else None

        peso = _num_despues_de('Peso')
        if peso:
            datos['peso'] = f"{int(peso)} lbs"
        alcance = _num_despues_de('Alcance')
        if alcance:
            datos['alcance'] = f'{alcance}"'
        estatura = _num_despues_de('Estatura')
        if estatura:
            datos['altura'] = f"{int(estatura // 12)}' {int(estatura % 12)}\""

        # Victorias por método → KO/SUB rate reales
        ko_w = _num_antes_de('Victorias por nocaut') or _num_antes_de('Wins by Knockout') or 0
        sub_w = _num_antes_de('Gana por Sumisión') or _num_antes_de('Wins by Submission') or 0
        if wins > 0:
            datos['ko_rate'] = round(ko_w / wins, 2)
            datos['sub_rate'] = round(sub_w / wins, 2)
            dec_w = max(0, wins - ko_w - sub_w)
            datos.setdefault('estadisticas_carrera', {})['decision_pct'] = round(dec_w / wins * 100, 1)

        # SLpM (primer número del comparador de stats)
        compare = re.findall(r'c-stat-compare__number[^>]*>\s*([\d.]+)', t)
        if compare:
            slpm = float(compare[0])
            datos['slpm_avg'] = slpm
            datos.setdefault('estadisticas_carrera', {})['sig_strikes_landed_per_min'] = slpm

        return datos

    # ──────────────────────────────────────────────────────────────────────
    # API PRINCIPAL (misma firma de siempre)
    # ──────────────────────────────────────────────────────────────────────

    def get_fighter_stats(self, name, light=False, athlete_id=None):
        """Obtiene estadísticas de un peleador (fuente: ESPN).

        Args:
            name:       Nombre del peleador.
            light:      True = solo bio + career stats (sin historial de peleas).
                        Usado por el backtester para minimizar requests.
            athlete_id: ID de ESPN si ya se conoce (evita la búsqueda por nombre).
        """
        normalized = self._normalize_name(name)

        # Caché DB (3 días). El modo completo exige formato 'espn';
        # el modo light acepta también 'espn-light'.
        cached = db.get_ufc_fighter_from_cache(normalized, max_age_days=3)
        if cached and cached.get('estadisticas_carrera', {}).get('sig_strikes_landed_per_min') is not None:
            fuente_cache = cached.get('fuente', '')
            if fuente_cache == 'espn' or (light and fuente_cache == 'espn-light'):
                print(f"  Usando cache de DB para {name}")
                return cached

        print(f"  Buscando {name} en ESPN MMA...")

        stats = {
            'nombre': name,
            'fuente': 'espn-light' if light else 'espn',
            'record': 'N/A',
            'wins': 0, 'losses': 0,
            'altura': 'N/A', 'alcance': 'N/A', 'peso': 'N/A',
            'edad': 0, 'division': '',
            'ko_rate': 0, 'sub_rate': 0, 'ko_losses': 0,
            'striking_accuracy': 0, 'takedown_accuracy': 0,
            'stance': 'Orthodox',
            'streak': 0,
            'was_koed_recently': False,
            'last_fights': [],
            'slpm_avg': 0.0,
            'td_avg': 0.0,
            'photo': '',
            'estadisticas_carrera': {
                'sig_strikes_landed_per_min': 0.0,
                'sig_strike_accuracy': 0.0,
                'td_avg_per_15min': 0.0,
                'td_accuracy': 0.0,
                'sub_avg_per_15min': 0.0,
                'avg_fight_time': 0.0,
            },
        }

        try:
            aid = athlete_id or self._find_athlete_id(name)
            if not aid:
                # 2ª fuente: ufc.com (datos verificados)
                ufc_data = self._scrape_ufc_com(name)
                if ufc_data:
                    print(f"    Datos reales obtenidos de ufc.com para {name}")
                    stats.update(ufc_data)
                    db.save_ufc_fighter_to_cache(normalized, stats)
                    return stats
                # 3ª fuente: tapology (también datos reales)
                try:
                    from scrapers.tapology_scraper import buscar_peleador
                    tap = buscar_peleador(name)
                    if tap:
                        print(f"    Datos reales obtenidos de tapology para {name}")
                        stats.update(tap)
                        db.save_ufc_fighter_to_cache(normalized, stats)
                        return stats
                except Exception:
                    pass
                print(f"    No encontrado en ESPN, ufc.com ni tapology")
                return stats          # sin cachear: permitir reintento

            self._parse_bio(aid, stats)
            self._parse_career_stats(aid, stats)
            if not light:
                self._parse_fight_history(aid, stats)

            career = stats['estadisticas_carrera']
            # Claves planas para el motor de análisis (compatibilidad)
            stats['slpm_avg'] = career.get('sig_strikes_landed_per_min', 0.0)
            stats['td_avg'] = career.get('td_avg_per_15min', 0.0)
            if career.get('sig_strike_accuracy'):
                stats['striking_accuracy'] = round(career['sig_strike_accuracy'] / 100, 2)
            if career.get('td_accuracy'):
                stats['takedown_accuracy'] = round(career['td_accuracy'] / 100, 2)
            # % de victorias por decisión (consistente con KO/SUB del récord)
            if stats['wins'] > 0:
                dec_wins = stats['wins'] - round(stats['ko_rate'] * stats['wins']) - round(stats['sub_rate'] * stats['wins'])
                career['decision_pct'] = round(max(0, dec_wins) / stats['wins'] * 100, 1)

            print(f"    Record: {stats['record']} | KO: {int(stats['ko_rate']*100)}% | "
                  f"SLpM: {stats['slpm_avg']:.2f} | Racha: {stats['streak']}W | "
                  f"Edad: {stats['edad']} | T.pelea: {career.get('avg_fight_time', 0):.1f}min")

            db.save_ufc_fighter_to_cache(normalized, stats)

        except Exception as e:
            print(f"    Error: {e}")

        return stats

    def get_ufc_odds_caliente(self):
        """Retorna las odds de UFC de Caliente.mx desde el caché"""
        return self.caliente_odds_cache

    def get_rankings(self):
        """Rankings P4P desde ESPN (ufcstats.com está bloqueado por anti-bot)."""
        rankings = []
        try:
            data = self._get_json("https://site.web.api.espn.com/apis/common/v3/sports/mma/ufc/rankings")
            if data:
                for rk in data.get('rankings', []):
                    if 'pound' in rk.get('name', '').lower() or 'p4p' in rk.get('shortName', '').lower():
                        for i, comp in enumerate(rk.get('ranks', [])[:15], 1):
                            nombre = comp.get('athlete', {}).get('displayName', '')
                            if nombre:
                                rankings.append({'rank': i, 'name': nombre})
                        break
        except Exception:
            pass
        return rankings


if __name__ == "__main__":
    scraper = UFCStatsScraper()
    test = scraper.get_fighter_stats("Diego Lopes")
    print(json.dumps(test, indent=2, default=str, ensure_ascii=False))
