# Test simple del motor MLB sin caracteres Unicode

from motors.motor_mlb_completo import motor_mlb

print("Testing MLB Motor...")
pitchers = motor_mlb.obtener_analisis_lanzadores_hoy()
print(f"Pitchers obtained: {len(pitchers)}")

if pitchers:
    for team, info in list(pitchers.items())[:5]:
        name = info.get("lanzador", "N/A")
        k9 = info.get("k9", 0)
        era = info.get("era", 0)
        print(f"{team}: {name} | K/9: {k9} | ERA: {era}")

print("Test completed successfully")