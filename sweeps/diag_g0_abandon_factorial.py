"""G0: diagnostic causal factoriel abandon_gen_filter x abandon_cooldown_days.

Quatre bras, meme instrumentation et early_slot=1 :
  current = 1/365 ; no_filter = 0/365 ; permanent = 1/0 ; neither = 0/0.
Ce 5x6 est diagnostique uniquement. Il ne peut pas adopter un nouveau default.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import bench_v2
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    arm_statistics,
    build_arms,
    comparison_setting_audit,
    enable_savegame_cleanup,
    experiments,
    keep,
    paired_comparisons,
    resolved_arm_settings,
    summarise,
    write_json_atomically,
)
from diag_c63_c58 import parse_c63_invest, summarise_empty_probes

STARTING_YEAR = 1970
DEFAULT_SEEDS = [42, 100, 999, 1234, 5678]
SHARED = "air_early_slot=1,decision_log=1,probe_portfolio=1"
CURRENT = f"OpexAI[{SHARED},abandon_gen_filter=1,abandon_cooldown_days=365]"
NO_FILTER = f"OpexAI[{SHARED},abandon_gen_filter=0,abandon_cooldown_days=365]"
PERMANENT = f"OpexAI[{SHARED},abandon_gen_filter=1,abandon_cooldown_days=0]"
NEITHER = f"OpexAI[{SHARED},abandon_gen_filter=0,abandon_cooldown_days=0]"
ARMS = (CURRENT, NO_FILTER, PERMANENT, NEITHER)
ARM_PARAMS = {
    CURRENT: (
        ("air_early_slot", 1), ("decision_log", 1), ("probe_portfolio", 1),
        ("abandon_gen_filter", 1), ("abandon_cooldown_days", 365),
    ),
    NO_FILTER: (
        ("air_early_slot", 1), ("decision_log", 1), ("probe_portfolio", 1),
        ("abandon_gen_filter", 0), ("abandon_cooldown_days", 365),
    ),
    PERMANENT: (
        ("air_early_slot", 1), ("decision_log", 1), ("probe_portfolio", 1),
        ("abandon_gen_filter", 1), ("abandon_cooldown_days", 0),
    ),
    NEITHER: (
        ("air_early_slot", 1), ("decision_log", 1), ("probe_portfolio", 1),
        ("abandon_gen_filter", 0), ("abandon_cooldown_days", 0),
    ),
}

EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def parse_fields(text):
    return dict(token.split("=", 1) for token in text.split() if "=" in token)


def as_int(fields, key, default=0):
    try:
        return int(fields.get(key, default))
    except (TypeError, ValueError):
        return default


def parse_mechanism(output):
    abandon_pairs = []
    prune_events = []
    discards = Counter()
    for raw in (output or "").splitlines():
        match = EVENT_RE.search(raw)
        if not match:
            continue
        year, month, day, kind, rest = match.groups()
        fields = parse_fields(rest)
        date = f"{year}-{int(month):02d}-{int(day):02d}"
        if kind == "ABANDON_PAIR":
            abandon_pairs.append({
                "date": date,
                "key": fields.get("key"),
                "count": as_int(fields, "count"),
                "cooldown": as_int(fields, "cooldown"),
            })
        elif kind == "ABANDON_PRUNE":
            prune_events.append({
                "date": date,
                "count": as_int(fields, "count"),
                "remaining": as_int(fields, "remaining"),
            })
        elif kind == "PROJECT_DISCARD" and fields.get("reason") == "abandoned_pair":
            discards[fields.get("mode", "unknown")] += 1

    by_key = defaultdict(list)
    for event in abandon_pairs:
        by_key[event["key"]].append(event)
    retried_keys = {
        key: events
        for key, events in by_key.items()
        if max((event["count"] for event in events), default=0) > 1
    }
    return {
        "abandon_pair_events": len(abandon_pairs),
        "unique_abandoned_keys": len(by_key),
        "repeat_abandon_events": sum(event["count"] > 1 for event in abandon_pairs),
        "retried_failed_keys": len(retried_keys),
        "max_failure_count": max((event["count"] for event in abandon_pairs), default=0),
        "cooldowns_observed": dict(Counter(event["cooldown"] for event in abandon_pairs)),
        "prune_events": len(prune_events),
        "pruned_pairs_total": sum(event["count"] for event in prune_events),
        "prune_remaining_max": max((event["remaining"] for event in prune_events), default=0),
        "discard_abandoned_pair_by_mode": dict(discards),
        "discard_abandoned_pair_total": sum(discards.values()),
    }


def parse_c63_exposure(output, years):
    parsed = parse_c63_invest(output)
    required_closed = list(range(STARTING_YEAR, STARTING_YEAR + years - 1))
    missing = [year for year in required_closed if year not in parsed]
    absent_n = 0
    absent_days = 0
    empty_probes = []
    abandon_pairs_max = 0
    for payload in parsed.values():
        bucket = payload["absent_causes"]["abandon_filtered"]
        absent_n += int(bucket["n"])
        absent_days += int(bucket["days"])
        empty_probes.extend(payload["empty_probes"])
        for probe in payload["empty_probes"]:
            abandon_pairs_max = max(abandon_pairs_max, int(probe.get("abandon_pairs") or 0))
    empty = summarise_empty_probes(empty_probes)
    return {
        "closed_years_seen": sorted(year for year in parsed if year in required_closed),
        "missing_closed_years": missing,
        "abandon_filtered_n": absent_n,
        "abandon_filtered_days": absent_days,
        "empty_probe_count": empty.get("n", 0),
        "empty_probe_abandon_filtered_sum": empty.get("abandon_filtered_sum", 0),
        "empty_probe_causes": empty.get("causes", {}),
        "abandon_pairs_max": abandon_pairs_max,
        "cache_scanned_sum": empty.get("cache_scanned_sum", 0),
        "cache_retained_sum": empty.get("cache_retained_sum", 0),
    }


def aggregate_mechanism(items):
    return {
        "runs": len(items),
        "abandon_pair_events": sum(x["mechanism"]["abandon_pair_events"] for x in items),
        "unique_abandoned_keys_sum": sum(x["mechanism"]["unique_abandoned_keys"] for x in items),
        "repeat_abandon_events": sum(x["mechanism"]["repeat_abandon_events"] for x in items),
        "retried_failed_keys_sum": sum(x["mechanism"]["retried_failed_keys"] for x in items),
        "prune_events": sum(x["mechanism"]["prune_events"] for x in items),
        "pruned_pairs_total": sum(x["mechanism"]["pruned_pairs_total"] for x in items),
        "discard_abandoned_pair_total": sum(x["mechanism"]["discard_abandoned_pair_total"] for x in items),
        "discard_abandoned_pair_by_mode": dict(sum(
            (Counter(x["mechanism"]["discard_abandoned_pair_by_mode"]) for x in items),
            Counter(),
        )),
        "abandon_filtered_n": sum(x["c63"]["abandon_filtered_n"] for x in items),
        "abandon_filtered_days": sum(x["c63"]["abandon_filtered_days"] for x in items),
        "empty_probe_abandon_filtered_sum": sum(x["c63"]["empty_probe_abandon_filtered_sum"] for x in items),
        "abandon_pairs_max": max((x["c63"]["abandon_pairs_max"] for x in items), default=0),
        "cache_scanned_sum": sum(x["c63"]["cache_scanned_sum"] for x in items),
        "cache_retained_sum": sum(x["c63"]["cache_retained_sum"] for x in items),
        "all_c63_closed_years_complete": all(not x["c63"]["missing_closed_years"] for x in items),
    }


def collect_unique_opex_output(series):
    """Recompose les evenements rares a travers les fenetres console de chaque checkpoint."""
    seen = set()
    lines = []
    for row in sorted(series, key=lambda item: item["date"]):
        for raw in (row.get("openttd_output") or "").splitlines():
            index = raw.find("OPEX ")
            if index < 0:
                continue
            event = raw[index:]
            if event in seen:
                continue
            seen.add(event)
            lines.append(event)
    return "\n".join(lines)


def selftest():
    sample = "\n".join([
        "OPEX 1970-1-1 ABANDON_PAIR key=pax|0|1|2 count=1 cooldown=365",
        "OPEX 1971-1-2 ABANDON_PRUNE count=1 remaining=0",
        "OPEX 1971-1-3 ABANDON_PAIR key=pax|0|1|2 count=2 cooldown=730",
        "OPEX 1971-1-4 PROJECT_DISCARD rank=0 mode=rail src=1 dst=2 reason=abandoned_pair",
    ])
    parsed = parse_mechanism(sample)
    assert parsed["abandon_pair_events"] == 2
    assert parsed["retried_failed_keys"] == 1
    assert parsed["pruned_pairs_total"] == 1
    assert parsed["discard_abandoned_pair_by_mode"]["rail"] == 1
    print("selftest OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "review_g0_abandon_factorial_4arm_5x6.json",
    )
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument(
        "--reuse-checkpoint",
        action="store_true",
        help="Reanalyse le JSONL checkpoint existant sans rejouer les parties.",
    )
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists() and not args.reuse_checkpoint:
        bench_v2.CHECKPOINT_PATH.unlink()

    built = {
        arm: local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ARM_PARAMS[arm])
        for arm in ARMS
    }
    setting_state = resolved_arm_settings(list(ARMS))
    setting_audit = comparison_setting_audit(setting_state)
    if args.reuse_checkpoint:
        if not bench_v2.CHECKPOINT_PATH.exists():
            raise SystemExit(f"checkpoint absent: {bench_v2.CHECKPOINT_PATH}")
        rows = [
            json.loads(line)
            for line in bench_v2.CHECKPOINT_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        enable_savegame_cleanup()
        rows = list(run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            max_workers=min(args.workers, 6),
            result_processor=keep,
            experiments=experiments(built, args.seeds, args.years, 1, STARTING_YEAR),
            ai_libraries=(
                bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                bananas_ai_library("5046524c", "Pathfinder.Rail"),
            ),
        ))

    summary = summarise(
        rows,
        expected_last_year=STARTING_YEAR + args.years - 1,
        expected_savegames=args.years * 12,
    )
    failed = [row for row in summary if not row["run_ok"]]
    raw_by_run = defaultdict(list)
    for row in rows:
        raw_by_run[tuple(row["run"])].append(row)

    by_run = {}
    by_arm = defaultdict(list)
    for row in summary:
        combined_output = collect_unique_opex_output(
            raw_by_run[(row["arm"], row["seed"], row["repeat"])]
        )
        mech = parse_mechanism(combined_output)
        c63 = parse_c63_exposure(combined_output, args.years)
        payload = {
            "arm": row["arm"],
            "seed": row["seed"],
            "run_ok": row["run_ok"],
            "failure_reason": row["failure_reason"],
            "last_date": row["last_date"],
            "n_savegames": row["n_savegames"],
            "economics": {
                "company_value": row.get("company_value"),
                "profit_year": row.get("profit_year"),
                "performance_history": row.get("performance_history"),
                "primary_vehicles": row.get("primary_vehicles"),
                "n_stations": row.get("n_stations"),
                "observed_opcodes_total": row.get("observed_opcodes_total"),
            },
            "mechanism": mech,
            "c63": c63,
        }
        by_run[f"{row['arm']}|{row['seed']}"] = payload
        by_arm[row["arm"]].append(payload)

    aggregates = {arm: aggregate_mechanism(by_arm[arm]) for arm in ARMS}
    metrics = (
        "company_value",
        "profit_year",
        "performance_history",
        "primary_vehicles",
        "n_stations",
        "observed_opcodes_total",
    )
    comparisons = paired_comparisons(summary, list(ARMS), metrics)
    current_comparisons = [
        item for item in comparisons
        if item["arm_a"] == CURRENT or item["arm_b"] == CURRENT
    ]
    invariants = {
        "all_20_runs_present": len(summary) == len(ARMS) * len(args.seeds),
        "all_runs_healthy_complete_horizon": not failed,
        "all_c63_closed_years_complete": all(
            aggregate["all_c63_closed_years_complete"]
            for aggregate in aggregates.values()
        ),
        "current_filter_exposed": aggregates[CURRENT]["abandon_filtered_n"] > 0
            or aggregates[CURRENT]["empty_probe_abandon_filtered_sum"] > 0,
        "current_memory_exposed": aggregates[CURRENT]["abandon_pair_events"] > 0,
        "cooldown_pruning_exposed": aggregates[CURRENT]["pruned_pairs_total"] > 0
            or aggregates[NO_FILTER]["pruned_pairs_total"] > 0,
        "permanent_arms_do_not_prune": aggregates[PERMANENT]["pruned_pairs_total"] == 0
            and aggregates[NEITHER]["pruned_pairs_total"] == 0,
    }
    payload = {
        "purpose": (
            "G0 2x2 causal diagnostic only. No default may change from this 5x6. "
            "A 20x10 adoption authority is permitted only if a non-current policy becomes "
            "a genuine candidate after mechanism and economic review."
        ),
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "workers": min(args.workers, 6),
        "arms": list(ARMS),
        "reference_arm": CURRENT,
        "factorial": {
            CURRENT: {"abandon_gen_filter": 1, "abandon_cooldown_days": 365},
            NO_FILTER: {"abandon_gen_filter": 0, "abandon_cooldown_days": 365},
            PERMANENT: {"abandon_gen_filter": 1, "abandon_cooldown_days": 0},
            NEITHER: {"abandon_gen_filter": 0, "abandon_cooldown_days": 0},
        },
        "shared_settings": {
            "air_early_slot": 1,
            "decision_log": 1,
            "probe_portfolio": 1,
        },
        "runner_setting_mode": (
            "explicit-only local_folder params; shipped defaults supply every other setting. "
            "resolved_arm_settings is retained as the audit of intended effective defaults."
        ),
        "setting_state": setting_state,
        "setting_audit": setting_audit,
        "invariants": invariants,
        "failed_runs": [
            {"arm": row["arm"], "seed": row["seed"], "reason": row["failure_reason"]}
            for row in failed
        ],
        "mechanism_by_arm": aggregates,
        "by_run": by_run,
        "statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": comparisons,
        "current_vs_alternatives": current_comparisons,
        "limits": [
            "decision_log and probe_portfolio are diagnostic instrumentation shared by all arms.",
            "ABANDON_PRUNE proves release from memory; repeated ABANDON_PAIR count>1 proves a released/retried key failed again, not that every released key was rebuilt.",
            "abandon_cooldown_days=0 means permanent memory, not memory disabled.",
            "cooldown also applies to AIR abandonment memory; abandon_gen_filter=0 does not disable AIR memory.",
            "5x6 cannot adopt a default.",
        ],
    }
    write_json_atomically(args.out, payload)
    print(json.dumps({
        "invariants": invariants,
        "mechanism_by_arm": aggregates,
        "current_vs_alternatives": current_comparisons,
        "failed_runs": payload["failed_runs"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
