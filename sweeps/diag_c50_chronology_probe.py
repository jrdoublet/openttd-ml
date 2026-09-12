"""Diagnostic C50 : Sonde chronologique legere (tresorerie, profit par ligne, projets batis et refuses).

Mesure passive sans decision_log=1 : relie le decrochage 1970 -> 1971+ face a AAAHogEx
a la tresorerie mensuelle, a la rentabilite des lignes existantes, et aux arbitrages de construction.
"""
import argparse
from collections import defaultdict
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

ARM = "OpexAI[c50_chronology_probe=1]"
DEFAULT_SEEDS = [100, 12345, 42, 7, 999]
C50_EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) C50_CHRONO\s*(.*)")


def parse_fields(fields_str):
    res = {}
    for token in fields_str.split():
        if "=" in token:
            k, v = token.split("=", 1)
            res[k] = v
    return res


def parse_events(output):
    events = []
    for line in (output or "").splitlines():
        m = C50_EVENT_RE.search(line)
        if m:
            y, mth, d, f_str = m.group(1), m.group(2), m.group(3), m.group(4)
            ev = parse_fields(f_str)
            ev["_log_date"] = f"{y}-{mth}-{d}"
            ev["_log_year"] = int(y)
            events.append(ev)
    return events


def process_c50_events(events):
    years_data = defaultdict(lambda: {
        "treasury_monthly": [],
        "treasury_annual": None,
        "line_profit_summary": None,
        "line_profits": [],
        "projects_built": [],
        "projects_refused_cash": [],
        "fleet_built": [],
    })

    for ev in events:
        phase = ev.get("phase")
        yr = int(ev.get("year", ev.get("_log_year", 0)))
        bucket = years_data[yr]

        if phase == "treasury_monthly":
            bucket["treasury_monthly"].append({
                "month": int(ev.get("month", 0)),
                "cash": int(ev.get("cash", 0)),
                "loan": int(ev.get("loan", 0)),
                "available": int(ev.get("available", 0)),
            })
        elif phase == "treasury_annual":
            bucket["treasury_annual"] = {
                "cash": int(ev.get("cash", 0)),
                "loan": int(ev.get("loan", 0)),
                "max_loan": int(ev.get("max_loan", 0)),
                "available": int(ev.get("available", 0)),
                "company_value": int(ev.get("company_value", 0)),
                "lines": int(ev.get("lines", 0)),
            }
        elif phase == "line_profit_summary":
            bucket["line_profit_summary"] = {
                "lines": int(ev.get("lines", 0)),
                "prof_sum": int(ev.get("prof_sum", 0)),
                "rev_sum": int(ev.get("rev_sum", 0)),
                "prof_lines": int(ev.get("prof_lines", 0)),
                "loss_lines": int(ev.get("loss_lines", 0)),
            }
        elif phase == "line_profit":
            bucket["line_profits"].append({
                "line": int(ev.get("line", 0)),
                "mode": ev.get("mode", "unknown"),
                "cargo": ev.get("cargo", "unknown"),
                "vehs": int(ev.get("vehs", 0)),
                "profit": int(ev.get("profit", 0)),
                "run_cost": int(ev.get("run_cost", 0)),
                "rev": int(ev.get("rev", 0)),
                "pred_profit": int(ev.get("pred_profit", 0)),
                "roi": int(ev.get("roi", 0)),
                "age": int(ev.get("age", 0)),
            })
        elif phase == "project_built":
            bucket["projects_built"].append({
                "mode": ev.get("mode", "unknown"),
                "rank": int(ev.get("rank", -1)),
                "line": int(ev.get("line", -1)),
                "cost": int(ev.get("cost", 0)),
                "profit": int(ev.get("profit", 0)),
                "roi": int(ev.get("roi", 0)),
                "cash_after": int(ev.get("cash_after", 0)),
                "available": int(ev.get("available", 0)),
            })
        elif phase == "refused_cash":
            bucket["projects_refused_cash"].append({
                "mode": ev.get("mode", "unknown"),
                "rank": int(ev.get("rank", -1)),
                "cost": int(ev.get("cost", 0)),
                "profit": int(ev.get("profit", 0)),
                "roi": int(ev.get("roi", 0)),
                "need": int(ev.get("need", 0)),
                "cash": int(ev.get("cash", 0)),
                "loan": int(ev.get("loan", 0)),
                "available": int(ev.get("available", 0)),
            })
        elif phase == "fleet_built":
            bucket["fleet_built"].append({
                "mode": ev.get("mode", "unknown"),
                "line": int(ev.get("line", -1)),
                "added": int(ev.get("added", 0)),
                "total": int(ev.get("total", 0)),
                "cash_after": int(ev.get("cash_after", 0)),
            })

    yearly_metrics = {}
    for yr, b in sorted(years_data.items()):
        avails = [m["available"] for m in b["treasury_monthly"]]
        cashes = [m["cash"] for m in b["treasury_monthly"]]
        ann = b["treasury_annual"] or {}

        # Projects built
        built_by_mode = defaultdict(lambda: {"count": 0, "cost": 0, "profit": 0, "rois": []})
        for p in b["projects_built"]:
            entry = built_by_mode[p["mode"]]
            entry["count"] += 1
            entry["cost"] += p["cost"]
            entry["profit"] += p["profit"]
            entry["rois"].append(p["roi"])

        built_summary = {
            "total_count": len(b["projects_built"]),
            "total_cost": sum(p["cost"] for p in b["projects_built"]),
            "by_mode": {
                m: {
                    "count": data["count"],
                    "cost": data["cost"],
                    "profit": data["profit"],
                    "mean_roi": round(statistics.mean(data["rois"]), 1) if data["rois"] else 0,
                } for m, data in built_by_mode.items()
            }
        }

        # Refused cash
        refused_by_mode = defaultdict(lambda: {"count": 0, "rois": [], "needs": []})
        for r in b["projects_refused_cash"]:
            entry = refused_by_mode[r["mode"]]
            entry["count"] += 1
            entry["rois"].append(r["roi"])
            entry["needs"].append(r["need"])

        refused_summary = {
            "total_count": len(b["projects_refused_cash"]),
            "by_mode": {
                m: {
                    "count": data["count"],
                    "mean_roi": round(statistics.mean(data["rois"]), 1) if data["rois"] else 0,
                    "mean_need": round(statistics.mean(data["needs"]), 1) if data["needs"] else 0,
                } for m, data in refused_by_mode.items()
            }
        }

        # Fleet built
        fleet_summary = {
            "refill_events": len(b["fleet_built"]),
            "vehicles_added": sum(f["added"] for f in b["fleet_built"]),
        }

        # Lines profit
        prof_by_mode = defaultdict(lambda: {"lines": 0, "vehs": 0, "profit": 0, "rev": 0})
        for lp in b["line_profits"]:
            entry = prof_by_mode[lp["mode"]]
            entry["lines"] += 1
            entry["vehs"] += lp["vehs"]
            entry["profit"] += lp["profit"]
            entry["rev"] += lp["rev"]

        lines_summary = b["line_profit_summary"] or {}
        lines_summary["by_mode"] = dict(prof_by_mode)

        yearly_metrics[yr] = {
            "treasury": {
                "available_mean": round(statistics.mean(avails), 1) if avails else ann.get("available", 0),
                "available_min": min(avails) if avails else ann.get("available", 0),
                "available_max": max(avails) if avails else ann.get("available", 0),
                "cash_mean": round(statistics.mean(cashes), 1) if cashes else ann.get("cash", 0),
                "end_cash": ann.get("cash", cashes[-1] if cashes else 0),
                "end_loan": ann.get("loan", 0),
                "end_available": ann.get("available", avails[-1] if avails else 0),
                "end_company_value": ann.get("company_value", 0),
                "months_recorded": len(avails),
            },
            "projects_built": built_summary,
            "projects_refused_cash": refused_summary,
            "fleet_built": fleet_summary,
            "lines_summary": lines_summary,
        }

    return yearly_metrics


