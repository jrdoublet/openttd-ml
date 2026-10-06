#!/usr/bin/env python3
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "results" / "c121_projectreal_5x6_clean_20260929_r2_analysis.json"
LOG_DIR = ROOT / "results" / "c121_projectreal_5x6_clean_20260929_r2_engine"

REAL_RE = re.compile(
    r"C121_REALIZATION phase=(\S+) year=(\d+) arm=(\w+) lines=(\d+) factor=([0-9.]+)"
)
BUILD_RE = re.compile(r"C121_BUILD .*?arm=(\w+).*?engine=(\d+)")


def realization_rows(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        m = REAL_RE.search(line)
        if m:
            rows.append(
                {
                    "phase": m.group(1),
                    "year": int(m.group(2)),
                    "arm": m.group(3),
                    "lines": int(m.group(4)),
                    "factor": float(m.group(5)),
                }
            )
    return rows


def build_counts(path):
    counts = Counter()
    if not path.exists():
        return counts
    for line in path.read_text(errors="replace").splitlines():
        m = BUILD_RE.search(line)
        if m:
            counts[m.group(1)] += 1
    return counts


def main():
    data = json.loads(ANALYSIS.read_text())
    pairs = sorted(data["policy_comparison"]["per_pair"], key=lambda p: p["seed"])
    for p in pairs:
        seed = p["seed"]
        print(f"\nSEED {seed}")
        print("year gap_delta profit_delta ref_slots_o/a ref_towns_o/a ref_aaa2_0")
        for row in p["annual_trajectory"]:
            a = row["air_structural_metrics"]
            gap_delta = row["variant_duel_gap"] - row["reference_duel_gap"]
            print(
                row["year"],
                gap_delta,
                row["policy_delta"],
                f"{a['airport_slots_opex']['reference']}/{a['airport_slots_aaahogex']['reference']}",
                f"{a['airport_towns_opex_present']['reference']}/{a['airport_towns_aaahogex_present']['reference']}",
                a["airport_towns_aaahogex_2_opex_0"]["reference"],
            )
        m = p["metrics"]
        print(
            "FINAL",
            "gap=", m["profit_year"]["duel_gap_evolution"],
            "profit=", m["profit_year"]["policy_delta"],
            "value=", m["company_value"]["policy_delta"],
        )

        for policy in ("c121_current", "c121_project_realization"):
            path = LOG_DIR / f"{policy}_seed{seed}_r0.log"
            rows = realization_rows(path)
            by_year = defaultdict(dict)
            for r in rows:
                if r["arm"] in ("hubsite", "hubhub"):
                    by_year[r["year"]][r["arm"]] = (r["factor"], r["lines"], r["phase"])
            print("REAL", policy, dict(sorted(by_year.items())))
            print("BUILDS", policy, dict(build_counts(path)))


if __name__ == "__main__":
    main()
