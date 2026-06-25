# -*- coding: utf-8 -*-
"""
UFC ANALYZER - CORREGIDO (SIEMPRE DA GANADOR)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.ufc_rankings_scraper import UFCRankingsScraper

class UFCAnalyzer:
    def __init__(self):
        self.rankings = UFCRankingsScraper()
    
    def calculate_score(self, fighter, opponent):
        score = 50
        
        w1 = fighter.get('wins', 0)
        l1 = fighter.get('losses', 0)
        w2 = opponent.get('wins', 0)
        l2 = opponent.get('losses', 0)
        
        name = fighter.get('nombre', '')
        
        # 1. CAMPEÓN
        bonus = self.rankings.get_bonus(name)
        if bonus >= 0.05:
            score += 10
        elif bonus >= 0.04:
            score += 7
        elif bonus >= 0.03:
            score += 5
        
        # 2. RANKING P4P
        p4p_pos = self.rankings.get_p4p_position(name)
        if p4p_pos:
            if p4p_pos <= 3:
                score += 6
            elif p4p_pos <= 5:
                score += 4
            elif p4p_pos <= 10:
                score += 2
        
        # 3. KO Rate
        ko1 = fighter.get('ko_rate', 0)
        if ko1 > 1: ko1 /= 100
        
        if ko1 >= 0.70:
            score += 7
        elif ko1 >= 0.60:
            score += 5
        elif ko1 >= 0.50:
            score += 3
        
        # 4. EXPERIENCIA
        exp1 = w1 + l1
        if exp1 >= 25:
            score += 5
        elif exp1 >= 18:
            score += 3
        elif exp1 >= 12:
            score += 1
        
        # 5. WIN RATE
        if w1 > 0:
            wr1 = w1 / (w1 + l1) if (w1 + l1) > 0 else 0.5
            wr2 = w2 / (w2 + l2) if (w2 + l2) > 0 else 0.5
            if wr1 > wr2 + 0.10:
                score += 3
        
        # 6. EDAD/PEAK
        age = fighter.get('edad') or 30
        if 27 <= age <= 32:
            score += 6
        elif age >= 36:
            score -= 3
        
        # 7. RACHA
        streak = fighter.get('streak', 0)
        if streak >= 3:
            score += 5
        elif streak >= 2:
            score += 3
        
        # 8. STRIKING ACCURACY
        striking = fighter.get('striking_accuracy', 0)
        if striking >= 0.50:
            score += 3
        elif striking >= 0.40:
            score += 1
        
        # 9. TAKEDOWN ACCURACY
        td = fighter.get('takedown_accuracy', 0)
        if td >= 0.50:
            score += 4
        elif td >= 0.35:
            score += 2

        # 10. DEFENSA (Str.Def / TD Def / SApM del cuadro de carrera UFCStats)
        ec = fighter.get('estadisticas_carrera', {}) or {}
        str_def = ec.get('sig_strike_defense', 0)
        if str_def >= 60:
            score += 3
        elif str_def >= 55:
            score += 2
        td_def = ec.get('td_defense', 0)
        if td_def >= 80:
            score += 3
        elif td_def >= 70:
            score += 2
        sapm = ec.get('sig_strikes_absorbed_per_min', 0)
        if 0 < sapm <= 3.0:
            score += 2  # recibe poco daño
        elif sapm >= 5.5:
            score -= 2  # absorbe demasiado

        # 11. VOLUMEN OFENSIVO (SLpM)
        slpm = ec.get('sig_strikes_landed_per_min', 0)
        if slpm >= 5.0:
            score += 3
        elif slpm >= 4.0:
            score += 2

        # 12. CAMBIO DE DIVISIÓN DE PESO (riesgo de adaptación)
        # Subir de peso: el cuerpo se está acostumbrando y el poder pega menos
        # contra rivales más grandes (caso Pereira). Bajar de peso: desgaste del
        # corte. Penaliza al que cambia de categoría.
        cambio = str(fighter.get('cambio_peso', '') or '').lower()
        if cambio in ('sube', 'subiendo', 'up', 'arriba'):
            score -= 6
        elif cambio in ('baja', 'bajando', 'down', 'abajo'):
            score -= 3

        return score
    
    def _cargar_calibracion(self):
        """Carga la calibración generada por el backtester (si existe)."""
        import json, os
        path = os.path.join("data", "ufc_calibracion.json")
        try:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                if getattr(self, '_calib_mtime', None) != mtime:
                    with open(path, encoding="utf-8") as f:
                        self._calibracion = json.load(f)
                    self._calib_mtime = mtime
                return self._calibracion
        except Exception:
            pass
        return {}

    def predict_method(self, winner_data, loser_data):
        """Predicción de método con señales reales: KO rate, sub rate/avg,
        tiempo promedio de pelea y % de decisiones. Confianza calibrada por
        backtest cuando hay muestras suficientes."""
        ko_rate = winner_data.get('ko_rate', 0)
        if ko_rate > 1: ko_rate /= 100
        sub_rate = winner_data.get('sub_rate', 0)
        if sub_rate > 1: sub_rate /= 100

        ec_w = winner_data.get('estadisticas_carrera', {}) or {}
        ec_l = loser_data.get('estadisticas_carrera', {}) or {}
        slpm = ec_w.get('sig_strikes_landed_per_min', 0)
        sub_avg = ec_w.get('sub_avg_per_15min', 0)
        td_acc_w = ec_w.get('td_accuracy', 0)
        avg_time_w = ec_w.get('avg_fight_time', 0)
        dec_pct_w = ec_w.get('decision_pct', 0)
        dec_pct_l = ec_l.get('decision_pct', 0)
        # Debilidades del RIVAL (definen si conviene buscar el KO o la sumisión)
        str_def_l = ec_l.get('sig_strike_defense', 0)   # mala defensa de golpeo → KO
        td_def_l = ec_l.get('td_defense', 0)            # mala defensa de derribo → sumisión
        rival_koed = loser_data.get('was_koed_recently', False)
        rival_ko_losses = loser_data.get('ko_losses', 0)
        rival_sub_losses = loser_data.get('sub_losses', 0)
        sube_peso = str(winner_data.get('cambio_peso', '') or '').lower() \
            in ('sube', 'subiendo', 'up', 'arriba')

        # Solo sumamos la debilidad del rival si el dato existe (>0)
        rival_chin = max(0, 55 - str_def_l) * 0.12 if str_def_l else 0
        rival_grapple_weak = max(0, 60 - td_def_l) * 0.12 if td_def_l else 0

        # KO/TKO: poder + volumen de golpeo + rival fácil de noquear
        score_ko = (ko_rate * 60) + max(0, slpm - 3.0) * 8 \
                   + (8 if rival_koed else 0) + min(rival_ko_losses, 4) * 3 \
                   + rival_chin
        if sube_peso:
            score_ko *= 0.75   # el poder no sube tan bien de categoría (Pereira)

        # SUMISIÓN: amenaza de sumisión + rival que se derriba/somete fácil
        score_sub = (sub_rate * 55) + sub_avg * 12 + min(rival_sub_losses, 4) * 3 \
                    + (rival_grapple_weak if td_acc_w >= 25 else rival_grapple_weak * 0.4)

        # DECISIÓN: historial de ir a las tarjetas + peleas largas
        score_dec = (dec_pct_w * 0.45) + (dec_pct_l * 0.25) \
                    + max(0, avg_time_w - 10) * 2.5
        if sube_peso:
            score_dec += 8     # adaptándose al peso → más probable que vaya largo

        scores = {"KO/TKO": score_ko, "Sumisión": score_sub, "Decisión": score_dec}
        metodo = max(scores, key=scores.get)
        total = sum(scores.values()) or 1
        conf = round(scores[metodo] / total * 100)
        conf = max(40, min(80, conf))

        # Ajuste con precisión real medida por el backtester
        calib = self._cargar_calibracion()
        precision = calib.get('metodo_precision', {}).get(metodo)
        if precision is not None and calib.get('muestras', 0) >= 15:
            conf = round((conf + precision) / 2)

        # Guardar el desglose normalizado para mostrar las 3 probabilidades
        self._ultimo_desglose_metodo = {
            k: round(v / total * 100) for k, v in scores.items()
        }
        return metodo, conf

    def desglose_metodo(self, winner_data, loser_data):
        """Probabilidades de los 3 métodos (KO/TKO, Sumisión, Decisión)."""
        self.predict_method(winner_data, loser_data)
        return getattr(self, '_ultimo_desglose_metodo', {})

    def totales_rounds(self, p1_data, p2_data, rounds_programados=3):
        """Over/Under de rounds (1.5, 2.5, 3.5...) con probabilidad y pick.

        Deriva del tiempo promedio de pelea de ambos y el poder de finalización.
        """
        def _ec(p):
            return p.get('estadisticas_carrera', {}) or {}
        t1 = _ec(p1_data).get('avg_fight_time', 0)
        t2 = _ec(p2_data).get('avg_fight_time', 0)
        tiempos = [t for t in (t1, t2) if t > 0]
        # Minutos esperados de pelea (si no hay datos, ~60% de la duración máxima)
        dur_max = rounds_programados * 5
        avg_min = sum(tiempos) / len(tiempos) if tiempos else dur_max * 0.6
        rounds_esperados = avg_min / 5.0  # cada round = 5 min

        resultado = []
        for linea in [1.5, 2.5, 3.5, 4.5][:rounds_programados + 1]:
            if linea >= rounds_programados + 0.5:
                continue
            # Prob de superar la línea según rounds esperados (curva suave)
            diff = rounds_esperados - linea
            prob_over = max(8, min(92, 50 + diff * 28))
            pick = "OVER" if prob_over >= 50 else "UNDER"
            conf = round(max(prob_over, 100 - prob_over))
            resultado.append({
                'linea': linea, 'pick': pick,
                'prob_over': round(prob_over), 'confianza': conf,
                'etiqueta': f"{pick} {linea} rounds",
            })
        return resultado

    def predecir_duracion(self, p1_data, p2_data, rounds=3):
        """¿La pelea llega a decisión (dura todos los rounds)?

        Señales: tiempo promedio de pelea de ambos, % de decisiones,
        poder de KO combinado y amenaza de sumisión.
        """
        def _ec(p):
            return p.get('estadisticas_carrera', {}) or {}

        ko1 = p1_data.get('ko_rate', 0)
        ko2 = p2_data.get('ko_rate', 0)
        if ko1 > 1: ko1 /= 100
        if ko2 > 1: ko2 /= 100

        t1 = _ec(p1_data).get('avg_fight_time', 0)
        t2 = _ec(p2_data).get('avg_fight_time', 0)
        dec1 = _ec(p1_data).get('decision_pct', 0)
        dec2 = _ec(p2_data).get('decision_pct', 0)
        sub1 = _ec(p1_data).get('sub_avg_per_15min', 0)
        sub2 = _ec(p2_data).get('sub_avg_per_15min', 0)
        slpm1 = _ec(p1_data).get('sig_strikes_landed_per_min', 0)
        slpm2 = _ec(p2_data).get('sig_strikes_landed_per_min', 0)
        kol1 = p1_data.get('ko_losses', 0)
        kol2 = p2_data.get('ko_losses', 0)

        dur_max = rounds * 5
        tiempos = [t for t in (t1, t2) if t > 0]
        avg_time = sum(tiempos) / len(tiempos) if tiempos else dur_max * 0.6

        # Base histórica UFC: ~48% de las peleas llegan a decisión
        p = 0.48
        p += (avg_time / dur_max - 0.55) * 0.55          # peleas largas → decisión
        p += ((dec1 + dec2) / 2 - 30) * 0.004            # historial de decisiones

        # PODER DE KO (lo que pediste): el de más poder manda; si AMBOS pegan
        # fuerte, todavía menos probable que llegue al límite.
        ko_max = max(ko1, ko2)
        ko_combo = ko1 + ko2
        p -= ko_max * 0.30
        p -= ko_combo * 0.10
        # Volumen del más activo: presión que acumula daño y abre el KO
        p -= max(0, max(slpm1, slpm2) - 4.0) * 0.03
        # Amenaza de sumisión de cualquiera de los dos
        p -= (sub1 + sub2) * 0.04
        # Quijada frágil (KO encajados) → más probable que termine antes
        p -= min(kol1 + kol2, 5) * 0.015

        # Offset medido por el backtester
        calib = self._cargar_calibracion()
        p += calib.get('distancia_offset', 0)

        p = max(0.08, min(0.92, p))
        va_decision = p >= 0.5

        if not va_decision and ko_max >= 0.55:
            razon = f"Alto poder de KO ({round(ko_max * 100)}%) → probable final anticipado"
        elif not va_decision and (sub1 + sub2) >= 1.0:
            razon = "Amenaza real de sumisión → puede terminar antes del límite"
        elif va_decision:
            razon = "Volumen/estilo de decisión → probable que llegue al límite"
        else:
            razon = "Estilos de finalización → puede terminar antes del límite"

        return {
            'va_a_decision': va_decision,
            'prob': round(p * 100),
            'pick': f"LLEGA A DECISIÓN ({rounds} rounds)" if va_decision
                    else "NO llega a decisión (termina antes)",
            'confianza': round(max(p, 1 - p) * 100),
            'razon': razon,
        }

    def calculate_probability(self, p1, p2):
        """Probabilidad de victoria de p1. Amplifica la diferencia de scores

        para evitar que todo quede comprimido en 50-55% (ambos parten de 50).
        """
        score1 = self.calculate_score(p1, p2)
        score2 = self.calculate_score(p2, p1)
        # La diferencia de scores manda; cada punto vale ~1.6% (centrado en 50)
        prob = 50 + (score1 - score2) * 1.6
        return round(max(12, min(88, prob)))
    
    def analizar_combate(self, p1_data, p2_data):
        prob = self.calculate_probability(p1_data, p2_data)
        p1_name = p1_data.get('nombre', 'P1')
        p2_name = p2_data.get('nombre', 'P2')
        score1 = self.calculate_score(p1_data, p2_data)
        score2 = self.calculate_score(p2_data, p1_data)
        
        # Determinar ganador (SIEMPRE)
        if prob >= 50:
            winner_data = p1_data
            winner_name = p1_name
            loser_data = p2_data
        else:
            winner_data = p2_data
            winner_name = p2_name
            loser_data = p1_data
        
        # Predecir método
        method, method_conf = self.predict_method(winner_data, loser_data)
        
        # Determinar si es pelea cerrada (para IA)
        is_close = 45 <= prob <= 55
        
        # SIEMPRE dar una recomendación
        if prob >= 65:
            decision = f"🔥 GANA {winner_name.upper()}"
            etiqueta = True
        elif prob >= 55:
            decision = f"📊 GANA {winner_name.upper()}"
            etiqueta = True
        elif prob <= 35:
            decision = f"🔥 GANA {winner_name.upper()}"
            etiqueta = True
        elif prob <= 45:
            decision = f"📊 GANA {winner_name.upper()}"
            etiqueta = True
        else:
            # Pelea cerrada (45-55%) - AÚN ASÍ damos ganador
            decision = f"📈 LIGERA VENTAJA {winner_name}"
            etiqueta = False
        
        # Predicción de duración (¿llega a decisión?)
        duracion = self.predecir_duracion(p1_data, p2_data)
        conf_ganador = prob if prob >= 50 else 100 - prob

        # Mercados extra (estilo sportsbook)
        metodo_probs = self.desglose_metodo(winner_data, loser_data)
        rounds_totales = self.totales_rounds(p1_data, p2_data)

        # ── Monte Carlo round-por-round: probabilidades COHERENTES de ganador,
        # método y totales de rounds del MISMO experimento. Se ancla en el modelo
        # ya calibrado (prob de ganador, distancia, split KO/Sub) y aporta el
        # reparto por round y los O/U con la convención real del sportsbook.
        montecarlo = None
        try:
            from motors.ufc_montecarlo import simular_combate
            p_win_f1 = prob / 100.0                      # prob de que gane p1
            p_finish = 1.0 - duracion.get('prob', 48) / 100.0
            ko_p = metodo_probs.get("KO/TKO", 0)
            sub_p = metodo_probs.get("Sumisión", 0)
            ko_split = ko_p / (ko_p + sub_p) if (ko_p + sub_p) > 0 else 0.6
            mc = simular_combate(p_win_f1, p_finish, ko_split, rounds=3, n=20000)
            # El MC reporta el ganador como p1/p2; lo traducimos a nombres.
            montecarlo = {
                "prob_ganador": {p1_name: mc["prob_win_f1"], p2_name: mc["prob_win_f2"]},
                "metodo_probs": mc["metodo_probs"],
                "prob_distancia": mc["prob_distancia"],
                "rounds_totales": mc["rounds_totales"],
                "duracion_media_min": mc["duracion_media_min"],
                "n": mc["n"],
            }
            # El MC da totales de rounds más realistas que la curva lineal previa.
            rounds_totales = mc["rounds_totales"]
        except Exception as _mce:
            pass

        # ── MEJOR APUESTA: comparar los 3 mercados y recomendar el más fuerte ──
        # Calibración del backtest ajusta la confianza real de cada mercado.
        calib = self._cargar_calibracion()
        prec_metodo = calib.get('metodo_precision', {}).get(method, 100)
        # Solo recortamos por precisión histórica si hay muestra suficiente
        if calib.get('muestras', 0) >= 15:
            method_conf_real = round((method_conf + prec_metodo) / 2)
        else:
            method_conf_real = method_conf

        mercados = [
            {
                'mercado': 'GANADOR (Moneyline)',
                'apuesta': f"Gana {winner_name}",
                'confianza': conf_ganador,
            },
            {
                'mercado': 'MÉTODO',
                'apuesta': f"{winner_name} por {method}",
                'confianza': method_conf_real,
            },
            {
                'mercado': 'DISTANCIA',
                'apuesta': duracion.get('pick', ''),
                'confianza': duracion.get('confianza', 0),
            },
        ]
        mejor_apuesta = max(mercados, key=lambda m: m['confianza'])

        return {
            'recomendacion': decision,
            'confianza': conf_ganador,
            'metodo': f"{method} ({method_conf}%)",
            'etiqueta_verde': etiqueta,
            'probabilidad_raw': prob / 100,
            'ganador': winner_name,
            'score1': score1,
            'score2': score2,
            'is_close': is_close,
            'method_detail': {'type': method, 'confidence': method_conf},
            'duracion': duracion,
            'mercados': mercados,
            'mejor_apuesta': mejor_apuesta,
            'metodo_probs': metodo_probs,       # {KO/TKO: %, Sumisión: %, Decisión: %}
            'rounds_totales': rounds_totales,    # [{linea, pick, prob_over, ...}] (Monte Carlo)
            'montecarlo': montecarlo,            # simulación coherente (ganador/método/rounds)
            'ganador_por_metodo': f"{winner_name} por {method}",
        }
