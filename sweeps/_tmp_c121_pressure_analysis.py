#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "results" / "c121_pressure_5x2_20260929_engine"
SEEDS = (42, 100, 999, 1234, 5678)
RX = re.compile(
    r"C121_PRESSURE year=(\d+) observed=(\d+) open=(\d+) "
    r"competitor=(\d+) locked=(\d+) served=(\d+)"
)

for seed in SEEDS:
    path = LOG_DIR / f"c121_pressure_probe_seed{seed}_r0.log"
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        m = RX.search(line)
        if not m:
            continue
        rows.append(tuple(int(x) for x in m.groups()))
    print(f"SEED {seed}")
    for year in (1970, 1971):
        yr = [r for r in rows if r[0] == year]
        open_total = sum(r[2] for r in yr)
        competitor_total = sum(r[3] for r in yr)
        locked_total = sum(r[4] for r in yr)
        pressured = competitor_total + locked_total
        contestable_pm = (competitor_total * 1000) // pressured if pressured else -1
        served_last = yr[-1][5] if yr else -1
        regime = "efficiency" if pressured >= 6 and contestable_pm >= 650 else "race"
        print(year, f"samples={len(yr)}", f"open={open_total}",
              f"competitor={competitor_total}", f"locked={locked_total}",
              f"pressured={pressured}", f"contestable_pm={contestable_pm}",
              f"served_last={served_last}", f"regime_next={regime}")
