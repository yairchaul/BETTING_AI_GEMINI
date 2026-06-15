import requests
from bs4 import BeautifulSoup

print("="*60)
print("DIAGNÓSTICO UFCSTATS")
print("="*60)

# Test 1: Conexión básica
print("\n[1] Testeando conexión con UFCStats...")
urls = [
    "http://ufcstats.com",
    "http://ufcstats.com/statistics/fighters?char=a&page=all",
    "http://ufcstats.com/fighter-details/ilia-topuria"
]

headers_list = [
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'},
    {'User-Agent': 'curl/7.68.0'},
]

for url in urls:
    print(f"\n🔗 URL: {url}")
    for headers in headers_list:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            print(f"  Headers {headers['User-Agent'][:30]}... -> Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"    ✅ ÉXITO! Longitud: {len(resp.text)} caracteres")
                # Guardar una muestra
                if "fighters" in url:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    rows = soup.find_all('tr')
                    print(f"    Filas encontradas: {len(rows)}")
                    if len(rows) > 5:
                        sample = rows[1].get_text(strip=True)[:100]
                        print(f"    Ejemplo: {sample}")
                break
            else:
                print(f"    ❌ Falló")
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:50]}")

# Test 2: Verificar si hay bloqueo por Cloudflare
print("\n[2] Verificando si hay bloqueo Cloudflare...")
try:
    resp = requests.get("http://ufcstats.com", timeout=10)
    if "cf-ray" in resp.headers:
        print("⚠️ Cloudflare detectado - Puede estar bloqueando")
    if "captcha" in resp.text.lower():
        print("⚠️ Captcha detectado")
except:
    pass

# Test 3: Probar con playwright (más robusto)
print("\n[3] Probando con playwright (si está instalado)...")
try:
    from playwright.sync_api import sync_playwright
    print("✅ Playwright disponible")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://ufcstats.com/statistics/fighters?char=a&page=all", timeout=30000)
        print(f"  Título: {page.title()}")
        rows = page.query_selector_all('tr')
        print(f"  Filas encontradas: {len(rows)}")
        browser.close()
except ImportError:
    print("❌ Playwright no instalado. Ejecuta: pip install playwright && playwright install")
except Exception as e:
    print(f"❌ Error con playwright: {e}")

print("\n" + "="*60)
print("FIN DEL DIAGNÓSTICO")
print("="*60)
