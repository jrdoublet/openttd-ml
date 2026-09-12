"""Diagnostic C55 : Isolation stricte du relâchement PAX routier et traçabilité causale.

Compare 3 bras purs sur 5 graines x 6 ans :
  1. Baseline     : OpexAI[c55_pax_trace_probe=1]
  2. PaxRelax     : OpexAI[c55_road_pax_origin_relax=1,c55_pax_trace_probe=1]
  3. FreightRelax : OpexAI[c55_freight_origin_relax=1,c55_pax_trace_probe=1]
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import statistics
import sys

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

ARM_BASELINE = "OpexAI[c55_pax_trace_probe=1]"
ARM_PAX = "OpexAI[c55_road_pax_origin_relax=1,c55_pax_trace_probe=1]"
ARM_FREIGHT = "OpexAI[c55_freight_origin_relax=1,c55_pax_trace_probe=1]"
ARMS = [ARM_BASELINE, ARM_PAX, ARM_FREIGHT]

EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C55_PAX_TRACE\s*(.*)")
FIELDS = ("revalidated", "origin_blocked", "spared", "elected", "built", "built_profit")

OPEX_EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_fields(fields):
    return dict(token.split("=", 1) for token in fields.split() if "=" in token)


def parse_trace_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def parse_all_opex_events(output):
    counts = Counter()
    for line in (output or "").splitlines():
        m = OPEX_EVENT_RE.search(line)
        if m:
            counts[m.group(4)] += 1
    return counts


def numeric(event):
    return {field: int(event.get(field, 0)) for field in FIELDS}


def build_trace_metrics(events):
    annual = {}
    summaries = []
    for event in events:
        if "year" not in event:
            continue
        phase = event.get("phase")
        if phase == "annual":
            year = int(event["year"])
            entry = annual.setdefault(year, {field: 0 for field in FIELDS})
            for field, value in numeric(event).items():
                entry[field] += value
        elif phase == "summary":
            summaries.append((int(event["year"]), numeric(event)))
    by_year = [{"year": year, **annual[year]} for year in sorted(annual)]
    cumulative = {field: 0 for field in FIELDS}
    for row in by_year:
        for field in FIELDS:
            cumulative[field] += row[field]
    last_summary = ({"year": summaries[-1][0], **summaries[-1][1]}
                    if summaries else {field: 0 for field in FIELDS})
    return {
        "by_year": by_year,
        "cumulative": cumulative,
        "last_summary": last_summary,
    }


def format_delta(val, base):
    if base is None or val is None or base == 0:
        return "-"
    diff = val - base
    pct = (diff / abs(base)) * 100
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:,.0f} ({sign}{pct:.1f}%)"


def run_selftest():
    sample_output = """
