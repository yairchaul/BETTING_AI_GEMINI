# -*- coding: utf-8 -*-
import streamlit as st
import os

class UFCDataAggregator:
    def __init__(self):
        # Intentamos importar el dataset, si no existe, usamos un mock para que no truene
        try:
            # Asumimos que ufc_dataset_integrator.py está en la raíz o en una carpeta accesible
            # Si está en una subcarpeta, la importación debería ser relativa o absoluta
            # Por ejemplo, si está en 'scrapers/ufc_dataset_integrator.py', sería:
            # from scrapers.ufc_dataset_integrator import UFCDatasetIntegrator
            from ufc_dataset_integrator import UFCDatasetIntegrator 
            self.dataset = UFCDatasetIntegrator() # Instancia real
        except (ImportError, FileNotFoundError):
            self.dataset = None
            print("⚠️ Advertencia: ufc_dataset_integrator no encontrado. Usando modo básico.")
        
        self.cache = {}
        print("✅ UFC Data Aggregator (Versión Pro) inicializado")

    def _parse_record(self, record_str):
        """Convierte '11-5-0' en diccionario numérico"""
        try:
            parts = str(record_str).split('-')
            if len(parts) >= 3:
                return {'wins': int(parts[0]), 'losses': int(parts[1]), 'draws': int(parts[2])}
        except:
            pass
        return {'wins': 0, 'losses': 0, 'draws': 0}

    def get_fighter_basic_data(self, fighter_name, espn_record=None):
        if fighter_name in self.cache:
            return self.cache[fighter_name]

        stats = self.dataset.get_fighter_stats(fighter_name) if self.dataset else {}
        record = espn_record if espn_record else stats.get('record', '0-0-0')

        data = {
            'nombre': fighter_name,
            'record': record,
            'altura': stats.get('altura', 'N/A'),
            'peso': stats.get('peso', 'N/A'),
            'alcance': stats.get('alcance', 'N/A'),
            'postura': stats.get('postura', 'Ortodoxa'),
            'record_dict': self._parse_record(record)
        }
        
        # --- LÓGICA TÉCNICA (SABERMETRICS UFC) ---
        # Si un peleador tiene más de 5cm de ventaja en alcance, es un "Pitcher con ventaja"
        self.cache[fighter_name] = data
        return data

    def get_fight_data(self, fighter1_name, fighter2_name, event_data=None):
        if not fighter1_name or not fighter2_name:
            return None

        # Extraer registros de ESPN si vienen en el evento
        record1, record2 = None, None
        if event_data:
            for fight in event_data:
                n1 = fight.get('peleador1', {}).get('nombre', '').lower()
                n2 = fight.get('peleador2', {}).get('nombre', '').lower()
                if fighter1_name.lower() in n1: record1 = fight['peleador1'].get('record')
                if fighter2_name.lower() in n2: record2 = fight['peleador2'].get('record')

        p1_data = self.get_fighter_basic_data(fighter1_name, record1)
        p2_data = self.get_fighter_basic_data(fighter2_name, record2)

        return {
            'peleador1': p1_data,
            'peleador2': p2_data,
            'real': True,
            'ventaja_alcance': self._comparar_alcance(p1_data, p2_data)
        }

    def _comparar_alcance(self, p1, p2):
        try:
            a1 = float(p1['alcance'].replace('cm', '').strip())
            a2 = float(p2['alcance'].replace('cm', '').strip())
            return p1['nombre'] if a1 > a2 else p2['nombre']
        except:
            return "N/A"
