# -*- coding: utf-8 -*-
import requests
import sys, io
from bs4 import BeautifulSoup
import pandas as pd

def extraer_stats_bateador(player_id):
    url = f"https://www.mlb.com/player/{player_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscamos la tabla de stats de la temporada actual (2026)
        # Basado en tu captura de Aaron Judge, buscamos el valor de HR y SLG
        table_row = soup.find("tr", {"id": "year-2026"})
        if not table_row:
            table_row = soup.find_all("tr")[-2] # Fila más reciente si no dice 2026

        stats = {
            "HR": table_row.find("td", {"data-col": "8"}).text,
            "SLG": table_row.find("td", {"data-col": "15"}).text,
            "OPS": table_row.find("td", {"data-col": "16"}).text
        }
        return stats
    except Exception as e:
        return {"error": str(e)}

def extraer_stats_pitcher(player_id):
    url = f"https://www.mlb.com/player/{player_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Basado en tu captura de Zack Littell, buscamos el PCL (ERA) y WHIP
        # El HR/9 suele estar en tablas avanzadas, pero calcularemos el riesgo
        table_row = soup.find("tr", {"id": "year-2026"})
        if not table_row:
            table_row = soup.find_all("tr")[-2]

        stats = {
            "ERA": table_row.find("td", {"data-col": "3"}).text,
            "WHIP": table_row.find("td", {"data-col": "11"}).text,
            "SO": table_row.find("td", {"data-col": "10"}).text
        }
        return stats
    except Exception as e:
        return {"error": str(e)}

# Prueba rápida con los IDs que pasaste
judge_id = "592450"
littell_id = "641793"

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8') # Forzar UTF-8 para la consola
    print(f"📊 Stats de Judge (HR): {extraer_stats_bateador(judge_id)}")
    print(f"🧤 Stats de Littell (Pitcher): {extraer_stats_pitcher(littell_id)}")
