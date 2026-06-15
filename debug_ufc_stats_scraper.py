# -*- coding: utf-8 -*-
"""
SCRIPT DE DIAGNÓSTICO AVANZADO PARA UFC_STATS_SCRAPER

Este script te ayuda a entender por qué las estadísticas de un peleador
(altura, alcance, SLpM, etc.) no se están extrayendo correctamente.
Sigue los mismos pasos que el scraper real pero muestra información detallada en cada etapa.
"""
import requests
import re
import os
import unicodedata
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- CONFIGURACIÓN ---
# Cambia este nombre por el del peleador que está fallando
FIGHTER_TO_DEBUG = "Ilia Topuria" 
# También puedes probar con otros que sepas que fallan, o con uno que funcione para comparar.
# FIGHTER_TO_DEBUG = "Islam Makhachev"

# --- NO MODIFICAR DEBAJO DE ESTA LÍNEA ---

def print_step(step, message):
    print(f"\n--- PASO {step}: {message} ---")

def print_result(success, message):
    if success:
        print(f"✅ ÉXITO: {message}")
    else:
        print(f"❌ FALLO: {message}")

def slugify_name(name):
    """Normaliza un nombre para una comparación más robusta."""
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    return name.lower().strip()

def debug_scraper(fighter_name):
    """Ejecuta el proceso de scraping paso a paso para un peleador."""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # PASO 1: Encontrar la URL del peleador
        print_step(1, f"Buscando la URL para '{fighter_name}' con Playwright")
        fighter_url = None
        try:
            last_name_initial = fighter_name.split(" ")[-1][0].lower()
            search_url = f"http://ufcstats.com/statistics/fighters?char={last_name_initial}&page=all"
            print(f"   URL de búsqueda: {search_url}")
            
            page.goto(search_url, timeout=30000)
            page.wait_for_selector('tr.b-statistics__table-row', timeout=15000)
            
            rows = page.query_selector_all('tr.b-statistics__table-row')
            print(f"   Filas de peleadores encontradas: {len(rows)}")
            
            fighter_name_cleaned = slugify_name(fighter_name)

            for row in rows:
                link_element = row.query_selector('td:nth-child(1) a')
                if link_element:
                    first_name = (row.query_selector('td:nth-child(1)').inner_text() or "").strip()
                    last_name_col = (row.query_selector('td:nth-child(2)').inner_text() or "").strip()
                    scraped_name = f"{first_name} {last_name_col}"
                    
                    if fighter_name_cleaned in slugify_name(scraped_name):
                        fighter_url = link_element.get_attribute('href')
                        print_result(True, f"URL encontrada: {fighter_url}")
                        break
            
            if not fighter_url:
                print_result(False, f"No se encontró un peleador que coincida con '{fighter_name}' en la página de la letra '{last_name_initial}'.")
                browser.close()
                return

        except PlaywrightTimeoutError:
            print_result(False, f"Timeout esperando la tabla de peleadores para la letra '{last_name_initial}'. El sitio puede estar bloqueando o tardando en cargar.")
            browser.close()
            return
        except Exception as e:
            print_result(False, f"Ocurrió una excepción al buscar la URL con Playwright: {e}")
            browser.close()
            return

        # PASO 2: Acceder a la página de detalles del peleador
        print_step(2, "Accediendo a la página de detalles del peleador")
        if not fighter_url:
            browser.close()
            return
            
        try:
            page.goto(fighter_url, wait_until="domcontentloaded", timeout=20000)
            html_content = page.content()
            
            # Guardar el HTML para inspección manual
            html_filename = "debug_ufc_fighter_page.html"
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"   HTML de la página guardado en: '{os.path.abspath(html_filename)}'")
            
            if "human" in html_content.lower() or "cloudflare" in html_content.lower():
                 print_result(False, "El contenido de la página parece ser una verificación de Cloudflare (anti-bot). El scraper está siendo bloqueado.")
                 browser.close()
                 return

            soup = BeautifulSoup(html_content, 'html.parser')
            print_result(True, "Página de detalles cargada y parseada.")

        except Exception as e:
            print_result(False, f"Ocurrió una excepción al acceder a la página de detalles: {e}")
            browser.close()
            return

        # PASO 3: Extraer las estadísticas
        print_step(3, "Intentando extraer las estadísticas específicas")
        
        stats_to_find = ["Height:", "Weight:", "Reach:", "STANCE:", "SLpM:", "Str. Acc.:", "TD Avg.:"]

        for stat_name in stats_to_find:
            value = "No encontrado"
            try:
                element = soup.find(lambda tag: tag.name == 'li' and stat_name in tag.get_text())
                if element:
                    value = element.get_text(strip=True).replace(stat_name, '').strip()
                    print_result(True, f"'{stat_name}': Encontrado -> '{value}'")
                else:
                    print_result(False, f"'{stat_name}': No se pudo encontrar el elemento.")
            except Exception as e:
                print_result(False, f"'{stat_name}': Excepción durante la extracción -> {e}")
        
        browser.close()

if __name__ == "__main__":
    print("="*60)
    print("DIAGNÓSTICO AVANZADO DEL SCRAPER DE UFCSTATS.COM")
    print("="*60)
    debug_scraper(FIGHTER_TO_DEBUG)
    print("\n" + "="*60)
    print("FIN DEL DIAGNÓSTICO.")
    print("Recomendaciones:")
    print("1. Revisa el archivo 'debug_ufc_fighter_page.html' en un navegador. ¿Se ve la página correctamente o es una página de error/bloqueo?")
    print("2. Si los selectores fallan, la estructura de la página de UFCStats.com ha cambiado. Se necesita actualizar el scraper.")
    print("3. Si el acceso a la página falla (error 403, Cloudflare), el problema es un bloqueo de IP o User-Agent. Se necesitarían técnicas más avanzadas (proxies, Playwright).")