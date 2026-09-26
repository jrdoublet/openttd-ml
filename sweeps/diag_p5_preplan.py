#!/usr/bin/env python3
"""Diagnostic P5 : mesure pré-planification A* rail pendant l'attente de capital.

Capture stdout OpenTTD (`-d script=4`) et produit le rapport complet P5 :
- Exposition du rail pendant les épisodes d'attente et hors épisodes
- Opcodes disponibles par épisode
- Coût réel d'un A* rail
- Gain potentiel et devenir des candidats
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
from analyse_p5_preplan import (  # noqa: E402
    analyze_p5, format_p5_report, parse_p5_output,
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
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--max-year", type=int, default=None,
                        help="Dernière année pour l'analyse des épisodes (défaut: 1970 + years - 1)")
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
        "wait_starts": [],
        "wait_ends": [],
        "rail_passes": [],
        "rail_searches": [],
        "build_lines": [],
    }
    series = []

    for record in summary_rows:
        s = record.get("seed")
        out_text = record.get("openttd_output") or ""
        parsed = parse_p5_output(out_text, seed=s)
        combined_data["wait_starts"].extend(parsed["wait_starts"])
        combined_data["wait_ends"].extend(parsed["wait_ends"])
        combined_data["rail_passes"].extend(parsed["rail_passes"])
        combined_data["rail_searches"].extend(parsed["rail_searches"])
        combined_data["build_lines"].extend(parsed["build_lines"])

        slim = {k: v for k, v in record.items() if k != "openttd_output"}
        slim["p5_wait_start_lines"] = out_text.count("P5_WAIT_START")
        slim["p5_wait_end_lines"] = out_text.count("P5_WAIT_END")
        slim["p5_rail_pass_lines"] = out_text.count("P5_RAIL_PASS")
        slim["p5_rail_search_lines"] = out_text.count("P5_RAIL_SEARCH")
        series.append(slim)

    max_year = args.max_year if args.max_year is not None else (1970 + args.years - 1)
    summary = analyze_p5(
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
        "report": format_p5_report(summary, args.seeds, max_year=max_year),
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
