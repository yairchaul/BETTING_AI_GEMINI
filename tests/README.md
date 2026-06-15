# Tests — backtesting-real-mlb

Suite ejecutable que cubre la spec
[`.kiro/specs/backtesting-real-mlb/`](../.kiro/specs/backtesting-real-mlb/).

Toda la suite corre **offline**. No hay llamadas de red ni dependencia de
servicios externos: los tests del scraper inyectan un fake `statsapi`, los
del auditor escriben en SQLite temporales (`tmp_path` de pytest) y los
del selector usan rutas a JSON dentro del directorio del test.

## Estructura

```
tests/
├── __init__.py
├── conftest.py              # fixtures comunes (temp_db, sample_game_result, ...)
├── test_models.py           # invariantes de los dataclasses (GameResult, Metrics, ...)
├── test_auditor.py          # classify_pick, match_game, evaluate, audit_pending
├── test_effectiveness.py    # compute_*, classify, is_equipo_trampa, persist
├── test_selector.py         # adjusted_confidence, select_best_pick, stake
├── test_properties.py       # property-based tests (hypothesis) — Properties 2,4,5,6,7,8,10
└── README.md                # este archivo
```

Las **Correctness Properties** del diseño cubiertas en `test_properties.py`:

| # | Propiedad                                  | Validates Requirements |
|---|--------------------------------------------|-----------------------|
| 2 | Conservación del marcador                  | 1.2                   |
| 4 | Cuota nunca nula                           | 2.2                   |
| 5 | Estado terminal monótono                   | 2.3                   |
| 6 | Cota de win rate                           | 3.1                   |
| 7 | Clasificación total y excluyente           | 3.2                   |
| 8 | No sobrescritura heurística                | 4.1                   |
| 10 | Penalización de estadio                   | 4.3                   |

Properties 1, 3 y 9 (idempotencia del scraper, HR por personId end-to-end y
exclusión EVITAR/TRAMPA en flujo completo) están cubiertas por los tests
unitarios y de integración del auditor y del selector; se difieren como
property tests adicionales si se requiere mayor cobertura.

## Comandos de ejecución

> Si el entorno no tiene `pytest`/`hypothesis`, instalar con
> `pip install pytest hypothesis` (ya están en `requirements-dev.txt`).

Toda la suite (sin watch, sin red):

```cmd
pytest tests/ -v
```

Solo unit tests (excluyendo property tests):

```cmd
pytest tests/ -v -m "not property"
```

Solo property tests:

```cmd
pytest tests/ -v -m property
```

Un módulo específico:

```cmd
pytest tests/test_auditor.py -v
```

Una clase / test específico:

```cmd
pytest tests/test_auditor.py::TestEvaluate::test_hr_winner_by_personid -v
```

Output más conciso:

```cmd
pytest tests/ --tb=short -q
```

## Fixtures destacadas (`conftest.py`)

* `temp_db` — `DatabaseManager` apuntando a un SQLite efímero (`tmp_path`).
* `sample_game_result` — Yankees @ Red Sox 8-3 con HR de Aaron Judge y 10 K
  de Gerrit Cole. Fecha 2025-06-01.
* `sample_game_result_dodgers` — Dodgers @ Giants 5-3 sin HR (caso negativo).
* `results_list` — lista lista para pasar a `MLBBacktestAuditor.match_game`.
* `make_pick(pick, evento, fecha, cuota, estado, pick_id)` — factory que
  crea un `BacktestPick` con valores default razonables.

## Network isolation

* Ningún test importa ni depende de `requests`, `httpx`, `playwright` o
  `statsapi` directamente sobre red.
* El scraper se prueba inyectando un fake `statsapi` con `monkeypatch`
  cuando aplica (en este momento la suite se enfoca en auditor /
  effectiveness / selector / properties).
* Las DB se crean en `tmp_path`, los JSON de resultados se escriben en
  `tmp_path`, y los factores de estadio también.

## Markers registrados

```ini
[pytest]
markers =
    property: hypothesis property-based tests (Correctness Properties del diseño)
    integration: tests de integración end-to-end
    slow: tests que tardan más de 1s
```
