# -*- coding: utf-8 -*-
"""
Modelos de datos compartidos para backtesting de MLB.

Este módulo define las estructuras de datos principales para el sistema
de backtesting de MLB según las especificaciones del diseño:
`.kiro/specs/backtesting-real-mlb/design.md` (sección Data Models).

Mantiene el módulo auto-contenido: solo importa de la stdlib (`dataclasses`,
`enum`, `typing`) para evitar ciclos en `motors/__init__.py` y permitir su
uso directo vía `from motors.mlb_backtest_models import ...`.

Requisitos cubiertos: 1.2 (conservación del marcador), 2.1 (HR por personId),
3.1 (cota de win_rate).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

__all__ = [
    "HomeRunRecord",
    "StrikeoutRecord",
    "GameResult",
    "BacktestPick",
    "Metrics",
    "Classification",
    "PickType",
    "validate_game_result_consistency",
    "calculate_win_rate_roi",
]


@dataclass
class HomeRunRecord:
    """Registro de Home Run individual para un jugador."""
    person_id: int        # personId oficial MLB
    full_name: str
    equipo: str           # normalizado
    home_runs: int        # >= 1 cuando conectó


@dataclass
class StrikeoutRecord:
    """Registro de Strikeouts para un pitcher."""
    person_id: int
    pitcher: str
    equipo: str
    strike_outs: int


@dataclass
class GameResult:
    """Resultado real de un partido de MLB."""
    game_pk: int          # clave única e idempotente
    fecha: str            # "YYYY-MM-DD"
    away: str             # normalizado
    home: str             # normalizado
    away_score: int
    home_score: int
    winner: str
    margin: int           # |away_score - home_score|
    total_runs: int
    venue: str
    home_runs: List[HomeRunRecord] = field(default_factory=list)
    strikeouts: List[StrikeoutRecord] = field(default_factory=list)
    status: str = "Final"  # "Final"

    def __post_init__(self):
        """Validar las reglas de integridad del GameResult."""
        # Validar que game_pk sea un entero positivo (clave única e idempotente)
        if not isinstance(self.game_pk, int) or isinstance(self.game_pk, bool):
            raise ValueError(
                f"game_pk debe ser un entero, no {type(self.game_pk).__name__}"
            )
        if self.game_pk <= 0:
            raise ValueError(
                f"game_pk debe ser un entero positivo, no {self.game_pk}"
            )

        # Validar que los marcadores sean enteros no negativos
        if not isinstance(self.away_score, int) or isinstance(self.away_score, bool):
            raise ValueError(
                f"away_score debe ser entero, no {type(self.away_score).__name__}"
            )
        if not isinstance(self.home_score, int) or isinstance(self.home_score, bool):
            raise ValueError(
                f"home_score debe ser entero, no {type(self.home_score).__name__}"
            )
        if self.away_score < 0:
            raise ValueError(f"away_score debe ser >= 0, no {self.away_score}")
        if self.home_score < 0:
            raise ValueError(f"home_score debe ser >= 0, no {self.home_score}")

        # Validar que total_runs sea igual a away_score + home_score
        if self.total_runs != self.away_score + self.home_score:
            raise ValueError(
                f"total_runs ({self.total_runs}) debe ser igual a "
                f"away_score ({self.away_score}) + home_score ({self.home_score})"
            )

        # Validar que winner sea away o home
        if self.winner not in [self.away, self.home]:
            raise ValueError(
                f"winner ({self.winner}) debe ser 'away' ({self.away}) o 'home' ({self.home})"
            )

        # Validar que winner tenga el marcador más alto
        if self.winner == self.away and self.away_score <= self.home_score:
            raise ValueError(
                f"winner={self.away} pero away_score ({self.away_score}) "
                f"no es mayor que home_score ({self.home_score})"
            )
        if self.winner == self.home and self.home_score <= self.away_score:
            raise ValueError(
                f"winner={self.home} pero home_score ({self.home_score}) "
                f"no es mayor que away_score ({self.away_score})"
            )

        # Validar que margin sea |away_score - home_score|
        calculated_margin = abs(self.away_score - self.home_score)
        if self.margin != calculated_margin:
            raise ValueError(
                f"margin ({self.margin}) debe ser |away_score ({self.away_score}) - "
                f"home_score ({self.home_score})| = {calculated_margin}"
            )

        # Validar que todos los HR tengan home_runs >= 1
        for hr in self.home_runs:
            if hr.home_runs < 1:
                raise ValueError(
                    f"HomeRunRecord para {hr.full_name} (person_id={hr.person_id}) "
                    f"debe tener home_runs >= 1, no {hr.home_runs}"
                )


@dataclass
class BacktestPick:
    """Predicción registrada en la tabla backtesting."""
    id: int               # ID único, vincula con tabla backtesting (integridad-datos)
    fecha: str
    deporte: str          # "MLB"
    evento: str           # "Away vs Home"
    pick: str             # texto del pick
    cuota: Optional[float] = None
    estado: str = "PENDIENTE"  # PENDIENTE | GANADA | PERDIDA
    
    def __post_init__(self):
        """Validar las reglas de integridad del BacktestPick."""
        # Validar que el estado sea uno de los permitidos
        valid_states = ["PENDIENTE", "GANADA", "PERDIDA"]
        if self.estado not in valid_states:
            raise ValueError(f"estado debe ser uno de {valid_states}, no '{self.estado}'")
        
        # Validar que deporte sea "MLB" (aunque podría extenderse en el futuro)
        if self.deporte != "MLB":
            raise ValueError(f"deporte debe ser 'MLB', no '{self.deporte}'")


@dataclass
class Metrics:
    """Métricas de efectividad para un tipo de pick o equipo."""
    total: int
    hits: int
    win_rate: float       # hits/total * 100
    profit: float         # unidades
    roi: float            # profit/total * 100
    last_10: List[str]    # ['W','L',...] más reciente primero
    
    def __post_init__(self):
        """Validar las reglas de integridad de las métricas."""
        # Validar que hits <= total
        if self.hits > self.total:
            raise ValueError(f"hits ({self.hits}) no puede ser mayor que total ({self.total})")
        
        # Validar que win_rate esté entre 0 y 100
        if not (0 <= self.win_rate <= 100):
            raise ValueError(f"win_rate debe estar entre 0 y 100, no {self.win_rate}")
        
        # Validar que last_10 tenga como máximo 10 elementos y solo contenga 'W' o 'L'
        if len(self.last_10) > 10:
            raise ValueError(f"last_10 debe tener como máximo 10 elementos, no {len(self.last_10)}")
        for result in self.last_10:
            if result not in ['W', 'L']:
                raise ValueError(f"last_10 solo puede contener 'W' o 'L', no '{result}'")


class Classification(Enum):
    """Clasificación de efectividad según backtesting."""
    ELITE = "ELITE"
    CONFIANZA = "CONFIANZA"
    RIESGO = "RIESGO"
    EVITAR = "EVITAR"


class PickType(Enum):
    """Tipos de picks disponibles en MLB."""
    HOME_RUN = "HOME_RUN"
    MONEYLINE = "MONEYLINE"
    OVER_UNDER = "OVER_UNDER"
    STRIKEOUTS = "STRIKEOUTS"
    HANDICAP = "HANDICAP"


# Funciones de utilidad para validación de modelos
def validate_game_result_consistency(results: List[GameResult]) -> bool:
    """
    Validar que no haya game_pk duplicados en una lista de GameResult.
    
    Args:
        results: Lista de GameResult a validar
        
    Returns:
        True si no hay duplicados, False en caso contrario
    """
    game_pks = set()
    for result in results:
        if result.game_pk in game_pks:
            return False
        game_pks.add(result.game_pk)
    return True


def calculate_win_rate_roi(hits: int, total: int, profit: float) -> Tuple[float, float]:
    """
    Calcular win_rate y ROI de forma consistente.
    
    Args:
        hits: Número de aciertos
        total: Número total de picks
        profit: Ganancia/pérdida total en unidades
        
    Returns:
        Tuple[float, float]: (win_rate, roi)
    """
    if total == 0:
        return 0.0, 0.0
    win_rate = (hits / total) * 100
    roi = (profit / total) * 100
    return win_rate, roi


if __name__ == "__main__":
    # Ejemplos de uso y pruebas básicas
    print("=== Modelos de datos para backtesting de MLB ===")
    
    # Crear un ejemplo de HomeRunRecord
    hr_record = HomeRunRecord(
        person_id=12345,
        full_name="Mike Trout",
        equipo="Los Angeles Angels",
        home_runs=2
    )
    print(f"HomeRunRecord: {hr_record}")
    
    # Crear un ejemplo de StrikeoutRecord
    k_record = StrikeoutRecord(
        person_id=67890,
        pitcher="Shohei Ohtani",
        equipo="Los Angeles Dodgers",
        strike_outs=8
    )
    print(f"StrikeoutRecord: {k_record}")
    
    # Crear un ejemplo de GameResult válido
    try:
        game_result = GameResult(
            game_pk=2024001234,
            fecha="2024-06-01",
            away="Los Angeles Dodgers",
            home="San Francisco Giants",
            away_score=5,
            home_score=3,
            winner="Los Angeles Dodgers",
            margin=2,
            total_runs=8,
            venue="Oracle Park",
            home_runs=[hr_record],
            strikeouts=[k_record]
        )
        print(f"GameResult válido creado: {game_result.game_pk}")
    except ValueError as e:
        print(f"Error en GameResult: {e}")
    
    # Crear un ejemplo de BacktestPick
    pick = BacktestPick(
        id=1001,
        fecha="2024-06-01",
        deporte="MLB",
        evento="Los Angeles Dodgers @ San Francisco Giants",
        pick="Los Angeles Dodgers ML",
        cuota=1.90,
        estado="PENDIENTE"
    )
    print(f"BacktestPick: ID={pick.id}, pick={pick.pick}")
    
    # Crear un ejemplo de Metrics
    metrics = Metrics(
        total=10,
        hits=6,
        win_rate=60.0,
        profit=4.5,
        roi=45.0,
        last_10=['W', 'L', 'W', 'W', 'L', 'W', 'W', 'L', 'W', 'W']
    )
    print(f"Metrics: win_rate={metrics.win_rate}%, roi={metrics.roi}%")
    
    # Mostrar enums
    print(f"Classification enum: {list(Classification)}")
    print(f"PickType enum: {list(PickType)}")