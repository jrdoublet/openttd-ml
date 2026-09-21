"""C43/E3 famille 2 : CASH_RESERVE_MIN mord-il ? Panneau CASH_RESERVE_PROBE (delta annuel,
tache "report") sous cash_reserve_probe=1.

Lit openttd_output UNE SEULE FOIS par (graine, arm), depuis la derniere ligne de checkpoint --
docs/taches.md 2026-09-08 (2562e96) : cette valeur est identique a chaque ligne de checkpoint
mensuel d'une meme partie, pas une tranche par checkpoint.
"""
import argparse
import re
from pathlib import Path

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup, keep, make_cfg
import bench_v2

import openttdlab

SCRIPT_DEBUG_LEVEL = "4"
_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", f"script={SCRIPT_DEBUG_LEVEL}") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

LINE_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[(\w)\] (.*)")
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_opex_decisions(output):
    events = []
    for line in (output or "").splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        _company, _level, text = m.groups()
        m2 = OPEX_RE.match(text.strip())
        if not m2:
            continue
        y, mo, d, kind, rest = m2.groups()
        fields = {}
        for token in rest.split():
            if "=" in token:
                key, _, value = token.partition("=")
                fields[key] = value
        events.append({"date": f"{y}-{mo}-{d}", "kind": kind, "fields": fields})
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 42, 73, 100, 2026])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--out", type=Path,
                        default=Path("results/diag_cash_reserve_probe_6y_5seeds.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arm_name = "OpexAI[cash_reserve_probe=1]"
    arms = build_arms([arm_name])
    cfg = make_cfg(1970)

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=3,
        result_processor=keep,
        experiments=[
            {"seed": seed, "days": 365 * args.years, "openttd_config": cfg,
             "ais": (arms[arm_name],), "bench_run": [arm_name, seed, 0]}
            for seed in args.seeds
        ],
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    by_run = {}
    for row in rows:
        key = tuple(row["run"])
        by_run.setdefault(key, []).append(row)

    yearly = []
    errors = []
    FAIL_MARKERS = ("Your script made an error", "The script died unexpectedly")

    for key, series in by_run.items():
        _arm, seed, _rep = key
        series.sort(key=lambda r: r["date"])
        output = series[-1].get("openttd_output") if series else None
        for marker in FAIL_MARKERS:
            if marker in (output or ""):
                errors.append({"seed": seed, "marker": marker})
        for ev in parse_opex_decisions(output):
            if ev["kind"] != "CASH_RESERVE_PROBE":
                continue
            f = ev["fields"]
            yearly.append({"seed": seed, "year": f["year"],
                           "calls": int(f["calls"]), "min_binds": int(f["min_binds"]),
                           "max_binds": int(f["max_binds"])})

    total_calls = sum(r["calls"] for r in yearly)
    total_min = sum(r["min_binds"] for r in yearly)
    total_max = sum(r["max_binds"] for r in yearly)

    per_seed = {}
    for seed in args.seeds:
        seed_rows = [r for r in yearly if r["seed"] == seed]
        per_seed[seed] = {
            "calls": sum(r["calls"] for r in seed_rows),
            "min_binds": sum(r["min_binds"] for r in seed_rows),
            "max_binds": sum(r["max_binds"] for r in seed_rows),
        }

    payload = {
        "seeds": args.seeds, "years": args.years, "arm": arm_name,
        "errors": errors,
        "total_calls": total_calls, "total_min_binds": total_min, "total_max_binds": total_max,
        "pct_min_binds": (100.0 * total_min / total_calls) if total_calls else None,
        "pct_max_binds": (100.0 * total_max / total_calls) if total_calls else None,
        "per_seed": per_seed,
        "yearly": yearly,
    }
    import json
    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    print(f"total_calls={total_calls} total_min_binds={total_min} ({payload['pct_min_binds']})"
          if total_calls else "no calls captured")
    print(f"total_max_binds={total_max} ({payload['pct_max_binds']})" if total_calls else "")
    print("errors:", errors)
    print("per_seed:", per_seed)
    print("out", args.out)


if __name__ == "__main__":
    main()
