# -*- coding: utf-8 -*-
"""SCRAPER MASIVO - Últimos 10 días de resultados MLB"""
import re
import os
import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
from typing import Optional, List

# MLB Stats API oficial (statsapi). Import defensivo: si la dependencia o el
# módulo de modelos no está disponible, fetch_boxscore degrada a None sin
# romper el resto del scraper (Playwright/ESPN sigue operativo).
try:
    import statsapi  # type: ignore
except Exception:  # pragma: no cover - dependencia opcional en runtime
    statsapi = None  # type: ignore

try:
    from motors.mlb_backtest_models import (
        GameResult,
        HomeRunRecord,
        StrikeoutRecord,
    )
except Exception:  # pragma: no cover - tolerar import fallido
    GameResult = None  # type: ignore
    HomeRunRecord = None  # type: ignore
    StrikeoutRecord = None  # type: ignore

# Estados terminales aceptados por la MLB Stats API. El diseño dice "solo Final"
# pero el feed real incluye estas variantes — todas son terminales.
_FINAL_STATUSES = {"Final", "Game Over", "Completed Early"}

# Ruta canónica del archivo idempotente de resultados (Task 2.2).
# Toda persistencia de collect_last_n_days fluye por aquí; el legado
# `resultados_10_dias.json` queda solo para `guardar_json` por compatibilidad.
RESULTS_JSON_PATH = "data/resultados_reales_15dias.json"

# Reintentos con backoff exponencial (Task 2.2 — Requirement 1.7).
# 3 intentos: 1s, 2s, 4s. Aplica tanto a schedule como a fetch_boxscore.
RETRY_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0

