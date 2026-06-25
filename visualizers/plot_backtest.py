# -*- coding: utf-8 -*-
import json
import os
import sys

def plot_backtest_evolution(report_path="data/walkforward_baseline.json"):
    """
    Genera un gráfico de la evolución del rendimiento (RPS) de los modelos
    a lo largo del tiempo a partir del reporte del backtest.
    """
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
    except ImportError:
        print("Por favor, instala matplotlib y pandas para generar el gráfico:")
        print("pip install matplotlib pandas")
        sys.exit(1)

    if not os.path.exists(report_path):
        print(f"Error: No se encuentra el archivo de reporte '{report_path}'.")
        print("Ejecuta primero 'python backtest_walkforward.py ml' para generarlo.")
        return

    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ventanas = data.get("ventanas", [])
    if not ventanas:
        print("El reporte no contiene datos por ventana para graficar.")
        return

    plot_data = []
    for v in ventanas:
        corte = v.get("corte")
        for pred_nombre, metrics in v.get("por_pred", {}).items():
            plot_data.append({"corte": corte, "predictor": pred_nombre, "rps": metrics.get("rps")})

    df = pd.DataFrame(plot_data)
    df['corte'] = pd.to_datetime(df['corte'])
    df = df.sort_values('corte')

    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(14, 8))

    for pred in sorted(df['predictor'].unique()):
        subset = df[df['predictor'] == pred]
        ax.plot(subset['corte'], subset['rps'], marker='o', linestyle='-', label=pred)

    ax.set_title('Evolución del Rendimiento (RPS) por Ventana de Backtest', fontsize=16)
    ax.set_xlabel('Fecha de Corte de Entrenamiento', fontsize=12)
    ax.set_ylabel('Ranked Probability Score (RPS) - Menor es mejor', fontsize=12)
    ax.legend(title='Predictor')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.xticks(rotation=45)
    plt.tight_layout()

    output_path = "data/backtest_evolution.png"
    plt.savefig(output_path)
    print(f"\n✅ Gráfico guardado en '{output_path}'")
    # plt.show() # Descomenta si quieres que se muestre en una ventana

if __name__ == "__main__":
    plot_backtest_evolution()