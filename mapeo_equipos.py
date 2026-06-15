# -*- coding: utf-8 -*-
"""MAPEO CENTRALIZADO NEON V24"""
import json
import os
import logging

def _load_config():
    """Carga los mapeos desde el archivo JSON externo"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'data', 'config_mlb.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                logging.getLogger("BETTING_AI_V24").info("Configuración de MLB cargada exitosamente desde archivo externo.")
                return json.load(f)
    except Exception as e:
        logging.getLogger("BETTING_AI_V24").error(f"Error al cargar config_mlb.json: {e}")
    return {"TRADUCCION_MLB": {}, "EQUIPOS_A_ABREV": {}}

_config = _load_config()
TRADUCCION_MLB = _config.get("TRADUCCION_MLB", {})
EQUIPOS_A_ABREV = _config.get("EQUIPOS_A_ABREV", {})

# Alias para mantener compatibilidad
EQUIPOS_TRAMPA = _config.get("EQUIPOS_TRAMPA", []) # Nueva lista de equipos trampa
EQUIPOS_ES_EN = TRADUCCION_MLB

def traducir_equipo(nombre_es):
    """Traduce nombre de equipo español -> inglés"""
    return TRADUCCION_MLB.get(nombre_es, nombre_es)

def obtener_abreviatura(nombre_en):
    """Obtiene abreviatura de equipo en inglés"""
    return EQUIPOS_A_ABREV.get(nombre_en, nombre_en[:3].upper())
