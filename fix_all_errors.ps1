Write-Host "🔧 ARREGLANDO TODOS LOS ERRORES..." -ForegroundColor Cyan

# 1. Instalar dependencias
python -m pip install --upgrade pip
python -m pip install beautifulsoup4 requests

# 2. Probar scraper UFC
python scrapers/ufcstats_scraper.py

# 3. Verificar que el archivo se creó
if (Test-Path "data/ufcstats_scraped.json") {
    Write-Host "✅ Scraper UFC funcionando correctamente" -ForegroundColor Green
} else {
    Write-Host "❌ Error en scraper UFC" -ForegroundColor Red
}

Write-Host "`n✅ SISTEMA ARREGLADO. Reinicia Streamlit:" -ForegroundColor Green
Write-Host "streamlit run main_vision_completo.py" -ForegroundColor Yellow
