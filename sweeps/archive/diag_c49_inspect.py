"""Inspection des logs de transition C49 sous configuration normale (5 graines x 6 ans)."""
import argparse
import json
from pathlib import Path
import re
import sys

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, summarise
)
import bench_v2

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

C49_SCARCITY_RE = re.compile(r"OPEX \d+-\d+-\d+ C49_SCARCITY (.*)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--out", type=str, default="/tmp/diag_c49_inspect.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = out_path.with_suffix(".jsonl")

    arms = build_arms(["OpexAI[c49_variable_denominator=1]"])
    exps = experiments(arms, args.seeds, args.years, repeats=1)

    rows = list(run_experiments(
        exps,
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
        result_processor=bench_v2.keep,
    ))

    summary = bench_v2.summarise(rows)
    for record in summary:
        print(f"\n=== Seed {record['seed']} (Val={record['company_value']}) ===")
        output = record.get("openttd_output", "")
        for line in output.splitlines():
            m = C49_SCARCITY_RE.search(line)
            if m:
                print(" ", m.group(1))


if __name__ == "__main__":
    main()
