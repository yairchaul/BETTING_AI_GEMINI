# -*- coding: utf-8 -*-
"""PANEL DE INTELIGENCIA - Tabla de rendimiento por equipo"""
import streamlit as st
import json
import pandas as pd
from collections import defaultdict

def mostrar_panel_inteligencia():
    """Muestra tabla de rendimiento por equipo (últimos 15 días)"""
    st.subheader("📊 Panel de Inteligencia: Rendimiento por Equipo (15d)")
    
    try:
        with open("data/resultados_reales_15dias.json", "r", encoding="utf-8") as f:
            resultados = json.load(f)
        
        stats = defaultdict(lambda: {"ganados": 0, "perdidos": 0, "total": 0})
        
        for r in resultados:
            # Calcular pick
            away_pct = r.get("away_wins", 0) / max(r.get("away_wins", 0) + r.get("away_losses", 0), 1)
            home_pct = r.get("home_wins", 0) / max(r.get("home_wins", 0) + r.get("home_losses", 0), 1)
            pick = r["local"] if home_pct > away_pct else r["visitante"]
            
            # También leer del campo 'pick' si existe
            pick_guardado = r.get("pick", pick)
            
            stats[pick_guardado]["total"] += 1
            if pick_guardado == r.get("ganador", ""):
                stats[pick_guardado]["ganados"] += 1
            else:
                stats[pick_guardado]["perdidos"] += 1
        
        df_data = []
        for eq, s in stats.items():
            if s["total"] >= 2:  # Solo mostrar equipos con al menos 2 picks
                wr = (s["ganados"] / s["total"]) * 100
                df_data.append({
                    "Equipo": eq,
                    "WR": f"{wr:.0f}%",
                    "Récord": f"{s['ganados']}-{s['perdidos']}",
                    "Estatus": "✅ RENTABLE" if wr >= 50 else "⚠️ TRAMPA"
                })
        
        if df_data:
            df = pd.DataFrame(df_data).sort_values(by="WR")
            
            # Colores
            def color_estatus(val):
                if "TRAMPA" in val:
                    return 'color: #ff4444; font-weight: bold'
                return 'color: #10b981; font-weight: bold'
            
            st.dataframe(
                df.style.applymap(color_estatus, subset=["Estatus"]),
                use_container_width=True,
                height=300
            )
            
            # Resumen
            trampas = len([d for d in df_data if "TRAMPA" in d["Estatus"]])
            st.caption(f"🔍 {trampas} equipos detectados como trampa | {len(df_data)} equipos analizados")
        else:
            st.info("📭 Aún no hay suficientes datos. Ejecuta más backtesting.")
    
    except FileNotFoundError:
        st.info("📭 No se encontró resultados_reales_15dias.json. Ejecuta el backtesting primero.")
    except Exception as e:
        st.error(f"Error: {e}")
