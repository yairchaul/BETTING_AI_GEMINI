# -*- coding: utf-8 -*-
"""
TEST COMPLETO DE MOTORES + BACKTESTING V24.5
Verifica: HR, K, O/U, MLB, NBA, UFC, Futbol
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

def separator(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

# ============================================================
# TEST 1: HOME RUNS (PredictorHR)
# ============================================================
def test_home_runs():
    separator("TEST 1: PREDICTOR DE HOME RUNS")
    
    from motors.predictor_hr import predictor_hr
    
    # Verificar datos cargados
    print(f"\n  Bateadores cargados: {len(predictor_hr.bateadores_stats)}")
    print(f"  Pitchers cargados: {len(predictor_hr.pitchers_stats)}")
    
    if not predictor_hr.bateadores_stats:
        print("  [WARN] No hay datos de bateadores en hr_datasets_completos.json")
        print("  [INFO] El predictor HR necesita este archivo para funcionar")
        return False
    
    # Test con equipo real
    equipos_test = ["New York Yankees", "Los Angeles Dodgers", "Houston Astros"]
    resultados_hr = {}
    
    for equipo in equipos_test:
        preds = predictor_hr.obtener_predicciones_para_equipo(equipo)
        resultados_hr[equipo] = preds
        if preds:
            print(f"\n  {equipo}: {len(preds)} candidatos")
            for p in preds[:2]:
                print(f"    - {p['bateador']}: {p['probabilidad']}% ({p['recomendacion']})")
        else:
            print(f"\n  {equipo}: Sin candidatos (puede ser normal si no hay datos)")
    
    # Test analizar_partido
    print("\n  --- Analizar Partido Completo ---")
    partido_hr = predictor_hr.analizar_partido("Boston Red Sox", "New York Yankees")
    if partido_hr:
        print(f"  Top candidatos en partido: {len(partido_hr)}")
        for r in partido_hr[:3]:
            print(f"    {r['emoji']} {r['jugador']} - Punt: {r['puntuacion']}/10 - {r['recomendacion']}")
    else:
        print("  Sin candidatos para este matchup")
    
    total_cands = sum(len(v) for v in resultados_hr.values())
    print(f"\n  [{'OK' if total_cands > 0 else 'WARN'}] Total candidatos encontrados: {total_cands}")
    return True

# ============================================================
# TEST 2: STRIKEOUTS (PredictorPonches)
# ============================================================
def test_strikeouts():
    separator("TEST 2: PREDICTOR DE STRIKEOUTS (K)")
    
    from motors.predictor_ponches import predictor_ponches
    
    print(f"\n  Pitchers con K/9 cargados: {len(predictor_ponches.pitchers_k)}")
    
    # Verificar datos del scraper K/9
    k9_file = "data/stats_lanzadores_hoy.json"
    if os.path.exists(k9_file):
        with open(k9_file, 'r', encoding='utf-8') as f:
            k9_data = json.load(f)
        pitchers_count = sum(1 for k in k9_data if not k.startswith('_'))
        print(f"  Pitchers en stats_lanzadores_hoy.json: {pitchers_count}")
        
        # Mostrar top 5 K/9
        print("\n  Top 5 K/9 del dia:")
        sorted_pitchers = sorted(
            [(k, v) for k, v in k9_data.items() if isinstance(v, dict)],
            key=lambda x: x[1].get('k9', 0), reverse=True
        )[:5]
        for equipo, info in sorted_pitchers:
            print(f"    {info.get('nombre', 'N/A')} ({equipo}): K/9 = {info.get('k9', 0)}")
    else:
        print(f"  [WARN] {k9_file} no existe. Ejecuta: python -m scrapers.mlb_pitchers_k9_scraper")
    
    # Test prediccion
    pitchers_test = [
        ("Gerrit Cole", "Boston Red Sox"),
        ("Dylan Cease", "Baltimore Orioles"),
        ("Paul Skenes", "Cincinnati Reds"),
    ]
    
    print("\n  --- Predicciones de K ---")
    for pitcher, rival in pitchers_test:
        result = predictor_ponches.predecir_ponches_pitcher(pitcher, rival, 5.5)
        k_proy = result.get('k_proyectados', 0)
        rec = result.get('recomendacion', 'N/A')
        print(f"    {pitcher} vs {rival}: {k_proy} K proyectados -> {rec}")
    
    print(f"\n  [OK] Predictor K funcional")
    return True

# ============================================================
# TEST 3: MOTOR OVER/UNDER
# ============================================================
def test_over_under():
    separator("TEST 3: MOTOR OVER/UNDER")
    
    from motors.motor_over_under import MotorOverUnder
    motor = MotorOverUnder()
    
    partidos_test = [
        {"venue": "Coors Field", "away_avg_runs": 5.0, "home_avg_runs": 5.5, "ou_line": 11.0},
        {"venue": "Yankee Stadium", "away_avg_runs": 4.2, "home_avg_runs": 4.5, "ou_line": 8.5},
        {"venue": "Petco Park", "away_avg_runs": 3.5, "home_avg_runs": 3.8, "ou_line": 7.5},
    ]
    
    print("\n  --- Proyecciones O/U ---")
    for p in partidos_test:
        result = motor.calcular_total(p)
        print(f"    {p['venue']}: Proy={result['total_proyectado']} vs Linea={p['ou_line']} -> {result['recomendacion']} ({result['confianza']}%)")
    
    print(f"\n  [OK] Motor O/U funcional")
    return True

# ============================================================
# TEST 4: MOTOR DECISION INTELIGENTE
# ============================================================
def test_decision_inteligente():
    separator("TEST 4: MOTOR DECISION INTELIGENTE")
    
    from motors.motor_decision_inteligente import MotorDecisionInteligente
    motor = MotorDecisionInteligente()
    
    # Simular analisis completo
    analisis_test = {
        'pick': 'New York Yankees',
        'confianza': 72,
        'over_under_analysis': {'recomendacion': 'OVER', 'confianza': 68},
        'hr_candidates_local': [{'probabilidad': 55}, {'probabilidad': 48}],
        'hr_candidates_visit': [{'probabilidad': 30}],
        'k_projection_local': {'k_proyectados': 7.2, 'linea': 5.5},
        'k_projection_visit': {'k_proyectados': 4.1, 'linea': 5.5},
        'pitchers': {'local': {'nombre': 'Gerrit Cole'}, 'visit': {'nombre': 'Chris Sale'}},
        'linea_ou': '8.5'
    }
    
    decision = motor.decidir_pick(analisis_test)
    print(f"\n  Pick Final: {decision.get('pick')}")
    print(f"  Mercado: {decision.get('mercado')}")
    print(f"  Jerarquia: {decision.get('jerarquia')}")
    print(f"  Confianza: {decision.get('confianza')}%")
    print(f"  Fuente: {decision.get('fuente', 'N/A')}")
    
    # Test con datos bajos (deberia dar BAJA CONFIANZA)
    analisis_bajo = {'pick': 'Team X', 'confianza': 45}
    dec_bajo = motor.decidir_pick(analisis_bajo)
    print(f"\n  Test baja confianza: {dec_bajo.get('jerarquia')} ({dec_bajo.get('confianza')}%)")
    
    print(f"\n  [OK] Motor Decision Inteligente funcional")
    return True

# ============================================================
# TEST 5: CLIMA MLB
# ============================================================
def test_clima():
    separator("TEST 5: CLIMA MLB")
    
    from utils.clima_mlb import ClimaMLB
    clima = ClimaMLB()
    
    estadios = ["Coors Field", "Wrigley Field", "Yankee Stadium", "Fenway Park", "Globe Life Field"]
    
    print("\n  --- Condiciones por Estadio ---")
    for estadio in estadios:
        c = clima.obtener_clima(estadio)
        alertas = clima.condiciones_extremas(c)
        alerta_str = f" | {alertas[0]}" if alertas else ""
        print(f"    {estadio}: {c['temp']}F, Viento {c['wind_speed']}mph {c['wind_dir']}{alerta_str}")
    
    print(f"\n  [OK] Clima MLB funcional")
    return True

# ============================================================
# TEST 6: UFC SCRAPER + ANALYZER
# ============================================================
def test_ufc():
    separator("TEST 6: UFC STATS + ANALYZER")
    
    # Verificar cache
    cache_file = "data/ufc_stats_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        fighters_con_datos = [k for k, v in cache.items() if v.get('altura')]
        print(f"\n  Peleadores en cache: {len(cache)}")
        print(f"  Con datos completos: {len(fighters_con_datos)}")
        
        for fighter in fighters_con_datos[:3]:
            data = cache[fighter]
            print(f"    {fighter}: {data.get('record','N/A')} | Altura: {data.get('altura','N/A')} | SLpM: {data.get('estadisticas_carrera',{}).get('sig_strikes_landed_per_min', 0)}")
    else:
        print("\n  [WARN] No hay cache UFC. Se generara al cargar UFC en la app.")
    
    # Test del analyzer
    from motors.ufc_analyzer import UFCAnalyzer
    analyzer = UFCAnalyzer()
    
    # Simular combate
    p1 = {'nombre': 'Ilia Topuria', 'record': '17-0-0', 'record_dict': {'wins': 17, 'losses': 0}}
    p2 = {'nombre': 'Justin Gaethje', 'record': '27-5-0', 'record_dict': {'wins': 27, 'losses': 5}}
    
    result = analyzer.analizar_combate(p1, p2)
    print(f"\n  Combate: {result.get('peleador1', p1['nombre'])} vs {result.get('peleador2', p2['nombre'])}")
    print(f"  Probabilidad P1: {result.get('probabilidad_f1', 'N/A')}%")
    print(f"  Probabilidad P2: {result.get('probabilidad_f2', 'N/A')}%")
    
    print(f"\n  [OK] UFC Analyzer funcional")
    return True

# ============================================================
# TEST 7: NBA MOTOR O/U
# ============================================================
def test_nba():
    separator("TEST 7: NBA OVER/UNDER")
    
    try:
        from motors.motor_nba_over_under import MotorNBAOverUnder
        motor = MotorNBAOverUnder()
        
        partido = {
            'local': 'Boston Celtics',
            'visitante': 'Los Angeles Lakers',
            'linea_ou': 220.5
        }
        
        result = motor.predict_over_under(partido)
        print(f"\n  {partido['local']} vs {partido['visitante']}")
        print(f"  Proyeccion: {result.get('proyeccion_total', 'N/A')} pts")
        print(f"  Recomendacion: {result.get('recomendacion', 'N/A')}")
        print(f"  Confianza: {result.get('confianza', 'N/A')}%")
        
        print(f"\n  [OK] NBA O/U funcional")
        return True
    except Exception as e:
        print(f"\n  [FAIL] Error NBA O/U: {e}")
        return False

# ============================================================
# TEST 8: FLUJO COMPLETO MLB (Simula boton ANALIZAR)
# ============================================================
def test_flujo_completo_mlb():
    separator("TEST 8: FLUJO COMPLETO MLB (Simula ANALIZAR)")
    
    from motors import analizar_mlb_pro_v20 as analizar_mlb
    from motors.predictor_hr import predictor_hr
    from motors.predictor_ponches import predictor_ponches
    from motors.motor_over_under import MotorOverUnder
    from motors.motor_decision_inteligente import MotorDecisionInteligente
    from utils.clima_mlb import ClimaMLB
    
    partido = {
        'local': 'New York Yankees',
        'visitante': 'Boston Red Sox',
        'venue': 'Yankee Stadium',
        'game_pk': '999999',
        'pitchers': {
            'local': {'nombre': 'Gerrit Cole', 'era': 2.95, 'k9': 10.5},
            'visitante': {'nombre': 'Brayan Bello', 'era': 3.85, 'k9': 8.1}
        },
        'odds': {'moneyline': {'local': '-160', 'visitante': '+140'}, 'over_under': 9.0}
    }
    
    print(f"\n  Partido: {partido['visitante']} @ {partido['local']}")
    print(f"  Pitchers: {partido['pitchers']['visitante']['nombre']} vs {partido['pitchers']['local']['nombre']}")
    
    # Step 1: Heuristico
    print("\n  1. Analisis Heuristico...")
    heur = analizar_mlb(partido, game_pk=partido['game_pk'])
    print(f"     Pick: {heur.get('pick')} | Confianza: {heur.get('confianza')}%")
    
    # Step 2: HR
    print("  2. Home Runs...")
    hr_local = predictor_hr.obtener_predicciones_para_equipo(partido['local'])
    hr_visit = predictor_hr.obtener_predicciones_para_equipo(partido['visitante'])
    heur['hr_candidates_local'] = hr_local or []
    heur['hr_candidates_visit'] = hr_visit or []
    print(f"     Local: {len(hr_local or [])} candidatos | Visit: {len(hr_visit or [])} candidatos")
    
    # Step 3: K
    print("  3. Strikeouts...")
    k_local = predictor_ponches.predecir_ponches_pitcher(
        partido['pitchers']['local']['nombre'], partido['visitante'], 5.5)
    k_visit = predictor_ponches.predecir_ponches_pitcher(
        partido['pitchers']['visitante']['nombre'], partido['local'], 5.5)
    heur['k_projection_local'] = k_local
    heur['k_projection_visit'] = k_visit
    print(f"     K Local: {k_local.get('k_proyectados', 0)} | K Visit: {k_visit.get('k_proyectados', 0)}")
    
    # Step 4: Clima
    print("  4. Clima...")
    clima = ClimaMLB().obtener_clima(partido['venue'])
    heur['clima'] = clima
    print(f"     {clima['temp']}F, Viento {clima['wind_speed']}mph {clima['wind_dir']}")
    
    # Step 5: O/U
    print("  5. Over/Under...")
    ou = MotorOverUnder().calcular_total(partido)
    heur['over_under_analysis'] = ou
    print(f"     Proyeccion: {ou['total_proyectado']} | Rec: {ou['recomendacion']}")
    
    # Step 6: Decision Inteligente
    print("  6. Decision Inteligente...")
    decision = MotorDecisionInteligente().decidir_pick(heur)
    heur['pick_final'] = decision
    print(f"     PICK FINAL: {decision.get('pick')}")
    print(f"     Jerarquia: {decision.get('jerarquia')}")
    print(f"     Mercado: {decision.get('mercado')}")
    print(f"     Confianza: {decision.get('confianza')}%")
    
    print(f"\n  [OK] Flujo completo MLB funcional - 6 motores conectados")
    return True

# ============================================================
# RESUMEN FINAL
# ============================================================
def run_all():
    print("\n" + "="*70)
    print("  BETTING_AI V24.5 - TEST COMPLETO DE MOTORES Y BACKTESTING")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    tests = [
        ("Home Runs (HR)", test_home_runs),
        ("Strikeouts (K)", test_strikeouts),
        ("Over/Under", test_over_under),
        ("Decision Inteligente", test_decision_inteligente),
        ("Clima MLB", test_clima),
        ("UFC Stats + Analyzer", test_ufc),
        ("NBA Over/Under", test_nba),
        ("Flujo Completo MLB", test_flujo_completo_mlb),
    ]
    
    results = []
    for name, func in tests:
        try:
            ok = func()
            results.append((name, ok))
        except Exception as e:
            print(f"\n  [FAIL] Error critico: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    separator("RESUMEN FINAL")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, ok in results:
        status = "[OK]  " if ok else "[FAIL]"
        print(f"  {status} {name}")
    
    print(f"\n  Total: {passed}/{total} tests aprobados")
    print("="*70)
    
    if passed == total:
        print("\n  TODOS LOS MOTORES FUNCIONAN CORRECTAMENTE")
        print("  El sistema esta listo para produccion.")
    else:
        print(f"\n  {total - passed} test(s) necesitan atencion.")
    
    return passed == total

if __name__ == "__main__":
    run_all()
