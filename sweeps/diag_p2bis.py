#!/usr/bin/env python3
"""Diagnostic P2 bis : reconciliation des passages projects sous probe_scheduler=1.

Capture stdout OpenTTD (`-d script=4`) et produit le rapport complet de reconciliation
entre passages de construction, etats du vivier et passages a vide.
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
from analyse_p2bis_reconciliation import (  # noqa: E402
    analyze_reconciliation, format_reconciliation_report, parse_p2bis_output,
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
    parser.add_argument("--reference", default="results/diag_v95b_probe0_4y_s42_100_999.json",
                        help="Fichier JSON de référence (probe_scheduler=0) pour perturbation")
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
        if not ref_path.is_absolute():
            ref_path = ROOT / ref_path
        if ref_path.exists():
            ref_data = json.loads(ref_path.read_text(encoding="utf-8"))
            baseline_series = ref_data.get("summary") or ref_data.get("series") or ref_data.get("rows") or []

    combined_data = {
        "passes": [],
        "builds": [],
        "resolves": [],
        "sched_events": [],
    }
    series = []

    for record in summary_rows:
        s = record.get("seed")
        out_text = record.get("openttd_output") or ""
        parsed = parse_p2bis_output(out_text, seed=s)
        combined_data["passes"].extend(parsed["passes"])
        combined_data["builds"].extend(parsed["builds"])
        combined_data["resolves"].extend(parsed["resolves"])
        combined_data["sched_events"].extend(parsed["sched_events"])

        slim = {k: v for k, v in record.items() if k != "openttd_output"}
        slim["p2_pass_lines"] = out_text.count("P2_PASS")
        slim["p2_build_lines"] = out_text.count("P2_BUILD")
        slim["p2_resolve_lines"] = out_text.count("P2_RESOLVE")
        series.append(slim)

    max_year = 1970 + args.years - 2 if args.years > 1 else 1970
    summary = analyze_reconciliation(
        combined_data,
        max_year=max_year,
        seed_series=series,
        baseline_series=baseline_series,
    )

    payload = {
        "arm": args.arm,
        "seeds": args.seeds,
        "years": args.years,
        "n_rows": len(series),
        "series": series,
        "summary": summary,
        "report": format_reconciliation_report(summary, args.seeds),
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "failed": [row for row in series if not row.get("run_ok", True)],
    }
    write_json_atomically(out, payload)
    report_path = out.with_suffix(".md")
    report_path.write_text(payload["report"], encoding="utf-8")
    sys.stdout.write(payload["report"])
    print(f"\nwrote {out} and {report_path}")
    if payload["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
