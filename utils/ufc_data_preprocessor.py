# -*- coding: utf-8 -*-
"""
UFC DATA PREPROCESSOR - Combina ESPN events with UFCStatsScraper details
"""

import requests
import json
import os
from scrapers.ufc_stats_scraper import UFCStatsScraper # Our improved scraper
from scrapers.espn_ufc import ESPN_UFC # To get event data

def main():
    print("--- 🥊 PREPROCESADOR UFC CON SCRAPER REAL ---")
    
    try:
        # Obtener eventos desde ESPN
        espn_scraper = ESPN_UFC()
        espn_fights = espn_scraper.get_events()
        
        ufcstats_scraper = UFCStatsScraper()
        fights = []
        
        for fight_espn in espn_fights:
            fighter1_name = fight_espn['peleador1']['nombre']
            fighter2_name = fight_espn['peleador2']['nombre']
            
            print(f"\n🔍 Procesando: {fighter1_name} vs {fighter2_name}")
            
            # Get detailed stats from UFCStatsScraper (which now handles its own caching and scraping)
            stats1_detailed = ufcstats_scraper.get_fighter_stats(fighter1_name) or {}
            stats2_detailed = ufcstats_scraper.get_fighter_stats(fighter2_name) or {}
            
            if stats1_detailed.get('error'):
                print(f"   ⚠️ Error obteniendo stats detalladas para {fighter1_name}: {stats1_detailed['error']}")
            if stats2_detailed.get('error'):
                print(f"   ⚠️ Error obteniendo stats detalladas para {fighter2_name}: {stats2_detailed['error']}")
            
            # Merge ESPN basic data with detailed stats
            # Prioritize ESPN's record and photo if available
            peleador1_final = {
                **stats1_detailed, # Start with detailed template
                'nombre': fighter1_name,
                'record': fight_espn['peleador1'].get('record', stats1_detailed.get('record', '0-0-0')), # Use ESPN record, fallback to scraper's or 0-0-0
                'photo': fight_espn['peleador1'].get('photo', ''),
                'odds': fight_espn['peleador1'].get('odds', 'N/A')
            }
            peleador2_final = {
                **stats2_detailed, # Start with detailed template
                'nombre': fighter2_name,
                'record': fight_espn['peleador2'].get('record', stats2_detailed.get('record', '0-0-0')), # Use ESPN record, fallback to scraper's or 0-0-0
                'photo': fight_espn['peleador2'].get('photo', ''),
                'odds': fight_espn['peleador2'].get('odds', 'N/A')
            }
            
            fights.append({
                'evento': fight_espn.get('evento', 'UFC Event'),
                'fecha': fight_espn.get('fecha', ''),
                'peleador1': peleador1_final,
                'peleador2': peleador2_final,
                'peso': fight_espn.get('peso', 'N/A')
            })
        
        # Guardar resultados una vez al final del bucle
        output_file = "data/ufc_preprocessed_fights.json"
        os.makedirs("data", exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(fights, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ {len(fights)} combates guardados en {output_file}")
        
        # Mostrar resumen
        print("\n📋 COMBATES PROCESADOS:")
        for i, fight in enumerate(fights, 1):
            p1 = fight['peleador1']
            p2 = fight['peleador2']
            print(f"  {i}. {p1['nombre']} ({p1.get('record', 'N/A')}) vs {p2.get('nombre', 'N/A')} ({p2.get('record', 'N/A')})")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