OPEX 1971-1-1 C55_PAX_TRACE phase=annual year=1971 revalidated=12 origin_blocked=5 spared=5 elected=2 built=2 built_profit=15400
OPEX 1971-1-1 C55_PAX_TRACE phase=summary year=1971 revalidated=12 origin_blocked=5 spared=5 elected=2 built=2 built_profit=15400
OPEX 1972-1-1 C55_PAX_TRACE phase=annual year=1972 revalidated=20 origin_blocked=8 spared=6 elected=3 built=2 built_profit=16200
OPEX 1972-1-1 C55_PAX_TRACE phase=summary year=1972 revalidated=32 origin_blocked=13 spared=11 elected=5 built=4 built_profit=31600
OPEX 1971-5-12 C55_PAX_SPARED src=42 dst=99 profit=7800
OPEX 1971-5-12 C55_PAX_ELECTED src=42 dst=99 profit=7800
OPEX 1971-5-12 C55_PAX_BUILT line=3 src=42 dst=99 profit=7800 cost=12000 vehicles=2
"""
    events = parse_trace_events(sample_output)
    metrics = build_trace_metrics(events)
    counts = parse_all_opex_events(sample_output)

    assert len(events) == 4, f"expected 4 trace events, got {len(events)}"
    assert metrics["cumulative"]["revalidated"] == 32
    assert metrics["cumulative"]["origin_blocked"] == 13
    assert metrics["cumulative"]["spared"] == 11
    assert metrics["cumulative"]["elected"] == 5
    assert metrics["cumulative"]["built"] == 4
    assert metrics["cumulative"]["built_profit"] == 31600
    assert metrics["last_summary"]["year"] == 1972
    assert metrics["last_summary"]["built"] == 4

    assert counts["C55_PAX_TRACE"] == 4
    assert counts["C55_PAX_SPARED"] == 1
    assert counts["C55_PAX_ELECTED"] == 1
    assert counts["C55_PAX_BUILT"] == 1

    print("Selftest passed successfully!")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[100, 12345, 42, 7, 999])
    parser.add_argument("--arms", nargs="+", default=ARMS)
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

    out = args.out or ROOT / "results" / "diag_c55_pax_isolation_6y_5seeds.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arms_dict = build_arms(args.arms)
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(arms_dict, args.seeds, args.years, 1, 1970),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))

    summary = summarise(rows)

    by_arm = {arm: [] for arm in args.arms}
    for record in summary:
        arm = record["arm"]
        if arm in by_arm:
            events = parse_trace_events(record.get("openttd_output", ""))
            counts = parse_all_opex_events(record.get("openttd_output", ""))
            metrics = build_trace_metrics(events)
            by_arm[arm].append({
                "seed": record["seed"],
                "run_ok": record["run_ok"],
                "company_value": record.get("company_value", 0),
                "profit_year": record.get("profit_year", 0),
                "profit": record.get("profit", 0),
                "performance_history": record.get("performance_history", 0),
                "n_vehicles": record.get("n_vehicles", 0),
                "n_stations": record.get("n_stations", 0),
                "median_station_rating": record.get("median_station_rating", 0),
                "trace_metrics": metrics,
                "event_counts": dict(counts),
            })

    failed = [{key: value for key, value in record.items() if key != "openttd_output"}
              for record in summary if not record["run_ok"]]

    # Aggregates per arm
    arm_aggregates = {}
    for arm, records in by_arm.items():
        ok_records = [r for r in records if r["run_ok"]]
        cvs = [r["company_value"] for r in ok_records]
        pys = [r["profit_year"] for r in ok_records]
        vehs = [r["n_vehicles"] for r in ok_records]
        stns = [r["n_stations"] for r in ok_records]
        ratings = [r["median_station_rating"] for r in ok_records if r.get("median_station_rating")]

        cum_spared = sum(r["trace_metrics"]["cumulative"]["spared"] for r in ok_records)
        cum_elected = sum(r["trace_metrics"]["cumulative"]["elected"] for r in ok_records)
        cum_built = sum(r["trace_metrics"]["cumulative"]["built"] for r in ok_records)
        cum_built_profit = sum(r["trace_metrics"]["cumulative"]["built_profit"] for r in ok_records)
        cum_origin_blocked = sum(r["trace_metrics"]["cumulative"]["origin_blocked"] for r in ok_records)
        cum_revalidated = sum(r["trace_metrics"]["cumulative"]["revalidated"] for r in ok_records)

        arm_aggregates[arm] = {
            "n_runs": len(records),
            "n_ok": len(ok_records),
            "company_value_mean": statistics.mean(cvs) if cvs else 0,
            "company_value_median": statistics.median(cvs) if cvs else 0,
            "profit_year_mean": statistics.mean(pys) if pys else 0,
            "profit_year_median": statistics.median(pys) if pys else 0,
            "n_vehicles_mean": statistics.mean(vehs) if vehs else 0,
            "n_stations_mean": statistics.mean(stns) if stns else 0,
            "rating_median": statistics.median(ratings) if ratings else 0,
            "revalidated_total": cum_revalidated,
            "origin_blocked_total": cum_origin_blocked,
            "spared_total": cum_spared,
            "elected_total": cum_elected,
            "built_total": cum_built,
            "built_profit_total": cum_built_profit,
        }

    # Print markdown summary
    print("\n" + "=" * 95)
    print("DIAGNOSTIC C55 : ISOLATION PAX ROUTIER vs FRET ROUTIER")
    print("=" * 95)
    headers = ["Metrique", "1. Baseline", "2. PaxRelax", "3. FreightRelax", "Delta Pax vs Base"]
    print(f"{headers[0]:<25} | {headers[1]:<16} | {headers[2]:<16} | {headers[3]:<16} | {headers[4]:<20}")
    print("-" * 105)

    arm_names = list(args.arms)
    base_name = arm_names[0] if len(arm_names) > 0 else ""
    pax_name = arm_names[1] if len(arm_names) > 1 else ""
    frt_name = arm_names[2] if len(arm_names) > 2 else ""

    base = arm_aggregates.get(base_name, {})
    pax = arm_aggregates.get(pax_name, {})
    frt = arm_aggregates.get(frt_name, {})

    def row(label, key, fmt="{:,.0f}"):
        b_val = base.get(key, 0)
        p_val = pax.get(key, 0)
        f_val = frt.get(key, 0)
        delta = format_delta(p_val, b_val)
        b_str = fmt.format(b_val)
        p_str = fmt.format(p_val)
        f_str = fmt.format(f_val)
        print(f"{label:<25} | {b_str:<16} | {p_str:<16} | {f_str:<16} | {delta:<20}")

    row("Company Value (mean)", "company_value_mean")
    row("Company Value (med)", "company_value_median")
    row("Profit Year (mean)", "profit_year_mean")
    row("Profit Year (med)", "profit_year_median")
    row("Vehicles (mean)", "n_vehicles_mean", fmt="{:.1f}")
    row("Stations (mean)", "n_stations_mean", fmt="{:.1f}")
    row("Station Rating (med)", "rating_median", fmt="{:.1f}")
    row("PAX Reval Evals", "revalidated_total")
    row("PAX Origin Blocked", "origin_blocked_total")
    row("PAX Spared", "spared_total")
    row("PAX Elected", "elected_total")
    row("PAX Built", "built_total")
    row("PAX Built Profit", "built_profit_total")
    print("=" * 105)

    result_payload = {
        "years": args.years,
        "seeds": args.seeds,
        "arms": args.arms,
        "arm_aggregates": arm_aggregates,
        "by_arm": by_arm,
        "failed_runs": failed,
        "failed_run_count": len(failed),
    }

    write_json_atomically(out, result_payload)
    print(f"\nResultats ecrits dans : {out}")
    if failed:
        print(f"ATTENTION : {len(failed)} echec(s) detecte(s) !")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
