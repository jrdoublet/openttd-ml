"""AC-05 : extraction hors ligne des coûts AIR_LIGHT hub_hub existants.

Ne lance aucune partie ; les invocations de phase ne sont pas des paires.
Le compteur CATALOG_COST ne s'aligne pas sur les tranches AIR_LIGHT :
per_pair_opcode_cost reste null même quand des records existent.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

DATE = re.compile(r"OPEX (\d{4})-\d+-\d+ (AIR_LIGHT v=1|CATALOG_COST )\s*(.*)")
FIELD = re.compile(r"([a-zA-Z_][\w]*)=([^\s]+)")


def analyse(path):
    rows = defaultdict(lambda: {
        "exits": 0, "hub_hub_phase_calls": 0, "hub_hub_phase_ops": 0,
        "hub_hub_phase_ticks": 0, "hub_hub_phase_days": 0,
        "hub_hub_yields": 0, "catalog_cost_records": 0,
        "catalog_hub_hub_pairs": 0, "peak_hub_hub_ops_per_exit": 0,
    })
    with Path(path).open(encoding="utf-8", errors="replace") as source:
        for line in source:
            match = DATE.search(line)
            if match is None:
                continue
            year, label = int(match.group(1)), match.group(2)
            fields = dict(FIELD.findall(match.group(3)))
            row = rows[year]
            if label.startswith("AIR_LIGHT"):
                if fields.get("edge") != "exit":
                    continue
                row["exits"] += 1
                row["hub_hub_phase_calls"] += int(fields.get("hub_hub_calls", 0))
                cost = int(fields.get("hub_hub_ops", 0))
                row["hub_hub_phase_ops"] += cost
                row["hub_hub_phase_ticks"] += int(fields.get("hub_hub_ticks", 0))
                row["hub_hub_phase_days"] += int(fields.get("hub_hub_days", 0))
                row["hub_hub_yields"] += fields.get("reason") == "hub_hub_yield"
                row["peak_hub_hub_ops_per_exit"] = max(
                    row["peak_hub_hub_ops_per_exit"], cost
                )
            else:
                row["catalog_cost_records"] += 1
                row["catalog_hub_hub_pairs"] += int(fields.get("air_hub_hub_pairs", 0))
    years = {str(year): value for year, value in sorted(rows.items())}
    keys = (
        "exits", "hub_hub_phase_calls", "hub_hub_phase_ops",
        "hub_hub_phase_ticks", "hub_hub_phase_days", "hub_hub_yields",
        "catalog_cost_records", "catalog_hub_hub_pairs",
    )
    return {
        "source": str(path), "scope": "existing single-arm diagnostic, no new run",
        "per_pair_opcode_cost": None, "per_pair_status": "not_identifiable",
        "notes": [
            "hub_hub_phase_calls are phase invocations, not examined pairs",
            "CATALOG_COST per cycle is not paired with AIR_LIGHT per invocation",
        ],
        "years": years,
        "totals": {k: sum(row[k] for row in years.values()) for k in keys},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = analyse(args.log)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps(summary["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
