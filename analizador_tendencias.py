# -*- coding: utf-8 -*-
"""
ANALIZADOR DE TENDENCIAS V2 - Detección dinámica de equipos trampa
Aprende de resultados reales y ajusta automáticamente
"""
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

class AnalizadorTendencias:
    def __init__(self):
        self.archivo_backtesting = "resultados_reales_15dias.json"
        self.archivo_aprendizaje = "data/aprendizaje_semanal.json"
        
        # Asegurar que el directorio existe
        os.makedirs("data", exist_ok=True)
        
        # Crear archivo si no existe
        if not os.path.exists(self.archivo_aprendizaje):
            with open(self.archivo_aprendizaje, "w", encoding="utf-8") as f:
                json.dump({
                    "umbrales_optimos": {},
                    "equipos_trampa": [],
                    "dias_optimos": {},
                    "handicaps_optimos": {},
                    "factores_ajuste": {},
                    "historial_semanal": []
                }, f, indent=2)
        
        self.cargar_datos()
    
    def cargar_datos(self):
        """Carga datos de forma segura"""
        try:
            with open(self.archivo_backtesting, "r", encoding="utf-8") as f:
                self.partidos = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.partidos = []
        
        try:
            with open(self.archivo_aprendizaje, "r", encoding="utf-8") as f:
                self.aprendizaje = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.aprendizaje = {
                "equipos_trampa": [],
                "historial_semanal": []
            }
    
    def analizar_tendencias(self):
        """Analiza tendencias y detecta equipos que rompen el algoritmo"""
        if not self.partidos:
            return {"equipos_trampa": [], "wr_global": 50}
        
        hoy = datetime.now()
        fallos_por_equipo = defaultdict(int)
        exitos_por_equipo = defaultdict(int)
        
        # Analizar últimos 15 días
        for p in self.partidos:
            fecha_str = p.get("fecha", "")
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            except:
                continue
            
            if (hoy - fecha).days <= 15:
                # Detectar qué equipo fue el pick
                away_pct = p.get("away_wins", 0) / max(p.get("away_wins", 0) + p.get("away_losses", 0), 1)
                home_pct = p.get("home_wins", 0) / max(p.get("home_wins", 0) + p.get("home_losses", 0), 1)
                pick = p["local"] if home_pct > away_pct else p["visitante"]
                ganador = p.get("ganador", "")
                
                # También leer del campo 'pick' si existe
                pick_guardado = p.get("pick", pick)
                
                if pick_guardado == ganador:
                    exitos_por_equipo[pick_guardado] += 1
                else:
                    fallos_por_equipo[pick_guardado] += 1
        
        # DETECCIÓN AUTOMÁTICA DE EQUIPOS TRAMPA
        equipos_trampa_detectados = []
        for equipo, fallos in fallos_por_equipo.items():
            total = fallos + exitos_por_equipo.get(equipo, 0)
            if total >= 3:
                wr_equipo = (exitos_por_equipo.get(equipo, 0) / total) * 100
                if wr_equipo < 35:
                    equipos_trampa_detectados.append(equipo)
        
        self.aprendizaje["equipos_trampa"] = equipos_trampa_detectados
        self._guardar_aprendizaje()
        
        return {
            "equipos_trampa": equipos_trampa_detectados,
            "wr_global": self._calcular_wr_total()
        }
    
    def _calcular_wr_total(self):
        """Calcula Win Rate global de los últimos 15 días"""
        if not self.partidos:
            return 50
        
        hoy = datetime.now()
        total = 0
        aciertos = 0
        
        for p in self.partidos:
            try:
                fecha = datetime.strptime(p["fecha"], "%Y-%m-%d")
            except:
                continue
            
            if (hoy - fecha).days <= 15:
                away_pct = p.get("away_wins", 0) / max(p.get("away_wins", 0) + p.get("away_losses", 0), 1)
                home_pct = p.get("home_wins", 0) / max(p.get("home_wins", 0) + p.get("home_losses", 0), 1)
                pick = p["local"] if home_pct > away_pct else p["visitante"]
                
                total += 1
                if pick == p.get("ganador", ""):
                    aciertos += 1
        
        return round((aciertos / total) * 100, 1) if total > 0 else 50
    
    def _guardar_aprendizaje(self):
        """Guarda el aprendizaje de forma segura"""
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.archivo_aprendizaje, "w", encoding="utf-8") as f:
                json.dump(self.aprendizaje, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def obtener_umbrales_dinamicos(self):
        """Retorna umbrales ajustados por tendencias"""
        # Base optimizada con 203 partidos
        umbrales = {
            "elite_diff_min": 15,
            "elite_diff_alt": 7,
            "seguro_diff_min": 5,
            "seguro_conf_min": 55,
            "rescate_diff_min": 2,
            "factor_domingo": 0.85,
            "factor_jueves": 0.90,
        }
        
        # Ajustar según equipos trampa detectados
        equipos_trampa = self.aprendizaje.get("equipos_trampa", [])
        if len(equipos_trampa) > 3:
            # Muchos equipos trampa = mercado volátil
            umbrales["elite_diff_min"] = 17
            umbrales["seguro_diff_min"] = 6
        
        return umbrales

# Prueba
if __name__ == "__main__":
    at = AnalizadorTendencias()
    tendencias = at.analizar_tendencias()
    umbrales = at.obtener_umbrales_dinamicos()
    
    print("🧠 TENDENCIAS DETECTADAS:")
    print(f"   WR Global: {tendencias.get('wr_global', 'N/A')}%")
    print(f"   Equipos trampa: {tendencias.get('equipos_trampa', [])}")
    print(f"   Umbrales dinámicos: {umbrales}")
