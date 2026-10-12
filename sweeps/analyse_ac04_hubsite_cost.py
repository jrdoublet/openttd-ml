"""AC-04: diagnostic existing AIR_LIGHT phase cost; never infer per-pair rate.

Usage: python -X utf8 sweeps/analyse_ac04_hubsite_cost.py TRACE.log --out summary.json

AIR_LIGHT is per invocation, CATALOG_COST is per completed catalog cycle and
is *not* a guaranteed aligned denominator for sliced AIR_LIGHT. If missing
or incompatible, cost_per_pair is explicitly null rather than fabricated.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re


DATE = re.compile(r"OPEX (\d{4})-\d+-\d+ (AIR_LIGHT v=1|CATALOG_COST )\s*(.*)")
FIELD = re.compile(r"([a-zA-Z_][\w]*)=([^\s]+)")


def analyse(path):
    annual = defaultdict(lambda: {"exits": 0, "phase_calls": 0, "phase_ops": 0,
                                 "phase_ticks": 0, "phase_days": 0,
                                 "total_air_ops": 0, "cat_cost_records": 0,
                                 "cat_hub_site_pairs": 0, "peak_phase_ops_per_exit": 0})
    summary = {"source": str(path), "scope": "single unmodified observed arm",
               "per_pair_opcode_cost": None, "per_pair_status": "not_identifiable",
               "notes": ["AIR_LIGHT counts full hub_site phase (including screening and idle), not actual pairs.",
                         "CATALOG_COST emitted per completed catalog cycle and cannot be naively joined to AIR_LIGHT slices."]}
    for line in path.open(encoding="utf-8", errors="replace"):
        match = DATE.search(line)
        if not match:
            continue
        year, tag, fields = int(match.group(1)), match.group(2), dict(FIELD.findall(match.group(3)))
        row = annual[year]
        if tag.startswith("AIR_LIGHT"):
            if fields.get("edge") != "exit":
                continue
            row["exits"] += 1
            row["total_air_ops"] += int(fields.get("ops", "0"))
            ops = int(fields.get("hub_site_ops", "0"))
            row["phase_ops"] += ops
            row["phase_calls"] += int(fields.get("hub_site_calls", "0"))
            row["phase_ticks"] += int(fields.get("hub_site_ticks", "0"))
            row["phase_days"] += int(fields.get("hub_site_days", "0"))
            row["peak_phase_ops_per_exit"] = max(row["peak_phase_ops_per_exit"], ops)
        elif tag.startswith("CATALOG_COST "):
            row["cat_cost_records"] += 1
            row["cat_hub_site_pairs"] += int(fields.get("air_hub_site_pairs", "0"))
    years = {str(k): v for k, v in sorted(annual.items())}
    summary["years"] = years
    summary["totals"] = {k: sum(v[k] for v in years.values()) for k in
                         ("exits", "phase_calls", "phase_ops", "phase_ticks",
                          "phase_days", "total_air_ops", "cat_cost_records", "cat_hub_site_pairs")}
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("log", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = analyse(args.log)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
