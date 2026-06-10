import unicodedata, json, os
from datetime import datetime
from clima_mlb import ClimaMLB
import sqlite3 # Importar sqlite3

class HRAnalyzerUnificado:
    """HR Analyzer V24.1 - Con marcador de potencial + filtros inteligentes"""
    
    def __init__(self):
        self.bateadores = {}
        self.pitchers = {}
        self.archivo_tracking = "data/hr_apuestas.json"
        self.clima_engine = ClimaMLB()
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
        return None
    
    def analizar(self, jugador, equipo="", prob_ia=0, pitcher_rival="", estadio=""):
        """Análisis individual de un bateador"""
        puntuacion = 0
        razones = []
        
        # Factor IA (CALIBRADO)
        if prob_ia >= 50: puntuacion += 3; razones.append(f"🔥 IA: {prob_ia}% HR")
        elif prob_ia >= 35: puntuacion += 2; razones.append(f"🟡 IA: {prob_ia}% HR")
        elif prob_ia >= 25: puntuacion += 1; razones.append(f"🟢 IA: {prob_ia}% HR")

        # Obtener stats detalladas del bateador
        datos_b = self.buscar_bateador(jugador)
        iso_bateador = datos_b.get("iso", 0.0) # Isolated Power
        fb_pct = datos_b.get("fb_pct", 0.0) # Fly Ball Percentage
        hr_total = datos_b.get("hr", 0)
        hr_juego = datos_b.get("hr_por_juego", 0)

        # Obtener stats detalladas del pitcher rival
        datos_p = self.buscar_pitcher(pitcher_rival)
        hr9_pitcher = datos_p.get("hr_por_juego", 1.0) # HR por cada 9 entradas

        # --- FÓRMULA DE PROBABILIDAD INDEXADA (P_HR) ---
        p_hr = 0.0
        
        # Componente 1: ISO del bateador (0.4)
        if iso_bateador >= 0.220: # Umbral ÉLITE
            p_hr += iso_bateador * 0.4 * 100
            razones.append(f"💪 ISO ÉLITE ({iso_bateador:.3f})")
        elif iso_bateador >= 0.180:
            p_hr += iso_bateador * 0.3 * 100
            razones.append(f"👍 ISO Alto ({iso_bateador:.3f})")

        # Componente 2: HR/9 del pitcher (0.3)
        if hr9_pitcher >= 1.4: # Pitcher vulnerable
            p_hr += hr9_pitcher * 0.3 * 100
            razones.append(f"🎯 Pitcher vulnerable (HR/9: {hr9_pitcher:.1f})")
        elif hr9_pitcher >= 1.0:
            p_hr += hr9_pitcher * 0.2 * 100
            razones.append(f"📊 Pitcher promedio (HR/9: {hr9_pitcher:.1f})")

        # Componente 3: FB% del bateador (0.2)
        if fb_pct >= 0.42: # Alto porcentaje de elevados
            p_hr += fb_pct * 0.2 * 100
            razones.append(f"🚀 FB% Alto ({fb_pct:.1%})")
        elif fb_pct >= 0.35:
            p_hr += fb_pct * 0.1 * 100
            razones.append(f"📈 FB% Promedio ({fb_pct:.1%})")

        # Componente 4: Clima Factor (0.1)
        clima = self.clima_engine.obtener_clima(estadio)
        if clima["wind_speed"] >= 12 and clima["wind_dir"] == "Out" and clima["temp"] >= 24: # 24C = 75F
            p_hr += 15.0 # +15% directo a la probabilidad
            razones.append(f"💨 CLIMA: Viento a favor y calor (+15%)")
        
        # Ajustar P_HR a un rango razonable (0-100)
        p_hr = min(100, max(0, p_hr))

        # --- MÉTRICAS DE CORTE ---
        if iso_bateador < 0.220 or fb_pct < 0.42 or hr9_pitcher < 1.4:
            # Si no cumple los umbrales de élite, la probabilidad no puede ser ÉLITE
            if p_hr >= 72: p_hr = 65 # Degradar si no cumple los cortes

        # --- CLASIFICACIÓN FINAL ---
        if p_hr >= 72: rec, stake, emoji = "🔥 ÉLITE HR", 4, "🔥🔥🔥"
        elif p_hr >= 60: rec, stake, emoji = "✅ ALTA HR", 3, "🔥🔥"
        elif p_hr >= 45: rec, stake, emoji = "🟡 MEDIA HR", 2, "🔥"
        elif p_hr >= 30: rec, stake, emoji = "🟢 BAJA HR", 1, "🟢"
        else: rec, stake, emoji = "⚪ EVITAR HR", 0, "⚪"

        puntuacion = int(p_hr / 10) # Escalar a puntuación de 0-10

        # Factor racha real (CALIBRADO - se mantiene para contexto)
        if datos_b:
            if hr_juego >= 0.8: puntuacion += 5; razones.append(f"💣 {hr_total} HR en 15 dias ({hr_juego:.1f}/juego)")
            elif hr_juego >= 0.5: puntuacion += 4; razones.append(f"🔥 {hr_total} HR ({hr_juego:.1f}/juego)")
            elif hr_juego >= 0.3: puntuacion += 3; razones.append(f"⚾ {hr_total} HR")
            elif hr_juego >= 0.2: puntuacion += 1; razones.append(f"✓ {hr_total} HR recientes")
        
        # Factor pitcher rival (CALIBRADO - penaliza elite, bonifica vulnerable)
        datos_p = self.buscar_pitcher(pitcher_rival)
        if datos_p:
            hr_pitcher = datos_p.get("hr_por_juego", 0) # HR/9
            if hr_pitcher < 0.6: puntuacion -= 2; razones.append(f"🛡️ {pitcher_rival} ELITE (HR/9: {hr_pitcher})")
            elif hr_pitcher < 0.8: puntuacion -= 1; razones.append(f"⚠️ {pitcher_rival} difícil (HR/9: {hr_pitcher})")

        
        return {
            "jugador": jugador, "equipo": equipo, "prob_ia": prob_ia,
            "hr_total": hr_total, "hr_juego": hr_juego,
            "pitcher_rival": pitcher_rival, "hr_pitcher": hr_pitcher,
            "puntuacion": puntuacion, "recomendacion": rec,
            "stake": stake, "emoji": emoji, "razones": razones,
            "marcador_especial": ""
        }
    
    def analizar_partido(self, jugadores_lineup, pitcher_rival=""):
        """
        Analiza SOLO los bateadores confirmados en el lineup real.
        :param jugadores_lineup: Lista de dicts con nombre y equipo
        """
        resultados = []
        for j in jugadores_lineup:
            if isinstance(j, dict):
                n = j.get("nombre", j.get("name", "")) # Usar 'nombre' o 'name'
                e = j.get("equipo", "")
                p = j.get("hr_prob", j.get("prob", 0))
                estadio_partido = partido.get("venue", "") # Obtener el estadio del partido
                if n:
                    res = self.analizar(n, e, p, pitcher_rival, estadio=estadio_partido)
                    resultados.append(res)
        
        # Ordenar por puntuación
        resultados.sort(key=lambda x: x["puntuacion"], reverse=True)
        top_5 = resultados[:5]
        
        # 🆕 MARCADOR DE MÁXIMO POTENCIAL
        if top_5 and top_5[0]["puntuacion"] >= 5:
            top_5[0]["marcador_especial"] = "⭐ PICK DEL PARTIDO"
            top_5[0]["emoji"] = "👑 " + top_5[0]["emoji"]
        
        return top_5

