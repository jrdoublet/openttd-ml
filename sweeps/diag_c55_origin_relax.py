"""Diagnostic C55 etape 1 : mesure annuelle passive du verrou OR des origines route."""
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

ARM = "OpexAI[c55_origin_relax_probe=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C55_ORIGIN_RELAX\s*(.*)")
FIELDS = ("candidates_seen", "rejected_total", "both_served", "one_served",
          "one_served_pax", "one_served_freight", "duplicate_exact")


def parse_fields(fields):
    return dict(token.split("=", 1) for token in fields.split() if "=" in token)


def parse_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def numeric(event):
    return {field: int(event.get(field, 0)) for field in FIELDS}


def build_metrics(events):
    """Somme les lignes annuelles; la derniere summary est le cumul final de chaque graine."""
    annual = {}
    summaries = []
    for event in events:
        if "year" not in event:
            continue
        if event.get("phase") == "annual":
            year = int(event["year"])
            entry = annual.setdefault(year, {field: 0 for field in FIELDS})
            for field, value in numeric(event).items():
                entry[field] += value
        elif event.get("phase") == "summary":
            summaries.append((int(event["year"]), numeric(event)))
    by_year = [{"year": year, **annual[year]} for year in sorted(annual)]
    cumulative = {field: 0 for field in FIELDS}
    for row in by_year:
        for field in FIELDS:
            cumulative[field] += row[field]
    return {"by_year": by_year, "cumulative": cumulative,
            "last_summary": ({"year": summaries[-1][0], **summaries[-1][1]}
                             if summaries else None)}


def run_selftest():
    output = "\n".join((
        "OPEX 1971-1-1 C55_ORIGIN_RELAX phase=annual year=1971 candidates_seen=10 rejected_total=6 both_served=2 one_served=4 one_served_pax=1 one_served_freight=3 duplicate_exact=1",
        "OPEX 1971-1-1 C55_ORIGIN_RELAX phase=summary year=1971 candidates_seen=10 rejected_total=6 both_served=2 one_served=4 one_served_pax=1 one_served_freight=3 duplicate_exact=1",
        "OPEX 1972-1-1 C55_ORIGIN_RELAX phase=annual year=1972 candidates_seen=20 rejected_total=8 both_served=3 one_served=5 one_served_pax=2 one_served_freight=3 duplicate_exact=0",
        "OPEX 1972-1-1 C55_ORIGIN_RELAX phase=summary year=1972 candidates_seen=30 rejected_total=14 both_served=5 one_served=9 one_served_pax=3 one_served_freight=6 duplicate_exact=1",
    ))
    metrics = build_metrics(parse_events(output))
    assert metrics["cumulative"]["one_served"] == 9
    assert metrics["cumulative"]["one_served_pax"] + metrics["cumulative"]["one_served_freight"] == 9
    assert metrics["last_summary"] == {"year": 1972, "candidates_seen": 30, "rejected_total": 14,
        "both_served": 5, "one_served": 9, "one_served_pax": 3, "one_served_freight": 6,
        "duplicate_exact": 1}
    print("selftest passed: annual aggregation and final C55 summary")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[100, 12345, 42, 7, 999])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")
    out = args.out or ROOT / "results" / "diag_c55_origin_relax_6y_5seeds.json"
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms([ARM]), args.seeds, args.years, 1, 1970),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    summary = summarise(rows)
    per_seed, all_events = [], []
    for record in summary:
        events = parse_events(record.get("openttd_output", ""))
        all_events.extend(events)
        per_seed.append({"seed": record["seed"], "run_ok": record["run_ok"],
                         "metrics": build_metrics(events)})
    failed = [{key: value for key, value in record.items() if key != "openttd_output"}
              for record in summary if not record["run_ok"]]
    write_json_atomically(out, {"years": args.years, "seeds": args.seeds, "arm": ARM,
        "per_seed": per_seed, "cumulative": build_metrics(all_events),
        "failed_runs": failed, "failed_run_count": len(failed)})
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
