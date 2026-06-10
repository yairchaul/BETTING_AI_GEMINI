# -*- coding: utf-8 -*-
"""MAPEO CENTRALIZADO NEON V24 - UTILS"""
import json
import os
import logging

logger = logging.getLogger("BETTING_AI.utils.mapeo")

def _load_config():
    """Carga los mapeos desde el archivo JSON externo en data/config_mlb.json"""
    try:
        base_dir = r"c:\Users\Yair\Desktop\BETTING_AI"
        config_path = os.path.join(base_dir, 'data', 'config_mlb.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error al cargar config_mlb.json: {e}")
    return {"TRADUCCION_MLB": {}, "EQUIPOS_A_ABREV": {}, "EQUIPOS_TRAMPA": []}

_config = _load_config()
TRADUCCION_MLB = _config.get("TRADUCCION_MLB", {})
EQUIPOS_A_ABREV = _config.get("EQUIPOS_A_ABREV", {})
EQUIPOS_TRAMPA = _config.get("EQUIPOS_TRAMPA", [])

def traducir_equipo(nombre_es):
    """Traduce nombre de equipo español -> inglés"""
    return TRADUCCION_MLB.get(nombre_es, nombre_es)

def obtener_abreviatura(nombre_en):
    """Obtiene abreviatura de equipo en inglés"""
    return EQUIPOS_A_ABREV.get(nombre_en, nombre_en[:3].upper())