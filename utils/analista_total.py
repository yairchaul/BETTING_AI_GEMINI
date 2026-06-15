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

_RESPONSE_SCHEMA = ('{"pick":"<texto>","confianza":<0-100>,"stake":<1-3>,'
                    '"razon":"<por qué, nombrando el factor clave>",'
                    '"alerta":"<aviso de contexto: cambio de peso, racha/momentum, lesión, '
                    'inactividad larga, debut, motivación — o cadena vacía si no aplica>",'
                    '"mercado":"MONEYLINE|OVER_UNDER|STRIKEOUTS|HOME_RUN|BTTS|HANDICAP|METODO|DISTANCIA"}')

_SYSTEM_PERSONA = (
    "Eres el 'Analista Deportivo BETTING_AI', experto senior en apuestas deportivas con enfoque cuantitativo "
    "PERO con criterio de contexto, como un apostador profesional que también lee la noticia. "
    "Tu trabajo: de TODOS los mercados disponibles del partido, elegir el ÚNICO con mayor valor esperado (EV) y probabilidad real, "
    "no solo el ganador. Recibes un análisis heurístico (trae datos reales: récords, pitchers, stats). "
    "PUEDES y DEBES CONTRADECIR al heurístico cuando el CONTEXTO lo justifique, y lo explicas. "
    "Usa tu conocimiento del contexto MÁS RECIENTE de cada equipo/peleador/jugador: "
    "• RACHA y MOMENTUM: alguien que llega ganando varias seguidas y en ascenso puede vencer a un favorito en papel "
    "(ejemplo típico: un peleador en racha que sorprende). Favorécelo aunque las stats base digan lo contrario. "
    "• CAMBIO DE DIVISIÓN DE PESO (UFC/boxeo): si un peleador SUBE de categoría, su poder pega menos contra rivales más "
    "grandes y el cuerpo aún se adapta → PENALÍZALO y avísalo. Si BAJA, considera el desgaste del corte. "
    "• LESIONES, REGRESO DE INACTIVIDAD LARGA, edad/declive, viajes, motivación (título, revancha). "
    "Si detectas cualquiera de estos, resúmelo en el campo 'alerta'. Si no, deja 'alerta' vacío. "
    "Reglas por deporte: "
    "MLB → Moneyline vs Over/Under vs Home Run (bateador concreto) vs Strikeouts del pitcher; el abridor del día es el factor #1. "
    "NBA → Moneyline vs Hándicap vs Total (O/U) vs props de triples. "
    "UFC → Ganador (Moneyline) vs Método (KO/Sumisión/Decisión) vs Distancia (si llega o no a decisión). "
    "Fútbol → 1X2 vs Doble oportunidad vs BTTS vs Over/Under goles. "
    "Sé conservador con la confianza: 50-60% pick dudoso, 60-72% sólido, 73%+ solo con ventaja clara. "
    "IMPORTANTE: Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional, sin markdown, sin explicaciones fuera del JSON. "
    f"Estructura OBLIGATORIA: {_RESPONSE_SCHEMA}"
)

