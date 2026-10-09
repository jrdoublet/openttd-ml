"""Summarize scored rail blocker visits and RID outcomes from one frozen campaign.

Pair matching is descriptive. A later RID with the same OD is not the same
project, and a blocked project has no observed counterfactual profit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median

from analyse_rail_preastar import analyse as analyse_astar


def _number(value):
    try:
        result = float(value)
        return result if result == result and result != float("inf") and result != -float("inf") else None
    except (ValueError, TypeError):
        return None


def _attempt_key(row):
    return row["arm"], row["seed"], row["repeat"]


def summarize(blocked, astar):
    attempts = defaultdict(list)
    for search in astar["attempts"]:
        attempts[_attempt_key(search)].append(search)
    grouped = defaultdict(list)
    coverage = Counter()
    for run in blocked["runs"]:
        key = _attempt_key(run)
        relevant = attempts.get(key, [])
        for ev in run["blocked_visits"]:
            coverage["all_blocker_visits"] += 1
            if ev["link_status"] != "adjacent_exact_kind_src_dst":
                coverage["unmatched_blocker_visits"] += 1
                continue
            if ev["kind"] != "freight":
                coverage["pax_blocker_visits"] += 1
                continue
            coverage["freight_blocker_visits"] += 1
            if ev["same_od_as_primary_search"]:
                coverage["self_pair_visits"] += 1
                continue
            coverage["freight_other_pair_visits"] += 1
            grouped[(*key, ev["year"], ev["kind"], ev["cargo"], ev["src"], ev["dst"])].append((ev, relevant))

    pairs = []
    for key, observed in sorted(grouped.items()):
        events = [r for r, _ in observed]
        reference = events[0]
        runs = observed[0][1]
        arm, seed, repeat, year, kind, cargo, src, dst = key
        starts = [r for r in runs if r["mode"] == "primary"
                  and r["kind"] == kind and r["cargo"] == cargo
                  and r["src"] == int(src) and r["dst"] == int(dst)
                  and r["start_date"] and r["start_date"] > reference["day"]]
        starts.sort(key=lambda r: (r["start_date"], r["rid"]))
        built = [r for r in starts if r["build_status"] == "built" and r["build_ok"] == 1]
        occupant = []
        for a in runs:
            if a["mode"] != reference["blocker"] or a["start_date"] is None:
                continue
            if a["start_date"] > reference["day"] or (a["end_date"] and a["end_date"] < reference["day"]):
                continue
            if a["mode"] == "primary" and (a["src"] != int(reference["blocker_src"])
                                                   or a["dst"] != int(reference["blocker_dst"])):
                continue
            occupant.append(a)
        scores = [_number(e["score_at_block"]) for e in events]
        scores = [s for s in scores if s is not None and s >= 0]
        profits = [_number(e["profit_predicted_at_block"]) for e in events]
        profits = [p for p in profits if p is not None and p >= 0]
        pairs.append({"seed": seed, "year": year, "kind": kind, "cargo": cargo,
                      "src": src, "dst": dst, "destination": reference["destination_at_block"],
                      "first_block": reference["day"], "last_block": events[-1]["day"],
                      "visits": len(events), "first_rank": reference["requested_rank"],
                      "first_score": _number(reference["score_at_block"]),
                      "score_median": median(scores) if scores else None,
                      "pred_profit_median": median(profits) if profits else None,
                      "capital_hint_first": _number(reference["budget_capital_at_block"]),
                      "blocker_mode": reference["blocker"],
                      "occupant_link": "one_RID" if len(occupant) == 1 else
                          ("ambiguous" if len(occupant) > 1 else "unmatched"),
                      "occupant_rid": occupant[0]["rid"] if len(occupant) == 1 else None,
                      "occupant_start": occupant[0]["start_date"] if len(occupant) == 1 else None,
                      "occupant_end": occupant[0]["end_date"] if len(occupant) == 1 else None,
                      "occupant_stop": occupant[0]["stop"] if len(occupant) == 1 else None,
                      "later_same_OD_starts": len(starts),
                      "later_same_OD_built": len(built),
                      "later_same_OD_first_RID": starts[0]["rid"] if starts else None,
                      "later_same_OD_build_RIDs": [r["rid"] for r in built]})

    annual = defaultdict(Counter)
    for pair in pairs:
        y = pair["year"]
        annual[y]["freight_distinct_od_excluding_self"] += 1
        annual[y]["freight_other_pair_visits"] += pair["visits"]
        annual[y]["rank_zero_distinct_od"] += int(pair["first_rank"] in ("0", 0))
        annual[y]["positive_score_distinct_od"] += int(pair["first_score"] is not None and pair["first_score"] > 0)
        annual[y]["one_occupant_RID"] += int(pair["occupant_link"] == "one_RID")
        annual[y]["later_same_OD_start"] += int(pair["later_same_OD_starts"] > 0)
        annual[y]["later_same_OD_built"] += int(pair["later_same_OD_built"] > 0)
    return {"scope": "freight blocked OD in instrumented timeline; no cash-at-refusal or counterfactual build proof",
            "coverage": dict(coverage), "annual": {str(y): dict(c) for y, c in sorted(annual.items())},
            "pairs_by_year": pairs, "astar": astar["summary"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blocked", type=Path)
    parser.add_argument("engine_dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    blocked = json.loads(args.blocked.read_text(encoding="utf8"))
    result = summarize(blocked, analyse_astar(args.engine_dir))
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print("coverage", result["coverage"])
    for year, values in result["annual"].items():
        print(year, values)
    print("astar", result["astar"])


if __name__ == "__main__":
    main()