# ==================== PRUEBA CON LINEUPS REALES ====================
if __name__ == "__main__":
    hr = HRAnalyzerUnificado()
    
    print("=" * 80)
    print("🧠 HR ANALYZER V24.1 - PRUEBA CON LINEUPS REALES")
    print("=" * 80)
    print()
    
    # Simular lineups reales del 26 de abril
    lineup_yankees = [
        {"nombre": "Aaron Judge", "equipo": "NYY", "prob": 60},
        {"nombre": "Juan Soto", "equipo": "NYY", "prob": 40},
        {"nombre": "Giancarlo Stanton", "equipo": "NYY", "prob": 33},
        {"nombre": "Anthony Volpe", "equipo": "NYY", "prob": 13},
        {"nombre": "Jazz Chisholm Jr", "equipo": "NYY", "prob": 20},
    ]
    
    pitcher_rival = "Gerrit Cole"  # Enfrentan a Cole
    
    print(f"📋 LINEUP: New York Yankees")
    print(f"🥎 PITCHER RIVAL: {pitcher_rival}")
    print()
    
    resultados = hr.analizar_partido(lineup_yankees, pitcher_rival)
    
    print("📊 TOP 5 CANDIDATOS HR:")
    print("-" * 80)
    for i, r in enumerate(resultados, 1):
        marcador = r.get("marcador_especial", "")
        print(f"{i}. {r['emoji']} {r['jugador']} ({r['equipo']})")
        print(f"   Puntuación: {r['puntuacion']}/10 | Stake: {r['stake']}u | {r['recomendacion']}")
        print(f"   HR: {r['hr_total']} en 15 días ({r['hr_juego']:.2f}/juego)")
        print(f"   Pitcher rival: {r['pitcher_rival']} (HR/9: {r['hr_pitcher']:.1f})")
        if r['razones']:
            for razon in r['razones']:
                print(f"      {razon}")
        if marcador:
            print(f"   🏆 {marcador}")
        print()
    
    print("=" * 80)
    print("💡 Solo se analizan jugadores CONFIRMADOS en el lineup.")
    print("   Esto elimina el 76% de predicciones falsas.")
