# -*- coding: utf-8 -*-
class GestorLigasUniversal:
    def __init__(self):
        self.ligas_activas = {
            "nba": True,
            "mlb": True,
            "ufc": True,
            "futbol": ["mex.1", "eng.1", "esp.1", "ita.1", "ger.1"]
        }

    def obtener_ligas_prioritarias(self):
        return self.ligas_activas
