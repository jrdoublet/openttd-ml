#!/usr/bin/env python3
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "results" / "c121_pressure_5x2_20260929_engine"
SEEDS = [42, 100, 999, 1234, 5678]
PAT = re.compile(
    r"C121_PRESSURE year=(\d+) observed=(\d+) open=(\d+) competitor=(\d+) "
    r"locked=(\d+) served=(\d+)"
)


for seed in SEEDS:
    path = LOG_DIR / f"c121_pressure_probe_seed{seed}_r0.log"
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        m = PAT.search(line)
        if not m:
            continue
        year, observed, open_, competitor, locked, served = map(int, m.groups())
        if observed <= 0:
            continue
        pressure = (competitor + locked) / observed
        rows.append((year, observed, open_, competitor, locked, served, pressure))

    print(f"\nSEED {seed}")
    for year in sorted({r[0] for r in rows}):
        ys = [r for r in rows if r[0] == year]
        mean_p = sum(r[6] for r in ys) / len(ys)
        max_p = max(r[6] for r in ys)
        mean_comp = sum(r[3] / r[1] for r in ys) / len(ys)
        first50 = next((r[5] for r in ys if r[6] >= 0.5), None)
        first_locked = next((r[5] for r in ys if r[4] > 0), None)
        last = ys[-1]
        print(
            f"year={year} n={len(ys)} mean_pressure={mean_p:.3f} "
            f"max_pressure={max_p:.3f} mean_comp={mean_comp:.3f} "
            f"first50_served={first50} first_locked_served={first_locked} "
            f"last=o{last[1]} open{last[2]} comp{last[3]} locked{last[4]} served{last[5]}"
        )
