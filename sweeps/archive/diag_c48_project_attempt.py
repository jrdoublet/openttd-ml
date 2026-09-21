"""Diagnostic C48 : ventile les tentatives de _tryBuildProjects par annee, mode et issue.

La sonde est passive : elle mesure la profondeur du portefeuille et les opcodes/jours des appels
de construction, sans modifier la selection ni l'ordonnancement.
"""
import argparse
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, keep, summarise, write_json_atomically,
)
import bench_v2

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

ARM = "OpexAI[c48_project_attempt_ledger=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C48_PROJECT_ATTEMPT\s*(.*)")
ATTEMPT_FIELDS = ("attempts", "ops", "days", "rank_sum")
PASS_FIELDS = ("passes", "attempts_total", "ops_total", "built", "best_len_sum", "max_rank_sum")


def parse_fields(fields):
    return dict(token.split("=", 1) for token in fields.split() if "=" in token)


def parse_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def sum_fields(rows, fields):
    total = {field: 0 for field in fields}
    for row in rows:
        for field in fields:
            total[field] += int(row.get(field, 0))
    return total


def aggregate_year_attempts(events):
    buckets = {}
    for event in events:
        if event.get("phase") != "annual" or "year" not in event or "key" not in event:
            continue
        mode, separator, outcome = event["key"].partition("|")
        if not separator:
            continue
        key = (int(event["year"]), mode, outcome)
        entry = buckets.setdefault(key, {field: 0 for field in ATTEMPT_FIELDS})
        for field in ATTEMPT_FIELDS:
            entry[field] += int(event.get(field, 0))
    return buckets


def aggregate_year_passes(events):
    buckets = {}
    for event in events:
        if event.get("phase") != "annual_pass" or "year" not in event:
            continue
        entry = buckets.setdefault(int(event["year"]), {field: 0 for field in PASS_FIELDS})
        for field in PASS_FIELDS:
            entry[field] += int(event.get(field, 0))
    return buckets


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def build_metrics(events):
    attempts = aggregate_year_attempts(events)
    passes = aggregate_year_passes(events)
    rows = []
    for year in sorted(set(passes) | {year for year, _, _ in attempts}):
        pass_entry = passes.get(year, {field: 0 for field in PASS_FIELDS})
        attempt_rows = []
        for (entry_year, mode, outcome), entry in attempts.items():
            if entry_year != year:
                continue
            attempt_rows.append({
                "mode": mode, "outcome": outcome, **entry,
                "ops_per_attempt": ratio(entry["ops"], entry["attempts"]),
                "days_per_attempt": ratio(entry["days"], entry["attempts"]),
                "mean_rank": ratio(entry["rank_sum"], entry["attempts"]),
            })
        attempt_rows.sort(key=lambda row: (row["mode"], row["outcome"]))
        attempted = sum_fields(attempt_rows, ATTEMPT_FIELDS)
        failed_ops = sum(row["ops"] for row in attempt_rows if row["outcome"] != "built")
        outside_ops = pass_entry["ops_total"] - attempted["ops"]
        rows.append({
            "year": year,
            "passes": pass_entry["passes"],
            "attempts_total": pass_entry["attempts_total"],
            "ops_total": pass_entry["ops_total"],
            "built": pass_entry["built"],
            "best_len_sum": pass_entry["best_len_sum"],
            "max_rank_sum": pass_entry["max_rank_sum"],
            "attempts_per_pass": ratio(pass_entry["attempts_total"], pass_entry["passes"]),
            "max_rank_per_pass": ratio(pass_entry["max_rank_sum"], pass_entry["passes"]),
            "best_len_per_pass": ratio(pass_entry["best_len_sum"], pass_entry["passes"]),
            "built_per_pass": ratio(pass_entry["built"], pass_entry["passes"]),
            "attempts": attempt_rows,
            "attempt_ops": attempted["ops"],
            "failed_attempt_ops": failed_ops,
            "failed_attempt_ops_share": ratio(failed_ops, attempted["ops"]),
            "outside_attempt_ops": outside_ops,
            "outside_attempt_ops_share": ratio(outside_ops, pass_entry["ops_total"]),
        })
    return {"by_year": rows}


def run_selftest():
    """Deux annees, deux modes et effectifs desequilibres : les ratios restent ponderes."""
    output = "\n".join((
        "OPEX 1971-1-1 C48_PROJECT_ATTEMPT phase=annual year=1971 key=road|built attempts=1 ops=100 days=2 rank_sum=0",
        "OPEX 1971-1-1 C48_PROJECT_ATTEMPT phase=annual year=1971 key=road|rejected attempts=1 ops=100 days=2 rank_sum=5",
        "OPEX 1971-1-1 C48_PROJECT_ATTEMPT phase=annual year=1971 key=road|rejected attempts=9 ops=1800 days=18 rank_sum=45",
        "OPEX 1971-1-1 C48_PROJECT_ATTEMPT phase=annual year=1971 key=air|rejected attempts=2 ops=200 days=4 rank_sum=8",
        "OPEX 1971-1-1 C48_PROJECT_ATTEMPT phase=annual_pass year=1971 passes=4 attempts_total=13 ops_total=2400 built=1 best_len_sum=40 max_rank_sum=20",
        "OPEX 1972-1-1 C48_PROJECT_ATTEMPT phase=annual year=1972 key=road|built attempts=9 ops=900 days=18 rank_sum=9",
        "OPEX 1972-1-1 C48_PROJECT_ATTEMPT phase=annual year=1972 key=air|rejected attempts=1 ops=1000 days=20 rank_sum=10",
        "OPEX 1972-1-1 C48_PROJECT_ATTEMPT phase=annual_pass year=1972 passes=2 attempts_total=10 ops_total=2500 built=2 best_len_sum=30 max_rank_sum=15",
    ))
    rows = build_metrics(parse_events(output))["by_year"]
    first, second = rows
    assert first["attempts_per_pass"] == 13 / 4
    assert first["failed_attempt_ops"] == 2100
    assert first["outside_attempt_ops"] == 200
    assert second["built_per_pass"] == 1
    road_built = next(row for row in first["attempts"] if row["mode"] == "road" and row["outcome"] == "built")
    assert road_built["ops_per_attempt"] == 100
    road_rejected = next(row for row in first["attempts"]
                         if row["mode"] == "road" and row["outcome"] == "rejected")
    # build_metrics() somme avant division : (100 + 1800) / (1 + 9), pas (100 + 200) / 2.
    assert road_rejected["ops_per_attempt"] == 190
    assert road_rejected["ops_per_attempt"] != 150
    print("selftest passed: weighted road rejected ops/attempt = 190.0, unweighted means = 150.0")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[100, 12345, 42, 7, 999])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / "diag_c48_project_attempt_6y_5seeds.json"
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms([ARM]), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    per_seed, all_events = [], []
    for record in summary:
        events = parse_events(record.get("openttd_output", ""))
        all_events.extend(events)
        per_seed.append({"seed": record["seed"], "run_ok": record["run_ok"],
                         "metrics": build_metrics(events)})
    failed = [{key: value for key, value in record.items() if key != "openttd_output"}
              for record in summary if not record["run_ok"]]
    payload = {"years": args.years, "seeds": args.seeds, "arm": ARM, "per_seed": per_seed,
               "cumulative": build_metrics(all_events), "failed_runs": failed,
               "failed_run_count": len(failed)}
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
