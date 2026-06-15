# -*- coding: utf-8 -*-
"""
UFC BACKTESTER — Valida el motor contra peleas reales (fuente: ESPN)

Para cada pelea histórica:
  1. Obtiene stats reales de ambos peleadores (modo light, por athlete_id)
  2. Corre UFCAnalyzer.analizar_combate como si la pelea no hubiera ocurrido
  3. Compara: ¿acertó GANADOR? ¿acertó MÉTODO (KO/Sub/Dec)? ¿acertó DISTANCIA?

Genera:
  - data/ufc_backtest_reporte.json   → métricas + detalle pelea por pelea
  - data/ufc_calibracion.json        → precisión por método + offset de distancia
                                        (el UFCAnalyzer la lee automáticamente)

Uso CLI:  python -m motors.ufc_backtester [dias] [max_peleas]
"""

import os
import re
import sys
import json
import time
import requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.ufc_stats_scraper import UFCStatsScraper
from analyzers.ufc_analyzer import UFCAnalyzer

_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates={d1}-{d2}"
_STATUS_URL = "https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/events/{eid}/competitions/{cid}/status"

REPORTE_PATH = os.path.join("data", "ufc_backtest_reporte.json")
CALIB_PATH = os.path.join("data", "ufc_calibracion.json")

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def _clasificar_metodo(texto):
    """Mapea el método de ESPN a las 3 categorías del motor."""
    if not texto:
        return None
    t = texto.upper()
    if 'KO' in t or 'TKO' in t:
        return 'KO/TKO'
    if 'SUB' in t:
        return 'Sumisión'
    if 'DEC' in t:
        return 'Decisión'
    return None        # DQ, NC, etc. — se excluye de métricas de método