def aggregate_across_seeds(seeds_metrics):
    years = sorted({yr for sm in seeds_metrics.values() for yr in sm})
    cum = []
    for yr in years:
        avail_means = [sm[yr]["treasury"]["available_mean"] for sm in seeds_metrics.values() if yr in sm]
        built_counts = [sm[yr]["projects_built"]["total_count"] for sm in seeds_metrics.values() if yr in sm]
        built_costs = [sm[yr]["projects_built"]["total_cost"] for sm in seeds_metrics.values() if yr in sm]
        refused_counts = [sm[yr]["projects_refused_cash"]["total_count"] for sm in seeds_metrics.values() if yr in sm]
        fleet_added = [sm[yr]["fleet_built"]["vehicles_added"] for sm in seeds_metrics.values() if yr in sm]

        prof_sums = [sm[yr]["lines_summary"].get("prof_sum", 0) for sm in seeds_metrics.values() if yr in sm]
        rev_sums = [sm[yr]["lines_summary"].get("rev_sum", 0) for sm in seeds_metrics.values() if yr in sm]
        loss_counts = [sm[yr]["lines_summary"].get("loss_lines", 0) for sm in seeds_metrics.values() if yr in sm]
        prof_counts = [sm[yr]["lines_summary"].get("prof_lines", 0) for sm in seeds_metrics.values() if yr in sm]

        cum.append({
            "year": yr,
            "mean_available_capital": round(statistics.mean(avail_means), 1) if avail_means else 0,
            "projects_built_sum": sum(built_counts),
            "projects_built_mean_per_seed": round(statistics.mean(built_counts), 2) if built_counts else 0,
            "projects_capital_sum": sum(built_costs),
            "projects_refused_cash_sum": sum(refused_counts),
            "fleet_vehicles_added_sum": sum(fleet_added),
            "total_line_profit_sum": sum(prof_sums),
            "total_line_revenue_sum": sum(rev_sums),
            "loss_lines_sum": sum(loss_counts),
            "profitable_lines_sum": sum(prof_counts),
        })
    return cum


