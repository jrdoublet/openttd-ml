#!/usr/bin/env python3
"""Résumé imprimable des funnel/rid P0 ; uniquement les mesures appariées au sein d'une partie."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


def analyse(report):
    rows = []
    cases = []
    for run in report["runs"]:
        seed = run["seed"]
        for year in range(1972, 1976):
            annual = run["annual"].get(str(year), {})
            per_kind = {}
            for kind in ("freight", "pax"):
                keys = [v for key, v in run["by_year_kind_cargo_destination"].items()
                        if key.startswith(f"{year}/{kind}/")
                        and key.endswith("/destination_unknown")]
                per_kind[kind] = {
                    "chosen_occurrences": sum(r.get("chosen/visits", 0) for r in keys),
                    "chosen_distinct_od_per_cargo": sum(r.get("chosen/distinct_od", 0) for r in keys),
                    "attempt_occurrences": sum(r.get("audit_attempt/visits", 0) for r in keys),
                    "attempt_distinct_od_per_cargo": sum(r.get("audit_attempt/distinct_od", 0) for r in keys),
                    "precheck_occurrences": sum(r.get("audit_precheck/visits", 0) for r in keys),
                    "dispatch_occurrences": sum(r.get("audit_dispatch/visits", 0) for r in keys),
                }
            rid = run["preastar"].get(str(year), {})
            rows.append({"seed": seed, "year": year, **per_kind,
                         "selection_eligible_freight_occurrences": annual.get("select/eligible_f", 0),
                         "selection_selected_freight_occurrences": annual.get("select/selected_f", 0),
                         "calls_freight_eligible": annual.get("select/calls_with_eligible_freight", 0),
                         "calls_freight_eligible_not_selected": annual.get("select/calls_eligible_but_not_selected", 0),
                         "head_air_given_freight_eligible": annual.get("select/head_air", 0),
                         "head_fleet_given_freight_eligible": annual.get("select/head_fleet", 0),
                         "freight_actual_cost_gbp_attempts": sum(
                             e.get("actual_gbp") or 0 for e in run["events"]
                             if e["date"][:4] == str(year) and e["phase"] == "attempt" and e["kind"] == "freight"),
                         "rail_audit_attempt_all_actual_gbp": annual.get("audit_attempt_actual_gbp", 0),
                         "rail_audit_attempt_all_opcodes": annual.get("audit_attempt_opcodes", 0),
                         "search_by_mode_start_year": rid,
                         "prepair_industry_pair_occurrences": annual.get("prepair/freight_ind_pairs", 0),
                         "prepair_town_pair_occurrences": annual.get("prepair/freight_town_pairs", 0)})
        by_identity = defaultdict(list)
        for ev in run["events"]:
            if ev["kind"] != "freight":
                continue
            key = (ev["cargo"], ev["src"], ev["dst"])
            by_identity[key].append(ev)
        for (cargo, src, dst), events in by_identity.items():
            if len(events) < 2:
                continue
            chosen = [e for e in events if e["phase"] == "chosen"]
            attempts = [e for e in events if e["phase"] == "attempt"]
            if not chosen and not attempts:
                continue
            reasons = Counter(e.get("reason") for e in attempts)
            costs = sum(e.get("actual_gbp") or 0 for e in attempts)
            first = min(events, key=lambda e: e["date"])
            last = max(events, key=lambda e: e["date"])
            cases.append({"seed": seed, "cargo": cargo, "src": src, "dst": dst,
                          "first_seen_date": first["date"], "last_seen_date": last["date"],
                          "chosen_occurrences": len(chosen), "attempt_occurrences": len(attempts),
                          "reasons": dict(reasons), "actual_cost_gbp_attempts": costs,
                          "first_chosen_predicted_profit_gbp_year": chosen[0].get("profit_predicted_gbp_year") if chosen else None,
                          "first_chosen_predicted_capital_gbp": chosen[0].get("capital_predicted_gbp") if chosen else None,
                          "first_chosen_log_line": chosen[0]["log_line"] if chosen else None,
                          "first_attempt_log_line": attempts[0]["log_line"] if attempts else None,
                          "link_confidence": "same_OD_but_attempt_identity_not_guaranteed"})
    rid_counts = defaultdict(Counter)
    for item in report["rid_detail"]:
        if item["start"]:
            y = int(item["start"][:4])
            if 1972 <= y <= 1975:
                rid_counts[(item["seed"], y, item["mode"], item["kind"], item["cargo"])][item["outcome"]] += 1
                if item["outcome"] != "unknown" and item["iters"] is not None:
                    rid_counts[(item["seed"], y, item["mode"], item["kind"], item["cargo"])]["iters_completed"] += item["iters"]
    return {"campaign_note": "instrumented single bundle only; project stages cannot be linked strictly without shared ID",
            "years": rows, "case_od_revisits": sorted(cases, key=lambda c: (-c["actual_cost_gbp_attempts"], -c["attempt_occurrences"])),
            "rid_by_start_year_seed_mode_kind_cargo": [
                {"seed": key[0], "year": key[1], "mode": key[2], "kind": key[3], "cargo": key[4], **dict(value)}
                for key, value in sorted(rid_counts.items())]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = analyse(json.loads(args.analysis.read_text(encoding="utf-8")))
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Rows", len(report["years"]), "cases", len(report["case_od_revisits"]),
          "RID groups", len(report["rid_by_start_year_seed_mode_kind_cargo"]))


if __name__ == "__main__":
    main()
