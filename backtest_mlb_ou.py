# -*- coding: utf-8 -*-
"""
BACKTEST O/U MLB — modelo de carreras (mlb_runs_model) LEAK-FREE.

Entrena el modelo con datos hasta una fecha de corte y predice el Over/Under de
los juegos POSTERIORES (no vistos), comparando con el total real. Mide si el
modelo de carreras a nivel equipo acierta el O/U mejor que los baselines.

Uso:  python backtest_mlb_ou.py [dias_test] [linea]
"""
import sys
import traceback
from datetime import datetime, timedelta


def ejecutar(dias_test=12, linea=8.5):
    import statsapi
    from motors.mlb_runs_model import entrenar, predecir

    corte_dt = datetime.now() - timedelta(days=int(dias_test))
    corte = corte_dt.strftime("%Y-%m-%d")
    print(f"Entrenando modelo de carreras con datos HASTA {corte} (leak-free)...", flush=True)
    modelo = entrenar(hasta_fecha=corte, guardar=False)
    if not modelo:
        print("Sin modelo (datos insuficientes).")
        return
    print(f"  modelo: {modelo['n_equipos']} equipos · {modelo['n_juegos']} juegos · "
          f"media_runs={modelo['media_runs']}", flush=True)

    # Juegos de prueba: finalizados DESPUÉS del corte
    games = statsapi.schedule(start_date=corte_dt.strftime("%m/%d/%Y"),
                              end_date=datetime.now().strftime("%m/%d/%Y"))
    test = [g for g in games if g.get("status") == "Final" and g.get("game_type") == "R"
            and g.get("game_date", "") > corte]

    modelo_ok = modelo_n = 0     # acierto del modelo de carreras (O/U)
    ml_ok = ml_n = 0             # acierto moneyline del modelo
    base_over = 0                # baseline "siempre OVER"
    n = 0
    for g in test:
        try:
            rl, rv = int(g["home_score"]), int(g["away_score"])
        except Exception:
            continue
        total_real = rl + rv
        pr = predecir(g.get("home_name"), g.get("away_name"), linea_total=linea, modelo=modelo)
        if not pr.get("disponible"):
            continue
        # Moneyline (no hay push)
        ml = pr.get("moneyline", {})
        if ml:
            pick_home = ml.get("local", 0) >= ml.get("visitante", 0)
            gano_home = rl > rv
            ml_n += 1
            if pick_home == gano_home:
                ml_ok += 1
        # O/U (excluye push)
        if total_real == linea:
            continue
        n += 1
        over_real = total_real > linea
        pick_over = pr["total"]["over"] >= 50
        if pick_over == over_real:
            modelo_ok += 1
        modelo_n += 1
        if over_real:
            base_over += 1

    if not modelo_n:
        print("Sin juegos de prueba evaluables.")
        return
    print("=" * 70)
    print(f"BACKTEST MLB modelo de carreras — {modelo_n} juegos no vistos")
    print("=" * 70)
    print(f"  O/U (línea {linea}):  modelo {modelo_ok}/{modelo_n} = {round(modelo_ok/modelo_n*100,1)}%")
    tasa_over = round(base_over / modelo_n * 100, 1)
    base_mejor = max(base_over, modelo_n - base_over)
    print(f"     baseline (lado más común): {round(base_mejor/modelo_n*100,1)}%  (OVER real {tasa_over}%)")
    if ml_n:
        print(f"  MONEYLINE: modelo {ml_ok}/{ml_n} = {round(ml_ok/ml_n*100,1)}%  "
              f"(baseline 'siempre local' ~ {round(sum(1 for g in test if str(g.get('home_score','0')).isdigit() and str(g.get('away_score','0')).isdigit() and int(g['home_score'])>int(g['away_score']))/max(1,ml_n)*100,1)}%)")
    print("=" * 70)


if __name__ == "__main__":
    dias = sys.argv[1] if len(sys.argv) > 1 else 12
    linea = float(sys.argv[2]) if len(sys.argv) > 2 else 8.5
    try:
        ejecutar(dias, linea)
    except Exception:
        traceback.print_exc()
