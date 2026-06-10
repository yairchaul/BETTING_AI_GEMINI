# -*- coding: utf-8 -*-
"""
UFC ANALYZER UNIFICADO V24 - Módulo Maestro
Unifica: Heurística (Alcance/Altura/KO) + Sabermetrics (Edad/Accuracy/P4P) + Jerarquía de Decisiones
"""
import logging
import re

logger = logging.getLogger(__name__)

class UFCAnalyzer:
    def __init__(self):
        self.rankings = None
        try:
            from scrapers.ufc_rankings_scraper import UFCRankingsScraper # Importación corregida
            self.rankings = UFCRankingsScraper()
        except ImportError:
            logger.warning("UFCRankingsScraper no encontrado. Se omitirá el bono P4P.")

        # Umbrales rescatados de la versión Enhanced
        self.umbral_ko = 0.65
        self.umbral_favorito = 0.60
        self.umbral_cierre = 0.45

    def _to_num(self, val):
        if isinstance(val, (int, float)): return val
        try: return float(val)
        except: return 0

    def _extraer_victorias(self, record):
        try:
            parts = str(record).split('-')
            return int(parts[0]) if len(parts) >= 1 else 0
        except:
            return 0

    def _parse_streak(self, streak_str: str) -> int:
        """Convierte una racha como 'W3' a 3 o 'L2' a -2."""
        if not isinstance(streak_str, str) or not streak_str:
            return 0
        # Usamos una expresión regular para capturar la letra y el número
        match = re.match(r'([WL])(\d+)', streak_str.upper())
        if match:
            tipo, valor = match.groups()
            valor = int(valor)
            return valor if tipo == 'W' else -valor
        return 0

    def _parse_height_to_cm(self, height_str: str) -> float:
        """Convierte altura en formato 'pies\'pulgadas"' a cm."""
        if not isinstance(height_str, str):
            return 0.0
        try:
            # Limpiar la cadena de entrada
            height_str = height_str.replace('"', '').strip()
            parts = height_str.split("'")
            feet = float(parts[0]) if parts[0] else 0.0
            inches = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
            return (feet * 30.48) + (inches * 2.54)
        except (ValueError, IndexError):
            return 0.0

    def _parse_reach_to_cm(self, reach_str: str) -> float:
        """Convierte alcance en formato 'pulgadas"' a cm."""
        if not isinstance(reach_str, str):
            return 0.0
        try:
            inches = float(reach_str.replace('"', '').strip())
            return inches * 2.54
        except (ValueError, IndexError):
            return 0.0

    def calculate_score(self, fighter, opponent):
        """Calcula el Power Score basado en 9 pilares técnicos."""
        score = 50
        
        # 1. CAMPEÓN / P4P
        if self.rankings:
            name = fighter.get('nombre', '')
            bonus = self.rankings.get_bonus(name)
            if bonus >= 0.05: score += 10
            elif bonus >= 0.03: score += 5
            
            p4p_pos = self.rankings.get_p4p_position(name)
            if p4p_pos and p4p_pos <= 10: score += 6

        # 2. KO Rate (Potencia)
        ko = self._to_num(fighter.get('ko_rate', 0))
        if isinstance(ko, str): ko = 0
        if ko > 1: ko /= 100
        if ko >= 0.65: score += 8
        elif ko >= 0.45: score += 4

        # 3. Ventaja Física (Alcance) - Pilar Heurístico (Corregido)
        a1 = self._parse_reach_to_cm(fighter.get('alcance', '0'))
        a2 = self._parse_reach_to_cm(opponent.get('alcance', '0'))
        if a1 > 0 and a2 > 0 and a1 > a2 + 5: # Ventaja crítica de 5cm
            score += 7
            # BONO ADICIONAL: Si tiene ventaja de alcance Y alto volumen de golpes
            slpm = self._to_num(fighter.get('estadisticas_carrera', {}).get('sig_strikes_landed_per_min', 0))
            if slpm >= 4.5:
                score += 3 # Bono extra por saber usar el alcance
        elif a1 > a2: score += 2

        # 3.1 Altura (Rescatado de Enhanced) (Corregido)
        h1 = self._parse_height_to_cm(fighter.get('altura', '0'))
        h2 = self._parse_height_to_cm(opponent.get('altura', '0'))
        if h1 > 0 and h2 > 0 and h1 > h2 + 5: score += 3 # Ventaja de 5cm

        # 4. Experiencia y Win Rate
        w1 = self._to_num(fighter.get('wins', 0))
        l1 = self._to_num(fighter.get('losses', 0))
        # Fallback: extraer del record string si wins/losses no están disponibles
        if w1 == 0 and fighter.get('record'):
            w1 = self._extraer_victorias(fighter.get('record', '0-0-0'))
            try:
                parts = str(fighter.get('record', '0-0-0')).split('(')[0].strip().split('-')
                l1 = int(parts[1]) if len(parts) > 1 else 0
            except:
                l1 = 0
        exp1 = w1 + l1
        if exp1 >= 20: score += 4
        
        # 5. Edad / Peak (27-32 es prime)
        age = self._to_num(fighter.get('edad', 30))
        if 27 <= age <= 32: score += 6
        elif age >= 36: score -= 4

        # 5.1 Racha Reciente (NUEVO)
        streak_val = self._parse_streak(fighter.get('streak', ''))
        if streak_val >= 3:
            score += 5 # Bono por racha de 3+ victorias
        elif streak_val <= -2:
            score -= 3 # Penalización por racha de 2+ derrotas

        # 6. Striking Accuracy (Mapeado de str_acc)
        s_acc = self._to_num(fighter.get('str_acc', 0))
        if s_acc > 1: s_acc /= 100
        if s_acc >= 0.50: score += 4

        # 7. Takedown Accuracy (Mapeado de td_acc)
        t_acc = fighter.get('td_acc', 0)
        if t_acc > 1: t_acc /= 100
        if t_acc >= 0.45: score += 4

        return score

    def analizar_combate(self, p1_data, p2_data):
        """Realiza el cruce de datos y devuelve el veredicto visual."""
        p1_nombre = p1_data.get('nombre', 'Peleador 1')
        p2_nombre = p2_data.get('nombre', 'Peleador 2')
        
        # Cálculo de Scores Técnicos
        score1 = self.calculate_score(p1_data, p2_data)
        score2 = self.calculate_score(p2_data, p1_data)
        
        total = score1 + score2
        prob = round((score1 / total) * 100) if total > 0 else 50
        
        # Determinar ganador (Siempre)
        if prob >= 50:
            winner_name, winner_data, loser_data = p1_data.get('nombre', 'P1'), p1_data, p2_data
            confianza = prob
        else:
            winner_name, winner_data, loser_data = p2_data.get('nombre', 'P2'), p2_data, p1_data
            confianza = 100 - prob

        # Predicción de Método (Normalizando tipos)
        ko_rate = self._to_num(winner_data.get('ko_rate', 0))
        if isinstance(ko_rate, (int, float)) and ko_rate > 1: ko_rate /= 100
        sub_rate = self._to_num(winner_data.get('sub_rate', 0))
        if isinstance(sub_rate, (int, float)) and sub_rate > 1: sub_rate /= 100

        # Rescatado de Pro: Si el perdedor tiene historial de ser noqueado o finalizado
        ko_losses = self._to_num(loser_data.get('ko_losses', 0))
        sub_losses = self._to_num(loser_data.get('sub_losses', 0))

        if ko_rate >= 0.55 or ko_losses >= 2: method, m_conf = "KO/TKO", 70
        elif sub_rate >= 0.35 or sub_losses >= 2: method, m_conf = "Sumisión", 65
        else: method, m_conf = "Decisión", 60
        
        # Lógica de Jerarquía de Decisiones (Rescatada de Enhanced)
        razon = "Superioridad técnica y estadística."
        if prob / 100 > self.umbral_ko and (ko_rate >= 0.50):
            decision_str = f"GANA {winner_name.upper()} POR KO/TKO"
            razon = "Dominio físico y alta potencia de finalización."
        elif confianza / 100 >= self.umbral_favorito:
            decision_str = f"GANA {winner_name.upper()} POR {method}"
            razon = "Favorito claro basado en métricas de rendimiento."
        elif self.umbral_cierre <= prob / 100 <= (1 - self.umbral_cierre):
            decision_str = f"LIGERA VENTAJA: {winner_name.upper()}"
            razon = "Pelea muy pareja, ventaja en detalles técnicos."
        else:
            decision_str = f"📊 GANA {winner_name.upper()}"

        # Etiqueta visual para Streamlit
        if confianza >= 65:
            recomendacion = f"🔥 {decision_str}"
            verde = True
        else:
            recomendacion = f"📊 {decision_str}"
            verde = False

        return {
            'recomendacion': recomendacion,
            'confianza': confianza,
            'metodo': f"{method} ({m_conf}%)",
            'etiqueta_verde': verde,
            'ganador': winner_name,
            'razon': razon,
            'probabilidad_raw': prob / 100,
            'score1': score1,
            'score2': score2,
            'is_close': 45 <= prob <= 55,
            'method_detail': {'type': method, 'confidence': m_conf}
        }