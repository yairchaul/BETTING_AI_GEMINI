# -*- coding: utf-8 -*-
"""
PARLAY ENGINE — Motor de construcción de parlays estructurados

Combina picks de MLB (HR, ML, O/U), NBA (ML, O/U), UFC y Soccer
para generar los mejores parlays del día con Expected Value (EV) positivo.

Flujo:
  1. construir_pool()   → normaliza picks de todas las fuentes
  2. generar_parlays()  → genera combinaciones 4-6 legs, filtra y rankea por EV
"""

import itertools
from typing import Dict, List, Optional
from datetime import datetime


# ─── Umbrales mínimos de confianza por tipo de pick ──────────────────────────
MIN_CONF: Dict[str, float] = {
    "HR_PROP":    28.0,   # HRs son eventos raros, umbral intencionalmente bajo
    "MONEYLINE":  58.0,
    "OVER_UNDER": 54.0,
    "HANDICAP":   56.0,
    "BTTS":       58.0,
    "UFC_ML":     55.0,
}

# ─── Cuotas por defecto cuando el scraper no las provee ──────────────────────
DEFAULT_ODDS: Dict[str, float] = {
    "HR_PROP":    3.50,   # ~+250 americano
    "MONEYLINE":  1.90,   # ~-110 americano
    "OVER_UNDER": 1.90,
    "HANDICAP":   1.90,
    "BTTS":       1.85,
    "UFC_ML":     2.20,
}

# ─── Máximo de picks por tipo dentro de un mismo parlay ──────────────────────
MAX_PER_TYPE: Dict[str, int] = {
    "HR_PROP":    2,
    "MONEYLINE":  3,
    "OVER_UNDER": 2,
    "HANDICAP":   2,
    "BTTS":       2,
    "UFC_ML":     2,
}


