"""Diagnostic apparié C41.44 : cache de desserte des villes fret rail OFF vs ON."""
import argparse
import re
import sys
from pathlib import Path

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

ARMS = (
    "OpexAI[c39_invalidation_probe=1,c41_rail_candidate_profile=1,c41_rail_freight_town_service_cache=0]",
    "OpexAI[c39_invalidation_probe=1,c41_rail_candidate_profile=1,c41_rail_freight_town_service_cache=1]",
)
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C41_RAIL_CANDIDATE_PROFILE\s*(.*)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out or ROOT / "results" / f"diag_c41_44_rail_freight_town_service_cache_paired_{args.years}y_{len(args.seeds)}seeds.json"
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(build_arms(list(ARMS)), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    for record in summary:
        events = [
            {key: value for token in fields.split() if "=" in token
             for key, _, value in (token.partition("="),)}
            for fields in EVENT_RE.findall(record.get("openttd_output", "") or "")
        ]
        record["c41_rail_candidate_ops"] = sum(int(event.get("ops", 0)) for event in events)
    failed = [record for record in summary if not record["run_ok"]]
    write_json_atomically(out, {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "arms": list(ARMS),
        "openttd_config": make_cfg(1970),
        "summary": summary,
        "failed_runs": failed,
        "statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": paired_comparisons(summary, list(ARMS)),
    })
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
