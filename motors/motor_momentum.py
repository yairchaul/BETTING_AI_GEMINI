import json
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

class MotorMomentumProfesional:
    """Aplica filtros profesionales basados en backtesting real"""
    
    def __init__(self):
        with open("resultados_reales_15dias.json", "r", encoding="utf-8") as f:
            self.partidos = json.load(f)
        self.cargar_inteligencia()
    
    def cargar_inteligencia(self):
        try:
            with open("data/inteligencia_umpires.json", "r", encoding="utf-8") as f:
                self.umpires = json.load(f)
        except:
            self.umpires = {}
        
        try:
            with open("data/factor_ou_diario.json", "r", encoding="utf-8") as f:
                self.factor_ou = json.load(f)
        except:
            self.factor_ou = {"factor_ou": 0}
    
    def obtener_ultimo_juego(self, equipo):
        """Busca el último juego de un equipo en el historial"""
        for p in reversed(self.partidos): # Buscar de más reciente a más antiguo
            if equipo in [p.get("visitante", ""), p.get("local", "")]:
                return p
        return None

    def obtener_ultimos_n_resultados(self, equipo, n=5):
        """Obtiene los últimos N resultados (ganado/perdido) para un equipo"""
        resultados = []
        for p in reversed(self.partidos):
            if equipo in [p.get("visitante", ""), p.get("local", "")]:
                resultados.append(1 if p.get("ganador") == equipo else 0)
                if len(resultados) == n: break
        return resultados

    def calcular_coeficiente_variacion(self, equipo):
        """Busca el último juego de un equipo"""
        for p in self.partidos:
            if equipo in [p.get("visitante", ""), p.get("local", "")]:
                return p
        return None
    
    def aplicar_filtros_profesionales(self, partido, resultado_heurístico):
        """
        Aplica TODOS los filtros profesionales:
        1. Efecto rebote (explosión ofensiva)
        2. Momentum shutout
        3. Viaje/cansancio
        4. Factor umpire
        5. Récord ponderado
        6. Cambio tendencia OVER/UNDER
        """
        pick = resultado_heurístico.get("pick", "")
        confianza = resultado_heurístico.get("confianza", 50)
        diff = resultado_heurístico.get("diff", 0)
        ajustes = []
        
        away = partido.get("visitante", "")
        home = partido.get("local", "")
        
        # 1. PENALTY DE FATIGA OFENSIVA (explosión >10 runs ayer)
        ultimo_away = self.obtener_ultimo_juego(away)
        ultimo_home = self.obtener_ultimo_juego(home)
        
        if ultimo_away:
            runs_away = ultimo_away.get("score_visitante", 0) if ultimo_away.get("visitante") == away else ultimo_away.get("score_local", 0)
            if runs_away >= 10:
                confianza *= 0.92
                ajustes.append(f"🔥 {away} anotó {runs_away} runs ayer (-8% confianza)")
        
        if ultimo_home:
            runs_home = ultimo_home.get("score_local", 0) if ultimo_home.get("local") == home else ultimo_home.get("score_visitante", 0)
            if runs_home >= 10:
                confianza *= 0.92
                ajustes.append(f"🔥 {home} anotó {runs_home} runs ayer (-8% confianza)")
        
        # 2. BONO DE MOMENTUM (shutout ayer)
        if ultimo_away:
            runs_recibidos_away = ultimo_away.get("score_local", 0) if ultimo_away.get("visitante") == away else ultimo_away.get("score_visitante", 0)
            if runs_recibidos_away == 0:
                confianza *= 1.08
                ajustes.append(f"🛡️ {away} blanqueó ayer (+8% confianza)")
        
        if ultimo_home:
            runs_recibidos_home = ultimo_home.get("score_visitante", 0) if ultimo_home.get("local") == home else ultimo_home.get("score_local", 0)
            if runs_recibidos_home == 0:
                confianza *= 1.08
                ajustes.append(f"🛡️ {home} blanqueó ayer (+8% confianza)")
        
        # 3. FACTOR UMPIRE
        umpire = partido.get("umpire", "")
        if umpire in self.umpires:
            u = self.umpires[umpire]
            factor_u = u.get("factor_influencia", 1.0)
            tendencia_u = u.get("tendencia_real", "NEUTRAL")
            
            if factor_u < 0.9:
                confianza *= 0.85
                ajustes.append(f"⚠️ Umpire {umpire} desfavorable (factor {factor_u})")
            elif factor_u > 1.1:
                confianza *= 1.10
                ajustes.append(f"✅ Umpire {umpire} favorable (factor {factor_u})")
            
            if tendencia_u == "OVER":
                ajustes.append(f"📈 Umpire {umpire}: tendencia OVER ({u.get('avg_runs_detectado', 0)} runs/partido)")
            elif tendencia_u == "UNDER":
                ajustes.append(f"📉 Umpire {umpire}: tendencia UNDER ({u.get('avg_runs_detectado', 0)} runs/partido)")
        
        # 4. CAMBIO TENDENCIA OVER/UNDER
        factor_ou = self.factor_ou.get("factor_ou", 0)
        if factor_ou < -0.5:
            ajustes.append(f"📉 Tendencia UNDER detectada (factor {factor_ou})")
        elif factor_ou > 0.5:
            ajustes.append(f"📈 Tendencia OVER detectada (factor {factor_ou})")
        
        # 5. FILTRO DE CONSISTENCIA (CV)
        resultados_equipo = self.obtener_ultimos_n_resultados(pick)
        if len(resultados_equipo) >= 5:
            cv = np.std(resultados_equipo) / np.mean(resultados_equipo) if np.mean(resultados_equipo) > 0 else 0
            if cv > 0.35:
                confianza *= 0.85 # Degradar 15% si es volátil
                ajustes.append(f"⚠️ Consistencia baja (CV={cv:.2f}): -15% confianza")
            else:
                ajustes.append(f"✅ Consistencia alta (CV={cv:.2f})")


        # 5. CONFIANZA FINAL
        confianza = max(10, min(95, confianza))
        
        return {
            "pick": pick,
            "confianza_original": resultado_heurístico.get("confianza", 50),
            "confianza_ajustada": round(confianza, 1),
            "diff": diff,
            "ajustes": ajustes,
            "factor_ou": factor_ou,
        }

# Prueba
if __name__ == "__main__":
    motor = MotorMomentumProfesional()
    partido = {"visitante": "NYY", "local": "BOS", "umpire": "Andy Fletcher"}
    resultado = {"pick": "NYY", "confianza": 65, "diff": 12}
    final = motor.aplicar_filtros_profesionales(partido, resultado)
    print(json.dumps(final, indent=2, ensure_ascii=False))
