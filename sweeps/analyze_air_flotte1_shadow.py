"""Analyse des instantanés AIRF1_*, sans traiter un RAIL non bâti comme réalisé.

Usage: python -B sweeps/analyze_air_flotte1_shadow.py "results/.../*.log"

Conditions d'un comparatif valide de *budget* (pas une preuve de profit):
snapshot et scan sur le même tick, construction AIR confirmée, alternative
RAIL encore au portefeuille au même tick, finançable avant le débit mais plus
après. Ni constructibilité ni causalité à deux ans ne sont déduites.
"""

from __future__ import annotations

import argparse
from collections import Counter
import glob
import json
from pathlib import Path
import re


LINE = re.compile(r"\bAIRF1_(BUY|RAIL|LIST|POOL|CLOCK|READY|OUTCOME)\s+(.*)$")
FIELD = re.compile(r"(\w+)=([^\s]+)")


def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_records(lines):
    """One stable ID per purchase; duplicates are explicitly disqualified."""
    records = {}
    for line in lines:
        match = LINE.search(line)
        if not match:
            continue
        kind, payload = match.groups()
        fields = dict(FIELD.findall(payload))
        event_id = fields.get("id")
        if not event_id:
            continue
        record = records.setdefault(event_id, {
            "id": event_id, "buy": None, "clock": None, "ready": None, "outcome": None,
            "list": None, "pool": None, "rail": [], "duplicates": [],
        })
        if kind == "RAIL":
            record["rail"].append(fields)
        else:
            slot = kind.lower()
            if record[slot] is not None:
                record["duplicates"].append(kind)
            else:
                record[slot] = fields
    return list(records.values())


def assess(records):
    counters = Counter()
    samples = []
    for record in records:
        buy = record["buy"]
        outcome = record["outcome"]
        clock = record["clock"]
        ready = record["ready"]
        if buy is None:
            counters["missing_buy"] += 1
            continue
        counters["purchases_seen"] += 1
        channel = buy.get("channel")
        counters[f"channel_{channel}"] += 1
        if record["duplicates"]:
            counters["duplicate_event_disqualified"] += 1
            continue
        if outcome is None:
            counters["missing_outcome"] += 1
            continue
        if outcome.get("outcome") != "built":
            counters["not_built"] += 1
            continue
        counters["built"] += 1
        if clock is None or clock.get("same_tick") != "1":
            counters["unstable_tick_disqualified"] += 1
            continue
        if ready is None or ready.get("same_tick") != "1" or ready.get("same_cash") != "1":
            counters["unmatched_transaction_time_disqualified"] += 1
            continue
        counters["stable_tick_built"] += 1
        if channel == "renewal":
            # V252 has no predicted incremental profit or ROI in the engine.
            counters["v252_roi_unavailable"] += 1
        if record["pool"] is None:
            counters["missing_pool"] += 1
        elif record["pool"].get("truncated") == "1":
            counters["unselected_rail_pool_truncated"] += 1
        listed = next((p for p in record["rail"]
                       if p.get("scope") == "listed_best_remaining"), None)
        if listed is None:
            counters["no_listed_rail_alternative"] += 1
            continue
        counters["listed_rail_compared"] += 1
        rail_pass_reason = (record["list"] or {}).get("rail_pass_reason", "unknown")
        rail_pass_stage = (record["list"] or {}).get("rail_pass_stage", "unknown")
        counters[f"listed_rail_pass_{rail_pass_stage}"] += 1
        counters[f"listed_rail_reason_{rail_pass_reason}"] += 1
        search_phase = buy.get("rail_search_phase")
        if search_phase:
            counters[f"with_rail_search_{search_phase}"] += 1
        if record["list"] and record["list"].get("search_same_best") == "1":
            counters["rail_search_matches_best"] += 1
        pre = listed.get("afford_now")
        post = listed.get("afford_after")
        if pre != "1":
            counters["rail_not_fundable_before"] += 1
            continue
        counters["rail_fundable_before"] += 1
        if post != "0":
            counters["rail_still_fundable_after"] += 1
            continue
        counters["rail_cash_crossing_proxy"] += 1
        counters[f"crossing_rail_pass_{rail_pass_stage}"] += 1
        counters[f"crossing_rail_reason_{rail_pass_reason}"] += 1
        if rail_pass_stage == "rejected":
            counters["crossings_with_rail_rejected_in_same_pass"] += 1
        else:
            counters["crossings_with_rail_eligibility_unresolved"] += 1
        cal_profit = to_float(buy.get("calibrated_profit"))
        spend_finance = to_float(buy.get("finance"))
        rail_roi = to_float(listed.get("roi_c70_finance"))
        air_roi = cal_profit * 1000 / spend_finance if (
            cal_profit is not None and spend_finance and spend_finance > 0) else None
        if channel == "reinforce" and air_roi is not None and rail_roi is not None:
            counters["crossing_with_both_roi"] += 1
            if rail_roi > air_roi:
                counters["crossing_rail_calibrated_roi_higher"] += 1
        # A shortlist is neither a proven constructible project nor a fork.
        samples.append({"id": record["id"], "channel": channel,
                        "rail_key": listed.get("key"),
                        "rail_pass_stage": rail_pass_stage,
                        "rail_pass_reason": rail_pass_reason,
                        "rail_finance": to_int(listed.get("finance")),
                        "air_spend": to_int(buy.get("spend")),
                        "rail_roi_calibrated": rail_roi,
                        "air_roi_calibrated": air_roi,
                        "causal_eviction": None})
    return {
        "verdict": "descriptive_shadow_only",
        "counts": dict(counters),
        "cash_crossing_examples": samples[:20],
        "proven_buildable_rail_opportunities": None,
        "rail_unbuilt_realized_two_year_roi": None,
        "profit_gain_from_reallocation": None,
        "caveat": "No same-save fork, no rail site-build proof; pool candidates may be stale.",
    }


def analyze(paths):
    # Event IDs include tick/cycle/line, not run/seed: keep files isolated.
    totals = Counter()
    examples = []
    files = 0
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as stream:
            data = assess(parse_records(stream))
        totals.update(data["counts"])
        examples.extend({"log": str(path), **row}
                        for row in data["cash_crossing_examples"][:5])
        files += 1
    return {
        "files": files, "verdict": "descriptive_shadow_only",
        "counts": dict(totals), "examples": examples[:20],
        "distinct_rail_keys_in_examples": len({row.get("rail_key") for row in examples
                                               if row.get("rail_key")}),
        "proven_buildable_rail_opportunities": None,
        "rail_unbuilt_realized_two_year_roi": None,
        "profit_gain_from_reallocation": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patterns", nargs="+")
    args = parser.parse_args()
    paths = sorted({Path(filename) for pattern in args.patterns
                    for filename in glob.glob(pattern)})
    if not paths:
        parser.error("no matching log files")
    print(json.dumps(analyze(paths), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
