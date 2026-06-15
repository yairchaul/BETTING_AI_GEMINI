# -*- coding: utf-8 -*-
import os, sqlite3, tempfile
from datetime import datetime, timedelta
from motors.mlb_effectiveness import EffectivenessCalculator
from motors.mlb_backtest_models import PickType, Classification, Metrics

# 1) DB temporal con picks variados
fd, db_path = tempfile.mkstemp(suffix=".db"); os.close(fd)
conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE backtesting (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, deporte TEXT, evento TEXT, pick TEXT, cuota REAL, estado TEXT, creado_en TEXT)")
fecha = datetime.now().strftime("%Y-%m-%d")
ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
rows = [
    # Yankees ML: 4 ganadas, 1 perdida (80% WR, ROI alto si cuota 1.90)
    (fecha, "MLB", "Yankees vs Red Sox", "Yankees ML", 1.90, "GANADA", fecha),
    (fecha, "MLB", "Yankees vs Red Sox", "Yankees ML", 1.95, "GANADA", fecha),
    (fecha, "MLB", "Yankees vs Red Sox", "Yankees ML", 2.00, "GANADA", fecha),
    (ayer,  "MLB", "Yankees vs Red Sox", "Yankees ML", 1.85, "GANADA", fecha),
    (ayer,  "MLB", "Yankees vs Red Sox", "Yankees ML", 1.80, "PERDIDA", fecha),
    # Over 8.5: 1 ganada, 2 perdidas (no atribuible a equipo)
    (fecha, "MLB", "X vs Y", "Over 8.5 carreras", 1.95, "GANADA", fecha),
    (fecha, "MLB", "X vs Y", "Over 8.5 carreras", 1.90, "PERDIDA", fecha),
    (ayer,  "MLB", "X vs Y", "Over 8.5 carreras", 1.90, "PERDIDA", fecha),
    # HR: 0 GANADA, 3 PERDIDA (WR 0%)
    (fecha, "MLB", "X vs Y", "Aaron Judge HR", 3.50, "PERDIDA", fecha),
    (fecha, "MLB", "X vs Y", "Aaron Judge HR", 3.20, "PERDIDA", fecha),
    (ayer,  "MLB", "X vs Y", "Aaron Judge HR", None,  "PERDIDA", fecha),
    # Pick PENDIENTE no debe contar
    (fecha, "MLB", "X vs Y", "Yankees ML", 1.90, "PENDIENTE", fecha),
]
conn.executemany("INSERT INTO backtesting (fecha, deporte, evento, pick, cuota, estado, creado_en) VALUES (?,?,?,?,?,?,?)", rows)
conn.commit(); conn.close()

class FakeDB:
    def __init__(self, p): self.p = p
    def _connect(self):
        c = sqlite3.connect(self.p, timeout=20)
        c.execute("PRAGMA journal_mode=WAL")
        return c

calc = EffectivenessCalculator(db=FakeDB(db_path))
by_type = calc.compute_by_pick_type(dias=15)
by_team = calc.compute_by_team(dias=15)

# Asserts pick type
assert PickType.MONEYLINE in by_type, f"Missing MONEYLINE: {list(by_type.keys())}"
ml = by_type[PickType.MONEYLINE]
assert ml.total == 5
assert ml.hits == 4
assert ml.win_rate == 80.0, f"win_rate={ml.win_rate}"
print("ML metrics:", ml)

assert PickType.OVER_UNDER in by_type
ou = by_type[PickType.OVER_UNDER]
assert ou.total == 3 and ou.hits == 1
print("OU metrics:", ou)

assert PickType.HOME_RUN in by_type
hr = by_type[PickType.HOME_RUN]
assert hr.total == 3 and hr.hits == 0
print("HR metrics:", hr)

# Asserts team
print("by_team keys:", list(by_team.keys()))
yankees_keys = [k for k in by_team.keys() if "Yank" in k or "yank" in k.lower()]
assert yankees_keys, f"Yankees not found in team metrics: {by_team.keys()}"
yankees_metrics = by_team[yankees_keys[0]]
assert yankees_metrics.total == 5 and yankees_metrics.hits == 4
print("Yankees:", yankees_metrics)

# Classification: WR=80, ROI alto -> ELITE
clas = calc.classify(yankees_metrics)
print("Yankees clas:", clas)
assert clas == Classification.ELITE, f"Expected ELITE, got {clas}"

# Borderline tests (Req 3.4-3.7)
def m(wr, roi, total=20, hits=None):
    if hits is None:
        hits = int(round(wr*total/100))
    profit = roi*total/100
    return Metrics(total=total, hits=hits, win_rate=wr, profit=profit, roi=roi, last_10=[])

assert calc.classify(m(70, 25)) == Classification.ELITE
assert calc.classify(m(60, 5)) == Classification.CONFIANZA
assert calc.classify(m(50, -5)) == Classification.RIESGO
assert calc.classify(m(40, -20)) == Classification.EVITAR  # WR<45 OR ROI<-15
assert calc.classify(m(50, -16)) == Classification.EVITAR  # ROI<-15

# Equipo_Trampa: 10 picks, 3 W, 7 L = 30% WR < 40%
trampa = calc._is_equipo_trampa(["W","L","L","L","W","L","L","W","L","L"])
assert trampa is True
no_trampa = calc._is_equipo_trampa(["W","W","W","W","L","L","L","W","W","L"])
assert no_trampa is False
print("Equipo_Trampa OK")

os.unlink(db_path)
print("OK: Tasks 6.1 + 6.2 pass.")
