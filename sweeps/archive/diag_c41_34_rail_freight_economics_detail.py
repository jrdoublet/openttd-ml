"""Diagnostic C41.34 : ventilation de l'économie des candidats fret rail."""
import argparse
import json
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (OPENGFX_VERSION, OPENTTD_VERSION, arm_statistics, build_arms,
                      enable_savegame_cleanup, experiments, keep, make_cfg, summarise,
                      write_json_atomically)
import bench_v2

_check = openttdlab.subprocess.check_output


def debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _check(args, *rest, **kwargs)


openttdlab.subprocess.check_output = debug
ARM = "OpexAI[c39_invalidation_probe=1,c41_rail_freight_economics_detail_profile=1]"
EVENT_RE = re.compile(r"(OPEX (\d+-\d+-\d+) C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE\s*(.*))")
METRICS = ("ops", "calls", "setup_ops", "setup_calls", "loop_ops", "loop_calls", "post_ops", "post_calls")


def events(output):
    seen, result = set(), []
    for raw, date, fields in EVENT_RE.findall(output or ""):
        if raw in seen:
            continue
        seen.add(raw)
        result.append({"date": date, **{
            key: value for token in fields.split() if "=" in token
            for key, _, value in (token.partition("="),)
        }})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--merge-inputs", nargs="+", type=Path, default=None,
                        help="Consolide des sorties unitaires déjà exécutées, sans lancer OpenTTD.")
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("years/seeds valides ; max-workers 1, 2 ou 3")

    out = args.out or ROOT / "results" / f"diag_c41_34_rail_freight_economics_detail_{args.years}y_{len(args.seeds)}seeds.json"
    if args.merge_inputs:
        inputs = [json.loads(path.read_text()) for path in args.merge_inputs]
        summary = [row for data in inputs for row in data["summary"]]
        failed = [row for row in summary if not row["run_ok"]]
        write_json_atomically(out, {
            "years": args.years, "seeds": args.seeds, "arms": [ARM],
            "openttd_config": inputs[0]["openttd_config"], "summary": summary,
            "failed_runs": failed, "statistics": arm_statistics(summary, [ARM]),
        })
        print("failed", len(failed), "out", out)
        if failed:
            raise SystemExit(1)
        return
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms([ARM]), args.seeds, args.years, 1, 1970),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    summary = summarise(rows)
    for row in summary:
        profile_events = events(row["openttd_output"])
        row["c41_rail_freight_economics_detail_profiles"] = profile_events
        for metric in METRICS:
            row["c41_freight_economics_" + metric] = sum(
                int(event.get(metric, 0)) for event in profile_events
            )
    failed = [row for row in summary if not row["run_ok"]]
    write_json_atomically(out, {
        "years": args.years, "seeds": args.seeds, "arms": [ARM],
        "openttd_config": make_cfg(1970), "summary": summary,
        "failed_runs": failed, "statistics": arm_statistics(summary, [ARM]),
    })
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
