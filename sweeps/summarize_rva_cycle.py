#!/usr/bin/env python3
"""Réanalyse descriptive de journaux existants, séparément par partie."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

from analyze_rva_cycle import analyze


def summarize(paths):
    sources, rows = [], []
    for path in paths:
        data = path.read_bytes()
        result = analyze(data.decode("utf-8", errors="replace").splitlines())
        sources.append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                        "samples": result["samples"], "cycles": len(result["cycles"])})
        for cycle in result["cycles"]:
            residual = cycle["residuals"]
            row = {"source": path.name, **cycle}
            row["ratio_midpoint"] = (statistics.mean(cycle["cycle_days"]) / residual["model_cycle_days"]
                                     if residual else None)
            rows.append(row)
    ratios = [r["ratio_midpoint"] for r in rows if r["ratio_midpoint"] is not None]
    covered = [r for r in rows if r["residuals"]]
    dwell = [r[k] for r in covered for k in ("dwell_a_days", "dwell_b_days")]
    median = lambda xs: statistics.median(xs) if xs else None
    summary = {"cycles": len(rows), "residual_covered_cycles": len(covered),
        "ratio_median": median(ratios),
        "ratio_quartiles_inclusive": statistics.quantiles(ratios, n=4, method="inclusive") if len(ratios) >= 2 else None,
        "dwell_endpoint_median_midpoint_days": median([statistics.mean(d) for d in dwell]),
        "dwell_endpoint_median_bounds_days": [median([d[i] for d in dwell]) for i in (0, 1)],
        "model_dwell_endpoint_median_days": median([r["residuals"]["model_dwell_per_leg_days"] for r in covered]),
        "cycle_median_midpoint_days": median([statistics.mean(r["cycle_days"]) for r in covered]),
        "model_cycle_median_days": median([r["residuals"]["model_cycle_days"] for r in covered])}
    return {"schema": 2, "coverage": "descriptive_existing_logs_not_economic_qualification",
        "method": "date intervals; final sample day included; midpoint summaries; correlated cycles, not independent seeds",
        "sources": sources, "summary": summary, "cycles": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(summarize(args.logs), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
