#!/usr/bin/env python3
"""Aggregate logged portfolio attempts and veto reasons, without causal inflation.

These are events in an intrusive, instrumented game. Do not equate reported
discard events, portfolio visits, or summary flags with distinct projects.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


LINE = re.compile(r"\bOPEX\s+(\d{4})-(\d{1,2})-(\d{1,2})\s+(MONTHLY_FUNNEL|PROJECT_DISCARD|FREIGHT_CARGO_FALLBACK|PROJECT_CHOSEN|P2_PASS|P5_BUILD_LINE)\s*(.*)")
PARAM = re.compile(r"([a-zA-Z0-9_]+)=([^\s]+)")


def parse(lines):
    data = defaultdict(lambda: {"funnel": Counter(), "funnel_reason": Counter(),
                                "discards": Counter(), "discard_unique": defaultdict(set),
                                "fallback": Counter(), "builds": Counter(),
                                "chosen": Counter(), "p2": Counter(), "per_month": defaultdict(Counter)})
    for line in lines:
        match = LINE.search(line)
        if not match:
            continue
        year, month, day, kind, raw = match.groups()
        vals = dict(PARAM.findall(raw))
        bucket = data[year]
        counts = bucket["per_month"][f"{int(month):02d}"]
        if kind == "MONTHLY_FUNNEL":
            bucket["funnel"]["events"] += 1
            counts["funnel_events"] += 1
            for metric in ("considered", "accepted", "funded", "attempted", "built"):
                try:
                    value = int(vals[metric])
                except (ValueError, KeyError):
                    continue
                bucket["funnel"][metric] += value
                counts[metric] += value
            for key, value in vals.items():
                if key.startswith("r_"):
                    try:
                        bucket["funnel_reason"][key[2:]] += int(value)
                    except ValueError:
                        pass
        elif kind == "PROJECT_DISCARD":
            reason = vals.get("reason", "unknown")
            mode = vals.get("mode", "unknown")
            bucket["discards"][f"{mode}/{reason}"] += 1
            # Unique per month/OD/reason only; repeated passes can still count
            # as a single observation even for different candidate identities.
            bucket["discard_unique"][f"{mode}/{reason}"].add((month, vals.get("src"), vals.get("dst")))
            counts[f"discard_{mode}_{reason}"] += 1
        elif kind == "FREIGHT_CARGO_FALLBACK":
            bucket["fallback"][f"{vals.get('from','?')}->{vals.get('to','?')}"] += 1
        elif kind == "PROJECT_CHOSEN":
            bucket["chosen"][vals.get("mode", "unknown")] += 1
        elif kind == "P5_BUILD_LINE":
            bucket["builds"][vals.get("mode", "unknown")] += 1
            counts[f"line_event_{vals.get('mode','unknown')}"] += 1
        elif kind == "P2_PASS":
            bucket["p2"]["visits"] += 1
            bucket["p2"]["initially_empty"] += vals.get("in_best") == "0"
    result = {}
    for year, x in sorted(data.items()):
        result[year] = {k: dict(x[k]) for k in ("funnel", "funnel_reason", "discards", "fallback", "builds", "chosen", "p2")}
        result[year]["discard_unique_OD_month"] = {k: len(v) for k,v in x["discard_unique"].items()}
        result[year]["per_month"] = {k: dict(v) for k,v in sorted(x["per_month"].items())}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("engine_logs", type=Path)
    p.add_argument("--seeds", type=int, nargs="+", default=[42,100,999])
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    by_seed = {}
    for seed in args.seeds:
        path = args.engine_logs / f"p0_projects_probe_portfolio_seed{seed}_r0.log"
        with path.open(encoding="utf8", errors="replace") as inp:
            by_seed[str(seed)] = parse(inp)
    result = {"by_seed": by_seed, "limitations": [
        "MONTHLY_FUNNEL rows are per projects pass (NOT once a month), despite label. Sum of considered candidates repeats the same portfolio.",
        "PROJECT_DISCARD logs are controlled by DECISION_LOG and may omit repeated physical refusals; counters are NOT unique failed alternatives.",
        "P5_BUILD_LINE records NET _lines increments, not gross physical builds or survival.",
        "One observed candidate or even a funded rank does not prove physical constructibility or annual profit.",
        "These games use intrusive decision_log, probe_portfolio and scheduler instrumentation; cannot be joined to unprofiled economic trajectories."]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    for seed in args.seeds:
        for year in ("1971","1972","1973"):
            x = by_seed[str(seed)].get(year, {})
            print(seed,year,"funnel",x.get("funnel"),"discards",x.get("discards"),
                  "fallback",x.get("fallback"),"lines",x.get("builds"))


if __name__ == "__main__":
    main()
