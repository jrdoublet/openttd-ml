#!/usr/bin/env python3
"""Diagnostic solo V95 item 1 : tours de file inutiles sous probe_scheduler.

Capture stdout OpenTTD (`-d script=4`) et resume via analyse_sched_idle.py.
Ne change aucun defaut. Pas un banc d'adoption.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (  # noqa: E402
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, keep, summarise, write_json_atomically,
)
import bench_v2  # noqa: E402
from analyse_sched_idle import (  # noqa: E402
    format_report, parse_sched_idle_output, summarize_events,
    summarize_monthly,
)

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 100, 999])
    parser.add_argument("--years", type=int, default=4)
    parser.add_argument("--arm", default="OpexAI[probe_scheduler=1]")
    parser.add_argument("--reference", help="Fichier JSON de reference (probe_scheduler=0) pour perturbation")
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args(argv)

    openttdlab.subprocess.check_output = _check_output_with_script_debug
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(build_arms([args.arm]), args.seeds, args.years, 1),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary_rows = summarise(
        rows,
        expected_last_year=1970 + args.years - 1,
        expected_savegames=args.years * 12,
    )

    baseline_series = None
    if args.reference:
        ref_path = Path(args.reference)
        if ref_path.exists():
            ref_data = json.loads(ref_path.read_text(encoding="utf-8"))
            baseline_series = ref_data.get("summary") or ref_data.get("series") or ref_data.get("rows") or []

    all_months = []
    all_reasons = []
    all_projs = []
    all_events = []
    all_c39 = []
    series = []

    for record in summary_rows:
        s = record.get("seed")
        out_text = record.get("openttd_output") or ""
        parsed = parse_sched_idle_output(out_text, seed=s)
        all_months.extend(parsed["months"])
        all_reasons.extend(parsed["reasons"])
        all_projs.extend(parsed["proj_years"])
        all_events.extend(parsed["events"])
        all_c39.extend(parsed["c39"])

        slim = {k: v for k, v in record.items() if k != "openttd_output"}
        slim["sched_idle_lines"] = out_text.count("SCHED_IDLE")
        series.append(slim)

    if all_events:
        summary = summarize_events(
            all_events, seed_series=series, baseline_series=baseline_series,
        )
    else:
        summary = summarize_events([])

    summary["raw_months_count"] = len(all_months)
    summary["raw_reasons_count"] = len(all_reasons)
    summary["raw_projs_count"] = len(all_projs)

    payload = {
        "arm": args.arm,
        "seeds": args.seeds,
        "years": args.years,
        "n_rows": len(series),
        "series": series,
        "summary": summary,
        "report": format_report(summary),
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "failed": [row for row in series if not row.get("run_ok", True)],
    }
    write_json_atomically(out, payload)
    report_path = out.with_suffix(".md")
    report_path.write_text(payload["report"], encoding="utf-8")
    sys.stdout.write(payload["report"])
    print(f"wrote {out} and {report_path}")
    if payload["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
