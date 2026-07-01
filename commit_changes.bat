@echo off
REM Script para hacer commit y push de los cambios

REM Verificar si Git está instalado
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Git no está instalado o no está en el PATH
    echo Por favor instala Git desde: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo ============================================
echo CAMBIOS REALIZADOS:
echo ============================================
echo.
echo 1. visual_futbol_triple.py
echo    - Mejorados los gráficos de barras (últimos 5 partidos)
echo    - Agregado título "Últimos partidos"
echo    - Mejor visualización con use_container_width
echo    - Altura aumentada a 120px
echo.
echo 2. utils/analista_total.py
echo    - Corregido error AttributeError cuando heur es None
echo    - Agregada protección: heur = heur or {}
echo.
echo ============================================
echo.

REM Agregar archivos modificados
git add visual_futbol_triple.py
git add utils/analista_total.py

REM Hacer commit
git commit -m "Fix: Corregido AttributeError en analista_total y mejorada visualización de gráficos en visual_futbol_triple

- Protección contra heur=None en _prompt_mlb (línea 337)
- Gráficos mejorados: últimos 5 partidos, títulos, altura 120px
- Mejor UX con etiquetas más claras y use_container_width"

REM Verificar si hay remote configurado
git remote -v
if %ERRORLEVEL% neq 0 (
    echo.
    echo WARNING: No hay remote configurado
    echo Por favor configura el remote con: git remote add origin [URL]
    pause
    exit /b 1
)

REM Push a GitHub
echo.
echo Subiendo cambios a GitHub...
git push

echo.
echo ============================================
echo COMPLETADO - Cambios subidos a GitHub
echo ============================================
pause