class MLBResultadosScraper:
    def __init__(self, dias=10):
        self.dias = dias
        self.resultados = []                    # legacy dicts (back-compat)
        # Nuevos atributos para collect_last_n_days (Task 2.2):
        # resultados_modelo guarda los GameResult vivos (sin partials),
        # _partials registra placeholders para reintentar en la próxima corrida.
        self.resultados_modelo: List["GameResult"] = []
        self._partials: dict = {}
    
    def scrape_ultimos_dias(self):
        """
        Devuelve resultados como list[dict] (back-compat). Intenta primero la
        MLB Stats API vía `collect_last_n_days`; si statsapi/modelos no están
        disponibles, fallan o devuelven lista vacía, degrada al scraper
        original Playwright/ESPN preservado en `_scrape_espn_fallback`.

        Postconditions:
          - self.resultados queda poblado con dicts en el shape histórico.
          - Las entradas parciales (game_pk con boxscore no disponible) se
            agregan con la marca `partial=True` para que generar_reporte y
            otros consumidores las distingan.
        """
        # Ruta preferida: API oficial vía collect_last_n_days.
        if statsapi is not None and GameResult is not None:
            try:
                # collect_last_n_days valida internamente el mínimo de 15 días.
                game_results = self.collect_last_n_days(dias=max(self.dias, 15))
                if game_results or self._partials:
                    self.resultados = [self._game_result_to_legacy_dict(gr) for gr in game_results]
                    # Adjuntar partials para que el consumidor los vea (back-compat).
                    for partial in self._partials.values():
                        self.resultados.append(self._partial_to_legacy_dict(partial))
                    return self.resultados
                # Lista vacía: cae al respaldo ESPN para no devolver nada al usuario.
                print("[scrape_ultimos_dias] MLB API sin resultados, usando ESPN fallback")
            except Exception as e:
                print(f"[scrape_ultimos_dias] MLB API falló, usando ESPN fallback: {e}")
        # Fallback: comportamiento legacy original (Playwright/ESPN).
        return self._scrape_espn_fallback()

    def _scrape_espn_fallback(self):
        """
        Respaldo Playwright/ESPN. Cuerpo original de `scrape_ultimos_dias`
        preservado verbatim. Se invoca cuando la MLB Stats API no está
        disponible o no produce resultados. Devuelve list[dict] en el shape
        legacy esperado por consumidores antiguos.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()
            
            for i in range(self.dias):
                fecha = datetime.now() - timedelta(days=i+1)
                fecha_str = fecha.strftime("%Y%m%d")
                url = f"https://www.espn.com.mx/beisbol/mlb/calendario/_/fecha/{fecha_str}"
                
                print(f"\n📅 Procesando {fecha.strftime('%Y-%m-%d')}...")
                
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Buscar todas las tablas de resultados
                    tables = soup.find_all('table')
                    juegos_dia = []
                    
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            row_text = row.get_text()
                            
                            # Buscar patrones de resultado (ej: "BOS 8, DET 6" o "NYY 7, KC 0")
                            score_pattern = r'([A-Z]{3})\s*(\d+)\s*,\s*([A-Z]{3})\s*(\d+)'
                            match = re.search(score_pattern, row_text)
                            
                            if match:
                                away_abbr = match.group(1)
                                away_score = match.group(2)
                                home_abbr = match.group(3)
                                home_score = match.group(4)
                                
                                # Mapeo de abreviaturas a nombres completos
                                team_names = {
                                    'DET': 'Detroit Tigers', 'BOS': 'Boston Red Sox',
                                    'NYY': 'New York Yankees', 'KC': 'Kansas City Royals',
                                    'HOU': 'Houston Astros', 'CLE': 'Cleveland Guardians',
                                    'CIN': 'Cincinnati Reds', 'TB': 'Tampa Bay Rays',
                                    'STL': 'St. Louis Cardinals', 'MIA': 'Miami Marlins',
                                    'ATL': 'Atlanta Braves', 'WSH': 'Washington Nationals',
                                    'BAL': 'Baltimore Orioles', 'PHI': 'Philadelphia Phillies',
                                    'CHC': 'Chicago Cubs', 'LAD': 'Los Angeles Dodgers',
                                    'COL': 'Colorado Rockies', 'TOR': 'Toronto Blue Jays',
                                    'LAA': 'Los Angeles Angels', 'ATH': 'Athletics',
                                    'SEA': 'Seattle Mariners', 'SF': 'San Francisco Giants',
                                    'MIL': 'Milwaukee Brewers', 'PIT': 'Pittsburgh Pirates',
                                    'NYM': 'New York Mets', 'MIN': 'Minnesota Twins',
                                    'TEX': 'Texas Rangers', 'ARI': 'Arizona Diamondbacks',
                                    'SD': 'San Diego Padres', 'CHW': 'Chicago White Sox'
                                }
                                
                                away_team = team_names.get(away_abbr, away_abbr)
                                home_team = team_names.get(home_abbr, home_abbr)
                                
                                # Determinar ganador
                                if int(away_score) > int(home_score):
                                    winner = away_team
                                    loser = home_team
                                    margin = int(away_score) - int(home_score)
                                else:
                                    winner = home_team
                                    loser = away_team
                                    margin = int(home_score) - int(away_score)
                                
                                # Extraer pitchers (buscar en celdas)
                                cells = row.find_all('td')
                                winning_pitcher = None
                                losing_pitcher = None
                                
                                for cell in cells:
                                    cell_text = cell.get_text()
                                    if 'Ganado' in cell_text:
                                        winning_pitcher = cell_text.replace('Ganado', '').strip()
                                    if 'Perdido' in cell_text:
                                        losing_pitcher = cell_text.replace('Perdido', '').strip()
                                
                                juego = {
                                    'fecha': fecha.strftime('%Y-%m-%d'),
                                    'away': away_team,
                                    'home': home_team,
                                    'away_score': int(away_score),
                                    'home_score': int(home_score),
                                    'winner': winner,
                                    'loser': loser,
                                    'margin': margin,
                                    'winning_pitcher': winning_pitcher,
                                    'losing_pitcher': losing_pitcher,
                                    'total_runs': int(away_score) + int(home_score)
                                }
                                
                                juegos_dia.append(juego)
                                print(f"   ✅ {away_team} @ {home_team}: {away_score}-{home_score} (Ganó: {winner})")
                    
                    self.resultados.extend(juegos_dia)
                    print(f"   📊 {len(juegos_dia)} juegos encontrados")
                    
                except Exception as e:
                    print(f"   ❌ Error: {str(e)[:50]}")
            
            browser.close()
        
        return self.resultados
    
    def guardar_json(self, filename="resultados_10_dias.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Resultados guardados en {filename}")
    
    def generar_reporte(self):
        if not self.resultados:
            return {}
        
        total_juegos = len(self.resultados)
        home_wins = sum(1 for r in self.resultados if r['winner'] == r['home'])
        away_wins = total_juegos - home_wins
        
        avg_margin = sum(r['margin'] for r in self.resultados) / total_juegos
        avg_total_runs = sum(r['total_runs'] for r in self.resultados) / total_juegos
        
        # Rachas por equipo
        team_streaks = {}
        for r in self.resultados:
            winner = r['winner']
            loser = r['loser']
            
            if winner not in team_streaks:
                team_streaks[winner] = {'wins': 0, 'losses': 0, 'last_10': []}
            if loser not in team_streaks:
                team_streaks[loser] = {'wins': 0, 'losses': 0, 'last_10': []}
            
            team_streaks[winner]['wins'] += 1
            team_streaks[loser]['losses'] += 1
            team_streaks[winner]['last_10'].append('W')
            team_streaks[loser]['last_10'].append('L')
        
        return {
            'total_juegos': total_juegos,
            'home_wins': home_wins,
            'away_wins': away_wins,
            'home_win_pct': round(home_wins / total_juegos * 100, 1),
            'avg_margin': round(avg_margin, 1),
            'avg_total_runs': round(avg_total_runs, 1),
            'team_streaks': team_streaks
        }

    # ------------------------------------------------------------------
    # Collect & persist (Task 2.2) — MLB Stats API con idempotencia
    # ------------------------------------------------------------------
    def collect_last_n_days(self, dias: Optional[int] = None) -> List["GameResult"]:
        """
        Recolecta resultados Final de los últimos N días vía MLB Stats API.

        Idempotente por game_pk: ejecutarla dos veces NO produce duplicados,
        porque fusiona con `data/resultados_reales_15dias.json` existente y
        devuelve solo GameResult únicos por game_pk.

        Preconditions:
          - dias >= 15 (si se pasa None, usa max(self.dias, 15)).
          - statsapi disponible (si no, retorna lista de existentes desde JSON).

        Postconditions:
          - Retorna lista de GameResult sin duplicados por game_pk.
          - Persiste en data/resultados_reales_15dias.json fusionando con lo previo.
          - Almacena los GameResult en self.resultados_modelo.
          - Los game_pk con boxscore no disponible se registran en self._partials
            como placeholders para reintentar en la próxima corrida.
        """
        # 1) Resolver el N efectivo y validarlo.
        if dias is None:
            dias = max(self.dias, 15)
        if not isinstance(dias, int) or isinstance(dias, bool) or dias < 15:
            raise ValueError("dias debe ser >= 15 (mínimo del spec)")

        # 2) Cargar el estado previo (fusión por game_pk para idempotencia).
        results: List["GameResult"] = self._load_results_json(RESULTS_JSON_PATH)
        indices: dict = {gr.game_pk: gr for gr in results}

        # 3) Si no hay statsapi, devolvemos lo que haya en disco sin error.
        if statsapi is None or GameResult is None:
            self.resultados_modelo = list(results)
            self._save_results_json(results, RESULTS_JSON_PATH)
            return results

        # 4) Recorrer los últimos N días.
        for i in range(1, dias + 1):
            fecha = datetime.now() - timedelta(days=i)
            date_str = fecha.strftime("%m/%d/%Y")
            games = self._schedule_with_retry(date_str)

            for game in games:
                if not isinstance(game, dict):
                    continue
                gp_raw = game.get("game_id") or game.get("game_pk")
                try:
                    gp = int(gp_raw) if gp_raw is not None else 0
                except (TypeError, ValueError):
                    continue
                if gp <= 0:
                    continue

                status = game.get("status", "")
                if status not in _FINAL_STATUSES:
                    continue

                # Si ya tenemos el GameResult completo de una corrida previa,
                # saltamos: idempotencia por game_pk.
                if gp in indices:
                    continue

                gr = self._fetch_boxscore_with_retry(gp)
                if gr is None:
                    # Degradación marcador-solo: marcamos como parcial usando
                    # el dict de schedule (que ya contiene away_score/home_score)
                    # para que la próxima corrida idempotente reintente el
                    # boxscore completo vía MLB API.
                    self._mark_partial(gp, fecha, game)
                    continue

                # Si este game_pk estaba como partial, lo eliminamos: ya está completo.
                if gp in self._partials:
                    del self._partials[gp]

                results.append(gr)
                indices[gr.game_pk] = gr

        # 5) Persistir de forma idempotente y dejar el estado en memoria.
        self.resultados_modelo = list(results)
        self._save_results_json(results, RESULTS_JSON_PATH)
        return results

    def _schedule_with_retry(self, date_str: str, max_attempts: int = RETRY_ATTEMPTS) -> list:
        """
        Llama a statsapi.schedule con backoff exponencial (1s, 2s, 4s).

        Retorna [] (sin lanzar) si statsapi no está disponible o si los 3
        intentos fallan; el caller debe asumir "sin juegos para esa fecha".
        """
        if statsapi is None:
            return []
        for attempt in range(max_attempts):
            try:
                games = statsapi.schedule(sportId=1, date=date_str)
                return games or []
            except Exception as e:
                if attempt == max_attempts - 1:
                    print(f"[schedule] FAIL date={date_str}: {e}")
                    return []
                time.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))
        return []

    def _fetch_boxscore_with_retry(
        self,
        game_pk: int,
        max_attempts: int = RETRY_ATTEMPTS,
    ) -> Optional["GameResult"]:
        """
        Envuelve `fetch_boxscore` con reintentos y backoff exponencial.

        `fetch_boxscore` ya degrada a None ante fallos internos; este wrapper
        repite la llamada hasta `max_attempts` veces con backoff 1s, 2s, 4s.
        Devuelve el primer GameResult válido o None tras agotar reintentos.
        """
        for attempt in range(max_attempts):
            result = self.fetch_boxscore(game_pk)
            if result is not None:
                return result
            if attempt < max_attempts - 1:
                time.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))
        return None

    def _mark_partial(self, game_pk: int, fecha: datetime, game_dict: dict) -> None:
        """Registra un placeholder parcial para reintentar en la próxima corrida."""
        self._partials[int(game_pk)] = {
            "game_pk": int(game_pk),
            "partial": True,
            "fecha": fecha.strftime("%Y-%m-%d"),
            "raw": game_dict,
        }

    def _game_result_to_dict(self, gr: "GameResult") -> dict:
        """Serializa un GameResult a dict JSON-safe para el archivo idempotente."""
        from dataclasses import asdict
        d = asdict(gr)
        d["partial"] = False
        return d

    def _dict_to_game_result(self, d: dict) -> Optional["GameResult"]:
        """
        Rehidrata un GameResult desde dict (best-effort).

        Retorna None si:
          - El dict está marcado como partial=True (debe procesarse aparte).
          - Los modelos no están disponibles.
          - La validación de GameResult falla.
        """
        if not isinstance(d, dict):
            return None
        if d.get("partial"):
            return None
        if GameResult is None or HomeRunRecord is None or StrikeoutRecord is None:
            return None
        try:
            hr_list = [HomeRunRecord(**h) for h in d.get("home_runs", []) if isinstance(h, dict)]
            k_list = [StrikeoutRecord(**k) for k in d.get("strikeouts", []) if isinstance(k, dict)]
            valid_keys = {
                "game_pk", "fecha", "away", "home", "away_score", "home_score",
                "winner", "margin", "total_runs", "venue", "status",
            }
            kwargs = {k: v for k, v in d.items() if k in valid_keys}
            kwargs["home_runs"] = hr_list
            kwargs["strikeouts"] = k_list
            return GameResult(**kwargs)
        except Exception:
            return None

    def _game_result_to_legacy_dict(self, gr: "GameResult") -> dict:
        """Convierte GameResult al shape legacy esperado por consumidores antiguos."""
        loser = gr.away if gr.winner == gr.home else gr.home
        return {
            "fecha": gr.fecha,
            "away": gr.away,
            "home": gr.home,
            "away_score": gr.away_score,
            "home_score": gr.home_score,
            "winner": gr.winner,
            "loser": loser,
            "margin": gr.margin,
            "winning_pitcher": None,
            "losing_pitcher": None,
            "total_runs": gr.total_runs,
            "game_pk": gr.game_pk,
            "venue": gr.venue,
            "home_runs": [
                {
                    "person_id": h.person_id,
                    "full_name": h.full_name,
                    "equipo": h.equipo,
                    "home_runs": h.home_runs,
                }
                for h in gr.home_runs
            ],
            "strikeouts": [
                {
                    "person_id": k.person_id,
                    "pitcher": k.pitcher,
                    "equipo": k.equipo,
                    "strike_outs": k.strike_outs,
                }
                for k in gr.strikeouts
            ],
        }

    def _partial_to_legacy_dict(self, partial: dict) -> dict:
        """Render de una entrada parcial al shape legacy."""
        raw = partial.get("raw", {}) or {}
        away_score = raw.get("away_score", 0) or 0
        home_score = raw.get("home_score", 0) or 0
        try:
            away_score = int(away_score)
        except (TypeError, ValueError):
            away_score = 0
        try:
            home_score = int(home_score)
        except (TypeError, ValueError):
            home_score = 0
        return {
            "fecha": partial.get("fecha", ""),
            "away": raw.get("away_name", "") or raw.get("away", ""),
            "home": raw.get("home_name", "") or raw.get("home", ""),
            "away_score": away_score,
            "home_score": home_score,
            "winner": "",
            "loser": "",
            "margin": 0,
            "winning_pitcher": None,
            "losing_pitcher": None,
            "total_runs": away_score + home_score,
            "game_pk": partial.get("game_pk", 0),
            "partial": True,
        }

    def _save_results_json(
        self,
        results: List["GameResult"],
        filename: str = RESULTS_JSON_PATH,
    ) -> None:
        """
        Persiste resultados de forma idempotente y atómica.

        Escribe primero a `<filename>.tmp` y hace os.replace al destino final
        para evitar corrupción si el proceso se interrumpe a mitad de write.
        """
        target_dir = os.path.dirname(filename) or "."
        os.makedirs(target_dir, exist_ok=True)
        full_payload = [self._game_result_to_dict(gr) for gr in results]
        # Adjuntar partials: garantizan que la próxima corrida los reintente.
        full_payload.extend(self._partials.values())
        tmp = filename + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(full_payload, f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp, filename)

    def _load_results_json(
        self,
        filename: str = RESULTS_JSON_PATH,
    ) -> List["GameResult"]:
        """
        Carga resultados previos (best-effort).

        - Entradas con `partial=True` se rehidratan a self._partials para que
          collect_last_n_days las reintente en esta corrida.
        - Entradas válidas se devuelven como List[GameResult].
        - Errores de parseo se silencian: tratamos el archivo como vacío.
        """
        if not os.path.exists(filename):
            return []
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:  # pragma: no cover - tolerar JSON corrupto
            print(f"[_load_results_json] WARN: {e}")
            return []
        if not isinstance(data, list):
            return []
        out: List["GameResult"] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            if entry.get("partial"):
                gp = entry.get("game_pk")
                if isinstance(gp, int) and gp > 0:
                    self._partials[gp] = entry
                continue
            gr = self._dict_to_game_result(entry)
            if gr is not None:
                out.append(gr)
        return out

    # ------------------------------------------------------------------
    # Aliases canónicos (Task 2.2) — nombres requeridos por el spec
    # ------------------------------------------------------------------
    def _persist_results(self, all_results: List[dict]) -> None:
        """
        Persiste merged results al RESULTS_JSON_PATH de forma atómica.

        Acepta una lista de dicts ya serializados (formato de
        `_game_result_to_dict`) y los escribe junto con los partials
        registrados en self._partials. Útil para tests y para callers
        externos que ya tienen el payload en formato dict.
        """
        os.makedirs(os.path.dirname(RESULTS_JSON_PATH) or ".", exist_ok=True)
        full_payload: List[dict] = list(all_results or [])
        # Adjuntar partials para garantizar reintento en la próxima corrida.
        full_payload.extend(self._partials.values())
        tmp = RESULTS_JSON_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(full_payload, f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp, RESULTS_JSON_PATH)

    def _load_existing_results(self) -> List[dict]:
        """
        Carga el contenido bruto del archivo idempotente como lista de dicts.

        A diferencia de `_load_results_json` (que rehidrata a GameResult y
        separa partials), este helper devuelve el JSON tal cual está en
        disco. Útil para tests de idempotencia y para inspección.
        """
        if not os.path.exists(RESULTS_JSON_PATH):
            return []
        try:
            with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _scrape_espn_fallback_per_day(self, fecha_str: str) -> List[dict]:
        """
        Reservado: respaldo por-día desde ESPN (no usado por el flujo actual).

        El flujo principal usa `_scrape_espn_fallback()` (sin args, body
        Playwright/ESPN preservado) cuando la MLB API no produce resultados.
        Para fallos por-game_pk, `collect_last_n_days` registra placeholders
        partial vía `_mark_partial` usando el dict de schedule (que ya trae
        marcador). Esta función queda como hook para futuras extensiones.
        """
        if not isinstance(fecha_str, str) or len(fecha_str) < 8:
            return []
        return []

    # ------------------------------------------------------------------
    # MLB Stats API oficial — boxscore por game_pk
    # ------------------------------------------------------------------
    def fetch_boxscore(self, game_pk: int) -> Optional["GameResult"]:
        """
        Obtiene un GameResult completo desde la MLB Stats API oficial.

        Preconditions:
          - game_pk es un entero positivo válido para la MLB Stats API.

        Postconditions:
          - Retorna un GameResult con total_runs == away_score + home_score
            y winner igual al equipo con mayor marcador.
          - home_runs[] contiene HR por personId con full_name y equipo.
          - strikeouts[] contiene K por pitcher con personId y equipo.
          - Retorna None (sin lanzar) si:
              * El módulo de modelos no está disponible.
              * statsapi no está disponible.
              * El game_pk es inválido o el partido no está en estado terminal.
              * El boxscore o el schedule no están disponibles.
              * Cualquier error de red/parsing ocurre.
        """
        # Si los modelos no están disponibles, no podemos construir el resultado.
        if GameResult is None or HomeRunRecord is None or StrikeoutRecord is None:
            return None
        if statsapi is None:
            return None
        if not isinstance(game_pk, int) or isinstance(game_pk, bool) or game_pk <= 0:
            return None

        try:
            # 1) Schedule: marcador, estado y venue (más fiable que teamStats).
            sched = statsapi.schedule(game_id=game_pk)
            if not sched:
                return None
            entry = sched[0] if isinstance(sched, list) else sched
            if not isinstance(entry, dict):
                return None

            status = entry.get("status", "")
            if status not in _FINAL_STATUSES:
                return None

            try:
                away_score = int(entry.get("away_score", 0) or 0)
                home_score = int(entry.get("home_score", 0) or 0)
            except (TypeError, ValueError):
                return None

            # MLB de temporada regular no admite empates (regla de extra innings).
            # Si llegan iguales, evitamos construir un GameResult inválido.
            if away_score == home_score:
                return None

            venue = entry.get("venue_name", "") or ""
            fecha = entry.get("game_date", "") or ""

            # 2) Boxscore: jugadores con HR y K por personId.
            box = statsapi.boxscore_data(game_pk)
            if not box:
                return None
            teams = box.get("teams", {}) if isinstance(box, dict) else {}
            if not teams:
                return None

            def _team_name(side_data: dict) -> str:
                team = side_data.get("team", {}) if isinstance(side_data, dict) else {}
                if not isinstance(team, dict):
                    return ""
                # Probar varios alias del nombre.
                for key in ("name", "teamName", "abbreviation"):
                    val = team.get(key)
                    if val:
                        return str(val)
                return ""

            home_data = teams.get("home", {}) if isinstance(teams, dict) else {}
            away_data = teams.get("away", {}) if isinstance(teams, dict) else {}
            if not isinstance(home_data, dict):
                home_data = {}
            if not isinstance(away_data, dict):
                away_data = {}

            home_team = _team_name(home_data)
            away_team = _team_name(away_data)
            # Si la API devolvió teams sin nombre legible, abortamos.
            if not home_team or not away_team:
                return None

            home_runs: List[HomeRunRecord] = []
            strikeouts: List[StrikeoutRecord] = []

            def _parse_side(side_data: dict, equipo: str) -> None:
                players = side_data.get("players", {}) if isinstance(side_data, dict) else {}
                if not isinstance(players, dict):
                    return
                for _key, player in players.items():
                    if not isinstance(player, dict):
                        continue
                    person = player.get("person", {})
                    if not isinstance(person, dict):
                        person = {}
                    try:
                        person_id = int(person.get("id", 0) or 0)
                    except (TypeError, ValueError):
                        person_id = 0
                    if person_id <= 0:
                        continue
                    full_name = str(person.get("fullName", "") or "")

                    stats = player.get("stats", {})
                    if not isinstance(stats, dict):
                        stats = {}

                    # HR del bateador.
                    batting = stats.get("batting", {})
                    if isinstance(batting, dict):
                        try:
                            hr_count = int(batting.get("homeRuns", 0) or 0)
                        except (TypeError, ValueError):
                            hr_count = 0
                        if hr_count >= 1:
                            home_runs.append(HomeRunRecord(
                                person_id=person_id,
                                full_name=full_name,
                                equipo=equipo,
                                home_runs=hr_count,
                            ))

                    # K del pitcher (solo si realmente lanzó).
                    pitching = stats.get("pitching", {})
                    if isinstance(pitching, dict):
                        try:
                            k_count = int(pitching.get("strikeOuts", 0) or 0)
                        except (TypeError, ValueError):
                            k_count = 0
                        ip_raw = pitching.get("inningsPitched", "0")
                        try:
                            ip_val = float(ip_raw) if ip_raw not in (None, "") else 0.0
                        except (TypeError, ValueError):
                            ip_val = 0.0
                        if k_count >= 1 and ip_val > 0:
                            strikeouts.append(StrikeoutRecord(
                                person_id=person_id,
                                pitcher=full_name,
                                equipo=equipo,
                                strike_outs=k_count,
                            ))

            _parse_side(home_data, home_team)
            _parse_side(away_data, away_team)

            winner = home_team if home_score > away_score else away_team
            margin = abs(away_score - home_score)
            total_runs = away_score + home_score

            return GameResult(
                game_pk=int(game_pk),
                fecha=fecha,
                away=away_team,
                home=home_team,
                away_score=away_score,
                home_score=home_score,
                winner=winner,
                margin=margin,
                total_runs=total_runs,
                venue=venue,
                home_runs=home_runs,
                strikeouts=strikeouts,
                status=status,
            )
        except Exception as exc:  # pragma: no cover - parseo defensivo
            print(f"[fetch_boxscore] WARN game_pk={game_pk}: {exc}")
            return None

if __name__ == "__main__":
    scraper = MLBResultadosScraper(dias=10)
    resultados = scraper.scrape_ultimos_dias()
    scraper.guardar_json()
    
    reporte = scraper.generar_reporte()
    print("\n📊 REPORTE DE LOS ÚLTIMOS 10 DÍAS:")
    print(f"   Total juegos: {reporte['total_juegos']}")
    print(f"   Victorias local: {reporte['home_wins']} ({reporte['home_win_pct']}%)")
    print(f"   Victorias visitante: {reporte['away_wins']}")
    print(f"   Margen promedio: {reporte['avg_margin']} carreras")
    print(f"   Total carreras promedio: {reporte['avg_total_runs']}")
