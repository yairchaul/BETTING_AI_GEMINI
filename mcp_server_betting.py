# -*- coding: utf-8 -*-
from mcp.server.fastmcp import FastMCP
from database_manager import db
from cerebro_new_ai import CerebroNewAI
import json

# Inicializar el servidor MCP
mcp = FastMCP("Betting AI Local")
new_ai = CerebroNewAI()

@mcp.tool()
def consultar_stats_jugador(equipo: str, stat: str, deporte: str = "nba"):
    """
    Consulta las mejores estadísticas de jugadores en la base de datos local.
    stat puede ser: 'three_pm', 'points', 'hr', 'avg'
    """
    resultado = db.get_top_player_stat(equipo, stat, limit=3, deporte=deporte)
    return json.dumps(resultado, ensure_ascii=False)

@mcp.tool()
def analizar_con_new_ai(deporte: str, local: str, visitante: str):
    """
    Usa el motor Cerebro New AI para obtener una predicción avanzada.
    """
    partido = {"local": local, "visitante": visitante}
    # Simulamos un resultado de heurística básico para el motor
    heuristica = {"recomendacion": "Analizar flujo de dinero", "confianza": 50}
    respuesta = new_ai.orquestrar_decision_final(deporte, partido, heuristica)
    return respuesta

@mcp.tool()
def obtener_racha_equipo(equipo: str):
    """
    Obtiene la racha de fallos reciente de un equipo para detectar 'equipos trampa'.
    """
    fallos = db.obtener_racha_fallos(equipo)
    return f"El equipo {equipo} ha fallado {fallos} veces en los últimos picks."

if __name__ == "__main__":
    # El servidor MCP corre sobre Stdio por defecto
    mcp.run()