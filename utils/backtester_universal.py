# -*- coding: utf-8 -*-
"""
BACKTESTER UNIVERSAL — V1
Extrae resultados reales de ESPN (MLB, NBA, UFC, Soccer),
cruza contra picks registrados en SQLite y calcula métricas de rendimiento
por deporte, tipo de apuesta y rango de confianza.

Uso:
    from utils.backtester_universal import BacktesterUniversal
    bt = BacktesterUniversal()
    reporte = bt.ejecutar_backtest_completo(dias=15)
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
import pandas as pd

logger = logging.getLogger(__name__)

DB_PATH       = os.path.join("data", "betting_stats.db")
PESOS_PATH    = os.path.join("data", "pesos_motores.json")
REPORTE_PATH  = os.path.join("data", "aprendizaje_backtest.json")
HISTORICO_PATH = os.path.join("data", "historico_resultados.json")

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# ─── Pesos por defecto ────────────────────────────────────────────────────────
PESOS_DEFAULT = {
    "power_factor_ml":              5.0,
    "ml_pitcher_vulnerable_penalty": 0.85,
    "ml_pitcher_novato_penalty":     0.88,
    "ml_racha_fallos_penalty":       0.80,
    "ml_valor_oculto_bonus":         8.0,
    "hr_ou_impact":                  0.015,
    "nba_pace_weight":               0.6,
    "nba_record_weight":             0.4,
    "ufc_pillar_weight":             1.0,
    "futbol_over_threshold":         3.0,
    "actualizado":                   None,
}


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTORES DE RESULTADOS REALES
# ══════════════════════════════════════════════════════════════════════════════

class ResultadoExtractor:
    """Descarga resultados reales de ESPN para los últimos N días."""

    def _fechas(self, dias: int) -> List[str]:
        hoy = datetime.now().date()
        return [(hoy - timedelta(days=d)).strftime("%Y%m%d") for d in range(dias)]

    # ── MLB ───────────────────────────────────────────────────────────────────
    def extraer_mlb(self, dias: int = 15) -> List[Dict]:
        resultados = []
        for fecha in self._fechas(dias):
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={fecha}"
                r = requests.get(url, headers=HEADERS, timeout=12)
                if r.status_code != 200:
                    continue
                for ev in r.json().get("events", []):
                    for comp in ev.get("competitions", []):
                        teams = comp.get("competitors", [])
                        if len(teams) < 2:
                            continue
                        home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
                        away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])
                        ht_score = int(home.get("score", 0) or 0)
                        at_score = int(away.get("score", 0) or 0)
                        total = ht_score + at_score
                        if total == 0 and comp.get("status", {}).get("type", {}).get("state") != "post":
                            continue
                        resultados.append({
                            "deporte":    "MLB",
                            "fecha":      fecha,
                            "home":       home.get("team", {}).get("displayName", ""),
                            "away":       away.get("team", {}).get("displayName", ""),
                            "score_home": ht_score,
                            "score_away": at_score,
                            "total":      total,
                            "ganador":    home.get("team", {}).get("displayName", "") if ht_score > at_score else away.get("team", {}).get("displayName", ""),
                            "over_under": float(comp.get("odds", [{}])[0].get("overUnder", 0) or 0),
                        })
            except Exception as e:
                logger.debug(f"MLB extractor fecha {fecha}: {e}")
        return resultados

    # ── NBA ───────────────────────────────────────────────────────────────────
    def extraer_nba(self, dias: int = 15) -> List[Dict]:
        resultados = []
        for fecha in self._fechas(dias):
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={fecha}"
                r = requests.get(url, headers=HEADERS, timeout=12)
                if r.status_code != 200:
                    continue
                for ev in r.json().get("events", []):
                    for comp in ev.get("competitions", []):
                        teams = comp.get("competitors", [])
                        if len(teams) < 2:
                            continue
                        home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
                        away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])
                        ht = int(home.get("score", 0) or 0)
                        at = int(away.get("score", 0) or 0)
                        if ht + at == 0:
                            continue
                        resultados.append({
                            "deporte":    "NBA",
                            "fecha":      fecha,
                            "home":       home.get("team", {}).get("displayName", ""),
                            "away":       away.get("team", {}).get("displayName", ""),
                            "score_home": ht,
                            "score_away": at,
                            "total":      ht + at,
                            "ganador":    home.get("team", {}).get("displayName", "") if ht > at else away.get("team", {}).get("displayName", ""),
                            "over_under": float(comp.get("odds", [{}])[0].get("overUnder", 0) or 0),
                        })
            except Exception as e:
                logger.debug(f"NBA extractor fecha {fecha}: {e}")
        return resultados

    # ── UFC ───────────────────────────────────────────────────────────────────
    def extraer_ufc(self, dias: int = 30) -> List[Dict]:
        resultados = []
        for fecha in self._fechas(dias):
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates={fecha}"
                r = requests.get(url, headers=HEADERS, timeout=12)
                if r.status_code != 200:
                    continue
                for ev in r.json().get("events", []):
                    for comp in ev.get("competitions", []):
                        teams = comp.get("competitors", [])
                        if len(teams) < 2:
                            continue
                        ganador_data = next((t for t in teams if t.get("winner")), None)
                        perdedor_data = next((t for t in teams if not t.get("winner")), None)
                        if not ganador_data:
                            continue
                        resultados.append({
                            "deporte": "UFC",
                            "fecha":   fecha,
                            "ganador": ganador_data.get("athlete", {}).get("displayName", ganador_data.get("team", {}).get("displayName", "")),
                            "perdedor": perdedor_data.get("athlete", {}).get("displayName", "") if perdedor_data else "",
                            "metodo":  comp.get("status", {}).get("type", {}).get("detail", ""),
                        })
            except Exception as e:
                logger.debug(f"UFC extractor fecha {fecha}: {e}")
        return resultados

    # ── Soccer ────────────────────────────────────────────────────────────────
    def extraer_soccer(self, dias: int = 15, ligas: Optional[List[str]] = None) -> List[Dict]:
        if ligas is None:
            ligas = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "mex.1", "usa.1", "fifa.world"]
        resultados = []
        for liga_id in ligas:
            for fecha in self._fechas(dias):
                try:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_id}/scoreboard?dates={fecha}"
                    r = requests.get(url, headers=HEADERS, timeout=12)
                    if r.status_code != 200:
                        continue
                    for ev in r.json().get("events", []):
                        for comp in ev.get("competitions", []):
                            teams = comp.get("competitors", [])
                            if len(teams) < 2:
                                continue
                            h = int(teams[0].get("score", 0) or 0)
                            a = int(teams[1].get("score", 0) or 0)
                            if h + a == 0 and comp.get("status", {}).get("type", {}).get("state") != "post":
                                continue
                            ganador = (
                                teams[0].get("team", {}).get("displayName", "")
                                if h > a else
                                teams[1].get("team", {}).get("displayName", "")
                                if a > h else "Empate"
                            )
                            resultados.append({
                                "deporte":    "SOCCER",
                                "liga":       liga_id,
                                "fecha":      fecha,
                                "home":       teams[0].get("team", {}).get("displayName", ""),
                                "away":       teams[1].get("team", {}).get("displayName", ""),
                                "score_home": h,
                                "score_away": a,
                                "total":      h + a,
                                "ganador":    ganador,
                                "btts":       h > 0 and a > 0,
                            })
                except Exception as e:
                    logger.debug(f"Soccer extractor {liga_id} {fecha}: {e}")
        return resultados


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR DE BACKTESTING
# ══════════════════════════════════════════════════════════════════════════════

class BacktesterUniversal:

    def __init__(self):
        self.extractor = ResultadoExtractor()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cargar_picks(self) -> pd.DataFrame:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=15)
            df = pd.read_sql(
                "SELECT fecha, deporte, evento, pick, cuota, estado FROM backtesting ORDER BY fecha DESC",
                conn,
            )
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error cargando picks de DB: {e}")
            return pd.DataFrame()

    def _cargar_pesos(self) -> Dict:
        try:
            if os.path.exists(PESOS_PATH):
                with open(PESOS_PATH) as f:
                    p = json.load(f)
                # Rellenar claves faltantes con defaults
                for k, v in PESOS_DEFAULT.items():
                    if k not in p:
                        p[k] = v
                return p
        except Exception:
            pass
        return PESOS_DEFAULT.copy()

    def _guardar_pesos(self, pesos: Dict):
        os.makedirs("data", exist_ok=True)
        pesos["actualizado"] = datetime.now().isoformat()
        with open(PESOS_PATH, "w") as f:
            json.dump(pesos, f, indent=2)

    def _actualizar_estado_picks(self, resultados: List[Dict]):
        """Cruza picks PENDIENTES de la DB contra resultados reales y actualiza estado."""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=15)
            cur = conn.cursor()
            cur.execute("SELECT id, evento, pick, deporte FROM backtesting WHERE estado = 'PENDIENTE'")
            pendientes = cur.fetchall()

            actualizados = 0
            for row_id, evento, pick, deporte in pendientes:
                for res in resultados:
                    if res.get("deporte") != deporte:
                        continue
                    home = res.get("home", "").lower()
                    away = res.get("away", "").lower()
                    ganador = res.get("ganador", "").lower()
                    pick_lower = (pick or "").lower()
                    evento_lower = (evento or "").lower()

                    # Verificar que el evento coincide con el resultado
                    evento_match = (
                        home in evento_lower or away in evento_lower
                        or (home and home[:6] in evento_lower)
                    )
                    if not evento_match:
                        continue

                    # Determinar GANADA / PERDIDA
                    estado = "PERDIDA"
                    if deporte in ("MLB", "NBA", "SOCCER", "UFC"):
                        if ganador and (ganador in pick_lower or pick_lower in ganador):
                            estado = "GANADA"
                        # Over/Under
                        elif "over" in pick_lower:
                            linea = res.get("over_under", 0)
                            total = res.get("total", 0)
                            if linea and total > linea:
                                estado = "GANADA"
                        elif "under" in pick_lower:
                            linea = res.get("over_under", 0)
                            total = res.get("total", 0)
                            if linea and total < linea:
                                estado = "GANADA"
                        elif "btts" in pick_lower or "ambos" in pick_lower:
                            if res.get("btts"):
                                estado = "GANADA"

                    cur.execute("UPDATE backtesting SET estado = ? WHERE id = ?", (estado, row_id))
                    actualizados += 1
                    break

            conn.commit()
            conn.close()
            logger.info(f"Picks actualizados: {actualizados}/{len(pendientes)}")
        except Exception as e:
            logger.error(f"Error actualizando estados: {e}")

    # ── Métricas ──────────────────────────────────────────────────────────────

    def _calcular_metricas(self, df: pd.DataFrame) -> Dict:
        """Calcula métricas de rendimiento por deporte y tipo de apuesta."""
        if df.empty:
            return {}

        df = df[df["estado"].isin(["GANADA", "PERDIDA"])].copy()
        if df.empty:
            return {}

        df["hit"] = (df["estado"] == "GANADA").astype(int)
        df["cuota"] = pd.to_numeric(df["cuota"], errors="coerce").fillna(1.9)
        df["profit"] = df.apply(
            lambda r: (r["cuota"] - 1) if r["hit"] == 1 else -1.0, axis=1
        )

        metricas = {}

        for deporte in df["deporte"].unique():
            sub = df[df["deporte"] == deporte]
            total = len(sub)
            hits  = sub["hit"].sum()
            wr    = hits / total * 100 if total else 0
            roi   = sub["profit"].sum() / total * 100 if total else 0
            metricas[deporte] = {
                "total":    int(total),
                "ganadas":  int(hits),
                "perdidas": int(total - hits),
                "win_rate": round(wr, 1),
                "roi_pct":  round(roi, 1),
                "profit_u": round(sub["profit"].sum(), 2),
            }

        # Global
        total_g = len(df)
        hits_g  = df["hit"].sum()
        metricas["GLOBAL"] = {
            "total":    int(total_g),
            "ganadas":  int(hits_g),
            "perdidas": int(total_g - hits_g),
            "win_rate": round(hits_g / total_g * 100, 1) if total_g else 0,
            "roi_pct":  round(df["profit"].sum() / total_g * 100, 1) if total_g else 0,
            "profit_u": round(df["profit"].sum(), 2),
        }

        return metricas

    # ── Auto-ajuste de pesos ──────────────────────────────────────────────────

    def _auto_ajustar_pesos(self, metricas: Dict) -> Dict:
        pesos = self._cargar_pesos()

        wr_mlb = metricas.get("MLB", {}).get("win_rate", 50)
        wr_nba = metricas.get("NBA", {}).get("win_rate", 50)

        # MLB
        if wr_mlb < 50:
            pesos["power_factor_ml"] = max(2.0, pesos["power_factor_ml"] - 0.5)
            pesos["ml_pitcher_vulnerable_penalty"] = max(0.70, pesos["ml_pitcher_vulnerable_penalty"] - 0.03)
            logger.info(f"⬇ Pesos MLB reducidos (WR {wr_mlb:.1f}%)")
        elif wr_mlb > 65:
            pesos["power_factor_ml"] = min(10.0, pesos["power_factor_ml"] + 0.5)
            logger.info(f"⬆ Pesos MLB aumentados (WR {wr_mlb:.1f}%)")

        # NBA
        if wr_nba < 50:
            pesos["nba_pace_weight"] = max(0.3, pesos.get("nba_pace_weight", 0.6) - 0.05)
            logger.info(f"⬇ Pesos NBA reducidos (WR {wr_nba:.1f}%)")

        self._guardar_pesos(pesos)
        return pesos

    # ── Punto de entrada principal ────────────────────────────────────────────

    def ejecutar_backtest_completo(
        self,
        dias: int = 15,
        guardar_historico: bool = True,
    ) -> Dict:
        """
        Extrae resultados reales, actualiza picks en DB, calcula métricas
        y auto-ajusta pesos. Retorna el reporte completo.
        """
        print(f"🧪 BACKTEST UNIVERSAL — {dias} días")
        print("=" * 52)

        # 1. Extraer resultados reales
        print("📡 Descargando resultados ESPN...")
        resultados: List[Dict] = []
        resultados += self.extractor.extraer_mlb(dias)
        resultados += self.extractor.extraer_nba(dias)
        resultados += self.extractor.extraer_ufc(dias)
        resultados += self.extractor.extraer_soccer(dias)

        print(f"   → {len(resultados)} resultados descargados")

        # 2. Guardar histórico
        if guardar_historico:
            os.makedirs("data", exist_ok=True)
            historico = []
            if os.path.exists(HISTORICO_PATH):
                try:
                    with open(HISTORICO_PATH) as f:
                        historico = json.load(f)
                except Exception:
                    pass
            # Deduplicar por (fecha, home, away)
            claves_existentes = {(r["fecha"], r.get("home", ""), r.get("away", "")) for r in historico}
            nuevos = [r for r in resultados if (r["fecha"], r.get("home", ""), r.get("away", "")) not in claves_existentes]
            historico.extend(nuevos)
            with open(HISTORICO_PATH, "w", encoding="utf-8") as f:
                json.dump(historico, f, indent=2, ensure_ascii=False)
            print(f"   → {len(nuevos)} nuevos resultados guardados en {HISTORICO_PATH}")

        # 3. Actualizar picks PENDIENTES en DB
        print("🔄 Actualizando estados de picks en DB...")
        self._actualizar_estado_picks(resultados)

        # 4. Calcular métricas
        print("📊 Calculando métricas de rendimiento...")
        df = self._cargar_picks()
        metricas = self._calcular_metricas(df)

        # 5. Mostrar resumen
        print("\n📈 RESULTADOS:")
        for deporte, m in metricas.items():
            if m["total"] == 0:
                continue
            icono = {"MLB": "⚾", "NBA": "🏀", "UFC": "🥊", "SOCCER": "⚽", "GLOBAL": "🌎"}.get(deporte, "📊")
            print(
                f"  {icono} {deporte:8s}  {m['total']:3d} picks  "
                f"WR {m['win_rate']:5.1f}%  ROI {m['roi_pct']:+6.1f}%  "
                f"Profit {m['profit_u']:+6.2f}u"
            )

        # 6. Auto-ajustar pesos
        print("\n⚙️  Ajustando pesos de motores...")
        pesos_nuevos = self._auto_ajustar_pesos(metricas)

        # 7. Guardar reporte
        reporte = {
            "timestamp":   datetime.now().isoformat(),
            "dias":        dias,
            "resultados_descargados": len(resultados),
            "metricas":    metricas,
            "pesos":       pesos_nuevos,
        }
        os.makedirs("data", exist_ok=True)
        with open(REPORTE_PATH, "w", encoding="utf-8") as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Reporte guardado en {REPORTE_PATH}")

        return reporte


# ── Inicializar pesos_motores.json si no existe ────────────────────────────────
def inicializar_pesos():
    """Crea pesos_motores.json con defaults si no existe."""
    if not os.path.exists(PESOS_PATH):
        os.makedirs("data", exist_ok=True)
        pesos = PESOS_DEFAULT.copy()
        pesos["actualizado"] = datetime.now().isoformat()
        with open(PESOS_PATH, "w") as f:
            json.dump(pesos, f, indent=2)
        logger.info(f"✅ {PESOS_PATH} inicializado con valores por defecto")


if __name__ == "__main__":
    inicializar_pesos()
    bt = BacktesterUniversal()
    bt.ejecutar_backtest_completo(dias=15)