class UFCBacktester:
    def __init__(self):
        self.scraper = UFCStatsScraper()
        self.analyzer = UFCAnalyzer()

    def _get_json(self, url, timeout=12):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    # ──────────────────────────────────────────────────────────────────────
    def obtener_peleas_historicas(self, dias=90):
        """Descarga todas las peleas UFC completadas de los últimos N días."""
        peleas = []
        hoy = datetime.now()
        inicio = hoy - timedelta(days=dias)

        # ESPN acepta rangos; pedimos en bloques de 30 días
        cursor = inicio
        while cursor < hoy:
            fin_bloque = min(cursor + timedelta(days=30), hoy)
            url = _SCOREBOARD_URL.format(
                d1=cursor.strftime('%Y%m%d'), d2=fin_bloque.strftime('%Y%m%d'))
            data = self._get_json(url, timeout=20)
            cursor = fin_bloque + timedelta(days=1)
            if not data:
                continue

            for ev in data.get('events', []):
                evento_nombre = ev.get('name', 'UFC')
                eid = ev.get('id')
                for comp in ev.get('competitions', []):
                    competidores = comp.get('competitors', [])
                    if len(competidores) != 2:
                        continue
                    ganador = next((c for c in competidores if c.get('winner')), None)
                    if not ganador:
                        continue        # sin ganador (NC, cancelada o futura)

                    st = comp.get('status', {})
                    rounds_prog = comp.get('format', {}).get('regulation', {}).get('periods', 3)

                    peleas.append({
                        'evento': evento_nombre,
                        'fecha': comp.get('date', '')[:10],
                        'event_id': eid,
                        'comp_id': comp.get('id'),
                        'p1_nombre': competidores[0].get('athlete', {}).get('displayName', ''),
                        'p1_id': competidores[0].get('id'),
                        'p2_nombre': competidores[1].get('athlete', {}).get('displayName', ''),
                        'p2_id': competidores[1].get('id'),
                        'ganador_real': ganador.get('athlete', {}).get('displayName', ''),
                        'rounds_programados': rounds_prog,
                        'round_final': st.get('period', 0),
                        'tiempo_final': st.get('displayClock', ''),
                    })
            time.sleep(0.2)

        print(f"[backtest] {len(peleas)} peleas completadas en {dias} dias")
        return peleas

    def _obtener_metodo(self, pelea):
        """El método real (KO/Sub/Dec) viene del endpoint status por pelea."""
        data = self._get_json(_STATUS_URL.format(eid=pelea['event_id'], cid=pelea['comp_id']))
        if data:
            return _clasificar_metodo(data.get('result', {}).get('displayName', ''))
        return None

    # ──────────────────────────────────────────────────────────────────────
    def ejecutar_backtest(self, dias=90, max_peleas=50, progreso_cb=None):
        """Corre el motor sobre las peleas históricas y mide los aciertos."""
        peleas = self.obtener_peleas_historicas(dias)
        peleas = peleas[:max_peleas]          # más recientes primero (ESPN ordena asc → invertir)
        peleas = list(reversed(peleas))[:max_peleas]

        detalle = []
        n = len(peleas)

        for i, pelea in enumerate(peleas):
            if progreso_cb:
                progreso_cb(i + 1, n, f"{pelea['p1_nombre']} vs {pelea['p2_nombre']}")

            # Stats reales de ambos (light: bio + career, por ID directo)
            p1 = self.scraper.get_fighter_stats(pelea['p1_nombre'], light=True, athlete_id=pelea['p1_id'])
            p2 = self.scraper.get_fighter_stats(pelea['p2_nombre'], light=True, athlete_id=pelea['p2_id'])

            # Sin datos mínimos de ambos → no se puede evaluar el motor
            if (p1.get('wins', 0) + p1.get('losses', 0)) == 0 or \
               (p2.get('wins', 0) + p2.get('losses', 0)) == 0:
                continue

            pred = self.analyzer.analizar_combate(p1, p2)
            metodo_real = self._obtener_metodo(pelea)
            metodo_pred = pred.get('method_detail', {}).get('type')
            dur = pred.get('duracion', {})

            fue_decision = metodo_real == 'Decisión'
            pred_decision = bool(dur.get('va_a_decision'))

            fila = {
                'fecha': pelea['fecha'],
                'evento': pelea['evento'],
                'pelea': f"{pelea['p1_nombre']} vs {pelea['p2_nombre']}",
                'ganador_real': pelea['ganador_real'],
                'ganador_pred': pred.get('ganador', ''),
                'confianza': pred.get('confianza', 0),
                'ganador_ok': pred.get('ganador', '') == pelea['ganador_real'],
                'metodo_real': metodo_real,
                'metodo_pred': metodo_pred,
                'metodo_ok': (metodo_real == metodo_pred) if metodo_real else None,
                'fue_decision': fue_decision if metodo_real else None,
                'pred_decision': pred_decision,
                'distancia_ok': (fue_decision == pred_decision) if metodo_real else None,
                'prob_decision_pred': dur.get('prob', 0),
            }
            detalle.append(fila)
            time.sleep(0.15)

        return self._generar_reporte(detalle, dias)

    # ──────────────────────────────────────────────────────────────────────
    def _generar_reporte(self, detalle, dias):
        evaluadas = len(detalle)
        if evaluadas == 0:
            return {'error': 'Sin peleas evaluables', 'muestras': 0}

        # ── Ganador ──
        aciertos_g = sum(1 for d in detalle if d['ganador_ok'])
        por_confianza = {}
        for lo, hi, key in [(50, 55, '50-55%'), (55, 65, '55-65%'), (65, 101, '65%+')]:
            grupo = [d for d in detalle if lo <= d['confianza'] < hi]
            if grupo:
                por_confianza[key] = {
                    'peleas': len(grupo),
                    'aciertos': sum(1 for d in grupo if d['ganador_ok']),
                    'precision': round(sum(1 for d in grupo if d['ganador_ok']) / len(grupo) * 100, 1),
                }

        # ── Método (matriz de confusión + precisión por método predicho) ──
        con_metodo = [d for d in detalle if d['metodo_ok'] is not None]
        metodo_precision = {}
        confusion = {}
        for m in ('KO/TKO', 'Sumisión', 'Decisión'):
            predichas = [d for d in con_metodo if d['metodo_pred'] == m]
            if predichas:
                ok = sum(1 for d in predichas if d['metodo_ok'])
                metodo_precision[m] = round(ok / len(predichas) * 100, 1)
            confusion[m] = {}
            for m2 in ('KO/TKO', 'Sumisión', 'Decisión'):
                confusion[m][m2] = sum(
                    1 for d in con_metodo if d['metodo_pred'] == m and d['metodo_real'] == m2)

        # ── Distancia (¿llega a decisión?) ──
        con_dist = [d for d in detalle if d['distancia_ok'] is not None]
        dist_ok = sum(1 for d in con_dist if d['distancia_ok'])
        # Offset: diferencia entre tasa real de decisiones y prob promedio predicha
        if con_dist:
            tasa_real = sum(1 for d in con_dist if d['fue_decision']) / len(con_dist)
            prob_promedio = sum(d['prob_decision_pred'] for d in con_dist) / len(con_dist) / 100
            distancia_offset = round(max(-0.15, min(0.15, tasa_real - prob_promedio)), 3)
        else:
            tasa_real, distancia_offset = 0, 0

        reporte = {
            'timestamp': datetime.now().isoformat(),
            'dias': dias,
            'muestras': evaluadas,
            'ganador': {
                'aciertos': aciertos_g,
                'precision': round(aciertos_g / evaluadas * 100, 1),
                'por_confianza': por_confianza,
            },
            'metodo': {
                'muestras': len(con_metodo),
                'precision_por_metodo': metodo_precision,
                'confusion': confusion,
            },
            'distancia': {
                'muestras': len(con_dist),
                'aciertos': dist_ok,
                'precision': round(dist_ok / len(con_dist) * 100, 1) if con_dist else 0,
                'tasa_real_decisiones': round(tasa_real * 100, 1),
                'offset_aplicado': distancia_offset,
            },
            'detalle': detalle,
        }

        os.makedirs('data', exist_ok=True)
        with open(REPORTE_PATH, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)

        # ── Calibración que el motor lee automáticamente ──
        calibracion = {
            'actualizado': reporte['timestamp'],
            'muestras': evaluadas,
            'winner_precision': reporte['ganador']['precision'],
            'metodo_precision': metodo_precision,
            'distancia_offset': distancia_offset,
        }
        with open(CALIB_PATH, 'w', encoding='utf-8') as f:
            json.dump(calibracion, f, indent=2, ensure_ascii=False)

        print(f"[backtest] GANADOR: {reporte['ganador']['precision']}% "
              f"| METODO: {metodo_precision} "
              f"| DISTANCIA: {reporte['distancia']['precision']}% "
              f"(offset {distancia_offset:+.3f})")
        return reporte


if __name__ == "__main__":
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    max_p = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    bt = UFCBacktester()
    rep = bt.ejecutar_backtest(dias=dias, max_peleas=max_p)
    print(json.dumps({k: v for k, v in rep.items() if k != 'detalle'},
                     indent=2, ensure_ascii=False))
