import requests
import json

print("\n" + "="*50)
print("   DIAGNÓSTICO DE BALLLDONTLIE API")
print("="*50)

API_KEY = "c0da27f9-394d-473f-aae3-f8e0b48f27ef"
url = "https://api.balldontlie.io/v1/players?team_ids[]=14"
headers = {"Authorization": API_KEY}

print("\n1. Probando conexión a la API...")
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        players = data.get("data", [])
        print(f"   ✅ Jugadores encontrados: {len(players)}")
        
        if players:
            print("\n   Primeros 5 jugadores de Los Angeles Lakers:")
            for p in players[:5]:
                nombre = f"{p.get('first_name', '')} {p.get('last_name', '')}"
                print(f"      - {nombre}")
        else:
            print("   ⚠️ No se encontraron jugadores para Lakers")
    else:
        print(f"   ❌ Error HTTP: {response.status_code}")
        print(f"   Respuesta: {response.text[:200]}")
        
except Exception as e:
    print(f"   ❌ Error de conexión: {e}")

print("\n" + "="*50)

# Probar también con otro equipo
print("\n2. Probando con Golden State Warriors (ID 15)...")
url2 = "https://api.balldontlie.io/v1/players?team_ids[]=15"
try:
    response2 = requests.get(url2, headers=headers, timeout=10)
    if response2.status_code == 200:
        data2 = response2.json()
        players2 = data2.get("data", [])
        print(f"   ✅ Jugadores Warriors encontrados: {len(players2)}")
        if players2:
            print("   Primeros 3 jugadores:")
            for p in players2[:3]:
                nombre = f"{p.get('first_name', '')} {p.get('last_name', '')}"
                print(f"      - {nombre}")
    else:
        print(f"   ❌ Error: {response2.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*50)
print("✅ Diagnóstico completado")
