#!/usr/bin/env python3
"""Résumé du shadow C121 : stabilité PASS-only -> PASS+MAIL observé."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path


def stat(values):
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
    vals.sort()
    def q(frac):
        pos = (len(vals) - 1) * frac
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        if lo == hi:
            return vals[lo]
        return vals[lo] * (hi - pos) + vals[hi] * (pos - lo)
    return {
        "n": len(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "p25": q(0.25),
        "p75": q(0.75),
    }


def safe_ratio(a, b):
    if a is None or b is None or float(b) == 0.0:
        return None
    return float(a) / float(b)


def analyse(payload):
    builds = []
    by_seed = {}
    for row in payload.get("rows", []):
        seed = row.get("seed")
        seed_builds = [
            b for b in row.get("c121_builds", [])
            if b.get("replay_engine_total", -1) >= 0
        ]
        builds.extend(seed_builds)
        by_seed[str(seed)] = {
            "learning_events": len(seed_builds),
            "complete": sum(1 for b in seed_builds if b.get("replay_engine_complete") == 1),
        }

    fractions = [
        safe_ratio(b.get("replay_engine_known"), b.get("replay_engine_total"))
        for b in builds if b.get("replay_engine_total", 0) > 0
    ]
    complete = [b for b in builds if b.get("replay_engine_complete") == 1]
    fully_evaluated = [
        b for b in builds
        if b.get("replay_engine_evaluated") == b.get("replay_engine_known")
    ]
    eligible = [
        b for b in builds
        if b.get("replay_engine_evaluated", 0) >= 2
        and b.get("replay_pass_engine", -1) >= 0
        and b.get("replay_mail_engine", -1) >= 0
    ]
    changed = [
        b for b in eligible
        if b.get("replay_mail_changed") == 1
        or b.get("replay_pass_engine") != b.get("replay_mail_engine")
    ]
    stable = [b for b in eligible if b not in changed]

    return {
        "source_campaign": payload.get("campaign_id"),
        "coverage": {
            "learning_event_count": len(builds),
            "complete_count": len(complete),
            "complete_fraction": safe_ratio(len(complete), len(builds)),
            "fully_evaluated_count": len(fully_evaluated),
            "fully_evaluated_fraction": safe_ratio(len(fully_evaluated), len(builds)),
            "known_fraction": stat(fractions),
            "total_candidates": stat([b.get("replay_engine_total") for b in builds]),
            "known_candidates": stat([b.get("replay_engine_known") for b in builds]),
            "evaluated_candidates": stat([b.get("replay_engine_evaluated") for b in builds]),
            "by_seed": by_seed,
        },
        "mail_stability": {
            "eligible_count": len(eligible),
            "changed_count": len(changed),
            "stable_count": len(stable),
            "changed_fraction": safe_ratio(len(changed), len(eligible)),
            "pass_best_engine_counts": dict(Counter(str(b.get("replay_pass_engine")) for b in eligible)),
            "mail_best_engine_counts": dict(Counter(str(b.get("replay_mail_engine")) for b in eligible)),
            "fleet_delta_mail_minus_pass": stat([
                b.get("replay_mail_n") - b.get("replay_pass_n") for b in eligible
            ]),
            "revenue_delta_mail_minus_pass": stat([
                b.get("replay_mail_revenue") - b.get("replay_pass_revenue") for b in eligible
            ]),
            "profit_delta_mail_minus_pass": stat([
                b.get("replay_mail_profit") - b.get("replay_pass_profit") for b in eligible
            ]),
            "score_delta_mail_minus_pass": stat([
                b.get("replay_mail_score") - b.get("replay_pass_score") for b in eligible
            ]),
            "score_ratio_mail_over_pass": stat([
                safe_ratio(b.get("replay_mail_score"), b.get("replay_pass_score")) for b in eligible
            ]),
        },
        "opcode_note": {
            "shadow_ticks": stat([b.get("replay_shadow_ticks") for b in builds]),
            "shadow_ops": stat([b.get("replay_shadow_ops") for b in builds]),
            "eval_ticks_learning_events": stat([b.get("eval_ticks") for b in builds]),
            "eval_ops_learning_events": stat([b.get("eval_ops") for b in builds]),
        },
        "limitations": [
            "PASS-only and PASS+MAIL rankings use only engines whose exact capacities were observed in the current game.",
            "replay_engine_complete=1 means all currently buildable in-range candidates happened to be observed; otherwise the ranking has partial coverage.",
            "Events with fewer than two evaluated observed engines are excluded from the changed-fraction denominator.",
            "The shadow runs only when a new engine capacity pair is first learned, so its cost is not paid on every AIR build.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--out")
    args = parser.parse_args()
    source = Path(args.source)
    result = analyse(json.loads(source.read_text(encoding="utf-8")))
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"Sortie: {args.out}")


if __name__ == "__main__":
    main()
