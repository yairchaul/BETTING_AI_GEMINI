# -*- coding: utf-8 -*-
"""
HR ANALYZER UNIFICADO V24

Combina: Prediccion IA + Statcast real + Pitcher vulnerable + Tracking
"""

import json, os
from datetime import datetime

import sqlite3 # Importar sqlite3
class HRAnalyzerUnificado:
    def __init__(self):
        self.bateadores = {}
        self.pitchers = {}
        self.archivo_tracking = "data/hr_apuestas.json"
        self.clima_engine = ClimaMLB()
        self.db_path = "data/betting_stats.db"
        os.makedirs("data", exist_ok=True)
        self.cargar()
    
    def cargar(self):
        try:
            with open("hr_datasets_completos.json", "r", encoding="utf-8") as f:
                d = json.load(f)
                self.bateadores = d.get("bateadores", {})
                self.pitchers = d.get("pitchers", {})
            return True
        except: return False
    
    def normalizar(self, n):
        import unicodedata
        if not n: return ""
        n = unicodedata.normalize('NFD', n)
        n = n.encode('ascii', 'ignore').decode("utf-8")
        return n.lower().replace(".", "").replace("-", "").strip()
    
    def buscar_bateador(self, nombre):
        nn = self.normalizar(nombre)
        for b, datos in self.bateadores.items():
            if nn in self.normalizar(b): return datos
        partes = nn.split()
        for b, datos in self.bateadores.items():
            bn = self.normalizar(b)
            for p in partes:
                if len(p) > 3 and p in bn: return datos
        return None
    
    def buscar_pitcher(self, nombre):
        if not nombre or nombre in ["Por anunciar","N/A","TBD"]: return None
        nn = self.normalizar(nombre)
        for p, datos in self.pitchers.items():
            if nn in self.normalizar(p): return datos
        return {} # Return empty dict instead of None to avoid KeyError
    
    def analizar(self, jugador, equipo="", prob_ia=0, pitcher_rival="", estadio=""):
        """Análisis avanzado con fórmula P_HR"""
        puntuacion = 0
        razones = []
        
        # 1. Componente IA
        if prob_ia >= 65: puntuacion += 3; razones.append(f"🔥 IA: {prob_ia}% HR")
        elif prob_ia >= 55: puntuacion += 2; razones.append(f"🟡 IA: {prob_ia}% HR")
        elif prob_ia >= 45: puntuacion += 1; razones.append(f"🟢 IA: {prob_ia}% HR")
        
        # 2. Stats de Bateador (ISO / FB% / Historial)
        datos_b = self.buscar_bateador(jugador)
        iso = datos_b.get("iso", 0.180) if datos_b else 0.180
        fb_pct = datos_b.get("fb_pct", 0.35) if datos_b else 0.35
        hr_total = datos_b.get("hr", 0) if datos_b else 0
        hr_juego = datos_b.get("hr_por_juego", 0) if datos_b else 0

        # 3. Stats de Pitcher Rival
        datos_p = self.buscar_pitcher(pitcher_rival)
        hr9 = datos_p.get("hr_por_juego", 1.2) if datos_p else 1.2
        pitcher_mano_rival = datos_p.get("pitch_hand", "R") # Default to Right

        # --- FACTOR DE MOMENTUM (RECENCIA) ---
        fechas_hr = self.obtener_recencia_hr(jugador)
        multiplicador_momento = 1.0
        if fechas_hr:
            ultimo_hr = datetime.strptime(fechas_hr[0], "%Y-%m-%d")
            dias_desde_ultimo = (datetime.now() - ultimo_hr).days
            if dias_desde_ultimo <= 3:
                multiplicador_momento = 1.20 # Bono del 20% por estar en racha
                razones.append(f"🔥 CALIENTE: Anotó hace {dias_desde_ultimo} días")
            elif dias_desde_ultimo > 10:
                multiplicador_momento = 0.80 # Penalización del 20% por sequía
                razones.append(f"❄️ SEQUÍA: Sin HR en {dias_desde_ultimo} días")

        # --- FACTOR MANO DEL PITCHER RIVAL (PLATOON SPLIT) ---
        # Asumimos que un bateador fuerte (ISO > 0.200) tiene un bono contra zurdos
        if pitcher_mano_rival == 'L' and iso >= 0.200:
            multiplicador_momento *= 1.15 # Bono del 15% contra zurdos para bateadores de poder
            razones.append(f"💪 MATCHUP: Bateador de poder vs Zurdo ({pitcher_mano_rival}) (+15%)")

        # --- CÁLCULO P_HR INDEXADA ---
        p_hr = ((iso * 0.4) + (hr9 * 0.3) + (fb_pct * 0.2)) * multiplicador_momento
        
        # Ajuste Clima (Factor 0.1)
        clima = self.clima_engine.obtener_clima(estadio)
        if clima["wind_speed"] >= 12 and clima["wind_dir"] == "Out":
            p_hr += 0.15
            razones.append("💨 Viento Out (+15%)")

        p_hr_final = min(95, p_hr * 100)

        # Jerarquía V24
        if p_hr_final >= 72: rec, stake, emoji = "🔥 ÉLITE HR", 4, "👑"
        elif p_hr_final >= 60: rec, stake, emoji = "✅ ALTA HR", 3, "🔥"
        elif p_hr_final >= 45: rec, stake, emoji = "🟡 MEDIA HR", 2, "⚾"
        else: rec, stake, emoji = "⚪ EVITAR", 0, "❌"

        if datos_b:
            if hr_juego >= 2.0: puntuacion += 5; razones.append(f"💣 {hr_total} HR en 15 dias ({hr_juego:.1f}/juego)")
            elif hr_juego >= 1.5: puntuacion += 4; razones.append(f"🔥 {hr_total} HR ({hr_juego:.1f}/juego)")
        
        return {
            "jugador": jugador, "equipo": equipo, "prob_ia": prob_ia,
            "probabilidad": round(p_hr_final, 1),
            "puntuacion": int(p_hr_final/10), "recomendacion": rec,
            "stake": stake, "emoji": emoji, "razones": razones
        }
    
    def analizar_partido(self, jugadores, pitcher_rival=""):
        resultados = []
        for j in jugadores:
            if isinstance(j, dict):
                n = j.get("nombre", j.get("name", "")) # Usar 'nombre' o 'name'
                e = j.get("equipo", "")
                p = j.get("hr_prob", j.get("prob", 0))
                estadio_partido = j.get("stadium", "") # Obtener el estadio del partido
                if n: resultados.append(self.analizar(n, e, p, pitcher_rival, estadio=estadio_partido))
        resultados.sort(key=lambda x: x["puntuacion"], reverse=True)
        return resultados[:5]
    
    def obtener_top_bateadores(self, limite=10):
        m = []
        for n, d in self.bateadores.items():
            if d.get("hr_por_juego", 0) >= 0.5:
                m.append({"nombre": n, "equipo": d.get("equipo","N/A"), "hr_total": d.get("hr",0), "hr_juego": d.get("hr_por_juego",0)})
        m.sort(key=lambda x: x["hr_juego"], reverse=True)
        return m[:limite]
    
    def guardar_apuesta(self, juego, jugador, prob, rec):
        try:
            try:
                with open(self.archivo_tracking, "r", encoding="utf-8") as f: apuestas = json.load(f)
            except: apuestas = []
            apuestas.append({"fecha": datetime.now().strftime("%Y-%m-%d"), "juego": juego, "jugador": jugador, "probabilidad": prob, "recomendacion": rec, "resultado": None})
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

hr_analyzer = HRAnalyzerUnificado()
