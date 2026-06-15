# -*- coding: utf-8 -*-
"""
Módulo de Normalización de Equipos - BETTING_AI
Cumple con la Regla 14: Fuzzy Matching y Equivalencias.
"""
import os
import json
import logging
import unicodedata
from utils.mapeo_equipos import TRADUCCION_MLB, EQUIPOS_A_ABREV

try:
    from rapidfuzz import fuzz
    _FUZZ_OK = True
except ImportError:
    import difflib
    _FUZZ_OK = False

logger = logging.getLogger("BETTING_AI.utils.fuzzy")

# Mapeo inverso de abreviaturas para normalización (NYY -> New York Yankees)
REVERSE_ABREV = {v.upper(): k for k, v in EQUIPOS_A_ABREV.items()}

_SUFIJOS = (" jr", " sr", " iii", " ii", " iv")


def normalizar(texto):
    """Normaliza un nombre: quita acentos y ñ, minúsculas, sin puntos ni sufijos.

    'Gastón Bolaños' -> 'gaston bolanos'  |  'L. Messi' -> 'l messi'
    """
    if not texto:
        return ""
    # Descomponer y filtrar diacríticos (acentos)
    t = unicodedata.normalize("NFD", str(texto))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    # ñ ya cae con NFD, pero por seguridad:
    t = t.replace("ñ", "n").replace("Ñ", "n")
    t = t.lower().replace(".", " ").strip()
    # Quitar sufijos de nombre
    for suf in _SUFIJOS:
        if t.endswith(suf):
            t = t[: -len(suf)]
    return " ".join(t.split())


def generar_alias(nombre):
    """Genera alias de un nombre: completo, inicial+apellido, solo apellido."""
    n = normalizar(nombre)
    alias = {n} if n else set()
    partes = n.split()
    if len(partes) >= 2:
        nombre_pila, apellido = partes[0], partes[-1]
        alias.add(apellido)                        # solo apellido
        alias.add(f"{nombre_pila[0]} {apellido}")  # inicial + apellido
        alias.add(f"{nombre_pila[0]}{apellido}")   # inicial pegada
    return {a for a in alias if a}


def es_mismo_nombre(a, b, umbral=85):
    """True si dos nombres se refieren (con alta probabilidad) a la misma persona."""
    na, nb = normalizar(a), normalizar(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if generar_alias(a) & generar_alias(b):        # coincidencia por alias
        return True
    if _FUZZ_OK:
        return max(fuzz.WRatio(na, nb), fuzz.token_sort_ratio(na, nb)) >= umbral
    return difflib.SequenceMatcher(None, na, nb).ratio() * 100 >= umbral


def normalizar_equipo(nombre_sucio):
    """
    Convierte nombres de ESPN (Español/Inglés) al nombre estándar de la DB.
    Ejemplo: 'Rayos de Tampa Bay' -> 'Tampa Bay Rays'
    """
    if not nombre_sucio:
        return "TBD"
    
    nombre_limpio = nombre_sucio.strip()
    nombre_upper = nombre_limpio.upper()
    
    # 1. Búsqueda por Abreviatura (Ej: NYY -> New York Yankees)
    if nombre_upper in REVERSE_ABREV:
        return REVERSE_ABREV[nombre_upper]

    # 2. Búsqueda directa en el diccionario de Traducción
    if nombre_limpio in TRADUCCION_MLB:
        return TRADUCCION_MLB[nombre_limpio]
    
    # 3. Verificación si ya es el nombre estándar en inglés
    if nombre_limpio in TRADUCCION_MLB.values():
        return nombre_limpio

    # 4. Lógica de respaldo: Búsqueda parcial simple
    for esp, eng in TRADUCCION_MLB.items():
        if esp.lower() in nombre_limpio.lower() or eng.lower() in nombre_limpio.lower():
            return eng

    logger.warning(f"No se encontró coincidencia exacta para: {nombre_limpio}")
    return nombre_limpio

if __name__ == "__main__":
    # Prueba rápida
    test = "Rayos de Tampa Bay"
    print(f"Original: {test} | Normalizado: {normalizar_equipo(test)}")