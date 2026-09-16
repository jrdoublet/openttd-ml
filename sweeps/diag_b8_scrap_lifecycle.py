"""B8: diagnostic 5x6 du cycle de rebut et des projets de flotte AIR.

Le diagnostic conserve la politique early_slot adoptee et active seulement decision_log
pour observer les intervalles de rebut. Il ne constitue pas un banc d'adoption.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import bench_v2
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    enable_savegame_cleanup,
    keep as bench_keep,
    make_cfg,
    summarise as bench_summarise,
)
from game_health import assess_game, annotate_summary

STARTING_YEAR = 1970
SCRAP_TIMEOUT_YEARS = 2
DEFAULT_SEEDS = [42, 100, 999, 1234, 5678]
ARM = "OpexAI[air_early_slot=1,decision_log=1]"
OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def fields_from(rest):
    return dict(token.split("=", 1) for token in rest.split() if "=" in token)


def as_int(fields, key, default=None):
    try:
        return int(fields[key])
    except (KeyError, TypeError, ValueError):
        return default


def parse_events(output):
    events = []
    for raw in (output or "").splitlines():
        match = OPEX_RE.search(raw)
        if not match:
            continue
        year, month, day, kind, rest = match.groups()
        if kind not in ("SCRAP_LINE", "FEEDER_RECOVER", "AIR_FLEET", "FLEET_PROJECT"):
            continue
        events.append(
            {
                "year": int(year),
                "month": int(month),
                "day": int(day),
                "date": f"{year}-{int(month):02d}-{int(day):02d}",
                "kind": kind,
                "fields": fields_from(rest),
            }
        )
    return events


def analyse_lifecycle(events):
    active = {}
    starts = []
    removals = []
    recoveries = []
    air_refusals = []
    project_refusals = []
    forbidden_growth = []
    protocol_errors = []
    starts_by_mode = Counter()

    for event in events:
        fields = event["fields"]
        kind = event["kind"]
        line = as_int(fields, "line", -1)

        if kind == "SCRAP_LINE" and fields.get("action") == "start":
            start_year = as_int(fields, "start_year")
            mode = fields.get("mode", "unknown")
            if line < 0 or start_year is None:
                protocol_errors.append({"reason": "scrap_start_missing_fields", **event})
                continue
            if line in active:
                protocol_errors.append({"reason": "double_scrap_start", **event})
            record = {
                "line": line,
                "mode": mode,
                "date": event["date"],
                "year": event["year"],
                "start_year": start_year,
                "criterion": fields.get("criterion"),
            }
            active[line] = record
            starts.append(record)
            starts_by_mode[mode] += 1
            if start_year != event["year"]:
                protocol_errors.append({"reason": "start_year_mismatch", **event})

        elif kind == "FEEDER_RECOVER" and fields.get("action") == "cancel_scrap":
            record = {
                "line": line,
                "date": event["date"],
                "scrap_timer_reset": as_int(fields, "scrap_timer_reset"),
                "had_active_interval": line in active,
            }
            recoveries.append(record)
            active.pop(line, None)

        elif kind == "SCRAP_LINE" and fields.get("action") == "removed":
            elapsed = as_int(fields, "elapsed")
            start_year = as_int(fields, "start_year")
            criterion = fields.get("criterion")
            record = {
                "line": line,
                "date": event["date"],
                "criterion": criterion,
                "start_year": start_year,
                "elapsed": elapsed,
                "had_active_interval": line in active,
            }
            removals.append(record)
            if elapsed is None or start_year is None:
                protocol_errors.append({"reason": "scrap_remove_missing_fields", **event})
            elif elapsed < 0:
                protocol_errors.append({"reason": "negative_scrap_elapsed", **event})
            elif criterion == "timeout" and elapsed < SCRAP_TIMEOUT_YEARS:
                protocol_errors.append({"reason": "premature_timeout", **event})
            active.pop(line, None)

        elif kind == "AIR_FLEET" and fields.get("action") == "refuse" and fields.get("reason") == "scrapping":
            air_refusals.append({"line": line, "date": event["date"], "active": line in active})

        elif kind == "FLEET_PROJECT" and fields.get("action") == "refuse" and fields.get("reason") == "scrapping":
            project_refusals.append({"line": line, "date": event["date"], "active": line in active})

        elif kind in ("AIR_FLEET", "FLEET_PROJECT") and fields.get("action") == "grow":
            if line in active:
                forbidden_growth.append(
                    {
                        "line": line,
                        "date": event["date"],
                        "kind": kind,
                        "scrap_start": active[line],
                        "fields": fields,
                    }
                )

    return {
        "scrap_starts": starts,
        "scrap_starts_by_mode": dict(starts_by_mode),
        "scrap_removals": removals,
        "feeder_recoveries": recoveries,
        "air_scrapping_refusals": air_refusals,
        "fleet_project_scrapping_refusals": project_refusals,
        "forbidden_air_growth_during_scrap": forbidden_growth,
        "open_scrap_intervals_at_end": list(active.values()),
        "protocol_errors": protocol_errors,
        "counts": {
            "scrap_starts": len(starts),
            "air_scrap_starts": sum(row["mode"] == "air" for row in starts),
            "scrap_removals": len(removals),
            "timeout_removals": sum(row["criterion"] == "timeout" for row in removals),
            "feeder_recoveries": len(recoveries),
            "air_scrapping_refusals": len(air_refusals),
            "fleet_project_scrapping_refusals": len(project_refusals),
            "forbidden_air_growth_during_scrap": len(forbidden_growth),
        },
    }


def health_summary(rows, arm_name, years):
    series = sorted(rows, key=lambda row: row["date"])
    final_output = series[-1].get("openttd_output") or ""
    assessment = assess_game(
        series,
        starting_year=STARTING_YEAR,
        years=years,
        expected_companies=(arm_name,),
        slot_map={0: {"company_id": 0, "name": arm_name}},
        engine_log=final_output,
    )
    part = bench_summarise(
        series,
        expected_last_year=STARTING_YEAR + years - 1,
        expected_savegames=years * 12,
    )
    annotated = annotate_summary(part, series, assessment)
    if len(annotated) != 1:
        raise AssertionError(f"resume inattendu: {len(annotated)}")
    return annotated[0], assessment


def selftest():
    sample = "\n".join(
        (
            "OPEX 1971-1-2 SCRAP_LINE action=start line=7 mode=air dead_streak=3 "
            "threshold=3 vehicles=2 criterion=dead_streak start_year=1971",
            "OPEX 1971-2-2 AIR_FLEET action=refuse line=7 reason=scrapping planes=2 yield=10",
            "OPEX 1971-2-3 FLEET_PROJECT action=refuse line=7 reason=scrapping",
            "OPEX 1973-1-2 SCRAP_LINE action=removed line=7 criterion=timeout remaining=1 "
            "start_year=1971 elapsed=2",
            "OPEX 1974-1-2 SCRAP_LINE action=start line=8 mode=road dead_streak=3 "
            "threshold=3 vehicles=1 criterion=unprofitable start_year=1974",
            "OPEX 1974-2-2 FEEDER_RECOVER line=8 action=cancel_scrap scrap_timer_reset=1",
        )
    )
    analysed = analyse_lifecycle(parse_events(sample))
    assert not analysed["protocol_errors"], analysed
    assert not analysed["forbidden_air_growth_during_scrap"], analysed
    assert analysed["counts"]["air_scrap_starts"] == 1
    assert analysed["counts"]["air_scrapping_refusals"] == 1
    assert analysed["counts"]["fleet_project_scrapping_refusals"] == 1
    assert analysed["feeder_recoveries"][0]["scrap_timer_reset"] == 1

    bad = sample.replace(
        "OPEX 1971-2-2 AIR_FLEET action=refuse line=7 reason=scrapping planes=2 yield=10",
        "OPEX 1971-2-2 FLEET_PROJECT action=grow line=7 added=1 want=1",
    )
    analysed_bad = analyse_lifecycle(parse_events(bad))
    assert len(analysed_bad["forbidden_air_growth_during_scrap"]) == 1
    print("selftest OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "review_b8_scrap_lifecycle_5x6.json",
    )
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()

    arm = local_folder(
        str(ROOT / "ai" / "OpexAI"),
        "OpexAI",
        (("air_early_slot", 1), ("decision_log", 1)),
    )
    cfg = make_cfg(STARTING_YEAR)
    experiments = [
        {
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (arm,),
            "bench_run": [ARM, seed, 0],
        }
        for seed in args.seeds
    ]

    enable_savegame_cleanup()
    rows = list(
        run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            experiments=experiments,
            max_workers=min(args.workers, len(args.seeds)),
            result_processor=bench_keep,
            ai_libraries=(
                bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                bananas_ai_library("5046524c", "Pathfinder.Rail"),
            ),
        )
    )

    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row["run"])].append(row)

    by_seed = {}
    aggregate_counts = Counter()
    all_protocol_errors = []
    all_forbidden_growth = []
    all_recoveries = []
    health_ok = True
    economics = []

    for seed in args.seeds:
        key = (ARM, seed, 0)
        series = grouped.get(key, [])
        if not series:
            by_seed[str(seed)] = {"health": {"run_ok": False, "reason": "missing_run"}}
            health_ok = False
            continue

        final = max(series, key=lambda row: row["date"])
        summary, assessment = health_summary(series, ARM, args.years)
        health = {
            "run_ok": summary.get("run_ok"),
            "status": summary.get("status"),
            "horizon_complete": summary.get("horizon_complete"),
            "last_date": summary.get("last_date"),
            "n_savegames": summary.get("n_savegames"),
            "game_ok": assessment.get("game_ok"),
            "game_status": assessment.get("game_status"),
            "failure_reason": summary.get("failure_reason"),
        }
        run_health_ok = bool(
            health["run_ok"] and health["horizon_complete"] and health["game_ok"]
        )
        health_ok = health_ok and run_health_ok

        lifecycle = analyse_lifecycle(parse_events(final.get("openttd_output") or ""))
        aggregate_counts.update(lifecycle["counts"])
        all_protocol_errors.extend(
            [{"seed": seed, **item} for item in lifecycle["protocol_errors"]]
        )
        all_forbidden_growth.extend(
            [{"seed": seed, **item} for item in lifecycle["forbidden_air_growth_during_scrap"]]
        )
        all_recoveries.extend(
            [{"seed": seed, **item} for item in lifecycle["feeder_recoveries"]]
        )
        econ = {
            "company_value": summary.get("company_value"),
            "profit_year": summary.get("profit_year"),
            "performance_history": summary.get("performance_history"),
            "primary_vehicles": summary.get("primary_vehicles"),
            "air_primary_vehicles": (summary.get("primary_vehicles_by_mode") or {}).get("air"),
        }
        economics.append({"seed": seed, **econ})
        by_seed[str(seed)] = {
            "health": health,
            "economics": econ,
            "lifecycle": lifecycle,
        }

    timer_resets_ok = all(
        row.get("scrap_timer_reset") == 1 for row in all_recoveries
    )

    invariants = {
        "all_runs_healthy_complete_horizon": health_ok,
        "no_air_growth_during_scrap": not all_forbidden_growth,
        "scrap_event_schema_complete": not all_protocol_errors,
        "all_observed_feeder_recoveries_reset_timer": timer_resets_ok,
        "air_scrap_path_exercised": aggregate_counts["air_scrap_starts"] > 0,
        "feeder_recovery_path_exercised": aggregate_counts["feeder_recoveries"] > 0,
        "stale_fleet_project_guard_exercised": (
            aggregate_counts["fleet_project_scrapping_refusals"] > 0
        ),
    }

    payload = {
        "purpose": (
            "B8 lifecycle invariant diagnostic on adopted early_slot policy; "
            "not an adoption benchmark"
        ),
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "workers": min(args.workers, len(args.seeds)),
        "arm": ARM,
        "explicit_settings": {"air_early_slot": 1, "decision_log": 1},
        "scrap_timeout_years": SCRAP_TIMEOUT_YEARS,
        "by_seed": by_seed,
        "aggregate_counts": dict(aggregate_counts),
        "economics": economics,
        "invariants": invariants,
        "protocol_errors": all_protocol_errors,
        "forbidden_air_growth_during_scrap": all_forbidden_growth,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"aggregate_counts": dict(aggregate_counts), "invariants": invariants}, sort_keys=True))
    print(f"ecrit {args.out}")


if __name__ == "__main__":
    main()