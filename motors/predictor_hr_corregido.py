# -*- coding: utf-8 -*-
"""
PREDICTOR HR PRO - VERSION CORREGIDA Y OPTIMIZADA
Correcciones principales:
1. Uso correcto de game_pk en todas las funciones
2. Integración con mlb_partidos_hoy en lugar de juegos_hoy
3. Manejo robusto de archivos faltantes
4. Optimización de memoria y tokens
"""

import json, os, unicodedata
from datetime import datetime
import requests
import streamlit as st

class PredictorHRCorregido:
    def __init__(self, data_source=None, mlb_partidos_hoy=None):
        """
        Constructor optimizado con manejo de errores robusto.
        :param data_source: Dict opcional con stats de bateadores/pitchers
        :param mlb_partidos_hoy: Lista de partidos MLB de hoy (debe incluir game_pk)
        """
        self.bateadores_stats = {}
        self.pitchers_stats = {}
        self.mlb_partidos_hoy = mlb_partidos_hoy if mlb_partidos_hoy is not None else []
        self.archivo_tracking = "data/hr_apuestas.json"
        os.makedirs("data", exist_ok=True)
        
        # Carga de datos con fallbacks robustos
        if data_source:
            self.bateadores_stats = data_source.get("bateadores", {})
            self.pitchers_stats = data_source.get("pitchers", {})
        else:
            self._cargar_datos_con_fallbacks()
    
    # ==================== UTILIDADES OPTIMIZADAS ====================
    def normalizar(self, texto):
        """Elimina acentos y caracteres especiales - optimizada para velocidad"""
        if not texto: 
            return ""
        texto = unicodedata.normalize('NFD', str(texto))
        texto = texto.encode('ascii', 'ignore').decode("utf-8")
        return texto.lower().strip().replace(".", "").replace(" jr", "").replace(" sr", "")
    
    def _cargar_datos_con_fallbacks(self):
        """Carga datos con múltiples fallbacks para robustez"""
        # Try 1: hr_datasets_completos.json
        try:
            with open("hr_datasets_completos.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.bateadores_stats = data.get("bateadores", {})
                self.pitchers_stats = data.get("pitchers", {})
                print("✓ Datos HR cargados desde hr_datasets_completos.json")
                return
        except Exception as e:
            print(f"⚠️ Error cargando hr_datasets_completos.json: {e}")
        
        # Try 2: data/hr_stats.json (fallback)
        try:
            with open("data/hr_stats.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.bateadores_stats = data.get("bateadores", {})
                self.pitchers_stats = data.get("pitchers", {})
                print("✓ Datos HR cargados desde data/hr_stats.json")
                return
        except:
            print("⚠️ No se encontraron datasets HR. Usando datos vacíos.")
            self.bateadores_stats = {}
            self.pitchers_stats = {}
    
    def _fetch_game_lineup(self, game_pk):
        """Obtiene lineup oficial con caché inteligente"""
        if not game_pk: 
            return {'home': [], 'away': []}
        
        lineup_cache_path = os.path.join("data", f"lineup_cache_{game_pk}.json")
        
        # Check cache (5 minutos de validez)
        if os.path.exists(lineup_cache_path):
            try:
                file_age = datetime.now().timestamp() - os.path.getmtime(lineup_cache_path)
                if file_age < 300:  # 5 minutos
                    with open(lineup_cache_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except:
                pass
        
        # Fetch from MLB API
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        try:
            response = requests.get(url, timeout=8)
            if response.status_code == 200:
                data = response.json()
                home_lineup = []
                away_lineup = []
                
                boxscore = data.get('liveData', {}).get('boxscore', {})
                for team_type in ['home', 'away']:
                    batters = boxscore.get('teams', {}).get(team_type, {}).get('batters', [])
                    for batter_id in batters:
                        player_data = boxscore.get('players', {}).get(f'ID{batter_id}', {})
                        full_name = player_data.get('fullName')
                        if full_name:
                            if team_type == 'home':
                                home_lineup.append(full_name)
                            else:
                                away_lineup.append(full_name)
                
                lineups = {'home': home_lineup, 'away': away_lineup}
                with open(lineup_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(lineups, f, ensure_ascii=False, indent=2)
                return lineups
        except Exception as e:
            print(f"⚠️ Error fetching lineup for {game_pk}: {e}")
        
        return {'home': [], 'away': []}
    
    def _buscar_pitcher_rival_por_game_pk(self, equipo_nombre, game_pk):
        """Busca pitcher rival usando game_pk específico - OPTIMIZADO"""
        if not game_pk or not self.mlb_partidos_hoy:
            return {"pitcher_rival": "Por anunciar", "equipo_rival": "Rival", "mano": "R"}
        
        # Buscar partido específico por game_pk
        partido = None
        for p in self.mlb_partidos_hoy:
            if str(p.get('game_pk')) == str(game_pk):
                partido = p
                break
        
        if not partido:
            return {"pitcher_rival": "Por anunciar", "equipo_rival": "Rival", "mano": "R"}
        
        eq_buscado = self.normalizar(equipo_nombre)
        local_norm = self.normalizar(partido.get('local', ''))
        visitante_norm = self.normalizar(partido.get('visitante', ''))
        
        # Determinar si el equipo es local o visitante
        if eq_buscado == local_norm or eq_buscado in local_norm or local_norm in eq_buscado:
            # Equipo es local, pitcher rival es el visitante
            return {
                "pitcher_rival": partido.get('pitchers', {}).get('visitante', {}).get('nombre', 'Por anunciar'),
                "equipo_rival": partido.get('visitante', 'Rival'),
                "mano": partido.get('pitchers', {}).get('visitante', {}).get('mano', 'R')
            }
        elif eq_buscado == visitante_norm or eq_buscado in visitante_norm or visitante_norm in eq_buscado:
            # Equipo es visitante, pitcher rival es el local
            return {
                "pitcher_rival": partido.get('pitchers', {}).get('local', {}).get('nombre', 'Por anunciar'),
                "equipo_rival": partido.get('local', 'Rival'),
                "mano": partido.get('pitchers', {}).get('local', {}).get('mano', 'R')
            }
        
        return {"pitcher_rival": "Por anunciar", "equipo_rival": "Rival", "mano": "R"}
    
    # ==================== BATEADORES OPTIMIZADOS ====================
    def obtener_bateadores_activos(self, equipo_nombre, game_pk=None):
        """Busca bateadores para un equipo con filtro por lineup real"""
        bateadores = []
        vistos = set()
        equipo_buscado_norm = self.normalizar(equipo_nombre)
        
        # Obtener lineup oficial si hay game_pk
        lineup_oficial = []
        if game_pk:
            lineups = self._fetch_game_lineup(game_pk)
            # Determinar si el equipo es local o visitante en este game_pk
            for partido in self.mlb_partidos_hoy:
                if str(partido.get('game_pk')) == str(game_pk):
                    local_norm = self.normalizar(partido.get('local', ''))
                    if equipo_buscado_norm == local_norm or equipo_buscado_norm in local_norm or local_norm in equipo_buscado_norm:
                        lineup_oficial = lineups.get('home', [])
                    else:
                        lineup_oficial = lineups.get('away', [])
                    break
        
        for nombre_bateador, stats in self.bateadores_stats.items():
            equipo_bateador = stats.get('equipo', '')
            equipo_bateador_norm = self.normalizar(equipo_bateador)
            
            # Coincidencia de equipo
            coincide_equipo = (
                equipo_bateador_norm == equipo_buscado_norm or
                equipo_buscado_norm in equipo_bateador_norm or
                equipo_bateador_norm in equipo_buscado_norm
            )
            
            if not coincide_equipo:
                continue
            
            # Filtro por lineup oficial (si está disponible)
            if lineup_oficial:
                nombre_bateador_norm = self.normalizar(nombre_bateador)
                en_lineup = False
                for jugador_lineup in lineup_oficial:
                    if nombre_bateador_norm in self.normalizar(jugador_lineup) or self.normalizar(jugador_lineup) in nombre_bateador_norm:
                        en_lineup = True
                        break
                if not en_lineup:
                    continue
            
            nombre_limpio = nombre_bateador.strip()
            if nombre_limpio in vistos:
                continue
            vistos.add(nombre_limpio)
            
            hr_total = stats.get('hr', 0)
            if hr_total >= 1:
                hr_por_juego = stats.get('hr_por_juego', hr_total / 15)
                
                # Obtener información del pitcher rival
                rival_info = self._buscar_pitcher_rival_por_game_pk(equipo_nombre, game_pk)
                p_rival = rival_info.get("pitcher_rival", "")
                
                # Factor de ajuste por pitcher rival
                factor_pitcher = 1.0
                if p_rival and p_rival not in ["Por anunciar", "TBD", "N/A"]:
                    p_stats = self.pitchers_stats.get(self.normalizar(p_rival), {})
                    hr9_rival = float(p_stats.get('hr_por_juego', 1.2))
                    
                    if hr9_rival < 0.8: factor_pitcher = 0.80
                    elif hr9_rival < 1.0: factor_pitcher = 0.90
                    elif hr9_rival > 1.5: factor_pitcher = 1.20
                    elif hr9_rival > 1.2: factor_pitcher = 1.10
                
                prob_base = hr_por_juego * 100
                prob = min(85, max(5, prob_base * factor_pitcher))
                
                bateadores.append({
                    "nombre": nombre_limpio,
                    "hr_total": hr_total,
                    "hr_por_juego": round(hr_por_juego, 2),
                    "probabilidad": round(prob, 1),
                    "en_lineup": bool(lineup_oficial)  # Indica si estaba en lineup oficial
                })
        
        bateadores.sort(key=lambda x: x['hr_total'], reverse=True)
        return bateadores[:4]  # Top 4 bateadores
    
    # ==================== PREDICCIONES OPTIMIZADAS ====================
    def obtener_predicciones_para_equipo(self, equipo, game_pk=None):
        """Genera predicciones cruzando bateador vs pitcher rival - OPTIMIZADO"""
        predicciones = []
        bateadores = self.obtener_bateadores_activos(equipo, game_pk)
        rival_info = self._buscar_pitcher_rival_por_game_pk(equipo, game_pk)
        
        for b in bateadores:
            if b['probabilidad'] < 15:  # Umbral más alto para calidad
                continue
            
            prob = b['probabilidad']
            
            # Ajuste por mano del pitcher rival
            mano_rival = rival_info.get('mano', 'R')
            if mano_rival == "L":
                prob *= 1.12  # Ligeramente mayor ventaja vs zurdos
            elif mano_rival == "R":
                prob *= 0.98  # Ligera desventaja vs derechos
            
            # Ajuste por lineup oficial
            if b.get('en_lineup', False):
                prob *= 1.15  # Bonus por estar en lineup oficial
            
            prob = min(95, max(10, prob))  # Rango controlado
            
            # Clasificación optimizada
            if prob >= 45: rec, stake, emoji = "🔥 ELITE", "3u", "🔥"
            elif prob >= 30: rec, stake, emoji = "✅ ALTA", "2u", "✅"
            elif prob >= 20: rec, stake, emoji = "📊 MEDIA", "1u", "📊"
            else: rec, stake, emoji = "⚪ BAJA", "0.5u", "⚪"
            
            predicciones.append({
                "bateador": b['nombre'],
                "equipo": equipo,
                "hr_total": b['hr_total'],
                "hr_por_juego": b['hr_por_juego'],
                "probabilidad": round(prob, 1),
                "recomendacion": rec,
                "stake": stake,
                "emoji": emoji,
                "equipo_rival": rival_info["equipo_rival"],
                "pitcher_rival": rival_info["pitcher_rival"],
                "mano_rival": mano_rival,
                "en_lineup": b.get('en_lineup', False)
            })
        
        predicciones.sort(key=lambda x: x['probabilidad'], reverse=True)
        return predicciones[:3]  # Top 3 predicciones
    
    # ==================== ANÁLISIS COMPLETO (LIGERO) ====================
    def analizar_completo_optimizado(self, jugador, equipo="", prob_ia=0, pitcher_rival=""):
        """Análisis ligero para reducir tokens"""
        puntuacion = 0
        razones = []
        
        # Factor IA (simplificado)
        if prob_ia >= 60: puntuacion += 3
        elif prob_ia >= 50: puntuacion += 2
        elif prob_ia >= 40: puntuacion += 1
        
        # Factor racha real (datos del bateador)
        datos_b = self.bateadores_stats.get(self.normalizar(jugador), {})
        if datos_b:
            hr_total = datos_b.get("hr", 0)
            if hr_total >= 5: puntuacion += 4
            elif hr_total >= 3: puntuacion += 3
            elif hr_total >= 1: puntuacion += 1
        
        # Factor pitcher rival (simplificado)
        if pitcher_rival and pitcher_rival not in ["Por anunciar", "TBD"]:
            datos_p = self.pitchers_stats.get(self.normalizar(pitcher_rival), {})
            if datos_p:
                hr_perm = datos_p.get("hr_permitidos", 0)
                if hr_perm >= 3: puntuacion += 2
                elif hr_perm >= 1: puntuacion += 1
        
        # Decisión final optimizada
        if puntuacion >= 5: rec, stake = "APOSTAR", 2
        elif puntuacion >= 3: rec, stake = "CONSIDERAR", 1
        else: rec, stake = "NO APOSTAR", 0
        
        return {
            "jugador": jugador,
            "equipo": equipo,
            "puntuacion": puntuacion,
            "recomendacion": rec,
            "stake": stake,
            "razones": razones if razones else ["Análisis básico"]
        }
    
    # ==================== MÉTODOS DE TRACKING OPTIMIZADOS ====================
    def guardar_apuesta_optimizada(self, juego, jugador, prob, rec):
        """Guarda apuesta optimizada para reducir I/O"""
        try:
            apuestas = []
            if os.path.exists(self.archivo_tracking):
                with open(self.archivo_tracking, "r", encoding="utf-8") as f:
                    apuestas = json.load(f)
            
            apuestas.append({
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "juego": juego[:50],  # Limitar longitud
                "jugador": jugador[:30],
                "probabilidad": round(prob, 1),
                "recomendacion": rec[:20],
                "resultado": None
            })
            
            # Mantener solo las últimas 100 apuestas
            if len(apuestas) > 100:
                apuestas = apuestas[-100:]
            
            with open(self.archivo_tracking, "w", encoding="utf-8") as f:
                json.dump(apuestas, f, indent=2, ensure_ascii=False)
            return True
        except:
            return False
    
    def obtener_estadisticas_resumidas(self):
        """Estadísticas resumidas para dashboard"""
        try:
            if not os.path.exists(self.archivo_tracking):
                return {"total": 0, "aciertos": 0, "tasa": 0.0}
            
            with open(self.archivo_tracking, "r", encoding="utf-8") as f:
                apuestas = json.load(f)
            
            total = len([a for a in apuestas if a.get("resultado") is not None])
            aciertos = len([a for a in apuestas if a.get("resultado") is True])
            
            return {
                "total": total,
                "aciertos": aciertos,
                "tasa": round((aciertos/total)*100, 1) if total > 0 else 0.0
            }
        except:
            return {"total": 0, "aciertos": 0, "tasa": 0.0}

# Instancia global optimizada
predictor_hr_optimizado = PredictorHRCorregido()

# Función de integración para motor_mlb_pro.py
def calcular_power_factor_optimizado(equipo, game_pk=None, predictor=None):
    """Versión optimizada para motor_mlb_pro.py"""
    if predictor is None:
        predictor = predictor_hr_optimizado
    
    try:
        predicciones = predictor.obtener_predicciones_para_equipo(equipo, game_pk=game_pk)
        if not predicciones:
            return 0, 0
        
        # Suma ponderada de probabilidades
        poder_total = sum([p.get('probabilidad', 0) * (1.5 if p.get('recomendacion', '').startswith('🔥') else 1.0) 
                          for p in predicciones])
        return round(poder_total, 1), len(predicciones)
    except Exception as e:
        print(f"⚠️ Error en calcular_power_factor_optimizado: {e}")
        return 0, 0