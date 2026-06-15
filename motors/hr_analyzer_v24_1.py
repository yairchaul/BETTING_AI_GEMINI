# -*- coding: utf-8 -*-
import unicodedata, json, os
from datetime import datetime
from utils.clima_mlb import ClimaMLB
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
        if not nombre or nombre in ["Por anunciar", "N/A", "TBD"]: return None
        nn = self.normalizar(nombre)
        for p, datos in self.pitchers.items():
            if nn in self.normalizar(p): return datos
        return None