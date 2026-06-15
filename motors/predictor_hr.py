# -*- coding: utf-8 -*-
"""
PREDICTOR HR PRO - DINAMICO + UNIFICADO (Ahora en motors/)
Combina: Deteccion inteligente + Multiplicadores mano pitcher + Analisis completo
"""

import json, os, unicodedata
from datetime import datetime

class PredictorHR:
    def __init__(self, data_source=None, pitchers_hoy=None):
        """
        Constructor Dinamico.
        :param data_source: Dict opcional con stats de bateadores/pitchers
        :param pitchers_hoy: Lista opcional con los juegos del dia
        """
        self.bateadores_stats = {}
        self.pitchers_stats = {}
        self.juegos_hoy = []
        self.archivo_tracking = "data/hr_apuestas.json"
        os.makedirs("data", exist_ok=True)
        
        # Carga dinamica (memoria > archivos)
        if data_source:
            self.bateadores_stats = data_source.get("bateadores", {})
            self.pitchers_stats = data_source.get("pitchers", {})
        else:
            self._cargar_desde_archivo("hr_datasets_completos.json")
        
        self.mlb_partidos_hoy = pitchers_hoy if pitchers_hoy is not None else [] # Inicializar el atributo
        # Si no se pasan partidos, intentar cargar pitchers del archivo (fallback)
        if not self.mlb_partidos_hoy:
            # Esto es un fallback, idealmente mlb_partidos_hoy se pasa desde main
            # y contiene game_pk y pitchers.
            self._cargar_pitchers_archivo("pitchers_hoy_selenium.json")
    
    # ==================== UTILIDADES ====================
    def normalizar(self, texto):
        """Elimina acentos y caracteres especiales"""
        if not texto: return ""
        texto = unicodedata.normalize('NFD', texto)
        texto = texto.encode('ascii', 'ignore').decode("utf-8")
        return texto.lower().strip().replace(".", "").replace(" jr", "").replace(" sr", "")
    
    def _cargar_desde_archivo(self, ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.bateadores_stats = data.get("bateadores", {})
                self.pitchers_stats = data.get("pitchers", {})
        except: pass
    
    def _cargar_pitchers_archivo(self, ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.juegos_hoy = data.get("juegos", [])
        except: pass
    
    def _fetch_game_lineup(self, game_pk):
        """
        Obtiene el lineup oficial de un juego específico desde MLB Stats API.
        Retorna un dict {'home': [nombres], 'away': [nombres]}
        """
        if not game_pk: return {'home': [], 'away': []}
        
        import requests # Importar requests aquí
        lineup_cache_path = os.path.join("data", f"lineup_cache_{game_pk}.json")
        if os.path.exists(lineup_cache_path):
            try:
                with open(lineup_cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass

        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        try:
            response = requests.get(url, timeout=8).json()
            home_lineup = []
            away_lineup = []
            
            # Extraer lineup del boxscore
            boxscore = response.get('liveData', {}).get('boxscore', {})
            for team_type in ['home', 'away']:
                batters = boxscore.get('teams', {}).get(team_type, {}).get('batters', [])
                for batter_id in batters:
                    player_data = boxscore.get('players', {}).get(f'ID{batter_id}', {})
                    full_name = player_data.get('fullName')
                    if full_name:
                        (home_lineup if team_type == 'home' else away_lineup).append(full_name)
            
            lineups = {'home': home_lineup, 'away': away_lineup}
            with open(lineup_cache_path, 'w', encoding='utf-8') as f: json.dump(lineups, f, ensure_ascii=False, indent=2)
            return lineups
        except Exception as e:
            print(f"Error fetching lineup for {game_pk}: {e}")
            return {'home': [], 'away': []}

    # ==================== BUSQUEDA DE PITCHER RIVAL (DINAMICO) ====================
    def _buscar_pitcher_rival(self, equipo_nombre):
        """Busca rival usando coincidencia parcial de nombres (Sin diccionarios gigantes)"""
        eq_buscado = self.normalizar(equipo_nombre)
        
        # Palabras clave para equipos problematicos
        palabras_clave = {
            "white sox": ["white sox", "chicago white sox", "medias blancas"],
            "red sox": ["red sox", "boston red sox", "medias rojas"],
            "blue jays": ["blue jays", "toronto blue jays", "azulejos"],
            "guardians": ["guardians", "cleveland guardians", "guardianes"],
            "rays": ["rays", "tampa bay rays"],
            "athletics": ["athletics", "oakland athletics", "atleticos"],
        }
        
        for juego in self.juegos_hoy:
            away = self.normalizar(juego.get("away_team", ""))
            home = self.normalizar(juego.get("home_team", ""))
            
            # Verificar coincidencia directa
            coincide_away = eq_buscado in away or away in eq_buscado
            coincide_home = eq_buscado in home or home in eq_buscado
            
            # Verificar con palabras clave
            if not coincide_away and not coincide_home:
                for clave, variantes in palabras_clave.items():
                    for v in variantes:
                        v_norm = self.normalizar(v)
                        if v_norm in eq_buscado or eq_buscado in v_norm:
                            if v_norm in away or away in v_norm:
                                coincide_away = True
                            if v_norm in home or home in v_norm:
                                coincide_home = True
                            break
            
            if coincide_away:
                return {
                    "pitcher_rival": juego.get("home_pitcher", "Por anunciar"),
                    "equipo_rival": juego.get("home_team", "Rival"),
                    "mano": juego.get("home_pitcher_hand", "R")
                }
            
            if coincide_home:
                return {
                    "pitcher_rival": juego.get("away_pitcher", "Por anunciar"),
                    "equipo_rival": juego.get("away_team", "Rival"),
                    "mano": juego.get("away_pitcher_hand", "R")
                }
        
        return {"pitcher_rival": "Por anunciar", "equipo_rival": "Rival", "mano": "R"}
    
    # ==================== BATEADORES POR EQUIPO ====================
    def obtener_bateadores_activos(self, equipo_nombre, game_pk=None):
        """Busca bateadores para un equipo usando coincidencia flexible"""
        bateadores = []
        vistos = set()
        equipo_buscado_norm = self.normalizar(equipo_nombre)
        
        for nombre_bateador, stats in self.bateadores_stats.items():
            equipo_bateador = stats.get('equipo', '')

            # --- FILTRO ESTRICTO POR LINEUP OFICIAL (FUZZY MATCHING) ---
            if game_pk:
                lineups = self._fetch_game_lineup(game_pk)
                current_lineup = []
                for p in self.mlb_partidos_hoy:
                    if p.get('game_pk') == game_pk:
                        if self.normalizar(p.get('local')) == equipo_buscado_norm:
                            current_lineup = lineups.get('home', [])
                        elif self.normalizar(p.get('visitante')) == equipo_buscado_norm:
                            current_lineup = lineups.get('away', [])
                        break
                if not any(self.normalizar(nombre_bateador) in self.normalizar(ln) or self.normalizar(ln) in self.normalizar(nombre_bateador) for ln in current_lineup):
                    continue # Si el bateador no está en el lineup de hoy, lo ignoramos
            equipo_bateador_norm = self.normalizar(equipo_bateador)
            
            # Coincidencia flexible
            coincide = (
                equipo_bateador_norm == equipo_buscado_norm or
                equipo_buscado_norm in equipo_bateador_norm or
                equipo_bateador_norm in equipo_buscado_norm
            )
            
            if not coincide: continue
            
            nombre_limpio = nombre_bateador.strip()
            if nombre_limpio in vistos: continue
            vistos.add(nombre_limpio)
            
            hr_total = stats.get('hr', 0)
            if hr_total >= 1:
                hr_por_juego = stats.get('hr_por_juego', hr_total/15)
                # Factor de ajuste por pitcher rival (MATCHUP-ADJUSTED)
                rival_info = self._buscar_pitcher_rival(equipo_nombre)
                p_rival = rival_info.get("pitcher_rival", "")
                p_stats = self.pitchers_stats.get(self.normalizar(p_rival), {})
                hr9_rival = float(p_stats.get('hr_por_juego', 1.2))
                
                factor_pitcher = 1.0
                if hr9_rival < 0.8: factor_pitcher = 0.80
                elif hr9_rival < 1.0: factor_pitcher = 0.90
                elif hr9_rival > 1.5: factor_pitcher = 1.20
                elif hr9_rival > 1.2: factor_pitcher = 1.10
                
                prob_base = hr_por_juego * 100
                prob = min(85, max(5, prob_base * factor_pitcher))
                prob = prob
                
                bateadores.append({
                    "nombre": nombre_limpio,
                    "hr_total": hr_total,
                    "hr_por_juego": round(hr_por_juego, 2),
                    "probabilidad": round(prob, 1)
                })
        
        bateadores.sort(key=lambda x: x['hr_total'], reverse=True)
        return bateadores[:4]
    
    # ==================== PREDICCIONES POR EQUIPO (CON MULTIPLICADOR DE MANO) ====================
    def obtener_predicciones_para_equipo(self, equipo, game_pk=None):
        """Genera predicciones cruzando bateador vs pitcher rival"""
        predicciones = []
        bateadores = self.obtener_bateadores_activos(equipo, game_pk) # Pasar game_pk
        rival_info = self._buscar_pitcher_rival(equipo) # Esto sigue siendo por equipo, no por game_pk
        
        for b in bateadores:
            if b['probabilidad'] < 12: continue
            
            prob = b['probabilidad']
            
            # 🆕 Ajuste por mano del pitcher rival (zurdo vs derecho)
            mano_rival = rival_info.get('mano', 'R')
            if mano_rival == "L":
                prob *= 1.1  # Bateadores suelen tener ventaja contra zurdos
            else:
                prob *= 1.0
            
            prob = min(95, prob)
            
            # Clasificacion
            if prob >= 40: rec, stake = "🔥 ELITE", "4u"
            elif prob >= 25: rec, stake = "✅ ALTA", "3u"
            else: rec, stake = "📊 MEDIA", "2u"
            
            predicciones.append({
                "bateador": b['nombre'],
                "equipo": equipo,
                "hr_total": b['hr_total'],
                "hr_por_juego": b['hr_por_juego'],
                "probabilidad": round(prob, 1),
                "recomendacion": rec,
                "stake": stake,
                "equipo_rival": rival_info["equipo_rival"],
                "pitcher_rival": rival_info["pitcher_rival"],
                "mano_rival": mano_rival
            })
        
        predicciones.sort(key=lambda x: x['probabilidad'], reverse=True)
        return predicciones[:3]
    
    # ==================== ANALISIS COMPLETO (UNIFICADO) ====================
    def buscar_bateador_stats(self, nombre):
        nn = self.normalizar(nombre)
        for b, datos in self.bateadores_stats.items():
            if nn in self.normalizar(b): return datos
        return None
    
    def buscar_pitcher_stats(self, nombre):
        if not nombre or nombre in ["Por anunciar", "N/A", "TBD"]: return None
        nn = self.normalizar(nombre)
        for p, datos in self.pitchers_stats.items():
            if nn in self.normalizar(p): return datos
        return None
    
    def analizar_completo(self, jugador, equipo="", prob_ia=0, pitcher_rival=""):
        """Analisis completo de HR con puntuacion"""
        puntuacion = 0
        razones = []
        
        # Factor IA
        if prob_ia >= 65: puntuacion += 3; razones.append(f"🔥 IA: {prob_ia}% HR")
        elif prob_ia >= 55: puntuacion += 2; razones.append(f"🟡 IA: {prob_ia}% HR")
        elif prob_ia >= 45: puntuacion += 1; razones.append(f"🟢 IA: {prob_ia}% HR")
        
        # Factor racha real
        datos_b = self.buscar_bateador_stats(jugador)
        hr_total, hr_juego = 0, 0
        if datos_b:
            hr_total = datos_b.get("hr", 0)
            hr_juego = datos_b.get("hr_por_juego", 0)
            if hr_juego >= 2.0: puntuacion += 5; razones.append(f"💣 {hr_total} HR en 15 dias ({hr_juego:.1f}/juego)")
            elif hr_juego >= 1.5: puntuacion += 4; razones.append(f"🔥 {hr_total} HR ({hr_juego:.1f}/juego)")
            elif hr_juego >= 1.0: puntuacion += 3; razones.append(f"⚾ {hr_total} HR")
            elif hr_juego >= 0.5: puntuacion += 1; razones.append(f"✓ {hr_total} HR recientes")
        
        # Factor pitcher rival
        datos_p = self.buscar_pitcher_stats(pitcher_rival)
        hr_pitcher = 0
        if datos_p:
            hr_pitcher = datos_p.get("hr_por_juego", 0)
            hr_perm = datos_p.get("hr_permitidos", 0)
            if hr_pitcher >= 2.0: puntuacion += 3; razones.append(f"🎯 {pitcher_rival} permite {hr_perm} HR ({hr_pitcher:.1f}/juego)")
            elif hr_pitcher >= 1.5: puntuacion += 2; razones.append(f"📊 {pitcher_rival} vulnerable")
            elif hr_pitcher >= 1.0: puntuacion += 1
        
        if puntuacion >= 7: rec, stake, emoji = "APOSTAR HR", 3, "🔥🔥🔥"
        elif puntuacion >= 5: rec, stake, emoji = "APOSTAR HR", 2, "🔥🔥"
        elif puntuacion >= 3: rec, stake, emoji = "CONSIDERAR HR", 1, "🟡"
        else: rec, stake, emoji = "NO APOSTAR", 0, "⚪"
        
        return {
            "jugador": jugador, "equipo": equipo, "prob_ia": prob_ia,
            "hr_total": hr_total, "hr_juego": hr_juego,
            "pitcher_rival": pitcher_rival, "hr_pitcher": hr_pitcher,
            "puntuacion": puntuacion, "recomendacion": rec,
            "stake": stake, "emoji": emoji, "razones": razones
        }
    
    def analizar_partido(self, away_team, home_team, game_pk=None):
        """Analiza todos los bateadores de un partido"""
        resultados = []
        rival_away = self._buscar_pitcher_rival(away_team)
        rival_home = self._buscar_pitcher_rival(home_team)
        
        for b in self.obtener_bateadores_activos(away_team, game_pk): # Pasar game_pk
            r = self.analizar_completo(b['nombre'], away_team, b['probabilidad'], rival_away['pitcher_rival'])
            if r['stake'] >= 1: resultados.append(r)
        
        for b in self.obtener_bateadores_activos(home_team, game_pk): # Pasar game_pk
            r = self.analizar_completo(b['nombre'], home_team, b['probabilidad'], rival_home['pitcher_rival'])
            if r['stake'] >= 1: resultados.append(r)
        
        resultados.sort(key=lambda x: x['puntuacion'], reverse=True)
        return resultados[:5]
    
    # ==================== TRACKING ====================
    def guardar_apuesta(self, juego, jugador, prob, rec):
        try:
            try:
                with open(self.archivo_tracking, "r", encoding="utf-8") as f: apuestas = json.load(f)
            except: apuestas = []
            apuestas.append({
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "juego": juego, "jugador": jugador,
                "probabilidad": prob, "recomendacion": rec, "resultado": None
            })
            with open(self.archivo_tracking, "w", encoding="utf-8") as f: json.dump(apuestas, f, indent=2, ensure_ascii=False)
            return True
        except: return False
    
    def obtener_estadisticas(self):
        try:
            with open(self.archivo_tracking, "r", encoding="utf-8") as f: apuestas = json.load(f)
            stats = {"total": 0, "aciertos": 0}
            for ap in apuestas:
                if ap["resultado"] is not None:
                    stats["total"] += 1
                    if ap["resultado"]: stats["aciertos"] += 1
            if stats["total"] > 0: stats["tasa"] = round((stats["aciertos"]/stats["total"])*100, 1)
            return stats
        except: return None


    def calcular_probabilidad_mejorada(self, bateador_stats, pitcher_rival, estadio="", dia_semana=None):
        """Calcula probabilidad HR con factores de ajuste basados en backtesting"""
        
        # Probabilidad base (hr_por_juego * 100)
        hr_juego = bateador_stats.get("hr_por_juego", 0.02)
        prob_base = min(85, hr_juego * 100)
        
        ajustes = []
        multiplicador = 1.0
        
        # Factor 1: Pitcher rival vulnerable (HR/9 > 1.5)
        pitcher_stats = self.buscar_pitcher_stats(pitcher_rival) if hasattr(self, 'buscar_pitcher_stats') else None
        if pitcher_stats:
            hr9 = pitcher_stats.get("hr_por_juego", 1.0)
            if hr9 > 1.5:
                multiplicador *= 1.3
                ajustes.append(f"🎯 Pitcher vulnerable (HR/9={hr9:.1f}): x1.3")
            elif hr9 > 1.2:
                multiplicador *= 1.15
                ajustes.append(f"📊 Pitcher algo vulnerable (HR/9={hr9:.1f}): x1.15")
            elif hr9 < 0.6:
                multiplicador *= 0.7
                ajustes.append(f"🛡️ Pitcher élite (HR/9={hr9:.1f}): x0.7")
        
        # Factor 2: Estadio favorable (factor HR > 1.15)
        try:
            with open("data/estadios_db.json", "r", encoding="utf-8") as f:
                estadios = json.load(f)
            if estadio in estadios:
                factor_hr = estadios[estadio].get("factor_hr", 1.0)
                if factor_hr > 1.2:
                    multiplicador *= 1.2
                    ajustes.append(f"🏟️ Estadio favorable ({estadio}): x1.2")
                elif factor_hr > 1.1:
                    multiplicador *= 1.1
                    ajustes.append(f"🏟️ Estadio algo favorable ({estadio}): x1.1")
                elif factor_hr < 0.85:
                    multiplicador *= 0.85
                    ajustes.append(f"🏟️ Estadio difícil ({estadio}): x0.85")
        except:
            pass
        
        # Factor 3: Día de la semana (viernes/sábado = más HR)
        if dia_semana is None:
            dia_semana = datetime.now().weekday()
        
        if dia_semana in [4, 5]:  # Viernes o Sábado
            multiplicador *= 1.15
            ajustes.append(f"📅 Fin de semana: x1.15")
        elif dia_semana == 0:  # Lunes
            multiplicador *= 1.10
            ajustes.append(f"📅 Lunes (alta tendencia HR): x1.10")
        elif dia_semana == 6:  # Domingo
            multiplicador *= 0.90
            ajustes.append(f"📅 Domingo (baja tendencia HR): x0.90")
        
        # Factor 4: Temperatura (si hay datos de clima)
        # (Se puede integrar con clima_mlb.py)
        
        prob_final = min(92, prob_base * multiplicador)
        
        # Determinar stake según probabilidad final
        if prob_final >= 50:
            stake = "4u"
            recomendacion = "🔥🔥🔥 ELITE"
        elif prob_final >= 35:
            stake = "3u"
            recomendacion = "🔥🔥 ALTA"
        elif prob_final >= 25:
            stake = "2u"
            recomendacion = "🔥 MEDIA"
        elif prob_final >= 18:
            stake = "1u"
            recomendacion = "🟡 BAJA"
        else:
            stake = "0u"
            recomendacion = "⚪ EVITAR"
        
        return {
            "probabilidad": round(prob_final, 1),
            "probabilidad_base": round(prob_base, 1),
            "multiplicador": round(multiplicador, 2),
            "ajustes": ajustes,
            "stake": stake,
            "recomendacion": recomendacion,
            "hr_total": bateador_stats.get("hr", 0),
            "hr_juego": hr_juego,
        }


    def calcular_probabilidad_refinada(self, bateador_stats, pitcher_rival, umpire_nombre=""):
        """Probabilidad HR con factores de umpire y pitcher"""
        hr_por_juego = bateador_stats.get("hr_por_juego", 0.02)
        prob = min(85, hr_por_juego * 100)
        
        # Factor pitcher rival
        if pitcher_rival and pitcher_rival != "TBD":
            pitcher_stats = self.bateadores_stats.get(pitcher_rival, {}) if hasattr(self, 'bateadores_stats') else {}
            if not pitcher_stats:
                try:
                    pitcher_stats = self.buscar_pitcher_stats(pitcher_rival) if hasattr(self, 'buscar_pitcher_stats') else {}
                except:
                    pass
        
        # Factor umpire
        if umpire_nombre:
            try:
                import json
                with open("data/inteligencia_umpires.json", "r", encoding="utf-8") as f:
                    umpires = json.load(f)
                if umpire_nombre in umpires:
                    u = umpires[umpire_nombre]
                    if u.get("tendencia_real") == "OVER":
                        prob *= 1.10
                    elif u.get("tendencia_real") == "UNDER":
                        prob *= 0.90
            except:
                pass
        
        return round(min(92, max(5, prob)), 1)

# Instancia global
predictor_hr = PredictorHR()
