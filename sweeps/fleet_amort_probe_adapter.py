"""Decode complete VM election blocks; never reconstruct orders from scores."""
from collections import defaultdict
import math

from sweeps.diag_air_selection_light import parse_log, reference
from sweeps.parallel_fleet_amort_shadow import SCHEMA, analyse_payload


def number(fields, key, integer=False):
    value = int(fields[key]) if integer else float(fields[key])
    if not math.isfinite(value):
        raise ValueError(key)
    return value


def candidate(event, budget):
    f = event["fields"]
    context = {"budget": budget, "admitted": True}
    for dest, src, integer in (("finance_capital", "finance", True),
                               ("denominator", "denominator", True),
                               ("calibration_factor", "factor", False),
                               ("priority", "priority", True),
                               ("early_slot_bonus_pct", "bonus", True),
                               ("revenue_annual", "revenue", True),
                               ("stable_index", "index", True), ("quantity", "quantity", True)):
        context[dest] = number(f, src, integer)
    def view(profit, calibrated, score):
        return {"profitAnnual": number(f, profit), "calibratedProfitAnnual": number(f, calibrated),
                "score": number(f, score), "context": dict(context)}
    row = {"id": f["candidate"], "mode": f["mode"], "category": f["category"],
           "baseline": view("profit", "calibrated", "score"),
           "alternative": view("net", "net_calibrated", "net_score"),
           "original_quantity": number(f, "original", True), "event": reference(event)}
    if row["category"] == "fleet_legacy":
        if f["observed"] not in ("0", "1"):
            raise ValueError("observed")
        row["project"] = {"mode": "fleet", "profitAnnual": number(f, "profit"),
                          "profitIsObserved": f["observed"] == "1",
                          "payload": {"want": context["quantity"], "planePrice": number(f, "price", True),
                                      "line": {"mode": f["line_mode"], "lineId": number(f, "line", True)}}}
    return row


def audit(text, source, *, campaign, arm, seed, repeat):
    events, issues = parse_log(text, source)
    groups = defaultdict(list)
    costs = []
    for e in events:
        if e["tag"] == "FLEET_AMORT_COST":
            costs.append({"event": reference(e), "fields": e["fields"]})
        if e["tag"] == "FLEET_AMORT":
            groups[e["company"], e["session"], e["fields"].get("id")].append(e)
    elections, rejected = [], []
    for (company, session, identity), block in groups.items():
        try:
            starts = [e for e in block if e["fields"].get("phase") == "begin"]
            ends = [e for e in block if e["fields"].get("phase") == "end"]
            rows = [e for e in block if e["fields"].get("phase") == "candidate"]
            if (company is None or identity is None or len(starts) != 1 or len(ends) != 1
                    or len(block) != len(rows) + 2 or block[0] != starts[0] or block[-1] != ends[0]
                    or any(e["fields"].get("v") != "1" for e in block)):
                raise ValueError("incomplete_or_duplicate_block")
            f, end = starts[0]["fields"], ends[0]["fields"]
            if f["supported"] != "1" or f["calibrated"] not in ("0", "1") or end["complete"] != "1":
                raise ValueError("unsupported_or_incomplete")
            count = number(f, "count", True)
            if count != number(end, "count", True) or count != len(rows):
                raise ValueError("count_mismatch")
            budget = number(f, "budget", True)
            decoded = [candidate(e, budget) for e in rows]
            if [r["baseline"]["context"]["stable_index"] for r in decoded] != list(range(count)):
                raise ValueError("incomplete_insertion_order")
            def order(key):
                return [] if end[key] == "none" else end[key].split(",")
            elections.append({"campaign": campaign, "arm": arm, "seed": seed, "repeat": repeat,
                              "company": int(company), "phase": f"{source}:session{session}",
                              "decision_id": identity, "revision": number(f, "revision", True),
                              "date": number(f, "day", True), "complete": True,
                              "candidate_count": count, "all_admitted_before_limit": True,
                              "order_source": "selector", "comparison_scope": "fixed_admission",
                              "settings": {"c84": False, "c85": False, "c121": False, "c122": False,
                                           "c115": 1, "v92": False, "calibrated": f["calibrated"] == "1",
                                           "cadence_off": True},
                              "candidates": decoded, "baseline_order": order("baseline"),
                              "alternative_order": order("alternative"),
                              "start": reference(starts[0]), "end": reference(ends[0])})
        except (KeyError, ValueError, TypeError, OverflowError) as error:
            rejected.append({"company": company, "session": session, "id": identity,
                             "reason": str(error), "lines": [e["line"] for e in block]})
    payload = {"schema": SCHEMA, "elections": elections}
    return {"snapshot": payload, "analysis": analyse_payload(payload), "rejected_blocks": rejected,
            "parse_issues": issues, "costs": costs,
            "coverage": "absent" if not groups else "observed_blocks",
            "source_health": "must_be_checked_by_harness", "inversions_if_absent": None}