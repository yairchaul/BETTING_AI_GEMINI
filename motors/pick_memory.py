# -*- coding: utf-8 -*-
"""
PICK MEMORY — La "memoria" del BETTING_AI (ciclo de aprendizaje).

Implementa las 3 fases del plan:
  FASE 1 (Memoria):    log_pick() registra cada pick generado con estado 'pendiente'.
  FASE 2 (Reflexión):  stats() calcula tasa de acierto global / por deporte / por mercado.
  FASE 3 (Evolución):  factor_confianza() devuelve un multiplicador (<1 penaliza,
                       >1 premia) según el rendimiento histórico de ese mercado/deporte,
                       para que el selector de picks/parlays sea más inteligente.

Almacenamiento: data/pick_history.json (lista de picks; ver data/history_schema.json).
Es additivo: NO reemplaza la tabla SQLite 'backtesting' existente.
"""
import os
import json
import uuid
import threading
from datetime import datetime

HISTORY_PATH = os.path.join("data", "pick_history.json")
_LOCK = threading.Lock()

ESTADOS_VALIDOS = {"pendiente", "ganado", "perdido", "push", "cancelado"}


def _ahora_iso():
    return datetime.now().isoformat(timespec="seconds")


class PickMemory:
    def __init__(self, path=HISTORY_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        if not os.path.exists(self.path):
            self._guardar([])

    # ── IO ───────────────────────────────────────────────────────────────
    def _cargar(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []

    def _guardar(self, picks):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(picks, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # ── FASE 1: MEMORIA ───────────────────────────────────────────────────
    def log_pick(self, pick_data: dict) -> str:
        """Registra un pick (estado 'pendiente'). Devuelve su id.

        Idempotente por (fecha_evento, deporte, evento, pick): si ya existe un
        pick equivalente pendiente del mismo día, no lo duplica.
        """
        with _LOCK:
            picks = self._cargar()
            fecha = pick_data.get("fecha") or datetime.now().strftime("%Y-%m-%d")
            fecha_evento = pick_data.get("fecha_evento") or fecha
            deporte = (pick_data.get("deporte") or "").upper()
            evento = pick_data.get("evento", "")
            texto = pick_data.get("pick", "")

            # Dedupe
            for p in picks:
                if (p.get("fecha_evento") == fecha_evento and
                        (p.get("deporte") or "").upper() == deporte and
                        p.get("evento") == evento and
                        p.get("pick") == texto):
                    return p.get("id", "")

            pid = uuid.uuid4().hex[:8]
            registro = {
                "id": pid,
                "fecha": fecha,
                "timestamp": _ahora_iso(),
                "deporte": deporte,
                "liga": pick_data.get("liga", ""),
                "evento": evento,
                "local": pick_data.get("local", ""),
                "visitante": pick_data.get("visitante", ""),
                "mercado": pick_data.get("mercado", ""),
                "pick": texto,
                "seleccion": pick_data.get("seleccion", ""),
                "linea": pick_data.get("linea"),
                "cuota": float(pick_data.get("cuota", 1.90) or 1.90),
                "odds_american": str(pick_data.get("odds_american", "")),
                "confianza": float(pick_data.get("confianza", 0) or 0),
                "ev": float(pick_data.get("ev", 0) or 0),
                "stake": int(pick_data.get("stake", 1) or 1),
                "fuente": pick_data.get("fuente", "Heuristico"),
                "fecha_evento": fecha_evento,
                "estado": "pendiente",
                "resultado_real": "",
                "resuelto_en": None,
                "parlay_id": pick_data.get("parlay_id"),
            }
            picks.append(registro)
            self._guardar(picks)
            return pid

    def log_varios(self, lista_picks, parlay_id=None):
        """Registra una lista de picks (p.ej. las legs de un parlay)."""
        ids = []
        for pd in lista_picks:
            if parlay_id and not pd.get("parlay_id"):
                pd = dict(pd, parlay_id=parlay_id)
            ids.append(self.log_pick(pd))
        return ids

    # ── Resolución de resultados ──────────────────────────────────────────
    def resolver(self, pick_id: str, estado: str, resultado_real: str = "") -> bool:
        estado = (estado or "").lower()
        if estado not in ESTADOS_VALIDOS:
            return False
        with _LOCK:
            picks = self._cargar()
            for p in picks:
                if p.get("id") == pick_id:
                    p["estado"] = estado
                    p["resultado_real"] = resultado_real
                    p["resuelto_en"] = _ahora_iso()
                    self._guardar(picks)
                    return True
        return False

    def pendientes(self):
        return [p for p in self._cargar() if p.get("estado") == "pendiente"]

    def todos(self):
        return self._cargar()

    # ── FASE 2: REFLEXIÓN ─────────────────────────────────────────────────
    def stats(self):
        """Tasa de acierto global, por deporte y por mercado (solo resueltos)."""
        picks = self._cargar()
        resueltos = [p for p in picks if p.get("estado") in ("ganado", "perdido")]

        def _resumen(subset):
            n = len(subset)
            ok = sum(1 for p in subset if p.get("estado") == "ganado")
            wr = round(ok / n * 100, 1) if n else 0.0
            # ROI con cuotas: ganadas pagan (cuota-1), perdidas -1
            ganancia = sum((p.get("cuota", 1.9) - 1) if p.get("estado") == "ganado" else -1
                           for p in subset)
            roi = round(ganancia / n * 100, 1) if n else 0.0
            return {"total": n, "aciertos": ok, "win_rate": wr, "roi": roi}

        por_deporte = {}
        por_mercado = {}
        por_deporte_mercado = {}
        por_fuente = {}
        por_fuente_deporte = {}
        for p in resueltos:
            dep = (p.get("deporte") or "?").upper()
            mer = p.get("mercado") or "?"
            fte = p.get("fuente") or "Heuristico"
            por_deporte.setdefault(dep, []).append(p)
            por_mercado.setdefault(mer, []).append(p)
            por_deporte_mercado.setdefault((dep, mer), []).append(p)
            por_fuente.setdefault(fte, []).append(p)
            por_fuente_deporte.setdefault((fte, dep), []).append(p)

        # Pendientes por fuente (para ver qué se está acumulando aún sin resolver)
        pend_por_fuente = {}
        for p in picks:
            if p.get("estado") == "pendiente":
                pend_por_fuente[p.get("fuente") or "Heuristico"] = \
                    pend_por_fuente.get(p.get("fuente") or "Heuristico", 0) + 1

        return {
            "global": _resumen(resueltos),
            "pendientes": sum(1 for p in picks if p.get("estado") == "pendiente"),
            "por_deporte": {k: _resumen(v) for k, v in por_deporte.items()},
            "por_mercado": {k: _resumen(v) for k, v in por_mercado.items()},
            "por_deporte_mercado": {f"{k[0]} · {k[1]}": _resumen(v)
                                    for k, v in por_deporte_mercado.items()},
            "por_fuente": {k: _resumen(v) for k, v in por_fuente.items()},
            "por_fuente_deporte": {f"{k[0]} · {k[1]}": _resumen(v)
                                   for k, v in por_fuente_deporte.items()},
            "pendientes_por_fuente": pend_por_fuente,
        }

    # ── FASE 3: EVOLUCIÓN ─────────────────────────────────────────────────
    def factor_confianza(self, deporte: str, mercado: str, min_muestras: int = 8) -> float:
        """Multiplicador de confianza según el rendimiento histórico.

        - <1.0 penaliza mercados con baja tasa de acierto (ej. Over 2.5 fútbol).
        - >1.0 premia mercados consistentemente acertados.
        Devuelve 1.0 si no hay muestras suficientes (no castiga sin datos).
        """
        dep = (deporte or "").upper()
        mer = mercado or ""
        subset = [p for p in self._cargar()
                  if (p.get("deporte") or "").upper() == dep
                  and p.get("mercado") == mer
                  and p.get("estado") in ("ganado", "perdido")]
        if len(subset) < min_muestras:
            return 1.0
        wr = sum(1 for p in subset if p["estado"] == "ganado") / len(subset)
        # Mapear win-rate a un factor suave en [0.5, 1.25]
        if wr >= 0.60:
            return 1.25
        if wr >= 0.53:
            return 1.10
        if wr >= 0.47:
            return 1.0
        if wr >= 0.40:
            return 0.80
        return 0.55

    def ajustar_confianza(self, deporte, mercado, confianza):
        """Aplica el factor histórico a una confianza (acotado 1-99)."""
        try:
            c = float(confianza) * self.factor_confianza(deporte, mercado)
            return max(1, min(99, round(c, 1)))
        except Exception:
            return confianza


# Instancia global
pick_memory = PickMemory()