class ParlayEngine:
    """
    Construye y rankea parlays con EV positivo a partir del pool de picks
    generado por los motores de análisis de cada deporte.
    """

    def __init__(
        self,
        min_legs: int = 4,
        max_legs: int = 6,
        min_parlay_prob: float = 3.0,   # % mínimo de probabilidad combinada
        top_parlays: int = 3,
        max_pool: int = 15,             # limita combinatoria
    ):
        self.min_legs = min_legs
        self.max_legs = max_legs
        self.min_parlay_prob = min_parlay_prob
        self.top_parlays = top_parlays
        self.max_pool = max_pool

    # ══════════════════════════════════════════════════════════════════════════
    # NORMALIZACIÓN — cada fuente → formato estándar de pick
    # ══════════════════════════════════════════════════════════════════════════

    def extraer_picks_mlb(
        self,
        mlb_partidos: List[Dict],
        analisis_mlb: Dict,
    ) -> List[Dict]:
        picks = []
        
        partidos_map = {p.get("game_pk"): p for p in mlb_partidos if p.get("game_pk")}

        for idx, resultado in analisis_mlb.items():
            if not isinstance(resultado, dict):
                continue
            
            partido = None
            game_pk = resultado.get("game_pk")
            if game_pk and game_pk in partidos_map:
                partido = partidos_map[game_pk]
            elif isinstance(idx, int) and idx < len(mlb_partidos):
                partido = mlb_partidos[idx]
            
            if not partido:
                continue

            evento = f"{partido.get('visitante','?')} @ {partido.get('local','?')}"

            # 1. Mejor apuesta (ML, Handicap, O/U, K)
            mejor_apuesta = resultado.get("mejor_apuesta")
            if mejor_apuesta:
                mercado = mejor_apuesta.get("mercado", "")
                conf_ajustada = mejor_apuesta.get("confianza_ajustada", 0)
                
                if "HANDICAP" in mercado: pick_type = "HANDICAP"
                elif "TOTAL" in mercado: pick_type = "OVER_UNDER"
                elif "MONEYLINE" in mercado: pick_type = "MONEYLINE"
                elif "PONCHES" in mercado: pick_type = "PONCHES"
                else: pick_type = "MONEYLINE"

                if conf_ajustada >= MIN_CONF.get(pick_type, 58.0) and mercado != "HOME_RUN":
                    pick_dict = {
                        "sport": "⚾ MLB", "evento": evento, "mercado": mercado,
                        "pick": mejor_apuesta.get("pick", ""), "prob": conf_ajustada,
                        "tipo": "SEGURO", "cuota": DEFAULT_ODDS.get(pick_type, 1.90),
                        "is_adjusted": True,
                    }
                    picks.append(pick_dict)
                    
                    is_local_pick = partido.get('local', '') in mejor_apuesta.get('pick', '')
                    streak = partido.get('local_streak', '') if is_local_pick else partido.get('visitante_streak', '')
                    if streak:
                        picks[-1]['streak'] = streak

            # 2. HR candidates
            for hr in resultado.get("hr_candidates", []):
                if hr.get("en_lineup") is False:
                    continue
                prob_modelo = hr.get("probabilidad", hr.get("prob", 0))
                prob_hr = _calibrar_prob_hr(prob_modelo)
                if prob_hr >= MIN_CONF["HR_PROP"]:
                    picks.append({
                        "sport": "⚾ MLB", "evento": evento, "mercado": "HOME RUN",
                        "pick": f"{hr.get('jugador', hr.get('nombre','?'))} pega HR",
                        "prob": prob_hr, "prob_modelo": prob_modelo,
                        "tipo": "BOMBA", "cuota": DEFAULT_ODDS["HR_PROP"],
                    })

        return picks

    def extraer_picks_nba(self, analisis_nba: Dict) -> List[Dict]:
        picks = []
        for evento_key, resultado in analisis_nba.items():
            if not isinstance(resultado, dict):
                continue
            pick_final = resultado.get("pick_final", {})
            if not pick_final:
                continue

            jerarquia = pick_final.get("jerarquia", "")
            if jerarquia not in ("ELITE", "SEGURO"):
                continue

            mercado = pick_final.get("mercado", "Moneyline")
            pick_type = (
                "OVER_UNDER"
                if any(k in mercado.lower() for k in ("over", "under", "o/u", "total"))
                else "MONEYLINE"
            )
            conf = float(pick_final.get("confianza", 0))
            if conf < MIN_CONF[pick_type]:
                continue

            picks.append(self._make_pick(
                sport="NBA",
                evento=evento_key,
                pick_label=pick_final.get("pick", ""),
                pick_type=pick_type,
                confidence=conf,
                cuota=float(pick_final.get("cuota", DEFAULT_ODDS[pick_type])),
                metadata={"jerarquia": jerarquia},
            ))
        return picks

    def extraer_picks_ufc(self, analisis_ufc: Dict) -> List[Dict]:
        picks = []
        for evento_key, resultado in analisis_ufc.items():
            if not isinstance(resultado, dict):
                continue
            pick_final = resultado.get("pick_final", {})
            if not pick_final:
                continue

            conf = float(pick_final.get("confianza", 0))
            if conf < MIN_CONF["UFC_ML"]:
                continue

            picks.append(self._make_pick(
                sport="UFC",
                evento=evento_key,
                pick_label=pick_final.get("pick", ""),
                pick_type="UFC_ML",
                confidence=conf,
                cuota=float(pick_final.get("cuota", DEFAULT_ODDS["UFC_ML"])),
                metadata={},
            ))
        return picks

    def extraer_picks_futbol(self, analisis_futbol: Dict) -> List[Dict]:
        picks = []
        for evento_key, resultado in analisis_futbol.items():
            if not isinstance(resultado, dict):
                continue
            pick_final = resultado.get("pick_final", {})
            if not pick_final:
                continue

            mercado = pick_final.get("mercado", "")
            if "btts" in mercado.lower() or "ambos" in mercado.lower():
                pick_type = "BTTS"
            elif any(k in mercado.lower() for k in ("over", "goles", "total")):
                pick_type = "OVER_UNDER"
            else:
                pick_type = "MONEYLINE"

            conf = float(pick_final.get("confianza", 0))
            if conf < MIN_CONF.get(pick_type, 60.0):
                continue

            picks.append(self._make_pick(
                sport="SOCCER",
                evento=evento_key,
                pick_label=pick_final.get("pick", ""),
                pick_type=pick_type,
                confidence=conf,
                cuota=float(pick_final.get("cuota", DEFAULT_ODDS.get(pick_type, 1.90))),
                metadata={"mercado": mercado},
            ))
        return picks

    # ══════════════════════════════════════════════════════════════════════════
    # POOL CONSOLIDADO
    # ══════════════════════════════════════════════════════════════════════════

    def construir_pool(
        self,
        mlb_partidos: Optional[List[Dict]] = None,
        analisis_mlb: Optional[Dict] = None,
        analisis_nba: Optional[Dict] = None,
        analisis_ufc: Optional[Dict] = None,
        analisis_futbol: Optional[Dict] = None,
    ) -> List[Dict]:
        """Reúne y rankea todos los picks calificados del día."""
        picks: List[Dict] = []

        picks += self.extraer_picks_mlb(mlb_partidos or [], analisis_mlb or {})
        picks += self.extraer_picks_nba(analisis_nba or {})
        picks += self.extraer_picks_ufc(analisis_ufc or {})
        picks += self.extraer_picks_futbol(analisis_futbol or {})

        # Score compuesto: confianza + bono por edge positivo
        for p in picks:
            p["score"] = p["confidence"] + max(0.0, p["edge"]) * 0.5

        picks.sort(key=lambda x: x["score"], reverse=True)

        # Deduplicar por pick_label (mismo bateador en dos fuentes, etc.)
        vistos: set = set()
        dedupe: List[Dict] = []
        for p in picks:
            key = f"{p['sport']}::{p['pick']}"
            if key not in vistos:
                vistos.add(key)
                dedupe.append(p)

        return dedupe

    # ══════════════════════════════════════════════════════════════════════════
    # GENERACIÓN DE PARLAYS
    # ══════════════════════════════════════════════════════════════════════════

    def generar_parlays(
        self,
        mlb_partidos: Optional[List[Dict]] = None,
        analisis_mlb: Optional[Dict] = None,
        analisis_nba: Optional[Dict] = None,
        analisis_ufc: Optional[Dict] = None,
        analisis_futbol: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Genera los mejores parlays del día ordenados por EV descendente.
        Retorna una lista de dicts (máximo self.top_parlays).
        """
        pool = self.construir_pool(
            mlb_partidos, analisis_mlb, analisis_nba, analisis_ufc, analisis_futbol
        )

        if len(pool) < self.min_legs:
            return []

        candidatos = pool[:self.max_pool]
        parlays: List[Dict] = []

        for n_legs in range(self.min_legs, self.max_legs + 1):
            for combo in itertools.combinations(candidatos, n_legs):
                resultado = self._evaluar_parlay(list(combo))
                if resultado is not None:
                    parlays.append(resultado)

        parlays.sort(key=lambda x: x["ev"], reverse=True)

        # Seleccionar top sin solapamiento excesivo entre parlays
        seleccionados: List[Dict] = []
        for p in parlays:
            if len(seleccionados) >= self.top_parlays:
                break
            if not self._solapamiento_excesivo(p, seleccionados):
                seleccionados.append(p)

        return seleccionados

    # ══════════════════════════════════════════════════════════════════════════
    # EVALUACIÓN INDIVIDUAL DE UN PARLAY
    # ══════════════════════════════════════════════════════════════════════════

    def _evaluar_parlay(self, picks: List[Dict]) -> Optional[Dict]:
        """Evalúa un combo. Retorna None si no cumple todos los filtros."""
        conteo_tipo: Dict[str, int] = {}
        conteo_evento: Dict[str, int] = {}

        for p in picks:
            t = p["pick_type"]
            conteo_tipo[t] = conteo_tipo.get(t, 0) + 1
            if conteo_tipo[t] > MAX_PER_TYPE.get(t, 2):
                return None

            ev = p["evento"]
            conteo_evento[ev] = conteo_evento.get(ev, 0) + 1
            if conteo_evento[ev] > 2:
                return None  # máximo 2 picks del mismo juego

        # Probabilidad combinada con penalización por correlación
        prob = 1.0
        for p in picks:
            prob *= p["confidence"] / 100.0
            if conteo_evento.get(p["evento"], 0) > 1:
                prob *= 0.95  # -5% por picks correlacionados en el mismo juego

        if prob * 100.0 < self.min_parlay_prob:
            return None

        cuota = 1.0
        for p in picks:
            cuota *= p["cuota"]

        ev = (prob * cuota) - 1.0
        if ev <= 0:
            return None

        return {
            "legs": picks,
            "n_legs": len(picks),
            "prob_combinada": round(prob * 100.0, 2),
            "cuota_combinada": round(cuota, 2),
            "ev": round(ev, 4),
            "ev_pct": round(ev * 100.0, 1),
            "sports": sorted({p["sport"] for p in picks}),
            "tipos": [p["pick_type"] for p in picks],
            "generado_en": datetime.now().isoformat(),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _make_pick(
        sport: str,
        evento: str,
        pick_label: str,
        pick_type: str,
        confidence: float,
        cuota: float,
        metadata: Dict,
    ) -> Dict:
        cuota = max(1.05, cuota)
        implied = (1.0 / cuota) * 100.0
        return {
            "sport": sport,
            "evento": evento,
            "pick": pick_label,
            "pick_type": pick_type,
            "confidence": round(confidence, 1),
            "cuota": round(cuota, 2),
            "implied_prob": round(implied, 1),
            "edge": round(confidence - implied, 1),
            "metadata": metadata,
            "score": 0.0,  # se calcula en construir_pool
        }

    @staticmethod
    def _solapamiento_excesivo(
        nuevo: Dict,
        existentes: List[Dict],
        max_shared: int = 2,
    ) -> bool:
        """True si el parlay nuevo comparte ≥ max_shared legs con alguno ya seleccionado."""
        picks_nuevo = {p["pick"] for p in nuevo["legs"]}
        for ex in existentes:
            picks_ex = {p["pick"] for p in ex["legs"]}
            if len(picks_nuevo & picks_ex) >= max_shared:
                return True
        return False