_MODEL_KEYS = {
    "Claude": "claude",
    "DeepSeek": "deepseek",
    "Gemini": "gemini",
    "Groq": "groq",
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
        claude_client=None,
        deepseek_client=None,
        gemini_client=None,
        groq_client=None,
        new_ai_client=None,
        openai_client=None,
        selected_model: str = "Heurístico",
        conservative_mode: bool = False,
        token_log: list = None,
        token_alert_threshold: int = 5000,
    ):
        # Diccionario de clientes de IA disponibles, ordenado alfabéticamente.
        self._clients = {
            "claude": claude_client,
            "deepseek": deepseek_client,
            "gemini": gemini_client,
            "groq": groq_client,
            "new_ai": new_ai_client,  # Considerar refactorizar a un nombre de proveedor estándar
            "openai": openai_client,
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
        local = partido.get('local', 'Local')
        visit = partido.get('visitante', 'Visitante')
        rec_l = partido.get('local_record') or partido.get('record_local', 'N/A')
        rec_v = partido.get('visitante_record') or partido.get('record_visit', 'N/A')
        odds = partido.get('odds', {}) or {}
        ml = odds.get('moneyline', {}) if isinstance(odds.get('moneyline'), dict) else {}
        ou = odds.get('overUnder') or odds.get('over_under', 'N/A')
        if self.conservative_mode:
            return (f"NBA: {local} ({rec_l}) vs {visit} ({rec_v}). "
                    f"Pick heurístico: {heuristica.get('recomendacion', 'N/A')} "
                    f"({heuristica.get('confianza', 0)}%). Confirma o corrige. JSON.")
        return (
            f"Deporte: NBA\n"
            f"Partido: {local} (local, {rec_l}) vs {visit} (visita, {rec_v})\n"
            f"Racha local: {partido.get('local_streak', 'N/A')} | Racha visitante: {partido.get('visitante_streak', 'N/A')}\n"
            f"Moneyline: local={ml.get('local', 'N/A')} / visitante={ml.get('visitante', 'N/A')}\n"
            f"Total O/U: {ou}\n"
            f"Análisis heurístico (motores propios): {json.dumps(heuristica, ensure_ascii=False)[:700]}\n"
            "Elige el mejor mercado (Moneyline, Hándicap o Total) y da tu recomendación final en JSON."
        )

    def _prompt_mlb(self, partido: dict, heur: dict, hr_candidates: list,
                    clima: dict, k_proj: dict, ou_analysis) -> str:
        local = partido.get('local', 'Local')
        visit = partido.get('visitante', 'Visitante')
        pit = partido.get('pitchers', {}) or {}
        p_loc = pit.get('local', {}).get('nombre', 'TBD') if isinstance(pit.get('local'), dict) else 'TBD'
        p_vis = pit.get('visitante', {}).get('nombre', 'TBD') if isinstance(pit.get('visitante'), dict) else 'TBD'
        odds = partido.get('odds', {}) or {}
        # Los candidatos HR pueden venir del argumento o dentro del heurístico (motor v25)
        hrs = hr_candidates or heur.get('hr_candidates', []) or []
        hr_desc = [f"{c.get('jugador', c.get('player', '?'))} ({c.get('probabilidad', c.get('prob', 0))}%)" for c in hrs[:4]]
        k_picks = heur.get('k_picks', [])
        if self.conservative_mode:
            return (f"MLB: {visit} @ {local}. Pick: {heur.get('pick', 'N/A')} ({heur.get('confianza', 0)}%). "
                    f"HR candidatos: {len(hrs)}. O/U: {heur.get('ou_pick', 'N/A')}. JSON.")
        return (
            f"Deporte: MLB\n"
            f"Partido: {visit} (visita) @ {local} (local)\n"
            f"Récords: local={partido.get('local_record', 'N/A')} / visitante={partido.get('visitante_record', 'N/A')}\n"
            f"Pitcher local: {p_loc} | Pitcher visitante: {p_vis}\n"
            f"Línea O/U carreras: {odds.get('over_under', 'N/A')}\n"
            f"Clima: {json.dumps(clima, ensure_ascii=False)[:180] if clima else 'N/A'}\n"
            f"Candidatos a HOME RUN (bateador + prob real): {', '.join(hr_desc) if hr_desc else 'ninguno detectado'}\n"
            f"Picks de Strikeouts (pitcher): {json.dumps(k_picks, ensure_ascii=False)[:200] if k_picks else 'N/A'}\n"
            f"O/U heurístico: {heur.get('ou_pick', 'N/A')} ({heur.get('ou_confianza', 0)}%)\n"
            f"Análisis heurístico completo: {json.dumps(heur, ensure_ascii=False)[:700]}\n"
            "De TODOS los mercados (Moneyline, O/U carreras, Home Run de un bateador concreto, Strikeouts del pitcher), "
            "elige el de mayor probabilidad/valor y justifícalo. Recomendación final en JSON."
        )

    def _prompt_ufc(self, combate: dict, resultado: dict, mercados_disponibles: Optional[str] = None) -> str:
        # El combate trae peleador1/peleador2 (cada uno dict con stats reales)
        p1 = combate.get('peleador1', {}) if isinstance(combate.get('peleador1'), dict) else {}
        p2 = combate.get('peleador2', {}) if isinstance(combate.get('peleador2'), dict) else {}
        n1 = p1.get('nombre') or combate.get('peleador_a', 'Peleador A')
        n2 = p2.get('nombre') or combate.get('peleador_b', 'Peleador B')

        def _resumen(p):
            ec = p.get('estadisticas_carrera', {}) or {}
            return (f"record {p.get('record', 'N/A')}, KO {int((p.get('ko_rate', 0) or 0)*100)}%, "
                    f"edad {p.get('edad', '?')}, división {p.get('division', '?')} ({p.get('peso', '?')}), "
                    f"SLpM {ec.get('sig_strikes_landed_per_min', 0)}, "
                    f"racha {p.get('streak', 0)}W")

        if self.conservative_mode:
            return (f"UFC: {n1} vs {n2}. Pick: {resultado.get('ganador', resultado.get('pick', 'N/A'))} "
                    f"({resultado.get('confianza', 0)}%). JSON.")

        mercados_prompt = ""
        if mercados_disponibles:
            mercados_prompt = f"\nMercados/cuotas: {mercados_disponibles}\n"
        mejor = resultado.get('mejor_apuesta', {})

        return (
            f"Deporte: UFC/MMA\n"
            f"Pelea: {n1} vs {n2}\n"
            f"{n1}: {_resumen(p1)}\n"
            f"{n2}: {_resumen(p2)}\n"
            f"Heurístico → ganador: {resultado.get('ganador', 'N/A')} ({resultado.get('confianza', 0)}%), "
            f"método: {resultado.get('metodo', 'N/A')}, "
            f"mejor mercado: {mejor.get('mercado', 'N/A')} → {mejor.get('apuesta', 'N/A')} ({mejor.get('confianza', 0)}%)\n"
            f"{mercados_prompt}"
            "Antes de decidir, valora el CONTEXTO con tu conocimiento: ¿alguno SUBE o BAJA de división de peso? "
            "¿quién llega con mejor racha/momentum? ¿regreso de inactividad, lesión o declive por edad? "
            "Si la racha o el cambio de peso cambian el panorama, contradice al heurístico y dilo en 'alerta'. "
            "Luego evalúa Ganador vs Método (KO/Sumisión/Decisión) vs Distancia (¿llega a decisión?) y elige el de mayor valor. "
            "Recomendación final en JSON."
        )

    def _prompt_futbol(self, partido: dict, heur: dict, jerarquico: dict) -> str:
        local = partido.get('home') or partido.get('local', 'Local')
        visit = partido.get('away') or partido.get('visitante', 'Visitante')
        odds = partido.get('odds', {}) or {}
        ml = odds.get('moneyline', {}) if isinstance(odds.get('moneyline'), dict) else {}
        es_torneo = partido.get('es_torneo', False)
        fase = partido.get('fase', '')
        if self.conservative_mode:
            return (f"Fútbol: {local} vs {visit}. Pick: {heur.get('pick', 'N/A')}. JSON.")
        return (
            f"Deporte: Fútbol{' (TORNEO eliminatoria)' if es_torneo else ''}\n"
            f"Partido: {local} (local) vs {visit} (visita)\n"
            f"Liga/Torneo: {partido.get('liga', 'N/A')}" + (f" | Fase: {fase}\n" if fase else "\n") +
            f"Récords: local={partido.get('local_record', 'N/A')} / visitante={partido.get('visitante_record', 'N/A')}\n"
            f"Cuotas 1X2: local={ml.get('home', ml.get('local', 'N/A'))} / "
            f"empate={ml.get('draw', 'N/A')} / visita={ml.get('away', ml.get('visitante', 'N/A'))}\n"
            f"O/U goles: {odds.get('over_under', 'N/A')}\n"
            f"Análisis heurístico jerárquico: {json.dumps(heur, ensure_ascii=False)[:500]}\n"
            "Evalúa 1X2 vs Doble oportunidad vs BTTS vs Over/Under goles y elige el de mayor valor. "
            "Recomendación final en JSON."
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

    def analizar_ufc(self, combate: dict, resultado: dict, mercados_disponibles: Optional[str] = None) -> dict:
        return self._dispatch(self._prompt_ufc(combate, resultado, mercados_disponibles))

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