def keep_c50(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}

    stnn = chunks.get("STNN", {})
    stations_list = stnn.values() if isinstance(stnn, dict) else stnn
    ratings = [g["rating"] for s in stations_list for g in s.get("goods", []) if g.get("rating", 0) > 0]
    med_rating = statistics.median(ratings) if ratings else 0

    output = row.get("output", "")
    events = parse_events(output)
    metrics = process_c50_events(events)

    # Free heavy objects immediately
    row.clear()

    return ({
        "arm": ARM,
        "seed": row.get("experiment", {}).get("seed", 0) if "experiment" in row else 0,
        "company_value": last_closed.get("company_value", 0),
        "performance_history": last_closed.get("performance_history", 0),
        "median_station_rating": med_rating,
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "yearly_metrics": metrics,
    },)


def selftest():
    sample_log = """
[script:0] OPEX 1970-1-1 C50_CHRONO phase=treasury_monthly year=1970 month=0 cash=100000 loan=100000 available=95000
[script:0] OPEX 1970-2-1 C50_CHRONO phase=treasury_monthly year=1970 month=1 cash=90000 loan=100000 available=85000
[script:0] OPEX 1970-3-15 C50_CHRONO phase=project_built mode=road rank=0 line=1 cost=20000 profit=10000 roi=500 cash_after=70000 available=65000
[script:0] OPEX 1970-4-10 C50_CHRONO phase=refused_cash mode=rail rank=1 cost=80000 profit=25000 roi=312 need=80000 cash=70000 loan=100000 available=65000
[script:0] OPEX 1970-5-2 C50_CHRONO phase=fleet_built mode=road line=1 added=2 total=4 cash_after=66000
[script:0] OPEX 1970-12-31 C50_CHRONO phase=line_profit year=1970 line=1 mode=road cargo=PASS vehs=4 profit=8500 run_cost=1500 rev=10000 pred_profit=10000 roi=500 age=0
[script:0] OPEX 1970-12-31 C50_CHRONO phase=line_profit_summary year=1970 lines=1 prof_sum=8500 rev_sum=10000 prof_lines=1 loss_lines=0
[script:0] OPEX 1970-12-31 C50_CHRONO phase=treasury_annual year=1970 cash=66000 loan=100000 max_loan=300000 available=261000 company_value=125000 lines=1
"""
    events = parse_events(sample_log)
    assert len(events) == 8, f"Expected 8 events, got {len(events)}"
    res = process_c50_events(events)
    assert 1970 in res, "Year 1970 missing from metrics"
    m70 = res[1970]
    assert m70["treasury"]["months_recorded"] == 2
    assert m70["treasury"]["available_min"] == 85000
    assert m70["projects_built"]["total_count"] == 1
    assert m70["projects_built"]["by_mode"]["road"]["cost"] == 20000
    assert m70["projects_refused_cash"]["total_count"] == 1
    assert m70["fleet_built"]["vehicles_added"] == 2
    assert m70["lines_summary"]["prof_sum"] == 8500
    print("selftest OK: all 8 events parsed and verified.")


def main():
    parser = argparse.ArgumentParser(description="Diagnostic C50 : sonde chronologique legere")
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--out", type=Path, default=Path("results/diag_c50_chronology_probe_6y_5seeds.json"))
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()

    enable_savegame_cleanup()
    arms = build_arms([ARM])

    print(f"Lancement du diagnostic C50 sur {len(args.seeds)} graines x {args.years} ans...")

    exps = experiments(arms, args.seeds, args.years, repeats=1, starting_year=1970)

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=min(len(args.seeds), 3),
        result_processor=keep,
        experiments=exps,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    summary = summarise(rows)

    results_by_seed = {}
    for record in summary:
        events = parse_events(record.get("openttd_output", ""))
        metrics = process_c50_events(events)
        seed = record["seed"]
        results_by_seed[seed] = metrics

    cumulative = aggregate_across_seeds(results_by_seed)

    failed = [{key: value for key, value in record.items() if key != "openttd_output"}
              for record in summary if not record["run_ok"]]

    payload = {
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "arm": ARM,
        "by_seed": results_by_seed,
        "cumulative": cumulative,
        "failed_runs": failed,
        "failed_run_count": len(failed),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomically(args.out, payload)
    print(f"Resultats C50 enregistres dans {args.out}")


if __name__ == "__main__":
    main()
