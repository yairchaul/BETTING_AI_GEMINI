# -*- coding: utf-8 -*-
"""
Cargador de equipos trampa desde archivo de configuración.
Elimina la dependencia directa de st.session_state.
"""

import json
import os
from datetime import datetime, timedelta


class EquipoTrampaLoader:
    """Carga y cachea la lista de equipos trampa desde un archivo de configuración."""
    
    def __init__(self, config_path="data/equipos_trampa.json", cache_ttl_minutos=60):
        self.config_path = config_path
        self.cache_ttl = timedelta(minutes=cache_ttl_minutos)
        self._cache = None
        self._last_load = None
    
    def load(self):
        """Carga la lista con caché por tiempo."""
        ahora = datetime.now()
        if self._cache is not None and self._last_load and (ahora - self._last_load) < self.cache_ttl:
            return self._cache
        
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache = data.get("equipos_trampa", [])
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback: intentar leer desde el motor de decisión si existe (solo en Streamlit)
            self._cache = self._fallback_from_motor()
        
        self._last_load = ahora
        return self._cache
    
    def _fallback_from_motor(self):
        """Compatibilidad: si el archivo no existe, intentar obtener desde motor_decision (solo en Streamlit)."""
        try:
            import streamlit as st
            if 'motor_decision' in st.session_state and st.session_state.motor_decision:
                return getattr(st.session_state.motor_decision, 'equipos_trampa', [])
        except ImportError:
            pass
        return []
    
    def save(self, equipos_trampa):
        """Guarda la lista actualizada en el archivo."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({
                "equipos_trampa": equipos_trampa,
                "ultima_actualizacion": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        self._cache = equipos_trampa
        self._last_load = datetime.now()
    
    def actualizar_desde_motor(self):
        """Actualiza el archivo desde el motor de decisión si está disponible."""
        trampas = self._fallback_from_motor()
        if trampas:
            self.save(trampas)
        return trampas
