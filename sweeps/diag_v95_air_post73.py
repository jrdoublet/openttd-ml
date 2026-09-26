#!/usr/bin/env python3
"""V95 : diagnostic solo des occasions AIR post-1973 journalisees par OpexAI.

Capture AILog via ``-d script=4`` puis conserve, pour chaque sauvegarde de
decembre, les lignes ``V95_AIR_POST73`` de l'annee correspondante. Le script ne
change aucune decision : seul ``v95_air_post73_probe=1`` est force.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

DEFAULT_SEEDS = (42, 100, 999)
DEFAULT_YEARS = 6
TAG_RE = re.compile(r"V95_AIR_POST73 year=(\d+) month=(\d+)\s+(.*)")

try:
    import openttdlab
    from openttdlab import bananas_ai_library, local_folder, run_experiments
    from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg

    _real_check_output = openttdlab.subprocess.check_output

    def _check_output_with_script_debug(args, *rest, **kwargs):
        args = tuple(args)
        if any(str(arg).startswith("-vnull") for arg in args):
            args = args[:1] + ("-d", "script=4") + args[1:]
        return _real_check_output(args, *rest, **kwargs)

    openttdlab.subprocess.check_output = _check_output_with_script_debug
except ImportError:
    pass


def parse_fields(text: str) -> dict:
    fields = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            fields[key] = int(value)
        except ValueError:
            try:
                fields[key] = float(value)
            except ValueError:
                fields[key] = value
    return fields


def parse_v95_logs(output: str) -> dict[int, list[dict]]:
    by_year: dict[int, list[dict]] = {}
    for year_s, month_s, fields_s in TAG_RE.findall(output or ""):
        year = int(year_s)
        row = parse_fields(fields_s)
        row["year"] = year
        row["month"] = int(month_s)
        by_year.setdefault(year, []).append(row)
    return by_year


def keep(row):
    # ``openttdlab`` serialise ce callback vers ses workers Windows. Ne pas
    # dependre des globals du module ici : les diagnostics historiques gardent
    # leurs result_processor autonomes pour la meme raison.
    import re as _re

    date_s = str(row.get("date", ""))
    parts = date_s.split("-", 2)
    if len(parts) < 2 or parts[1] != "12":
        return ()
    try:
        year = int(parts[0])
    except ValueError:
        return ()
    seed = row.get("experiment", {}).get("seed")
    events = []
    tag_re = _re.compile(r"V95_AIR_POST73 year=(\d+) month=(\d+)\s+(.*)")
    for year_s, month_s, fields_s in tag_re.findall(row.get("output", "") or ""):
        if int(year_s) != year:
            continue
        fields = {}
        for token in fields_s.split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            try:
                fields[key] = int(value)
            except ValueError:
                try:
                    fields[key] = float(value)
                except ValueError:
                    fields[key] = value
        fields["year"] = year
        fields["month"] = int(month_s)
        events.append(fields)
    return ({"seed": seed, "year": year, "date": date_s, "events": events},)


def summarize(rows: list[dict]) -> dict:
    town_events = [dict(event, _seed=row.get("seed"))
                   for row in rows for event in row.get("events", [])
                   if event.get("phase") == "town"]
    summaries = [event for row in rows for event in row.get("events", [])
                 if event.get("phase") == "summary"]
    families = Counter(str(event.get("family", "unknown")) for event in town_events)
    current_rejects = Counter(str(event.get("current_reject", "unknown")) for event in town_events)
    shadow_rejects = Counter(str(event.get("shadow_reject", "unknown")) for event in town_events)
    candidates = [event for event in town_events if event.get("shadow_reject") == "candidate"]
    measured_positive = [event for event in town_events if event.get("measured_profit", -1) > 0]

    def competitor_airports(event):
        direct = event.get("competitor_airports")
        if isinstance(direct, int) and direct >= 0:
            return direct
        slots = event.get("slots_remaining")
        own = event.get("own_airports", 0)
        if isinstance(slots, int) and 0 <= slots <= 2 and isinstance(own, int):
            return max(0, 2 - slots - own)
        return -1

    def median(values):
        values = [value for value in values if isinstance(value, (int, float)) and value >= 0]
        return statistics.median(values) if values else None

    def group_summary(events):
        sites = [event for event in events if "anchor" in event]
        current_positive = [event for event in sites if event.get("profit", -1) > 0]
        measured = [event for event in sites if event.get("measured_profit", -1) > 0]
        measured_affordable = [event for event in measured
                               if event.get("measured_capital", 10**18) <= event.get("available", -1)]
        measured_50k = [event for event in measured if event.get("measured_profit", -1) >= 50000]
        measured_50k_affordable = [event for event in measured_50k
                                   if event.get("measured_capital", 10**18) <= event.get("available", -1)]
        measured_50k_pax75 = [event for event in measured_50k
                              if event.get("pax_site_est", -1) >= 75]
        measured_50k_pax75_cost30 = [event for event in measured_50k_pax75
                                     if 0 <= event.get("site_cost_est", 10**18) <= 30000]
        pax_cross = {}
        for threshold in (25, 40, 50, 60, 75):
            rows = [event for event in measured_50k
                    if event.get("pax_site_est", -1) >= threshold]
            pax_cross[str(threshold)] = {
                "events": len(rows),
                "unique_seed_towns": len({
                    (event.get("_seed"), event.get("town")) for event in rows
                }),
                "cost_le_30k": sum(
                    0 <= event.get("site_cost_est", 10**18) <= 30000 for event in rows
                ),
            }
        nondegraded = [event for event in measured
                       if event.get("measured_profit", -1) >= event.get("profit", 10**18)]
        nondegraded_affordable = [event for event in nondegraded
                                  if event.get("measured_capital", 10**18) <= event.get("available", -1)]
        incremental = [event for event in measured
                       if event.get("hub_only_profit", 10**18) < event.get("measured_profit", -1)]
        strict = [event for event in nondegraded
                  if event.get("hub_only_profit", 10**18) < event.get("measured_profit", -1)]
        strict_affordable = [event for event in strict
                             if event.get("measured_capital", 10**18) <= event.get("available", -1)]
        return {
            "events": len(events),
            "unique_seed_towns": len({(event.get("_seed"), event.get("town")) for event in events}),
            "sites": len(sites),
            "current_positive": len(current_positive),
            "measured_positive": len(measured),
            "measured_positive_unique_seed_towns": len({
                (event.get("_seed"), event.get("town")) for event in measured
            }),
            "measured_affordable": len(measured_affordable),
            "measured_profit_ge_50k": len(measured_50k),
            "measured_profit_ge_50k_affordable": len(measured_50k_affordable),
            "measured_profit_ge_50k_unique_seed_towns": len({
                (event.get("_seed"), event.get("town")) for event in measured_50k
            }),
            "measured_profit_ge_50k_pax_site_ge_75": len(measured_50k_pax75),
            "measured_profit_ge_50k_pax75_site_cost_le_30k": len(measured_50k_pax75_cost30),
            "measured_profit_ge_50k_pax75_cost30_unique_seed_towns": len({
                (event.get("_seed"), event.get("town")) for event in measured_50k_pax75_cost30
            }),
            "measured_profit_ge_50k_by_pax_site_threshold": pax_cross,
            "measured_nondegraded": len(nondegraded),
            "measured_nondegraded_affordable": len(nondegraded_affordable),
            "measured_nondegraded_unique_seed_towns": len({
                (event.get("_seed"), event.get("town")) for event in nondegraded
            }),
            "measured_incremental": len(incremental),
            "strict_nondegraded_incremental": len(strict),
            "strict_nondegraded_incremental_affordable": len(strict_affordable),
            "strict_unique_seed_towns": len({
                (event.get("_seed"), event.get("town")) for event in strict
            }),
            "median_pax_site_est": median([event.get("pax_site_est") for event in sites]),
            "median_site_cost_est": median([event.get("site_cost_est") for event in sites]),
            "median_current_profit": median([event.get("profit") for event in current_positive]),
            "median_measured_profit": median([event.get("measured_profit") for event in measured]),
            "median_measured_gain_when_nondegraded": median([
                event.get("measured_profit", -1) - event.get("profit", -1) for event in nondegraded
            ]),
            "median_site_incremental_profit": median([
                event.get("measured_profit", -1) - event.get("hub_only_profit", -1)
                for event in incremental
            ]),
        }

    groups = {
        "small_lt600": [event for event in town_events if event.get("pop", 10**18) < 600],
        "physical_second_open": [event for event in town_events if event.get("slots_remaining") == 1],
        "physical_second_own": [event for event in town_events
                                if event.get("slots_remaining") == 1 and event.get("own_airports", 0) > 0],
        "physical_second_competitor": [event for event in town_events
                                       if event.get("slots_remaining") == 1
                                       and event.get("own_airports", 0) == 0
                                       and competitor_airports(event) > 0],
        "physical_second_competitor_served": [event for event in town_events
                                              if event.get("slots_remaining") == 1
                                              and event.get("own_airports", 0) == 0
                                              and competitor_airports(event) > 0
                                              and event.get("current_reject") == "origin_served"],
        "competitor_present": [event for event in town_events if competitor_airports(event) > 0],
        "locked": [event for event in town_events if event.get("slots_remaining") == 0],
    }

    def values(field, events=town_events):
        return [event[field] for event in events if isinstance(event.get(field), (int, float))]

    return {
        "snapshots": len(rows),
        "town_events": len(town_events),
        "families": dict(sorted(families.items())),
        "current_rejects": dict(sorted(current_rejects.items())),
        "shadow_rejects": dict(sorted(shadow_rejects.items())),
        "summary_events": summaries,
        "candidate_count": len(candidates),
        "candidate_towns": sorted({event.get("town") for event in candidates if isinstance(event.get("town"), int)}),
        "candidate_profit": values("profit", candidates),
        "candidate_pax_prod": values("pax_prod", candidates),
        "candidate_mail_prod": values("mail_prod", candidates),
        "candidate_pax_site_est": values("pax_site_est", candidates),
        "candidate_mail_site_est": values("mail_site_est", candidates),
        "measured_positive_count": len(measured_positive),
        "measured_positive_towns": sorted({event.get("town") for event in measured_positive
                                            if isinstance(event.get("town"), int)}),
        "measured_profit": values("measured_profit"),
        "groups": {name: group_summary(events) for name, events in groups.items()},
        "all_profit": values("profit"),
        "all_pax_prod": values("pax_prod"),
        "all_pax_site_est": values("pax_site_est"),
    }


def run_selftest() -> None:
    sample = (
        "[script:0] [0] [I] V95_AIR_POST73 year=1973 month=4 phase=town family=small "
        "town=12 pop=540 current_reject=pop_floor shadow_reject=candidate pax_prod=91 "
        "pax_site_est=44 profit=88000 capital=90000 measured_profit=12000\n"
        "V95_AIR_POST73 year=1973 month=4 phase=summary towns=43 small=8 second=3 sites=7 "
        "profitable=5 affordable=2 hubs=14 available=100000\n"
    )
    parsed = parse_v95_logs(sample)
    assert len(parsed[1973]) == 2
    assert parsed[1973][0]["family"] == "small"
    assert parsed[1973][0]["town"] == 12
    assert parsed[1973][0]["profit"] == 88000
    result = summarize([{"seed": 42, "year": 1973, "events": parsed[1973]}])
    assert result["candidate_count"] == 1
    assert result["measured_positive_count"] == 1
    assert result["families"] == {"small": 1}
    assert result["shadow_rejects"] == {"candidate": 1}
    print("diag_v95_air_post73 selftest passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--shared", action="store_true",
                        help="run OpexAI against the local AAAHogEx copy on the same map")
    parser.add_argument("--from-json", type=Path,
                        help="recompute the summary from an existing V95 JSON without running a game")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_v95_air_post73.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if args.from_json is not None:
        payload = json.loads(args.from_json.read_text(encoding="utf-8"))
        payload["summary"] = summarize(payload.get("rows", []))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload["summary"].get("groups", {}), indent=2))
        print(f"Resume recalcule sans partie: {args.out}")
        return

    enable_savegame_cleanup()
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("v95_air_post73_probe", 1),))
    aaahogex = None
    if args.shared:
        aaahogex = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
    cfg = make_cfg(1970)
    experiments = [
        {
            "bench_context": "duel" if args.shared else "solo",
            "bench_arm": "OpexAI[v95_air_post73_probe=1]",
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (opex, aaahogex) if args.shared else (opex,),
        }
        for seed in args.seeds
    ]

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.max_workers,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    rows.sort(key=lambda row: (row.get("seed", 0), row.get("year", 0)))
    payload = {"rows": rows, "summary": summarize(rows)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(f"Snapshots captures: {len(rows)}, sortie: {args.out}")


if __name__ == "__main__":
    main()
