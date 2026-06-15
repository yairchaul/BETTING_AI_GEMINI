# -*- coding: utf-8 -*-
"""
BACKTESTING TAB — Multi-Sport Renderer
Muestra métricas de rendimiento para todos los deportes + pesos dinámicos.
"""

import json
import os
import sqlite3
import logging

import streamlit as st
import pandas as pd

logger = logging.getLogger(__name__)

REPORTE_PATH   = os.path.join("data", "aprendizaje_backtest.json")
PESOS_PATH     = os.path.join("data", "pesos_motores.json")
DB_PATH        = os.path.join("data", "betting_stats.db")
HISTORICO_PATH = os.path.join("data", "historico_resultados.json")

SPORT_ICONS = {
    "MLB": "⚾", "MLB-K": "🎳", "MLB-HR": "💣", "MLB-OU": "📊",
    "NBA": "🏀", "UFC": "🥊", "SOCCER": "⚽", "GLOBAL": "🌎",
}


def _cargar_reporte() -> dict:
    try:
        if os.path.exists(REPORTE_PATH):
            with open(REPORTE_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _cargar_pesos() -> dict:
    try:
        if os.path.exists(PESOS_PATH):
            with open(PESOS_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _cargar_picks_db() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        df = pd.read_sql(
            "SELECT fecha, deporte, evento, pick, cuota, estado FROM backtesting ORDER BY id DESC",
            conn,
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def _metrica_card(titulo: str, valor: str, delta: str = "", color: str = "#22c55e"):
    st.markdown(
        f"<div style='background:#1e293b;border-radius:8px;padding:12px;text-align:center'>"
        f"<div style='color:#94a3b8;font-size:0.75rem'>{titulo}</div>"
        f"<div style='color:{color};font-size:1.5rem;font-weight:700'>{valor}</div>"
        f"{'<div style=color:#6b7280;font-size:0.7rem>' + delta + '</div>' if delta else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )


def _auto_run_backtest_if_stale():
    """Ejecuta el backtest automáticamente si el reporte tiene >24h o no existe."""
    if st.session_state.get("backtest_auto_ran"):
        return
    st.session_state.backtest_auto_ran = True

    rep = _cargar_reporte()
    ts_str = rep.get("timestamp", "")
    need_run = not rep or not ts_str
    if not need_run:
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(ts_str[:19])
            need_run = (datetime.now() - ts).total_seconds() > 86400
        except Exception:
            need_run = True

    if need_run:
        with st.spinner("⏳ Ejecutando backtest automático (primera vez del día)..."):
            try:
                from utils.backtester_universal import BacktesterUniversal
                bt = BacktesterUniversal()
                bt.ejecutar_backtest_completo(dias=15)
                st.toast("✅ Backtest completado.", icon="📊")
            except Exception as _e:
                logger.warning(f"Auto-backtest falló: {_e}")


def render_backtest_tab():
    """Renderiza la pestaña completa de backtesting multi-sport."""
    _auto_run_backtest_if_stale()
    st.header("📊 Backtesting Universal — Todos los Deportes")

    # ── Botón de ejecución ──────────────────────────────────────────────────
    col_btn, col_dias = st.columns([3, 1])
    with col_dias:
        dias = st.number_input("Días a analizar", min_value=5, max_value=60, value=15, step=5)
    with col_btn:
        st.write("")  # espaciado
        if st.button("▶️  EJECUTAR BACKTEST UNIVERSAL", use_container_width=True, type="primary"):
            with st.spinner("⏳ Descargando resultados ESPN y cruzando picks..."):
                try:
                    from utils.backtester_universal import BacktesterUniversal
                    bt = BacktesterUniversal()
                    reporte = bt.ejecutar_backtest_completo(dias=int(dias))
                    st.success(
                        f"✅ Backtest completado — "
                        f"{reporte.get('resultados_descargados', 0)} resultados descargados"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error en BacktesterUniversal: {e}")
                    logger.exception(e)

    st.markdown("---")

    # ── Cargar último reporte ───────────────────────────────────────────────
    reporte = _cargar_reporte()
    metricas = reporte.get("metricas", {})

    if not metricas:
        st.info("Ejecuta el backtest para ver métricas de rendimiento.")
        _render_picks_tabla()
        return

    ts = reporte.get("timestamp", "")[:16].replace("T", " ")
    dias_rep = reporte.get("dias", "?")
    descargas = reporte.get("resultados_descargados", 0)
    st.caption(f"Último reporte: {ts}  ·  {dias_rep} días  ·  {descargas} partidos descargados")

    # ── Tarjetas de métricas por deporte ────────────────────────────────────
    deportes_ordenados = ["GLOBAL", "MLB", "MLB-K", "MLB-HR", "MLB-OU", "NBA", "UFC", "SOCCER"]
    deportes_con_data = [d for d in deportes_ordenados if metricas.get(d, {}).get("total", 0) > 0]
    if not deportes_con_data:
        st.info("Sin métricas disponibles aún.")
        _render_picks_tabla()
        return
    cols = st.columns(min(len(deportes_con_data), 5))

    for col, dep in zip(cols, deportes_con_data):
        m = metricas.get(dep, {})
        wr = m.get("win_rate", 0)
        roi = m.get("roi_pct", 0)
        icon = SPORT_ICONS.get(dep, "📊")
        wr_color = "#22c55e" if wr >= 55 else "#f59e0b" if wr >= 45 else "#ef4444"
        with col:
            st.markdown(
                f"<div style='background:#1e293b;border-radius:10px;padding:14px;text-align:center'>"
                f"<div style='font-size:1.4rem'>{icon}</div>"
                f"<div style='color:white;font-weight:700;font-size:0.9rem'>{dep}</div>"
                f"<div style='color:{wr_color};font-size:1.6rem;font-weight:800'>{wr:.1f}%</div>"
                f"<div style='color:#94a3b8;font-size:0.72rem'>Win Rate</div>"
                f"<div style='color:{'#22c55e' if roi >= 0 else '#ef4444'};font-size:0.9rem;font-weight:600'>"
                f"ROI {roi:+.1f}%</div>"
                f"<div style='color:#6b7280;font-size:0.7rem'>{m.get('total', 0)} picks · "
                f"{m.get('ganadas', 0)}W-{m.get('perdidas', 0)}L</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Tabla interactiva de picks ───────────────────────────────────────────
    st.subheader("🗂️ Historial de Picks")
    _render_picks_tabla()

    st.markdown("---")

    # ── Pesos dinámicos del motor ────────────────────────────────────────────
    st.subheader("⚙️ Pesos Actuales de los Motores")
    pesos = _cargar_pesos()
    if pesos:
        col_p1, col_p2 = st.columns(2)
        pesos_sin_meta = {k: v for k, v in pesos.items() if k != "actualizado"}
        mitad = len(pesos_sin_meta) // 2
        items = list(pesos_sin_meta.items())
        with col_p1:
            for k, v in items[:mitad]:
                st.metric(k.replace("_", " ").title(), v)
        with col_p2:
            for k, v in items[mitad:]:
                st.metric(k.replace("_", " ").title(), v)
        if pesos.get("actualizado"):
            st.caption(f"Última actualización: {pesos['actualizado'][:16].replace('T', ' ')}")
    else:
        st.warning("⚠️ No se encontró pesos_motores.json. Ejecuta el backtest para generarlos.")

    # ── Histórico de resultados ─────────────────────────────────────────────
    if os.path.exists(HISTORICO_PATH):
        with st.expander("📦 Resultados Históricos Descargados", expanded=False):
            try:
                with open(HISTORICO_PATH, encoding="utf-8") as f:
                    hist = json.load(f)
                df_h = pd.DataFrame(hist)
                if not df_h.empty:
                    cols_show = [c for c in ["fecha", "deporte", "home", "away", "score_home", "score_away", "ganador"] if c in df_h.columns]
                    st.dataframe(df_h[cols_show].head(100), use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error cargando histórico: {e}")


def _render_picks_tabla():
    """Muestra tabla de picks con filtros y estados."""
    df = _cargar_picks_db()
    if df.empty:
        st.info("No hay picks registrados en la DB todavía.")
        return

    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        dep_opts = ["Todos"] + sorted(df["deporte"].dropna().unique().tolist())
        dep_sel = st.selectbox("Deporte", dep_opts, key="bt_dep")
    with col_f2:
        est_opts = ["Todos", "PENDIENTE", "GANADA", "PERDIDA"]
        est_sel = st.selectbox("Estado", est_opts, key="bt_est")
    with col_f3:
        n_rows = st.slider("Filas", 10, 200, 50, step=10, key="bt_rows")

    filtered = df.copy()
    if dep_sel != "Todos":
        filtered = filtered[filtered["deporte"] == dep_sel]
    if est_sel != "Todos":
        filtered = filtered[filtered["estado"] == est_sel]
    filtered = filtered.head(n_rows)

    def color_estado(val):
        if val == "GANADA":
            return "color: #22c55e; font-weight: 700"
        if val == "PERDIDA":
            return "color: #ef4444"
        return "color: #f59e0b"

    st.dataframe(
        filtered.style.map(color_estado, subset=["estado"]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"{len(filtered)} picks mostrados de {len(df)} en total")
