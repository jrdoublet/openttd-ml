"""Diagnostic apparié C41.30 : cache de croisière pax rail OFF vs ON (5×6 par défaut)."""
import argparse
import re
from pathlib import Path
import sys

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, arm_statistics, build_arms,
    enable_savegame_cleanup, experiments, keep, make_cfg, paired_comparisons,
    summarise, write_json_atomically,
)
import bench_v2

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

# Le profile est identique dans les deux arms : il donne le cout total de generation rail,
# sans modifier le choix de candidats. La seule difference fonctionnelle est le cache C41.30.
ARMS = (
    "OpexAI[c39_invalidation_probe=1,c41_rail_candidate_profile=1,c41_rail_pax_cruise_cache=0]",
    "OpexAI[c39_invalidation_probe=1,c41_rail_candidate_profile=1,c41_rail_pax_cruise_cache=1]",
)
EVENT_RE = re.compile(r"(OPEX (\d+-\d+-\d+) (C41_RAIL_CANDIDATE_PROFILE)\s*(.*))")


def rail_profiles(output):
    events, seen = [], set()
    for raw, date, kind, fields in EVENT_RE.findall(output or ""):
        if raw in seen:
            continue
        seen.add(raw)
        parsed = {key: value for token in fields.split() if "=" in token
                  for key, _, value in (token.partition("="),)}
        events.append({"raw": raw, "date": date, "kind": kind, **parsed})
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / f"diag_c41_30_rail_pax_cruise_cache_paired_{args.years}y_{len(args.seeds)}seeds.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms(list(ARMS)), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    events_by_run, seen_by_run = {}, {}
    for row in rows:
        key = tuple(row["run"])
        events_by_run.setdefault(key, [])
        seen_by_run.setdefault(key, set())
        for event in rail_profiles(row.get("openttd_output", "")):
            if event["raw"] in seen_by_run[key]:
                continue
            seen_by_run[key].add(event["raw"])
            del event["raw"]
            events_by_run[key].append(event)
    for record in summary:
        events = events_by_run.get((record["arm"], record["seed"], record["repeat"]), [])
        record["c41_rail_candidate_profiles"] = events
        record["c41_rail_candidate_ops"] = sum(int(event.get("ops", 0)) for event in events)
        record["c41_rail_candidate_calls"] = sum(int(event.get("calls", 0)) for event in events)
    failed = [record for record in summary if not record["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION, "opengfx_version": OPENGFX_VERSION,
        "years": args.years, "seeds": args.seeds, "arms": list(ARMS),
        "openttd_config": make_cfg(1970),
        "design": "paired OFF/ON; C39 logging and rail candidate profile are on in both arms, only C41.30 cruise cache differs",
        "summary": summary,
        "failed_runs": [{"arm": r["arm"], "seed": r["seed"], "failure_reason": r["failure_reason"]} for r in failed],
        "statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": paired_comparisons(summary, list(ARMS)),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(f"diagnostic invalide: {len(failed)} echec(s) NoAI")


if __name__ == "__main__":
    main()
