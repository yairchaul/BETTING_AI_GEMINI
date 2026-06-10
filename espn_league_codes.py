# -*- coding: utf-8 -*-

class ESPNLeagueCodes:
    """
    Clase sincronizada con main_vision_completo.py
    """
    LEAGUE_CODES = {
        "LIGA_MX": "mex.1",
        "PREMIER_LEAGUE": "eng.1",
        "LA_LIGA": "esp.1",
        "SERIE_A": "ita.1",
        "BUNDESLIGA": "ger.1",
        "CHAMPIONS_LEAGUE": "uefa.champions",
        "NBA": "nba",
        "MLB": "mlb",
        "UFC": "ufc"
    }

    @classmethod
    def obtener_todas(cls):
        """Método requerido en la línea 76 del main"""
        return cls.LEAGUE_CODES

    @staticmethod
    def get_code(league_name):
        return ESPNLeagueCodes.LEAGUE_CODES.get(league_name.upper(), "mex.1")
