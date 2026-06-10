# -*- coding: utf-8 -*-
"""
AnalistaTotal — Orquestador multi-proveedor de IA para decisiones de apuestas.

Proveedores soportados: Gemini, Groq, DeepSeek, Claude, OpenAI-compatible.
Modos: proveedor único o "Votación (Todas las IAs)" con mayoría simple.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_RESPONSE_SCHEMA = '{"pick":"<texto>","confianza":<0-100>,"stake":<1-3>,"razon":"<texto>","mercado":"MONEYLINE|OVER_UNDER|STRIKEOUTS|HOME_RUN|BTTS|HANDICAP"}'

_SYSTEM_PERSONA = (
    "Eres el 'Analista Deportivo BETTING_AI', experto senior en apuestas deportivas. "
    "Maximiza el ROI con análisis técnico riguroso. "
    "IMPORTANTE: Tu respuesta DEBE ser ÚNICAMENTE un objeto JSON válido, sin texto adicional, "
    "sin bloques de código markdown, sin explicaciones fuera del JSON. "
    f"Estructura OBLIGATORIA: {_RESPONSE_SCHEMA}"
)

_MODEL_KEYS = {
    "Gemini": "gemini",
    "Groq": "groq",
    "DeepSeek": "deepseek",
    "Claude": "claude",
    "OpenAI": "openai",
}


def _parse_json_safe(text: str) -> Optional[dict]:
    """Extrae el primer JSON válido del texto, limpiando markdown si es necesario."""
    if not text:
        return None
    # Strip markdown code fences
    for fence in ("```json", "```"):
        if fence in text:
            text = text.split(fence)[-1].split("```")[0]
    text = text.strip()
    # Find first { ... }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return None


class AnalistaTotal:
    """
    Orquestador de IA para análisis de partidos deportivos.

    Acepta múltiples clientes GenericAIClient y despacha las consultas según
    el modelo seleccionado por el usuario. Soporta modo de votación por mayoría.
    """

    def __init__(
        self,
        gemini_client=None,
        groq_client=None,
        deepseek_client=None,
        new_ai_client=None,
        claude_client=None,
        openai_client=None,
        selected_model: str = "Heurístico",
        conservative_mode: bool = False,
        token_log: list = None,
        token_alert_threshold: int = 5000,
    ):
        self._clients = {
            "gemini": gemini_client,
            "groq": groq_client,
            "deepseek": deepseek_client,
            "claude": claude_client,
            "openai": openai_client,
            "new_ai": new_ai_client,
        }
        self.selected_model = selected_model
        self.conservative_mode = conservative_mode
        self.token_log = token_log or []
        self.token_alert_threshold = token_alert_threshold

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _available_clients(self) -> list[tuple[str, object]]:
        """Retorna (nombre, cliente) para los proveedores con cliente válido."""
        result = []
        for name, client in self._clients.items():
            if client and getattr(client, "client", None):
                result.append((name, client))
        return result

    def _active_client(self):
        """Retorna el cliente correspondiente al modelo seleccionado."""
        key = _MODEL_KEYS.get(self.selected_model)
        if not key:
            return None, None
        client = self._clients.get(key)
        if client and getattr(client, "client", None):
            return key, client
        return None, None

    def _call(self, client, prompt: str) -> Optional[dict]:
        """Llama a un GenericAIClient y retorna el dict parseado o None."""
        try:
            raw = client.orquestrar_decision(prompt)
            result = _parse_json_safe(raw)
            if result and "pick" in result:
                return result
            # Fallback: if JSON came wrapped in an 'error' key
            if isinstance(result, dict) and "error" in result:
                logger.warning(f"Proveedor retornó error: {result['error']}")
            return None
        except Exception as e:
            logger.error(f"Error llamando proveedor: {e}")
            return None

    def _vote(self, prompt: str) -> dict:
        """
        Llama a todos los proveedores disponibles y retorna el resultado con
        mayor consenso (pick más frecuente). Añade campo 'proveedor' con el detalle.
        """
        available = self._available_clients()
        if not available:
            return {"error": "Sin proveedores disponibles", "pick": "N/A", "confianza": 0, "stake": 1, "razon": "Sin IAs configuradas", "mercado": "MONEYLINE"}

        responses = []
        for name, client in available:
            result = self._call(client, prompt)
            if result:
                result["_proveedor"] = name
                responses.append(result)

        if not responses:
            return {"error": "Todos los proveedores fallaron", "pick": "N/A", "confianza": 0, "stake": 1, "razon": "Error en todos los proveedores", "mercado": "MONEYLINE"}

        if len(responses) == 1:
            r = responses[0]
            r["proveedor"] = r.pop("_proveedor", "IA")
            return r

        # Mayoría por pick
        from collections import Counter
        picks = [r.get("pick", "") for r in responses]
        winner_pick, count = Counter(picks).most_common(1)[0]
        winners = [r for r in responses if r.get("pick") == winner_pick]
        best = max(winners, key=lambda r: r.get("confianza", 0))

        proveedores_usados = [r.pop("_proveedor", "?") for r in responses]
        best["proveedor"] = f"Votación {count}/{len(responses)} ({', '.join(proveedores_usados)})"
        best.pop("_proveedor", None)
        return best

    def _dispatch(self, prompt: str) -> dict:
        """Despacha el prompt al proveedor/modo seleccionado."""
        if self.selected_model == "Votación (Todas las IAs)":
            return self._vote(prompt)

        name, client = self._active_client()
        if not client:
            return {
                "error": f"Proveedor '{self.selected_model}' no disponible",
                "pick": "N/A", "confianza": 0, "stake": 1,
                "razon": f"API key de {self.selected_model} no configurada o cliente no inicializado",
                "mercado": "MONEYLINE",
            }
        result = self._call(client, prompt)
        if result:
            result["proveedor"] = self.selected_model
            return result
        return {
            "error": f"Respuesta inválida de {self.selected_model}",
            "pick": "N/A", "confianza": 0, "stake": 1,
            "razon": f"{self.selected_model} no devolvió JSON válido",
            "mercado": "MONEYLINE",
        }

    # ------------------------------------------------------------------ #
    # Prompt builders
    # ------------------------------------------------------------------ #

    def _prompt_nba(self, partido: dict, heuristica: dict) -> str:
        if self.conservative_mode:
            return (
                f"NBA: {partido.get('local')} vs {partido.get('visitante')}. "
                f"Pick heurístico: {heuristica.get('recomendacion', 'N/A')} "
                f"({heuristica.get('confianza', 0)}%). Confirma o corrige. JSON."
            )
        return (
            f"Deporte: NBA\n"
            f"Partido: {partido.get('local')} vs {partido.get('visitante')}\n"
            f"Record local: {partido.get('record_local', 'N/A')} | "
            f"Record visitante: {partido.get('record_visit', 'N/A')}\n"
            f"Racha local: {partido.get('racha_local', 'N/A')} | "
            f"Racha visitante: {partido.get('racha_visitante', 'N/A')}\n"
            f"Lesiones: {partido.get('lesiones', 'N/A')}\n"
            f"Cuota: {partido.get('cuota_local', 'N/A')} / {partido.get('cuota_visitante', 'N/A')}\n"
            f"Total O/U: {partido.get('total_ou', 'N/A')}\n"
            f"Análisis heurístico: {json.dumps(heuristica, ensure_ascii=False)[:600]}\n"
            "Proporciona tu recomendación final en JSON."
        )

    def _prompt_mlb(self, partido: dict, heur: dict, hr_candidates: list,
                    clima: dict, k_proj: dict, ou_analysis) -> str:
        if self.conservative_mode:
            return (
                f"MLB: {partido.get('local')} vs {partido.get('visitante')}. "
                f"Pick: {heur.get('pick', 'N/A')} ({heur.get('confianza', 0)}%). "
                f"HR candidatos: {len(hr_candidates)}. JSON."
            )
        hr_names = [c.get("jugador", c.get("player", "?")) for c in (hr_candidates or [])[:3]]
        return (
            f"Deporte: MLB\n"
            f"Partido: {partido.get('local')} vs {partido.get('visitante')}\n"
            f"Pitcher local: {partido.get('pitcher_local', 'N/A')} | "
            f"Pitcher visitante: {partido.get('pitcher_visitante', 'N/A')}\n"
            f"ERA local: {partido.get('era_local', 'N/A')} | "
            f"ERA visitante: {partido.get('era_visit', 'N/A')}\n"
            f"Clima: {json.dumps(clima, ensure_ascii=False)[:200] if clima else 'N/A'}\n"
            f"Candidatos HR: {', '.join(hr_names) if hr_names else 'ninguno'}\n"
            f"Proyecciones K: local={k_proj.get('local', 'N/A')}, visit={k_proj.get('visit', 'N/A')}\n"
            f"Análisis O/U: {str(ou_analysis)[:200] if ou_analysis else 'N/A'}\n"
            f"Análisis heurístico: {json.dumps(heur, ensure_ascii=False)[:600]}\n"
            "Proporciona tu recomendación final en JSON."
        )

    def _prompt_ufc(self, combate: dict, resultado: dict) -> str:
        if self.conservative_mode:
            return (
                f"UFC: {combate.get('peleador_a')} vs {combate.get('peleador_b')}. "
                f"Pick heurístico: {resultado.get('pick', 'N/A')} "
                f"({resultado.get('confianza', 0)}%). JSON."
            )
        return (
            f"Deporte: UFC/MMA\n"
            f"Pelea: {combate.get('peleador_a')} vs {combate.get('peleador_b')}\n"
            f"Stats A: {json.dumps(combate.get('stats_a', {}), ensure_ascii=False)[:300]}\n"
            f"Stats B: {json.dumps(combate.get('stats_b', {}), ensure_ascii=False)[:300]}\n"
            f"Análisis heurístico: {json.dumps(resultado, ensure_ascii=False)[:500]}\n"
            "Proporciona tu recomendación final en JSON."
        )

    def _prompt_futbol(self, partido: dict, heur: dict, jerarquico: dict) -> str:
        if self.conservative_mode:
            return (
                f"Fútbol: {partido.get('local')} vs {partido.get('visitante')}. "
                f"Pick: {heur.get('pick', 'N/A')}. JSON."
            )
        return (
            f"Deporte: Fútbol\n"
            f"Partido: {partido.get('local')} vs {partido.get('visitante')}\n"
            f"Liga: {partido.get('liga', 'N/A')}\n"
            f"Forma local: {partido.get('forma_local', 'N/A')} | "
            f"Forma visitante: {partido.get('forma_visitante', 'N/A')}\n"
            f"Cuotas: {partido.get('cuota_local', 'N/A')} / empate {partido.get('cuota_empate', 'N/A')} / {partido.get('cuota_visitante', 'N/A')}\n"
            f"Análisis heurístico: {json.dumps(heur, ensure_ascii=False)[:400]}\n"
            f"Análisis jerárquico: {json.dumps(jerarquico, ensure_ascii=False)[:400]}\n"
            "Proporciona tu recomendación final en JSON."
        )

    # ------------------------------------------------------------------ #
    # Public sport methods
    # ------------------------------------------------------------------ #

    def analizar_nba(self, partido: dict, heuristica: dict) -> dict:
        return self._dispatch(self._prompt_nba(partido, heuristica))

    def analizar_mlb(self, partido: dict, heur_res: dict,
                     hr_candidates: list = None, clima: dict = None,
                     k_projections: dict = None, ou_analysis=None) -> dict:
        return self._dispatch(
            self._prompt_mlb(partido, heur_res, hr_candidates or [], clima or {}, k_projections or {}, ou_analysis)
        )

    def analizar_ufc(self, combate: dict, resultado: dict) -> dict:
        return self._dispatch(self._prompt_ufc(combate, resultado))

    def analizar_futbol(self, partido: dict, heur_result: dict, jerarquico_result: dict) -> dict:
        return self._dispatch(self._prompt_futbol(partido, heur_result, jerarquico_result))

    def analizar_partido_completo(self, deporte: str, partido: dict, **kwargs) -> str:
        """Compatibilidad con código legacy que llama a este método."""
        deporte_lower = deporte.lower()
        if deporte_lower == "nba":
            result = self.analizar_nba(partido, kwargs)
        elif deporte_lower == "mlb":
            result = self.analizar_mlb(partido, kwargs)
        elif deporte_lower == "ufc":
            result = self.analizar_ufc(partido, kwargs)
        else:
            result = self.analizar_futbol(partido, kwargs, {})
        return json.dumps(result, ensure_ascii=False)
