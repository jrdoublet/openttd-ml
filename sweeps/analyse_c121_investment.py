"""Compact reader for diag_c121_investment.py reports."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    args = p.parse_args(argv)
    data = json.loads(args.report.read_text(encoding="utf-8"))

    paired = data.get("perturbation", {}).get("paired_final", {}).get("trace", {})
    pairs = paired.get("per_seed", [])
    perturb = {
        "per_seed": [{k: row.get(k) for k in ("seed", "opex_profit_delta", "aaa_profit_delta", "gap_delta")}
                     for row in pairs],
        "opex_profit_mean": statistics.mean(row["opex_profit_delta"] for row in pairs) if pairs else None,
        "opex_profit_max_abs": max((abs(row["opex_profit_delta"]) for row in pairs), default=None),
        "value_delta_pct": paired.get("value_delta_pct"),
    }

    total_builds = []
    reasons = Counter()
    per_seed = []
    growth = full = 0
    for key, trace in sorted(data.get("traces", {}).items()):
        builds = trace.get("builds", [])
        total_builds.extend(builds)
        reasons.update(trace.get("refusal_reasons", {}))
        growth += trace.get("growth_added", 0)
        full += trace.get("full_year_observations", 0)
        per_seed.append({
            "trace": key,
            "builds": len(builds),
            "decision_gt_initial": sum((b.get("decision_n") or 0) > (b.get("initial_n") or 0) for b in builds),
            "target_gt_initial": sum((b.get("target_n") or 0) > (b.get("initial_n") or 0) for b in builds),
            "score_capital_gt_available": sum((b.get("finance_score") or 0) > (b.get("available") or 0) for b in builds),
            "growth_added": trace.get("growth_added", 0),
            "full_year": trace.get("full_year_observations", 0),
            "refusals": trace.get("refusal_reasons", {}),
        })

    summary = {
        "checks": data.get("checks"),
        "probe_perturbation": perturb,
        "per_seed_attribution": per_seed,
        "total": {
            "builds": len(total_builds),
            "decision_gt_initial": sum((b.get("decision_n") or 0) > (b.get("initial_n") or 0) for b in total_builds),
            "target_gt_initial": sum((b.get("target_n") or 0) > (b.get("initial_n") or 0) for b in total_builds),
            "score_capital_gt_available": sum((b.get("finance_score") or 0) > (b.get("available") or 0) for b in total_builds),
            "decision_n": dict(sorted(Counter(b.get("decision_n") for b in total_builds).items(), key=lambda kv: str(kv[0]))),
            "target_n": dict(sorted(Counter(b.get("target_n") for b in total_builds).items(), key=lambda kv: str(kv[0]))),
            "growth_added": growth,
            "full_year_observations": full,
            "refusal_reasons": dict(reasons),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
