# -*- coding: utf-8 -*-
"""
PREDICTOR HR PRO - DINAMICO + UNIFICADO (MEJORADO)

Combina: Detección inteligente + Multiplicadores mano pitcher + Análisis completo + Visualización

Características principales:
1. Integración directa con visualizador MLB
2. Caché inteligente de lineups
3. Factores de ajuste basados en backtesting
4. Compatibilidad con clima y estadios
5. Tracking automatizado
"""

import json, os, unicodedata, hashlib
from datetime import datetime, timedelta
import streamlit as st
from database_manager import db # Importar el gestor de DB
try:
    from motors.hr_poisson import prob_hr as _prob_hr_poisson
except ImportError:
    from hr_poisson import prob_hr as _prob_hr_poisson

class PredictorHRPro:
    def __init__(self, data_source=None, mlb_partidos_hoy=None):
        """
        Constructor Dinamico Pro.
        :param data_source: Dict con stats de bateadores/pitchers
        :param mlb_partidos_hoy: Lista de partidos del día con game_pk
        """
        self.bateadores_stats = {}
        self.pitchers_stats = {}
        self.mlb_partidos_hoy = mlb_partidos_hoy or []
        self.archivo_tracking = "data/hr_apuestas_pro.json"
        self.cache_dir = "data/hr_cache"
        
        os.makedirs("data", exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        # Carga dinámica (memoria > archivos)
        if data_source:
            self.bateadores_stats = data_source.get("bateadores", {})
            self.pitchers_stats = data_source.get("pitchers", {})
        else:
            self._cargar_desde_archivo("hr_datasets_completos.json")
    
    # ==================== UTILIDADES MEJORADAS ====================
    def normalizar(self, texto):
        """Elimina acentos y caracteres especiales (optimizado)"""
        if not texto: return ""
        texto = unicodedata.normalize('NFD', texto)
        texto = texto.encode('ascii', 'ignore').decode("utf-8")
        texto = texto.lower().strip()
        
        # Eliminar sufijos comunes
        sufijos = [" jr", " sr", " ii", " iii", " iv"]
        for sufijo in sufijos:
            texto = texto.replace(sufijo, "")
        
        # Eliminar puntos
        texto = texto.replace(".", "")
        return texto
    
    def _cargar_desde_archivo(self, ruta):
        """Carga datos con caché inteligente"""
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.bateadores_stats = data.get("bateadores", {})
                self.pitchers_stats = data.get("pitchers", {})
        except Exception as e:
            print(f"⚠️ Error cargando datos: {e}")
    
    # ==================== CACHÉ DE LINEUPS INTELIGENTE ====================
    def _obtener_lineup_equipo(self, equipo_nombre, game_pk):
        """Obtiene lineup oficial usando MLB Stats API con caché en SQLite."""
        if not game_pk:
            return []
        
        # 1. Verificar caché en la base de datos
        cached_lineup = db.get_lineup_from_cache(game_pk, equipo_nombre, max_age_minutes=30)
        if cached_lineup is not None:
            return cached_lineup

        # 2. Obtener lineup desde API si no está en caché
        lineup = self._fetch_mlb_lineup(game_pk, equipo_nombre)
        
        # 3. Guardar en el caché de la base de datos
        if lineup:
            db.save_lineup_to_cache(game_pk, equipo_nombre, lineup)
        
        return lineup
    
    def _fetch_mlb_lineup(self, game_pk, equipo_nombre):
        """Obtiene lineup desde MLB Stats API"""
        import requests
        
        try:
            url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
            response = requests.get(url, timeout=10).json()
            
            # Buscar equipo en el response
            live_data = response.get('liveData', {})
            boxscore = live_data.get('boxscore', {})
            
            for team_type in ['home', 'away']:
                team_data = boxscore.get('teams', {}).get(team_type, {})
                team_name = team_data.get('team', {}).get('name', '')
                
                if self.normalizar(team_name) == self.normalizar(equipo_nombre):
                    batters = team_data.get('batters', [])
                    lineup = []
                    
                    for batter_id in batters:
                        player_data = boxscore.get('players', {}).get(f'ID{batter_id}', {})
                        if player_data:
                            player_name = player_data.get('fullName', '')
                            if player_name:
                                lineup.append(player_name)
                    
                    return lineup
            
            return []
        except Exception as e:
            print(f"❌ Error fetch lineup: {e}")
            return []
    
    # ==================== BUSQUEDA DE PITCHER RIVAL MEJORADA ====================
    def _buscar_pitcher_rival_pro(self, equipo_nombre, game_pk=None):
        """Busca pitcher rival usando información de partidos específicos"""
        equipo_norm = self.normalizar(equipo_nombre)
        
        # Buscar en partidos del día
        for partido in self.mlb_partidos_hoy:
            if game_pk and partido.get('game_pk') != game_pk:
                continue
            
            local = self.normalizar(partido.get('local', ''))
            visitante = self.normalizar(partido.get('visitante', ''))
            
            if equipo_norm == local:
                pitchers = partido.get('pitchers', {})
                return {
                    "pitcher_rival": pitchers.get('visitante', {}).get('nombre', 'TBD'),
                    "equipo_rival": partido.get('visitante', 'Rival'),
                    "mano": pitchers.get('visitante', {}).get('mano', 'R'),
                    "era": pitchers.get('visitante', {}).get('era', 0.0),
                    "k9": pitchers.get('visitante', {}).get('k9', 0.0),
                    "hr9": pitchers.get('visitante', {}).get('hr9', 1.0)
                }
            elif equipo_norm == visitante:
                pitchers = partido.get('pitchers', {})
                return {
                    "pitcher_rival": pitchers.get('local', {}).get('nombre', 'TBD'),
                    "equipo_rival": partido.get('local', 'Rival'),
                    "mano": pitchers.get('local', {}).get('mano', 'R'),
                    "era": pitchers.get('local', {}).get('era', 0.0),
                    "k9": pitchers.get('local', {}).get('k9', 0.0),
                    "hr9": pitchers.get('local', {}).get('hr9', 1.0)
                }
        
        # Fallback a método anterior
        return self._buscar_pitcher_rival_legacy(equipo_nombre)
    
    def _buscar_pitcher_rival_legacy(self, equipo_nombre):
        """Método legacy para compatibilidad"""
        try:
            with open("pitchers_hoy_selenium.json", "r", encoding="utf-8") as f:
                juegos = json.load(f).get("juegos", [])
        except:
            juegos = []
        
        eq_buscado = self.normalizar(equipo_nombre)
        
        for juego in juegos:
            away = self.normalizar(juego.get("away_team", ""))
            home = self.normalizar(juego.get("home_team", ""))
            
            if eq_buscado == away:
                return {
                    "pitcher_rival": juego.get("home_pitcher", "TBD"),
                    "equipo_rival": juego.get("home_team", "Rival"),
                    "mano": juego.get("home_pitcher_hand", "R"),
                    "era": 0.0,
                    "k9": 0.0,
                    "hr9": 1.0
                }
            elif eq_buscado == home:
                return {
                    "pitcher_rival": juego.get("away_pitcher", "TBD"),
                    "equipo_rival": juego.get("away_team", "Rival"),
                    "mano": juego.get("away_pitcher_hand", "R"),
                    "era": 0.0,
                    "k9": 0.0,
                    "hr9": 1.0
                }
        
        return {
            "pitcher_rival": "TBD",
            "equipo_rival": "Rival",
            "mano": "R",
            "era": 0.0,
            "k9": 0.0,
            "hr9": 1.0
        }
    
    # ==================== BATEADORES FILTRADOS POR LINEUP ====================
    def obtener_bateadores_activos_pro(self, equipo_nombre, game_pk=None):
        """Obtiene bateadores activos con filtro de lineup oficial"""
        bateadores_candidatos = []
        equipo_norm = self.normalizar(equipo_nombre)

        # El dataset de HR guarda el equipo como ABREVIATURA (NYY, LAD…),
        # mientras que aquí llega el nombre completo. Calculamos la abreviatura
        # para que el match funcione en ambos formatos.
        try:
            from mapeo_equipos import obtener_abreviatura
            abrev = obtener_abreviatura(equipo_nombre)
        except Exception:
            abrev = equipo_nombre[:3].upper()
        abrev_norm = self.normalizar(abrev)

        def _coincide_equipo(equipo_bateador):
            eb = self.normalizar(equipo_bateador)
            if not eb:
                return False
            return (eb == equipo_norm or eb == abrev_norm
                    or eb in equipo_norm or equipo_norm in eb)

        # Obtener lineup oficial si hay game_pk
        lineup_oficial = []
        if game_pk:
            lineup_oficial = self._obtener_lineup_equipo(equipo_nombre, game_pk)

        # Buscar bateadores del equipo
        for nombre_bateador, stats in self.bateadores_stats.items():
            equipo_bateador = stats.get('equipo', '')

            if not _coincide_equipo(equipo_bateador):
                continue
            
            # Si hay lineup oficial, verificar que el bateador esté en él
            if lineup_oficial:
                nombre_norm = self.normalizar(nombre_bateador)
                en_lineup = any(nombre_norm in self.normalizar(ln) or self.normalizar(ln) in nombre_norm for ln in lineup_oficial)
                if not en_lineup:
                    continue
            
            hr_total = stats.get('hr', 0)
            if hr_total >= 1:  # Solo bateadores con al menos 1 HR en últimos 15 días
                bateadores_candidatos.append({
                    "nombre": nombre_bateador.strip(),
                    "hr_total": hr_total,
                    "hr_por_juego": round(stats.get('hr_por_juego', hr_total/15), 2),
                    "avg": stats.get('avg', 0.0),
                    "ops": stats.get('ops', 0.0),
                    # True = confirmado en la alineación oficial; False = aún sin lineup
                    "en_lineup": bool(lineup_oficial),
                })
        
        # Ordenar por HR total (más reciente primero)
        bateadores_candidatos.sort(key=lambda x: x['hr_total'], reverse=True)
        return bateadores_candidatos[:6]  # Top 6
    
    # ==================== CALCULO DE PROBABILIDAD (POISSON CALIBRADO) ====================
    def calcular_probabilidad_hr_inteligente(self, bateador_stats, pitcher_info, estadio="", clima=None):
        """Probabilidad CALIBRADA de ≥1 HR vía el núcleo Poisson (motors.hr_poisson).
        P(≥1 HR)=1−e^(−λ), con λ = tasa·factor_pitcher·factor_parque·factor_mano y
        shrinkage de la tasa. Se topa en ~25% (realista) en vez del 95% del modelo
        viejo, que inflaba ~1.5× (validado con el backtest)."""
        hr_por_juego = bateador_stats.get("hr_por_juego", 0.0) or 0.0
        hr_total = bateador_stats.get("hr_total", 0) or 0
        ops = bateador_stats.get("ops", 0.0) or 0.0
        hr9_pitcher = pitcher_info.get("hr9", 1.0) or 1.0
        mano_pitcher = pitcher_info.get("mano", "R") or "R"

        # Factor de parque desde la base de estadios
        park_factor = 1.0
        try:
            with open("data/estadios_db.json", "r", encoding="utf-8") as f:
                estadios = json.load(f)
            if estadio in estadios:
                park_factor = estadios[estadio].get("factor_hr", 1.0)
        except Exception:
            pass

        prob_final = _prob_hr_poisson(
            hr_por_juego=hr_por_juego, hr_total=hr_total,
            pitcher_hr9=hr9_pitcher, park_factor=park_factor,
            mano_pitcher=mano_pitcher, ops=ops, clima=clima,
        )

        # Factores DESCRIPTIVOS (transparencia; no inflan la probabilidad)
        factores = []
        if hr9_pitcher > 1.4:
            factores.append(f"🎯 Pitcher vulnerable (HR/9={hr9_pitcher:.1f})")
        elif hr9_pitcher < 0.8:
            factores.append(f"🛡️ Pitcher difícil (HR/9={hr9_pitcher:.1f})")
        if mano_pitcher == "L":
            factores.append("👈 Abridor zurdo")
        if park_factor > 1.1:
            factores.append(f"🏟️ Estadio favorable ({estadio}, {park_factor:.2f})")
        elif park_factor < 0.9:
            factores.append(f"🏟️ Estadio difícil ({estadio}, {park_factor:.2f})")
        # Clima (ahora SÍ afecta la probabilidad vía hr_poisson.factor_clima)
        try:
            from motors.hr_poisson import factor_clima as _fc
        except ImportError:
            from hr_poisson import factor_clima as _fc
        fclima = _fc(clima)
        if fclima > 1.06:
            factores.append(f"🌡️ Clima a favor (calor/viento out, ×{fclima:.2f})")
        elif fclima < 0.94:
            factores.append(f"🌬️ Clima en contra (frío/viento in, ×{fclima:.2f})")
        if ops >= 0.90:
            factores.append(f"💪 Poder élite (OPS {ops:.2f})")
        if hr_total >= 20:
            factores.append(f"📊 {hr_total} HR en la temporada")

        # Stake/recomendación en la ESCALA REALISTA (el techo real es ~22%)
        if prob_final >= 21:
            stake, color, icono, recomendacion = "3u", "#00ff41", "🔥🔥", "ALTA"
        elif prob_final >= 17:
            stake, color, icono, recomendacion = "2u", "#fbbf24", "🔥", "MEDIA"
        elif prob_final >= 13:
            stake, color, icono, recomendacion = "1u", "#3b82f6", "🟡", "BAJA"
        else:
            stake, color, icono, recomendacion = "0u", "#94a3b8", "⚪", "EVITAR"

        return {
            "probabilidad": round(prob_final, 1),
            "probabilidad_base": round(prob_final, 1),
            "multiplicador": 1.0,
            "stake": stake,
            "color": color,
            "icono": icono,
            "recomendacion": recomendacion,
            "factores": factores,
            "hr_total": hr_total,
            "hr_por_juego": hr_por_juego
        }
    
    # ==================== ANALISIS COMPLETO PARA VISUALIZACIÓN ====================
    def analizar_equipo_completo(self, equipo_nombre, game_pk=None, estadio="", clima=None):
        """Análisis completo de HR para un equipo (para visualización)"""
        # Obtener bateadores activos
        bateadores = self.obtener_bateadores_activos_pro(equipo_nombre, game_pk)
        
        # Obtener información del pitcher rival
        pitcher_info = self._buscar_pitcher_rival_pro(equipo_nombre, game_pk)
        
        resultados = []
        for b in bateadores:
            # Calcular probabilidad inteligente
            probabilidad = self.calcular_probabilidad_hr_inteligente(b, pitcher_info, estadio, clima)
            
            resultados.append({
                "nombre": b['nombre'],
                "equipo": equipo_nombre,
                "hr_total": b['hr_total'],
                "hr_por_juego": b['hr_por_juego'],
                "en_lineup": b.get("en_lineup", False),
                "probabilidad": probabilidad['probabilidad'],
                "color": probabilidad['color'],
                "icono": probabilidad['icono'],
                "stake": probabilidad['stake'],
                "recomendacion": probabilidad['recomendacion'],
                "pitcher_rival": pitcher_info['pitcher_rival'],
                "mano_pitcher": pitcher_info['mano'],
                "hr9_pitcher": pitcher_info['hr9'],
                "factores": probabilidad['factores'][:3]  # Top 3 factores
            })
        
        # Ordenar por probabilidad
        resultados.sort(key=lambda x: x['probabilidad'], reverse=True)
        return resultados[:4]  # Top 4
    
    def analizar_partido_completo(self, local, visitante, game_pk=None, estadio="", clima=None):
        """Análisis completo para un partido (ambos equipos)"""
        resultados_local = self.analizar_equipo_completo(local, game_pk, estadio, clima)
        resultados_visitante = self.analizar_equipo_completo(visitante, game_pk, estadio, clima)
        
        return {
            "local": resultados_local,
            "visitante": resultados_visitante,
            "game_pk": game_pk,
            "estadio": estadio,
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== INTEGRACIÓN CON VISUALIZADOR MLB ====================
    def generar_html_visualizacion(self, analisis_partido, partido_info):
        """Genera HTML para visualización en Streamlit"""
        local = partido_info.get('local', 'Local')
        visitante = partido_info.get('visitante', 'Visitante')
        
        html = f"""
        <div style='background: linear-gradient(135deg, #1e293b, #0f172a); padding: 20px; border-radius: 15px; margin: 10px 0; border: 2px solid #3b82f6;'>
            <h3 style='color: #60a5fa; text-align: center; margin-bottom: 20px;'>💣 PREDICTOR HR PRO - {local} vs {visitante}</h3>
            
            <div style='display: flex; justify-content: space-between;'>
                <div style='width: 48%;'>
                    <h4 style='color: #3b82f6; border-bottom: 1px solid #3b82f6; padding-bottom: 5px;'>{local}</h4>
        """
        
        # Bateadores locales
        for i, bateador in enumerate(analisis_partido.get('local', [])):
            html += f"""
                    <div style='background: rgba(59, 130, 246, 0.1); padding: 10px; margin: 8px 0; border-radius: 8px; border-left: 4px solid {bateador["color"]};'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <div>
                                <strong style='color: #fff;'>{bateador["icono"]} {bateador["nombre"]}</strong><br>
                                <span style='color: #94a3b8; font-size: 12px;'>vs {bateador["pitcher_rival"]} ({bateador["mano_pitcher"]})</span>
                            </div>
                            <div style='text-align: right;'>
                                <span style='color: {bateador["color"]}; font-size: 18px; font-weight: bold;'>{bateador["probabilidad"]}%</span><br>
                                <span style='color: #fbbf24; font-size: 12px;'>{bateador["stake"]} | {bateador["recomendacion"]}</span>
                            </div>
                        </div>
                        <div style='margin-top: 5px;'>
                            <span style='color: #94a3b8; font-size: 11px;'>{bateador["hr_total"]} HR ({bateador["hr_por_juego"]}/juego) • HR/9 pitcher: {bateador["hr9_pitcher"]:.1f}</span>
                        </div>
                    </div>
            """
        
        html += """
                </div>
                
                <div style='width: 48%;'>
                    <h4 style='color: #ef4444; border-bottom: 1px solid #ef4444; padding-bottom: 5px;'>{visitante}</h4>
        """.replace("{visitante}", visitante)
        
        # Bateadores visitantes
        for i, bateador in enumerate(analisis_partido.get('visitante', [])):
            html += f"""
                    <div style='background: rgba(239, 68, 68, 0.1); padding: 10px; margin: 8px 0; border-radius: 8px; border-left: 4px solid {bateador["color"]};'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <div>
                                <strong style='color: #fff;'>{bateador["icono"]} {bateador["nombre"]}</strong><br>
                                <span style='color: #94a3b8; font-size: 12px;'>vs {bateador["pitcher_rival"]} ({bateador["mano_pitcher"]})</span>
                            </div>
                            <div style='text-align: right;'>
                                <span style='color: {bateador["color"]}; font-size: 18px; font-weight: bold;'>{bateador["probabilidad"]}%</span><br>
                                <span style='color: #fbbf24; font-size: 12px;'>{bateador["stake"]} | {bateador["recomendacion"]}</span>
                            </div>
                        </div>
                        <div style='margin-top: 5px;'>
                            <span style='color: #94a3b8; font-size: 11px;'>{bateador["hr_total"]} HR ({bateador["hr_por_juego"]}/juego) • HR/9 pitcher: {bateador["hr9_pitcher"]:.1f}</span>
                        </div>
                    </div>
            """
        
        html += """
                </div>
            </div>
            
            <div style='text-align: center; margin-top: 20px; padding: 10px; background: rgba(0, 255, 65, 0.1); border-radius: 10px; border: 1px solid #00ff41;'>
                <span style='color: #00ff41; font-size: 12px;'>💡 <strong>RECOMENDACIÓN:</strong> Priorizar picks con probabilidad >35% y stake ≥2u</span><br>
                <span style='color: #94a3b8; font-size: 11px;'>Factores: Pitcher vulnerable + Estadio favorable + Clima + Racha bateador</span>
            </div>
        </div>
        """
        
        return html
    
    # ==================== TRACKING Y ESTADÍSTICAS ====================
    def registrar_pick(self, partido, bateador, probabilidad, stake, resultado=None):
        """Registra un pick en el sistema de tracking"""
        try:
            try:
                with open(self.archivo_tracking, "r", encoding="utf-8") as f:
                    picks = json.load(f)
            except:
                picks = []
            
            picks.append({
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "partido": partido,
                "bateador": bateador,
                "probabilidad": probabilidad,
                "stake": stake,
                "resultado": resultado,
                "ganancia": None
            })
            
            with open(self.archivo_tracking, "w", encoding="utf-8") as f:
                json.dump(picks, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"❌ Error registrando pick: {e}")
            return False
    
    def obtener_estadisticas_pro(self):
        """Obtiene estadísticas avanzadas de picks"""
        try:
            with open(self.archivo_tracking, "r", encoding="utf-8") as f:
                picks = json.load(f)
            
            picks_resueltos = [p for p in picks if p.get("resultado") is not None]
            
            if not picks_resueltos:
                return {"total": 0, "aciertos": 0, "tasa": 0.0}
            
            total = len(picks_resueltos)
            aciertos = sum(1 for p in picks_resueltos if p["resultado"] == True)
            tasa = round((aciertos / total) * 100, 1)
            
            # Análisis por stake
            stake_stats = {}
            for p in picks_resueltos:
                stake = p.get("stake", "0u")
                if stake not in stake_stats:
                    stake_stats[stake] = {"total": 0, "aciertos": 0}
                stake_stats[stake]["total"] += 1
                if p["resultado"]:
                    stake_stats[stake]["aciertos"] += 1
            
            return {
                "total": total,
                "aciertos": aciertos,
                "tasa": tasa,
                "stake_stats": stake_stats
            }
        except:
            return {"total": 0, "aciertos": 0, "tasa": 0.0}


# Instancia global para uso directo
predictor_hr_pro = PredictorHRPro()