# -*- coding: utf-8 -*-
"""SCRAPER MANAGER - Multi-fuente con fallback"""
import sys
sys.path.insert(0, '.')
from scrapers.mlb_selenium_scraper import MLBSeleniumScraper
from scrapers.mlb_hybrid_scraper import MLBHybridScraper

class ScraperManager:
    def __init__(self):
        self.scrapers = [MLBHybridScraper(), MLBSeleniumScraper(headless=True)]
    
    def get_games(self):
        for scraper in self.scrapers:
            try:
                games = scraper.get_games_complete()
                if games and len(games) > 0:
                    print(f"✅ Fuente: {scraper.__class__.__name__} ({len(games)} juegos)")
                    return games
            except Exception as e:
                print(f"⚠️ Fallo {scraper.__class__.__name__}: {str(e)[:50]}")
        return []
