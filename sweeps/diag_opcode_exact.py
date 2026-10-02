#!/usr/bin/env python3
"""Solo C121 avec journal script=4 pour les lignes OPCODE_EXACT.

Ne change aucun defaut. Pas un banc d'adoption. Reutilise bench_v2.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
import bench_v2  # noqa: E402
from bench_v2 import (  # noqa: E402
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, keep, summarise, write_json_atomically,
)

_real_check_output = openttdlab.subprocess.check_output
EXACT_RE = re.compile(
    r"OPCODE_EXACT y=(\d+) site=(\S+) calls=(\d+) mismatch=(\d+) "
    r"ops_old=(\d+) ops_new=(\d+)"
)
ERROR_MARKERS = ("Your script made an error", "made an error", "The script died unexpectedly")


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


def _last_lines(text):
    """Derniere publication de chaque (annee, site) : la plus complete."""
    found = {}
    order = []
    for match in EXACT_RE.finditer(text or ""):
        year, site, calls, mismatch, ops_old, ops_new = match.groups()
        key = (int(year), site)
        if key not in found:
            order.append(key)
        found[key] = {
            "year": int(year),
            "site": site,
            "calls": int(calls),
            "mismatch": int(mismatch),
            "ops_old": int(ops_old),
            "ops_new": int(ops_new),
        }
    return [found[key] for key in order]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--years", type=int, required=True)
    parser.add_argument("--arm", required=True)
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
    log_path = out.with_suffix(".log")
    series = []
    log_chunks = []
    mismatches = 0
    script_errors = 0
    for record in summary_rows:
        text = record.get("openttd_output") or ""
        seed = record.get("seed")
        exact_lines = _last_lines(text)
        raw_exact = [line for line in text.splitlines() if "OPCODE_EXACT" in line]
        for line in raw_exact:
            log_chunks.append(f"seed={seed} {line}")
        for row in exact_lines:
            mismatches += row["mismatch"]
        for marker in ERROR_MARKERS:
            if marker in text:
                script_errors += text.count(marker)
        slim = {key: value for key, value in record.items() if key != "openttd_output"}
        slim["opcode_exact"] = exact_lines
        slim["opcode_exact_raw_lines"] = len(raw_exact)
        series.append(slim)

    log_path.write_text("\n".join(log_chunks) + ("\n" if log_chunks else ""), encoding="utf-8")
    payload = {
        "arm": args.arm,
        "seeds": args.seeds,
        "years": args.years,
        "n_rows": len(series),
        "series": series,
        "opcode_exact_mismatch_sum": mismatches,
        "script_error_hits": script_errors,
        "log": str(log_path),
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
    }
    write_json_atomically(out, payload)
    print(f"rows={len(series)} mismatch_sum={mismatches} script_error_hits={script_errors}")
    print(f"log={log_path}")
    return 0 if mismatches == 0 and script_errors == 0 and all(row.get("run_ok") for row in series) else 1


if __name__ == "__main__":
    sys.exit(main())
