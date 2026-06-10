# motors/predictor_strikes.py
import math

class PredictorStrikes:
    """Predice strikeouts de lanzadores basado en K/9, WHIP y bateadores rivales"""
    
    # Base de datos de K/9 por lanzador (valores reales de MLB)
    PITCHERS_K9 = {
        # Lanzadores Élite (K/9 > 10)
        "Spencer Strider": 13.8, "Jacob deGrom": 12.2, "Gerrit Cole": 11.5,
        "Kevin Gausman": 11.2, "Dylan Cease": 11.0, "Zack Wheeler": 10.1,
        "Shohei Ohtani": 10.2, "Yoshinobu Yamamoto": 10.8, "Pablo Lopez": 10.5,
        "Luis Castillo": 9.8, "Corbin Burnes": 9.3, "Mitch Keller": 9.1,
        
        # Lanzadores Buenos (K/9 8.5-9.5)
        "Max Fried": 8.5, "Framber Valdez": 8.9, "Sonny Gray": 8.7,
        "Logan Allen": 8.2, "Tanner Bibee": 9.0, "Shane McClanahan": 10.2,
        
        # Lanzadores Promedio (K/9 7.5-8.5)
        "Steven Matz": 7.5, "Nick Lodolo": 9.2, "Hunter Greene": 10.5,
        "Mitch Keller": 9.1, "Jose Quintana": 7.5, "Kyle Bradish": 8.0,
        "Reid Detmers": 8.0, "Parker Messick": 8.0, "Michael King": 9.5,
        "Christian Scott": 8.5, "Andrew Painter": 10.5, "Ryne Nelson": 7.5,
        "Bryce Miller": 9.5, "Lance McCullers Jr": 9.0, "Justin Steele": 9.0,
        "Jesus Luzardo": 9.0, "Yu Darvish": 9.0, "Brayan Bello": 7.5,
        "Garrett Crochet": 10.0, "Kumar Rocker": 10.5, "Max Meyer": 9.0,
        "Griffin Jax": 9.0, "Nick Pivetta": 9.5, "Chris Sale": 10.0,
        "Robbie Ray": 9.5, "Clayton Kershaw": 8.5, "Blake Snell": 11.0
    }
    
    # WHIP por lanzador (valores reales)
    PITCHERS_WHIP = {
        "Spencer Strider": 1.09, "Jacob deGrom": 1.01, "Gerrit Cole": 1.02,
        "Kevin Gausman": 1.11, "Dylan Cease": 1.24, "Zack Wheeler": 1.07,
        "Shohei Ohtani": 1.08, "Max Fried": 1.18, "Framber Valdez": 1.41,
        "Sonny Gray": 1.29, "Logan Allen": 1.20, "Tanner Bibee": 1.15,
        "Mitch Keller": 1.25, "Steven Matz": 1.30, "Kyle Bradish": 1.45,
        "Reid Detmers": 1.34, "Parker Messick": 1.37, "Luis Castillo": 1.15,
        "Pablo Lopez": 1.10, "Yoshinobu Yamamoto": 1.08, "Clayton Kershaw": 1.12
    }
    
    # Tasa de ponches por equipo (para ajuste por rival)
    TEAM_K_RATE = {
        "New York Yankees": 28.5, "Philadelphia Phillies": 32.1, "Atlanta Braves": 24.2,
        "Los Angeles Dodgers": 22.5, "Houston Astros": 19.8, "Boston Red Sox": 25.2,
        "Texas Rangers": 29.8, "Chicago White Sox": 27.5, "Seattle Mariners": 27.8,
        "Cleveland Guardians": 20.8, "Minnesota Twins": 25.5, "Toronto Blue Jays": 21.8,
        "Cincinnati Reds": 31.5, "Pittsburgh Pirates": 30.2, "San Diego Padres": 22.1,
        "San Francisco Giants": 24.5, "Chicago Cubs": 23.8, "Miami Marlins": 26.2,
        "Colorado Rockies": 26.5, "Arizona Diamondbacks": 23.5, "Oakland Athletics": 26.9,
        "Kansas City Royals": 22.5, "Detroit Tigers": 24.5, "Tampa Bay Rays": 22.5,
        "St. Louis Cardinals": 21.5, "Milwaukee Brewers": 23.5, "Washington Nationals": 24.5,
        "New York Mets": 23.5, "Baltimore Orioles": 22.5, "Los Angeles Angels": 26.2
    }
    
    def get_k9(self, pitcher_name):
        """Obtiene K/9 del lanzador"""
        # Buscar coincidencia parcial
        for nombre, k9 in self.PITCHERS_K9.items():
            if nombre.lower() in pitcher_name.lower() or pitcher_name.lower() in nombre.lower():
                return k9
        return 8.0  # Valor por defecto
    
    def get_whip(self, pitcher_name):
        """Obtiene WHIP del lanzador"""
        for nombre, whip in self.PITCHERS_WHIP.items():
            if nombre.lower() in pitcher_name.lower() or pitcher_name.lower() in nombre.lower():
                return whip
        return 1.35  # Valor por defecto
    
    def get_team_k_rate(self, team_name):
        """Obtiene tasa de ponches del equipo rival"""
        for nombre, tasa in self.TEAM_K_RATE.items():
            if nombre.lower() in team_name.lower() or team_name.lower() in nombre.lower():
                return tasa
        return 22.0  # Promedio MLB
    
    def predecir_strikes(self, pitcher_name, equipo_rival, innings_esperados=6):
        """Predice strikeouts del lanzador"""
        k9 = self.get_k9(pitcher_name)
        whip = self.get_whip(pitcher_name)
        tasa_k_rival = self.get_team_k_rate(equipo_rival)
        
        # Ajuste por WHIP (menor WHIP = más ponches)
        whip_factor = 1.0
        if whip < 1.1:
            whip_factor = 1.15
        elif whip > 1.4:
            whip_factor = 0.85
        
        # Ajuste por rival (mayor tasa de K = más ponches)
        rival_factor = tasa_k_rival / 22.0
        
        # Fórmula de proyección
        k_esperados = round((k9 / 9) * innings_esperados * whip_factor * rival_factor, 1)
        
        # Línea de apuesta sugerida
        if k9 >= 11.0:
            linea_sugerida = 6.5
        elif k9 >= 9.5:
            linea_sugerida = 5.5
        elif k9 >= 8.0:
            linea_sugerida = 4.5
        else:
            linea_sugerida = 3.5
        
        # Determinar recomendación
        diff = k_esperados - linea_sugerida
        if diff >= 1.0:
            rec = f"OVER {linea_sugerida}"
            confianza = min(85, 60 + int(diff * 10))
        elif diff <= -1.0:
            rec = f"UNDER {linea_sugerida}"
            confianza = min(85, 60 + int(abs(diff) * 10))
        else:
            rec = "PASAR"
            confianza = 50
        
        return {
            "pitcher": pitcher_name,
            "k9": k9,
            "whip": whip,
            "k_proyectados": k_esperados,
            "linea_sugerida": linea_sugerida,
            "recomendacion": rec,
            "confianza": confianza,
            "tasa_k_rival": tasa_k_rival,
            "diff": diff
        }

# Instancia global
predictor_strikes = PredictorStrikes()

if __name__ == "__main__":
    # Prueba
    test = predictor_strikes.predecir_strikes("Gerrit Cole", "Boston Red Sox")
    print(f"Gerrit Cole: {test['k_proyectados']} K, {test['recomendacion']}")
