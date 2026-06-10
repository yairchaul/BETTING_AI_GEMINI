# -*- coding: utf-8 -*-
"""
ESPN FÚTBOL COMPLETO - Datos críticos para modelo jerárquico
Extrae: Tiros al arco, Posesión, Faltas, Hándicaps, Over/Under, BTTS
"""

import requests
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class FutbolDataExtractor:
    """Extrae datos críticos para modelo jerárquico de fútbol"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        }
        self.cache_dir = "data/futbol_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Estadios con factores conocidos
        self.factores_estadio = {
            'Camp Nou': {'over': 1.15, 'btts': 1.10},
            'Old Trafford': {'over': 1.10, 'btts': 1.05},
            'Anfield': {'over': 1.12, 'btts': 1.08},
            'Etihad Stadium': {'over': 1.08, 'btts': 1.03},
            'Stamford Bridge': {'over': 1.05, 'btts': 1.02},
            'Emirates Stadium': {'over': 1.07, 'btts': 1.04},
            'Allianz Arena': {'over': 1.12, 'btts': 1.07},
            'Signal Iduna Park': {'over': 1.15, 'btts': 1.10},
            'Santiago Bernabéu': {'over': 1.10, 'btts': 1.05},
            'San Siro': {'over': 1.05, 'btts': 1.03},
        }
    
    def obtener_partido_completo(self, equipo_local, equipo_visitante, liga_id, fecha=None):
        """Obtiene datos COMPLETOS de un partido específico"""
        cache_key = f"{liga_id}_{equipo_local}_{equipo_visitante}_{fecha or 'hoy'}"
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        # Verificar caché (1 hora)
        if os.path.exists(cache_file):
            file_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if file_age < 3600:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    pass
        
        # Si no hay fecha, buscar partidos de hoy
        if not fecha:
            fecha = datetime.now().strftime("%Y%m%d")
        
        try:
            # Obtener scoreboard
            api_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_id}/scoreboard?dates={fecha}"
            response = requests.get(api_url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                for event in data.get('events', []):
                    for comp in event.get('competitions', []):
                        competitors = comp.get('competitors', [])
                        if len(competitors) >= 2:
                            local_data = competitors[0].get('team', {})
                            visitante_data = competitors[1].get('team', {})
                            
                            local_nombre = local_data.get('displayName', '')
                            visitante_nombre = visitante_data.get('displayName', '')
                            
                            # Verificar si es el partido que buscamos
                            if (equipo_local.lower() in local_nombre.lower() and 
                                equipo_visitante.lower() in visitante_nombre.lower()):
                                
                                # Extraer estadísticas detalladas
                                stats = self._extraer_estadisticas_detalladas(competitors)
                                odds = self._extraer_cuotas_detalladas(comp)
                                predicciones = self._generar_predicciones_jerarquicas(
                                    local_nombre, visitante_nombre, stats, odds, liga_id
                                )
                                
                                resultado = {
                                    'local': local_nombre,
                                    'visitante': visitante_nombre,
                                    'liga': liga_id,
                                    'fecha': event.get('date', ''),
                                    'estadio': comp.get('venue', {}).get('fullName', 'Desconocido'),
                                    'estadisticas': stats,
                                    'cuotas': odds,
                                    'predicciones': predicciones
                                }
                                
                                # Guardar en caché
                                with open(cache_file, 'w', encoding='utf-8') as f:
                                    json.dump(resultado, f, ensure_ascii=False, indent=2)
                                
                                return resultado
        except Exception as e:
            logger.error(f"Error obteniendo partido completo: {e}")
        
        return None
    
    def _extraer_estadisticas_detalladas(self, competitors):
        """Extrae estadísticas detalladas del partido"""
        stats = {
            'local': {'goles': 0, 'tiros': 0, 'tiros_arco': 0, 'posesion': 50, 'faltas': 0, 'corners': 0},
            'visitante': {'goles': 0, 'tiros': 0, 'tiros_arco': 0, 'posesion': 50, 'faltas': 0, 'corners': 0}
        }
        
        try:
            for i, competitor in enumerate(competitors):
                team_type = 'local' if i == 0 else 'visitante'
                
                # Goles
                score = competitor.get('score', '0')
                stats[team_type]['goles'] = int(score) if score.isdigit() else 0
                
                # Estadísticas del boxscore (si están disponibles)
                statistics = competitor.get('statistics', [])
                for stat in statistics:
                    name = stat.get('name', '').lower()
                    value = stat.get('displayValue', '0')
                    
                    if 'shots' in name:
                        stats[team_type]['tiros'] = self._parse_stat_value(value)
                    elif 'shots on goal' in name or 'shots on target' in name:
                        stats[team_type]['tiros_arco'] = self._parse_stat_value(value)
                    elif 'possession' in name:
                        stats[team_type]['posesion'] = self._parse_percentage(value)
                    elif 'fouls' in name:
                        stats[team_type]['faltas'] = self._parse_stat_value(value)
                    elif 'corner' in name:
                        stats[team_type]['corners'] = self._parse_stat_value(value)
        except Exception as e:
            logger.debug(f"Error extrayendo estadísticas: {e}")
        
        # Asegurar que la posesión suma 100%
        total_pos = stats['local']['posesion'] + stats['visitante']['posesion']
        if total_pos > 0:
            stats['local']['posesion'] = round(stats['local']['posesion'] / total_pos * 100, 1)
            stats['visitante']['posesion'] = round(100 - stats['local']['posesion'], 1)
        
        return stats
    
    def _extraer_cuotas_detalladas(self, competition):
        """Extrae cuotas detalladas"""
        odds = {
            'moneyline': {'local': 'N/A', 'empate': 'N/A', 'visitante': 'N/A'},
            'handicap': {'local': 'N/A', 'visitante': 'N/A', 'valor': 0},
            'over_under': {'over': 'N/A', 'under': 'N/A', 'linea': 2.5},
            'btts': {'si': 'N/A', 'no': 'N/A'}
        }
        
        try:
            odds_data = competition.get('odds', [])
            if odds_data:
                raw_odds = odds_data[0]
                
                # Moneyline
                if 'homeTeamOdds' in raw_odds:
                    odds['moneyline']['local'] = raw_odds['homeTeamOdds'].get('american', 'N/A')
                if 'awayTeamOdds' in raw_odds:
                    odds['moneyline']['visitante'] = raw_odds['awayTeamOdds'].get('american', 'N/A')
                if 'drawOdds' in raw_odds:
                    odds['moneyline']['empate'] = raw_odds['drawOdds'].get('american', 'N/A')
                
                # Over/Under
                if 'overUnder' in raw_odds:
                    odds['over_under']['linea'] = float(raw_odds['overUnder'])
                
                # Intentar extraer handicaps
                details = raw_odds.get('details', '')
                if 'handicap' in details.lower() or 'spread' in details.lower():
                    try:
                        parts = details.split()
                        for i, part in enumerate(parts):
                            if 'handicap' in part.lower() or 'spread' in part.lower():
                                if i + 1 < len(parts):
                                    odds['handicap']['valor'] = float(parts[i + 1])
                                    break
                    except:
                        pass
        except Exception as e:
            logger.debug(f"Error extrayendo cuotas: {e}")
        
        return odds
    
    def _generar_predicciones_jerarquicas(self, local, visitante, stats, odds, liga_id):
        """Genera predicciones jerárquicas según el modelo"""
        predicciones = []
        
        # 1. Over/Under
        ou_pred = self._predecir_over_under(local, visitante, stats, odds, liga_id)
        if ou_pred:
            predicciones.append(ou_pred)
        
        # 2. BTTS (Ambos equipos marcan)
        btts_pred = self._predecir_btts(local, visitante, stats, odds, liga_id)
        if btts_pred:
            predicciones.append(btts_pred)
        
        # 3. Moneyline (Ganador)
        ml_pred = self._predecir_moneyline(local, visitante, stats, odds, liga_id)
        if ml_pred:
            predicciones.append(ml_pred)
        
        # 4. Hándicap
        handicap_pred = self._predecir_handicap(local, visitante, stats, odds, liga_id)
        if handicap_pred:
            predicciones.append(handicap_pred)
        
        # 5. Over 1.5, 2.5, 3.5
        overs_pred = self._predecir_overs(local, visitante, stats, odds, liga_id)
        predicciones.extend(overs_pred)
        
        # Ordenar por confianza
        predicciones.sort(key=lambda x: x.get('confianza', 0), reverse=True)
        
        return predicciones
    
    def _predecir_over_under(self, local, visitante, stats, odds, liga_id):
        """Predice Over/Under"""
        linea = odds['over_under']['linea']
        goles_local = stats['local']['goles']
        goles_visitante = stats['visitante']['goles']
        tiros_arco_local = stats['local']['tiros_arco']
        tiros_arco_visitante = stats['visitante']['tiros_arco']
        
        # Cálculo básico
        goles_esperados = (tiros_arco_local * 0.3) + (tiros_arco_visitante * 0.3)
        goles_esperados = max(1.5, min(4.5, goles_esperados))
        
        diferencia = goles_esperados - linea
        confianza = min(90, max(30, 50 + abs(diferencia) * 20))
        
        pick = "OVER" if goles_esperados > linea else "UNDER"
        
        return {
            'tipo': 'OVER_UNDER',
            'pick': f"{pick} {linea}",
            'confianza': round(confianza, 1),
            'goles_esperados': round(goles_esperados, 2),
            'linea': linea,
            'razon': f"Goles esperados: {goles_esperados:.1f} vs Línea: {linea}"
        }
    
    def _predecir_btts(self, local, visitante, stats, odds, liga_id):
        """Predice Both Teams To Score"""
        # Factor de ataque basado en tiros al arco
        factor_local = stats['local']['tiros_arco'] / 5 if stats['local']['tiros_arco'] > 0 else 0.3
        factor_visitante = stats['visitante']['tiros_arco'] / 5 if stats['visitante']['tiros_arco'] > 0 else 0.3
        
        probabilidad_si = min(85, max(15, (factor_local * 40 + factor_visitante * 40)))
        probabilidad_no = 100 - probabilidad_si
        
        pick = "SI" if probabilidad_si > 55 else "NO"
        confianza = max(probabilidad_si, probabilidad_no)
        
        return {
            'tipo': 'BTTS',
            'pick': f"BTTS {pick}",
            'confianza': round(confianza, 1),
            'prob_si': round(probabilidad_si, 1),
            'prob_no': round(probabilidad_no, 1),
            'razon': f"Tiros al arco: Local {stats['local']['tiros_arco']}, Visitante {stats['visitante']['tiros_arco']}"
        }
    
    def _predecir_moneyline(self, local, visitante, stats, odds, liga_id):
        """Predice Moneyline"""
        # Basado en posesión y tiros al arco
        ventaja_local = (
            (stats['local']['posesion'] - 50) * 0.5 +
            (stats['local']['tiros_arco'] - stats['visitante']['tiros_arco']) * 2
        )
        
        if ventaja_local > 5:
            pick = local
            confianza = min(85, max(40, 50 + ventaja_local))
        elif ventaja_local < -5:
            pick = visitante
            confianza = min(85, max(40, 50 + abs(ventaja_local)))
        else:
            pick = "EMPATE"
            confianza = min(70, max(30, 50 - abs(ventaja_local)))
        
        return {
            'tipo': 'MONEYLINE',
            'pick': pick,
            'confianza': round(confianza, 1),
            'ventaja_local': round(ventaja_local, 1),
            'razon': f"Posesión: {stats['local']['posesion']}% vs {stats['visitante']['posesion']}%"
        }
    
    def _predecir_handicap(self, local, visitante, stats, odds, liga_id):
        """Predice Hándicap"""
        diferencia_goles = stats['local']['goles'] - stats['visitante']['goles']
        
        if diferencia_goles >= 2:
            handicap = 1.5
            pick = f"{local} -{handicap}"
            confianza = min(80, max(40, 60 + diferencia_goles * 10))
        elif diferencia_goles >= 1:
            handicap = 0.5
            pick = f"{local} -{handicap}"
            confianza = min(70, max(35, 50 + diferencia_goles * 10))
        elif diferencia_goles <= -2:
            handicap = 1.5
            pick = f"{visitante} -{handicap}"
            confianza = min(80, max(40, 60 + abs(diferencia_goles) * 10))
        elif diferencia_goles <= -1:
            handicap = 0.5
            pick = f"{visitante} -{handicap}"
            confianza = min(70, max(35, 50 + abs(diferencia_goles) * 10))
        else:
            return None
        
        return {
            'tipo': 'HANDICAP',
            'pick': pick,
            'confianza': round(confianza, 1),
            'handicap': handicap,
            'razon': f"Diferencia de goles: {diferencia_goles}"
        }
    
    def _predecir_overs(self, local, visitante, stats, odds, liga_id):
        """Predice Over 1.5, 2.5, 3.5"""
        goles_esperados = (stats['local']['tiros_arco'] * 0.3) + (stats['visitante']['tiros_arco'] * 0.3)
        goles_esperados = max(1.0, min(5.0, goles_esperados))
        
        predicciones = []
        
        for linea in [1.5, 2.5, 3.5]:
            if goles_esperados > linea:
                confianza = min(90, max(30, (goles_esperados - linea) * 30 + 40))
                predicciones.append({
                    'tipo': f'OVER_{linea}',
                    'pick': f"OVER {linea}",
                    'confianza': round(confianza, 1),
                    'linea': linea,
                    'razon': f"Goles esperados: {goles_esperados:.1f} > {linea}"
                })
        
        return predicciones
    
    def _parse_stat_value(self, value):
        """Parsea valor de estadística a número"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            return float(''.join(filter(str.isdigit, str(value))) or 0)
        except:
            return 0
    
    def _parse_percentage(self, value):
        """Parsea porcentaje a número"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            value_str = str(value).replace('%', '').strip()
            return float(value_str)
        except:
            return 50.0


class FutbolScraperCompleto:
    """Scraper completo para modelo jerárquico"""
    
    def __init__(self):
        self.extractor = FutbolDataExtractor()
        self.ligas_ids = {
            "Premier League": "eng.1",
            "La Liga": "esp.1",
            "Serie A": "ita.1",
            "Bundesliga": "ger.1",
            "Ligue 1": "fra.1",
            "Liga MX": "mex.1",
            "MLS": "usa.1",
            "Eredivisie": "ned.1",
            "Primeira Liga": "por.1",
            "Scottish Premiership": "sco.1",
            "A-League": "aus.1",
            "J1 League": "jpn.1",
            "K League 1": "kor.1",
            "Copa del Mundo": "fifa.world",
        }
    
    def obtener_partidos_con_predicciones(self, liga_nombre, fecha=None):
        """Obtiene partidos con predicciones jerárquicas completas"""
        liga_id = self.ligas_ids.get(liga_nombre)
        if not liga_id:
            return []
        
        # Primero obtener partidos básicos
        partidos_basicos = self._obtener_partidos_basicos(liga_id, fecha)
        
        # Enriquecer cada partido con predicciones
        partidos_completos = []
        for partido in partidos_basicos:
            completo = self.extractor.obtener_partido_completo(
                partido['local'],
                partido['visitante'],
                liga_id,
                fecha
            )
            
            if completo:
                partidos_completos.append(completo)
            else:
                # Fallback: usar datos básicos
                partido['predicciones'] = self._generar_predicciones_basicas(partido)
                partidos_completos.append(partido)
        
        return partidos_completos
    
    def _obtener_partidos_basicos(self, liga_id, fecha):
        """Obtiene partidos básicos desde ESPN"""
        if not fecha:
            fecha = datetime.now().strftime("%Y%m%d")
        
        try:
            api_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_id}/scoreboard?dates={fecha}"
            response = requests.get(api_url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                partidos = []
                
                for event in data.get('events', []):
                    for comp in event.get('competitions', []):
                        competitors = comp.get('competitors', [])
                        if len(competitors) >= 2:
                            local = competitors[0].get('team', {}).get('displayName', '')
                            visitante = competitors[1].get('team', {}).get('displayName', '')
                            
                            partidos.append({
                                'local': local,
                                'visitante': visitante,
                                'liga': liga_id,
                                'fecha': event.get('date', '')[:10],
                                'estadio': comp.get('venue', {}).get('fullName', 'Desconocido')
                            })
                
                return partidos
        except Exception as e:
            logger.error(f"Error obteniendo partidos básicos: {e}")
        
        return []
    
    def _generar_predicciones_basicas(self, partido):
        """Genera predicciones básicas cuando no hay datos completos"""
        return [
            {
                'tipo': 'MONEYLINE',
                'pick': partido['local'],
                'confianza': 45.0,
                'razon': 'Datos limitados - Predicción básica'
            },
            {
                'tipo': 'OVER_UNDER',
                'pick': 'OVER 2.5',
                'confianza': 50.0,
                'razon': 'Línea estándar'
            }
        ]