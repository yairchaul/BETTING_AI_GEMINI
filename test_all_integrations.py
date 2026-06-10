# -*- coding: utf-8 -*-
"""
TEST MAESTRO - Ejecuta todos los tests de integración
"""

import subprocess
import sys
import os
from datetime import datetime

def run_test_suite(test_file, nombre):
    """Ejecuta un suite de tests y retorna el resultado"""
    print("\n" + "+" + "="*78 + "+")
    print(f"|  EJECUTANDO: {nombre:<64} |")
    print("+" + "="*78 + "+")
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=120  # 2 minutos max por suite
        )
        
        # Mostrar output
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"[FAIL] TIMEOUT: {nombre} excedió 2 minutos")
        return False
    except Exception as e:
        print(f"[FAIL] ERROR ejecutando {nombre}: {e}")
        return False

def main():
    """Ejecuta todos los tests de integración"""
    print("\n" + "+" + "="*78 + "+")
    print("|" + " "*20 + "TEST MAESTRO DE INTEGRACIÓN V24.5.1" + " "*23 + "|")
    print("|" + " "*25 + f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}" + " "*26 + "|")
    print("+" + "="*78 + "+")
    
    # Cambiar al directorio del script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Suites de tests
    suites = [
        ("test_mlb_integration.py", "MLB Integration"),
        ("test_nba_integration.py", "NBA Integration"),
        ("test_ufc_integration.py", "UFC Integration")
    ]
    
    resultados = []
    
    for test_file, nombre in suites:
        if not os.path.exists(test_file):
            print(f"\n[WARN] ADVERTENCIA: {test_file} no encontrado, saltando...")
            resultados.append((nombre, False))
            continue
        
        exito = run_test_suite(test_file, nombre)
        resultados.append((nombre, exito))
    
    # Resumen final
    print("\n\n" + "+" + "="*78 + "+")
    print("|" + " "*25 + "RESUMEN FINAL DE TESTS" + " "*30 + "|")
    print("+" + "="*78 + "+")
    
    total = len(resultados)
    aprobados = sum(1 for _, r in resultados if r)
    
    for nombre, resultado in resultados:
        status = "[OK] PASS" if resultado else "[FAIL] FAIL"
        espacios = " " * (70 - len(nombre) - len(status))
        print(f"|  {status}  {nombre}{espacios}|")
    
    print("+" + "="*78 + "+")
    espacios_total = " " * (78 - 30 - len(str(aprobados)) - len(str(total)))
    print(f"|  Total: {aprobados}/{total} suites aprobadas{espacios_total}|")
    print("+" + "="*78 + "+")
    
    if aprobados == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON! Sistema 100% funcional.\n")
        return 0
    else:
        print(f"\n[WARN] {total - aprobados} suite(s) fallaron. Revisa los errores arriba.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
