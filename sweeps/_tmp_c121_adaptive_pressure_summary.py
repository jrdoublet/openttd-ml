#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AN = ROOT / "results" / "c121_projectreal_adaptive_pressure_5x6_20260929_analysis.json"
LOG_DIR = ROOT / "results" / "c121_projectreal_adaptive_pressure_5x6_20260929_engine"
RX = re.compile(r"C121_STRATEGY source_year=(\d+) pressured=(\d+) contestable_permille=(-?\d+) regime=(\w+)")

d = json.loads(AN.read_text())
for p in sorted(d["policy_comparison"]["per_pair"], key=lambda x: x["seed"]):
    seed = p["seed"]
    m = p["metrics"]
    a = p["air_structural_metrics"]
    print(
        "SEED", seed,
        "profit_delta", m["profit_year"]["policy_delta"],
        "gap", m["profit_year"]["duel_gap_evolution"],
        "value_delta", m["company_value"]["policy_delta"],
        "aaa20", a["airport_towns_aaahogex_2_opex_0"]["policy_delta"],
        "opex_slots", a["airport_slots_opex"]["policy_delta"],
        "opex_towns", a["airport_towns_opex_present"]["policy_delta"],
    )
    path = LOG_DIR / f"c121_projectreal_adaptive_pressure_seed{seed}_r0.log"
    states = []
    for line in path.read_text(errors="replace").splitlines():
        mm = RX.search(line)
        if mm:
            states.append((int(mm.group(1)), int(mm.group(2)), int(mm.group(3)), mm.group(4)))
    print("STRATEGY", *states)
