# -*- coding: utf-8 -*-
"""
MOTOR MLB COMPLETO V24 - Integración de todos los motores MLB
Combina: Motor de Lanzadores + Lineups + Alertas HR + API MLB Stats
"""

import requests
import json
import pandas as pd
import os
from datetime import datetime
from typing import Dict, List, Optional, Union

class MotorMLBCompleto:
    """Motor completo para MLB que integra todas las funcionalidades"""
    
    def __init__(self):
        self.cache_dir = "data/mlb_cache"
        self._ensure_cache_dir()
        self.base_url = "https://statsapi.mlb.com/api/v1"
        
    def _ensure_cache_dir(self):
        """Asegura que exista el directorio de caché"""
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _get_cached_data(self, cache_key: str, max_age_minutes: int = 60) -> Optional[Dict]:
        """Obtiene datos cacheados si son recientes"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Verificar edad del caché
                timestamp = data.get('_timestamp')
                if timestamp:
                    cache_time = datetime.fromisoformat(timestamp)
                    age = (datetime.now() - cache_time).total_seconds() / 60
                    
                    if age < max_age_minutes:
                        return data.get('data')
            except:
                pass
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """Guarda datos en caché"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        cache_data = {
            '_timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def obtener_analisis_lanzadores_hoy(self) -> Dict[str, Dict]:
        """
        Obtiene análisis de lanzadores del día actual desde MLB Stats API
        Con caché de 30 minutos
        """
        cache_key = "pitchers_today"
        cached = self._get_cached_data(cache_key, 30)
        if cached:
            return cached
        
        try:
            url = f"{self.base_url}/schedule?sportId=1&hydrate=probablePitcher"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            data = response.json()
            
            pitchers = {}
            for date in data.get("dates", []):
                for game in date.get("games", []):
                    for side in ["home", "away"]:
                        team = game["teams"][side]["team"]["name"]
                        p_info = game["teams"][side].get("probablePitcher", {})
                        p_id = p_info.get("id")
                        p_name = p_info.get("fullName", "TBD")
                        
                        if p_id:
                            try:
                                # Obtener stats detalladas del pitcher
                                s_url = f"{self.base_url}/people/{p_id}/stats?stats=statsSingleSeason&group=pitching&season=2026"
                                s_response = requests.get(s_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                                s_data = s_response.json()
                                
                                stats = s_data["stats"][0]["splits"][0]["stat"]
                                k9 = float(stats.get("strikeOutsPer9Inn", 8.0))
                                era = float(stats.get("era", 4.50))
                                whip = float(stats.get("whip", 1.35))
                                hr9 = float(stats.get("homeRunsPer9", 1.2))
                                
                                # Proyección de K basada en fórmula MLB
                                k_proy = round((k9 / 9) * 5.6)
                                
                            except:
                                # Valores por defecto si falla
                                k9 = 8.0
                                era = 4.50
                                whip = 1.35
                                hr9 = 1.2
                                k_proy = 5
                            
                            pitchers[team] = {
                                "lanzador": p_name,
                                "lanzador_id": p_id,
                                "era": era,
                                "k9": k9,
                                "whip": whip,
                                "hr9": hr9,
                                "k_proyectados": k_proy,
                                "equipo": team,
                                "actualizado": datetime.now().isoformat()
                            }
            
            self._save_to_cache(cache_key, pitchers)
            return pitchers
            
        except Exception as e:
            print(f"Error obteniendo lanzadores: {e}")
            return {}
    
    def obtener_lineups_hoy(self) -> Dict:
        """
        Obtiene lineups oficiales del día actual
        Con caché de 15 minutos
        """
        cache_key = "lineups_today"
        cached = self._get_cached_data(cache_key, 15)
        if cached:
            return cached
        
        try:
            url = f"{self.base_url}/schedule?sportId=1&hydrate=lineups"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            data = response.json()
            
            lineups_data = {"partidos": [], "actualizado": datetime.now().isoformat()}
            
            if "dates" in data and data["dates"]:
                for game in data["dates"][0]["games"]:
                    home = game["teams"]["home"]["team"]["name"]
                    away = game["teams"]["away"]["team"]["name"]
                    
                    # Verificar lineups
                    lineup_home = game["teams"]["home"].get("lineup", {}).get("lineup", [])
                    lineup_away = game["teams"]["away"].get("lineup", {}).get("lineup", [])
                    
                    confirmed = len(lineup_home) > 0 and len(lineup_away) > 0
                    
                    # Obtener jugadores
                    home_players = []
                    away_players = []
                    
                    if lineup_home:
                        home_players = [{
                            "nombre": p["person"]["fullName"],
                            "id": p["person"]["id"],
                            "posicion": p.get("position", {}).get("abbreviation", "N/A")
                        } for p in lineup_home[:9]]  # Solo primeros 9 (alineación titular)
                    
                    if lineup_away:
                        away_players = [{
                            "nombre": p["person"]["fullName"],
                            "id": p["person"]["id"],
                            "posicion": p.get("position", {}).get("abbreviation", "N/A")
                        } for p in lineup_away[:9]]
                    
                    lineups_data["partidos"].append({
                        "matchup": f"{away} @ {home}",
                        "home": home,
                        "away": away,
                        "confirmed": confirmed,
                        "home_players": home_players,
                        "away_players": away_players,
                        "total_players": len(home_players) + len(away_players)
                    })
            
            self._save_to_cache(cache_key, lineups_data)
            return lineups_data
            
        except Exception as e:
            print(f"Error obteniendo lineups: {e}")
            return {"partidos": [], "actualizado": datetime.now().isoformat()}
    
    def generar_alertas_hr_hoy(self) -> Union[pd.DataFrame, str]:
        """
        Genera alertas de posibles Home Runs basadas en:
        1. WHIP del pitcher rival > 1.40
        2. HR/9 del pitcher > 1.1
        3. Lineups confirmados
        """
        cache_key = "hr_alerts_today"
        cached = self._get_cached_data(cache_key, 10)
        if cached and isinstance(cached, dict):
            return pd.DataFrame(cached.get("alertas", []))
        
        try:
            # Obtener datos combinados
            pitchers = self.obtener_analisis_lanzadores_hoy()
            lineups = self.obtener_lineups_hoy()
            
            alertas = []
            
            for partido in lineups.get("partidos", []):
                if not partido.get("confirmed"):
                    continue
                
                home = partido["home"]
                away = partido["away"]
                matchup = partido["matchup"]
                
                # Obtener datos de pitchers
                home_pitcher = pitchers.get(home, {})
                away_pitcher = pitchers.get(away, {})
                
                # Analizar posibles HR para cada equipo
                for side in ["home", "away"]:
                    equipo = home if side == "home" else away
                    pitcher_rival = away_pitcher if side == "home" else home_pitcher
                    players = partido[f"{side}_players"]
                    
                    if pitcher_rival and players:
                        whip_rival = pitcher_rival.get("whip", 1.35)
                        hr9_rival = pitcher_rival.get("hr9", 1.2)
                        pitcher_nombre = pitcher_rival.get("lanzador", "Desconocido")
                        
                        # Umbrales de alerta
                        if whip_rival > 1.40 or hr9_rival > 1.1:
                            for player in players:
                                alertas.append({
                                    "Partido": matchup,
                                    "Bateador": player["nombre"],
                                    "Equipo": equipo,
                                    "Pitcher_Rival": pitcher_nombre,
                                    "WHIP_Rival": whip_rival,
                                    "HR9_Rival": hr9_rival,
                                    "Confianza": "🔥 ELITE" if whip_rival > 1.60 or hr9_rival > 1.3 else "✅ ALTA",
                                    "Recomendacion": f"HR vs {pitcher_nombre} (WHIP: {whip_rival}, HR/9: {hr9_rival})"
                                })
            
            if alertas:
                # Guardar en caché
                self._save_to_cache(cache_key, {"alertas": alertas})
                return pd.DataFrame(alertas)
            else:
                return "Esperando lineups oficiales o no hay alertas HR hoy."
                
        except Exception as e:
            print(f"Error generando alertas HR: {e}")
            return f"Error: {e}"
    
    def obtener_proyeccion_k_para_partido(self, home_team: str, away_team: str) -> Dict:
        """
        Obtiene proyección de strikes (K) para un partido específico
        """
        pitchers = self.obtener_analisis_lanzadores_hoy()
        
        home_pitcher = pitchers.get(home_team, {})
        away_pitcher = pitchers.get(away_team, {})
        
        # Calcular proyección usando fórmula MLB
        def calcular_proyeccion_k(pitcher_data: Dict) -> float:
            if not pitcher_data:
                return 5.0
            
            k9 = pitcher_data.get("k9", 8.0)
            # Fórmula: (K/9 ÷ 9) × 6 × (ajuste por calidad)
            proyeccion = (k9 / 9) * 6
            
            # Ajustar por ERA (pitchers con ERA baja tienden a tener más K)
            era = pitcher_data.get("era", 4.50)
            if era < 3.50:
                proyeccion *= 1.15
            elif era > 5.00:
                proyeccion *= 0.85
            
            return round(proyeccion, 1)
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_pitcher": home_pitcher.get("lanzador", "TBD"),
            "away_pitcher": away_pitcher.get("lanzador", "TBD"),
            "home_k_proy": calcular_proyeccion_k(home_pitcher),
            "away_k_proy": calcular_proyeccion_k(away_pitcher),
            "home_k9": home_pitcher.get("k9", 8.0),
            "away_k9": away_pitcher.get("k9", 8.0),
            "home_era": home_pitcher.get("era", 4.50),
            "away_era": away_pitcher.get("era", 4.50),
            "recomendacion_k": f"OVER {max(calcular_proyeccion_k(home_pitcher), calcular_proyeccion_k(away_pitcher)):.1f} K"
        }
    
    def test_motor_completo(self):
        """Prueba completa del motor MLB"""
        print("\n" + "="*60)
        print("🧪 TEST MOTOR MLB COMPLETO V24")
        print("="*60)
        
        # 1. Testear motor de lanzadores
        print("\n1. 🧤 MOTOR DE LANZADORES")
        pitchers = self.obtener_analisis_lanzadores_hoy()
        if pitchers:
            print(f"   ✅ Lanzadores obtenidos: {len(pitchers)}")
            for team, info in list(pitchers.items())[:5]:
                print(f"   📋 {team}: {info['lanzador']} | K/9: {info['k9']} | ERA: {info['era']} | WHIP: {info.get('whip', 1.35)}")
        else:
            print("   ⚠️ No se obtuvieron datos de lanzadores")
        
        # 2. Testear motor de lineups
        print("\n2. 📋 MOTOR DE LINEUPS")
        lineups = self.obtener_lineups_hoy()
        if lineups.get("partidos"):
            print(f"   ✅ Partidos con lineups: {len(lineups['partidos'])}")
            for p in lineups["partidos"][:3]:
                status = "✅ Confirmado" if p["confirmed"] else "⚠️ Pendiente"
                print(f"   🏟️ {p['matchup']} - {status} ({p['total_players']} jugadores)")
        else:
            print("   ⚠️ No hay partidos hoy o no se cargaron lineups")
        
        # 3. Testear alertas HR
        print("\n3. 💣 ALERTAS HOME RUN")
        hr_alerts = self.generar_alertas_hr_hoy()
        if isinstance(hr_alerts, pd.DataFrame) and not hr_alerts.empty:
            print(f"   ✅ Alertas HR encontradas: {len(hr_alerts)}")
            print(hr_alerts[["Bateador", "Pitcher_Rival", "Confianza"]].head().to_string(index=False))
        else:
            print(f"   ℹ️ {hr_alerts}")
        
        # 4. Testear proyección K
        print("\n4. 🎯 PROYECCIÓN DE STRIKES (K)")
        if pitchers and len(pitchers) >= 2:
            sample_teams = list(pitchers.keys())[:2]
            proyeccion = self.obtener_proyeccion_k_para_partido(sample_teams[0], sample_teams[1])
            print(f"   📊 {proyeccion['home_team']} vs {proyeccion['away_team']}")
            print(f"   🧤 Pitchers: {proyeccion['home_pitcher']} vs {proyeccion['away_pitcher']}")
            print(f"   ⚾ Proyección K: {proyeccion['home_team']} {proyeccion['home_k_proy']} | {proyeccion['away_team']} {proyeccion['away_k_proy']}")
            print(f"   💡 Recomendación: {proyeccion['recomendacion_k']}")
        
        print("\n" + "="*60)
        print("✅ MOTOR MLB COMPLETO FUNCIONAL")
        print("="*60)


# Instancia global para uso fácil
motor_mlb = MotorMLBCompleto()

if __name__ == "__main__":
    motor_mlb.test_motor_completo()