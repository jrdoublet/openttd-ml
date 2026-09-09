"""Diagnostic C41.46 : séparer les opcodes nets d'une tranche A* rail de ceux de la tâche de
file exécutée dans la même passe de _runNextTask (voir docs/04_arbitrage_rail_search.md).
Purement observatoire : aucun dueCycle, aucune borne, aucune décision modifiée.
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

ARM = "OpexAI[c41_rail_slice_ledger=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C41_RAIL_SLICE_LEDGER\s*(.*)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / f"diag_c41_46_rail_slice_ledger_{args.years}y_{len(args.seeds)}seeds.json"
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
    for record in summary:
        events = [
            {key: value for token in fields.split() if "=" in token
             for key, _, value in (token.partition("="),)}
            for fields in EVENT_RE.findall(record.get("openttd_output", "") or "")
        ]
        record["c41_rail_slice_events"] = events
        for key in ("calls", "not_done_calls", "net_ops", "task_ops", "iter_delta"):
            record[f"c41_rail_slice_{key}"] = sum(int(event.get(key, 0)) for event in events)
    failed = [record for record in summary if not record["run_ok"]]
    write_json_atomically(out, {"years": args.years, "seeds": args.seeds, "summary": summary, "failed_runs": failed})
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
