"""Diagnostic C48.1 : ventile par annee le cout interne de OpexIncrementalUpdateProjects.

La sonde est purement observatoire : elle mesure les phases, leurs volumes et le reste du cout
total apres une regeneration incrementale, sans changer portefeuille, construction ou scheduler.
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

ARM = "OpexAI[c48_incremental_profile=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C48_INCREMENTAL\s*(.*)")
STEPS = ("tension_ctx", "groups_replay", "feeders", "fleet", "air", "selection")
FIELDS = ("calls", "ops", "days", "lines", "groups", "projects_scanned", "retained",
          "fresh_feeders", "fleet_plan", "air_plans", "alternatives", "selected")
VOLUMES = {
    "groups_replay": ("groups", "projects_scanned", "retained"),
    "feeders": ("fresh_feeders",),
    "fleet": ("fleet_plan",),
    "air": ("air_plans",),
    "selection": ("alternatives", "selected"),
    "total": ("lines",),
}


def parse_fields(fields):
    return dict(token.split("=", 1) for token in fields.split() if "=" in token)


def parse_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def aggregate_year_steps(events):
    """Somme les numerateurs et denominateurs par (annee, phase), jamais des moyennes."""
    buckets = {}
    for event in events:
        if event.get("phase") != "annual" or "year" not in event or "step" not in event:
            continue
        key = (int(event["year"]), event["step"])
        entry = buckets.setdefault(key, {field: 0 for field in FIELDS})
        for field in FIELDS:
            entry[field] += int(event.get(field, 0))
    return buckets


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def phase_row(step, entry, total_ops):
    row = {"step": step, **entry, "ops_share_of_total": ratio(entry["ops"], total_ops),
           "ops_per_call": ratio(entry["ops"], entry["calls"])}
    # Une unite est toujours le volume cumule de la phase : somme(ops) / somme(volume).
    row["ops_per_volume"] = {
        field: ratio(entry["ops"], entry[field]) for field in VOLUMES.get(step, ())
    }
    return row


def build_metrics(events):
    buckets = aggregate_year_steps(events)
    years = sorted({year for year, _ in buckets})
    by_year, lines_and_total_ops = [], []
    for year in years:
        total = buckets.get((year, "total"), {field: 0 for field in FIELDS})
        phases = [phase_row(step, buckets[(year, step)], total["ops"])
                  for step in STEPS if (year, step) in buckets]
        phases.sort(key=lambda row: row["ops_share_of_total"] or 0, reverse=True)
        phase_ops = sum(row["ops"] for row in phases)
        remainder_ops = total["ops"] - phase_ops
        by_year.append({
            "year": year,
            "total": phase_row("total", total, total["ops"]),
            "phases_by_ops_share_desc": phases,
            "remainder_ops": remainder_ops,
            "remainder_ops_share_of_total": ratio(remainder_ops, total["ops"]),
        })
        lines_and_total_ops.append({"year": year, "lines": total["lines"],
                                    "total_ops": total["ops"], "total_calls": total["calls"]})
    return {"by_year": by_year, "lines_and_total_ops_by_year": lines_and_total_ops}


def run_selftest():
    """Deux annees desequilibrees : prouve que les ratios sont ponderes."""
    output = "\n".join((
        "OPEX 1971-1-1 C48_INCREMENTAL phase=annual year=1971 step=groups_replay calls=1 ops=100 days=1 lines=0 groups=1 projects_scanned=1 retained=1 fresh_feeders=0 fleet_plan=0 air_plans=0 alternatives=0 selected=0",
        "OPEX 1971-1-1 C48_INCREMENTAL phase=annual year=1971 step=selection calls=2 ops=400 days=2 lines=0 groups=0 projects_scanned=0 retained=0 fresh_feeders=0 fleet_plan=0 air_plans=0 alternatives=20 selected=4",
        "OPEX 1971-1-1 C48_INCREMENTAL phase=annual year=1971 step=total calls=1 ops=700 days=3 lines=100 groups=0 projects_scanned=0 retained=0 fresh_feeders=0 fleet_plan=0 air_plans=0 alternatives=0 selected=0",
        "OPEX 1972-1-1 C48_INCREMENTAL phase=annual year=1972 step=groups_replay calls=9 ops=1800 days=9 lines=0 groups=9 projects_scanned=90 retained=45 fresh_feeders=0 fleet_plan=0 air_plans=0 alternatives=0 selected=0",
        "OPEX 1972-1-1 C48_INCREMENTAL phase=annual year=1972 step=total calls=9 ops=2200 days=9 lines=2 groups=0 projects_scanned=0 retained=0 fresh_feeders=0 fleet_plan=0 air_plans=0 alternatives=0 selected=0",
    ))
    metrics = build_metrics(parse_events(output))
    annual = {row["year"]: row for row in metrics["by_year"]}
    buckets = aggregate_year_steps(parse_events(output))
    first = buckets[(1971, "groups_replay")]
    second = buckets[(1972, "groups_replay")]
    weighted = (first["ops"] + second["ops"]) / (first["calls"] + second["calls"])
    unweighted = (first["ops"] / first["calls"] + second["ops"] / second["calls"]) / 2
    assert weighted == 190  # (100 + 1800) / (1 + 9)
    assert weighted != unweighted and unweighted == 150
    groups = next(row for row in annual[1972]["phases_by_ops_share_desc"]
                  if row["step"] == "groups_replay")
    assert groups["ops_per_volume"]["projects_scanned"] == 20
    assert annual[1971]["remainder_ops"] == 200
    assert annual[1971]["remainder_ops_share_of_total"] == 200 / 700
    assert metrics["lines_and_total_ops_by_year"] == [
        {"year": 1971, "lines": 100, "total_ops": 700, "total_calls": 1},
        {"year": 1972, "lines": 2, "total_ops": 2200, "total_calls": 9},
    ]
    print("selftest passed: weighted groups ops/call = 190.0; unweighted annual means = 150.0")


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

    out = args.out or ROOT / "results" / "diag_c48_1_incremental_profile_6y_5seeds.json"
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
