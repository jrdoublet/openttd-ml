#!/usr/bin/env python3
"""R19/V126 : coûts nets observés des échecs AIR jusqu'au rollback.

Ne valorise PAS les aéroports orphelins conservés ni les tickets censurés.
Les coûts `actual` des TRY incluent les récupérations immédiates ; seul le
champ `deferred_net` des tickets terminés s'y additionne.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from parse_air_finance_margin import parse_log_file, parse_kv_payload, to_int


RECOVERY = re.compile(r"\b(AIR_RECOVERY_(?:CREATE|STEP|COMPLETE))\s+(.*)$")


def parse_recovery(path: Path):
    by_id = {}
    duplicated = set()
    with path.open(encoding="utf-8", errors="replace") as stream:
        for text in stream:
            m = RECOVERY.search(text)
            if not m:
                continue
            kind, data = m.group(1), parse_kv_payload(m.group(2))
            ident = data.get("id", "")
            if not ident:
                continue
            record = by_id.setdefault(ident, {"created": 0, "steps": [], "completed": 0,
                                              "deferred_net": None})
            if kind == "AIR_RECOVERY_CREATE":
                record["created"] += 1
                if record["created"] > 1:
                    duplicated.add(ident)
            elif kind == "AIR_RECOVERY_STEP":
                record["steps"].append({"delta": to_int(data.get("delta")),
                                        "deferred_net": to_int(data.get("deferred_net")),
                                        "vehicles_left": to_int(data.get("vehicles_left")),
                                        "airports_left": to_int(data.get("airports_left"))})
            else:
                record["completed"] += 1
                record["deferred_net"] = to_int(data.get("deferred_net"))
    return by_id, sorted(duplicated)


def analyze(path: Path):
    run = parse_log_file(path)
    recoveries, duplicated = parse_recovery(path)
    failed = [r for r in run.tries if r.outcome == "failed"]
    records = []
    referenced = []
    for failure in failed:
        ident = failure.raw_kv.get("recovery_id", "none")
        orphan = failure.raw_kv.get("orphan_kept") == "1"
        ticket = recoveries.get(ident) if ident != "none" else None
        if ident != "none":
            referenced.append(ident)
        if orphan:
            state = "retained_asset"
            final = None
        elif ident == "none":
            state = "no_ticket"
            final = failure.actual
        elif ident in duplicated or ticket is None or ticket["completed"] != 1:
            state = "pending_or_unmatched"
            final = None
        elif failure.actual is None or ticket["deferred_net"] is None:
            state = "missing_accounting"
            final = None
        else:
            state = "rollback_completed"
            final = failure.actual + ticket["deferred_net"]
        records.append({
            "date": failure.date,
            "src_town": failure.src_town, "dst_town": failure.dst_town,
            "reason": failure.reason, "new_airports": failure.new_airports,
            "initial_actual": failure.actual,
            "recovery_id": ident, "orphan_retained": orphan,
            "recovery_deferred_net": ticket["deferred_net"] if ticket else None,
            "state": state, "final_accounted_net": final,
        })
    states = Counter(r["state"] for r in records)
    known = [r["final_accounted_net"] for r in records if r["final_accounted_net"] is not None]
    return {
        "file": path.name, "arm": run.arm, "seed": run.seed,
        "failed_count": len(failed), "states": dict(states),
        "initial_cost_sum_known": sum(r.actual for r in failed if r.actual is not None),
        "accounted_final_net_sum_known": sum(known), "accounted_final_net_count": len(known),
        "tickets_created": sum(v["created"] for v in recoveries.values()),
        "tickets_completed": sum(v["completed"] for v in recoveries.values()),
        "tickets_unreferenced": sorted(set(recoveries) - set(referenced)),
        "duplicate_ticket_ids": duplicated,
        "failed_records": records,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", nargs="+", type=Path)
    p.add_argument("--json", type=Path)
    args = p.parse_args()
    paths = []
    for arg in args.inputs:
        paths.extend(sorted(arg.glob("*.log")) if arg.is_dir() else [arg])
    if not paths:
        p.error("aucun fichier .log")
    result = {"runs": [analyze(path) for path in paths],
              "limitations": ["retained airports are assets with unknown later value",
                              "pending rollback tickets are right-censored",
                              "completed immediate rollback is already included in initial_actual",
                              "trace ids can collide after same-day Save/Load; duplicates are excluded"]}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for run in result["runs"]:
        print(f"{run['file']}: failed={run['failed_count']} states={run['states']} "
              f"cost_now={run['initial_cost_sum_known']} "
              f"complete_net_known={run['accounted_final_net_sum_known']} "
              f"n_known={run['accounted_final_net_count']}")


if __name__ == "__main__":
    main()
