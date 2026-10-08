"""Fixed-anchor, exact twelve-month future labels; no partial-year imputation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from analyse_station_supply import metrics
from station_supply import supply_intervals
from station_supply_bounds import bounded_intervals

PREDICTORS = ("b9_own", "b9_visible")


def annual_cases(analysis, bounded=False, surviving_growth=False):
    if surviving_growth and not bounded:
        raise ValueError("surviving growth is a separate bounded diagnostic")
    snapshots = analysis["snapshots"]
    cargo = analysis["pass_cargo"]
    intervals = []
    for a, b in zip(snapshots, snapshots[1:]):
        def decoder(previous, current):
            return bounded_intervals(previous, current, surviving_growth=surviving_growth) if bounded else supply_intervals(previous, current)
        intervals.append({r["station"]: r for r in decoder(
            a["station_supply"], b["station_supply"])
            if r.get("cargo") == cargo})
    cases, excluded = [], Counter()
    # Same fixed anchors on all seeds. First year is never a future label.
    for index in range(12, len(snapshots), 12):
        anchor = snapshots[index]
        for key, row in anchor["station_sources"].items():
            if row["owner"] != 0 or not row["airport"]:
                continue
            station = int(key)
            if index + 12 >= len(snapshots):
                excluded["incomplete_future_horizon"] += 1
                continue
            days = snapshots[index + 12]["economy_date"] - anchor["economy_date"]
            if days not in (365, 366):
                excluded["not_twelve_month_horizon"] += 1
                continue
            future = [period.get(station) for period in intervals[index:index + 12]]
            if any(r is None or not r["bounded" if bounded else "exact"] for r in future):
                excluded["missing_or_inexact_future_interval"] += 1
                continue
            if sum(r["period_days"] for r in future) != days:
                raise ValueError("noncontiguous annual future label")
            if any(row.get(p + "_monthly") is None for p in PREDICTORS):
                excluded["missing_anchor_forecast"] += 1
                continue
            # Station coordinates/build identity remain unchanged in each exact
            # interval; graph compression/merge is excluded even if cargo exists.
            label = ({"actual_lower": sum(r["lower"] for r in future),
                      "actual_upper": sum(r["upper"] for r in future)} if bounded else
                     {"actual": sum(r["arrivals"] for r in future)})
            cases.append({"game_id": analysis["game_id"], "seed": analysis["seed"],
                          "station": station, "start_date": anchor["economy_date"],
                          "end_date": snapshots[index + 12]["economy_date"],
                          "period_days": days, "future_exact_intervals": sum(r["exact"] for r in future),
                          "surviving_growth_intervals": sum(r.get("continuity") == "surviving_graph_growth" for r in future),
                          **label,
                          "shared_at_anchor": row["b9_visible_monthly"] < row["b9_own_monthly"],
                          **{p: row[p + "_monthly"] * days / 30.4 for p in PREDICTORS}})
    return cases, dict(excluded)


def bounds_metrics(cases):
    lower = sum(r["actual_lower"] for r in cases)
    upper = sum(r["actual_upper"] for r in cases)
    output = {"n": len(cases), "stations": len({(r["game_id"], r["station"]) for r in cases}),
              "actual_lower": lower, "actual_upper": upper, "predictors": {}}
    if lower <= 0:
        return output
    for p in PREDICTORS:
        min_error = sum(max(r["actual_lower"]-r[p], 0, r[p]-r["actual_upper"]) for r in cases)
        max_error = sum(max(abs(r[p]-r["actual_lower"]), abs(r[p]-r["actual_upper"])) for r in cases)
        predicted = sum(r[p] for r in cases)
        output["predictors"][p] = {"wape_lower": min_error/upper, "wape_upper": max_error/lower,
                                    "bias_pct_lower": 100*(predicted/upper-1),
                                    "bias_pct_upper": 100*(predicted/lower-1)}
    deltas = []
    for r in cases:
        # Absolute-error difference is piecewise linear. Evaluate every corner.
        points = [r["actual_lower"], r["actual_upper"]] + [r[p] for p in PREDICTORS
                  if r["actual_lower"] <= r[p] <= r["actual_upper"]]
        deltas.append([abs(r["b9_visible"]-a)-abs(r["b9_own"]-a) for a in points])
    output["absolute_error_delta_lower"] = sum(min(d) for d in deltas)
    output["absolute_error_delta_upper"] = sum(max(d) for d in deltas)
    output["visible_better_for_every_admissible_label"] = output["absolute_error_delta_upper"] < 0
    return output


def summarize_bounds(analyses, surviving_growth=False):
    cases, exclusions = [], {}
    for a in analyses:
        rows, excluded = annual_cases(a, bounded=True, surviving_growth=surviving_growth)
        cases.extend(rows)
        exclusions[a["game_id"]] = excluded
    seeds = sorted({a["seed"] for a in analyses})
    return {"kind": "secondary_bounded_future_year_not_exact_gate",
            "surviving_growth": surviving_growth,
            "seeds": seeds, "cases": cases, "exclusions": exclusions,
            "metrics": bounds_metrics(cases),
            "by_seed": {str(s): bounds_metrics([r for r in cases if r["seed"] == s]) for s in seeds},
            "precision_gate_pass": False, "adoption": False,
            "limitation": "compression bounds; no exact annual label, no route profit qualification"}


def summarize(analyses):
    cases, exclusions = [], {}
    for a in analyses:
        rows, excluded = annual_cases(a)
        cases.extend(rows)
        exclusions[a["game_id"]] = excluded
    seeds = sorted({a["seed"] for a in analyses})
    by_seed = {str(seed): {p: metrics([r for r in cases if r["seed"] == seed], p)
                           for p in PREDICTORS} for seed in seeds}
    total = {p: metrics(cases, p) for p in PREDICTORS}
    def improved(m):
        return m["b9_visible"]["wape"] is not None and m["b9_own"]["wape"] is not None \
            and m["b9_visible"]["wape"] < m["b9_own"]["wape"]
    passed = improved(total) and all(improved(m) for m in by_seed.values())
    return {"kind": "exact_future_year_core_capture_not_economic_qualification",
            "seeds": seeds, "cases": cases, "exclusions": exclusions,
            "metrics": total, "by_seed": by_seed,
            "by_shared_at_anchor": {str(shared): {p: metrics(
                [r for r in cases if r["shared_at_anchor"] == shared], p)
                for p in PREDICTORS} for shared in (False, True)},
            "precision_gate_pass": passed, "adoption": False,
            "limitation": "station capture at own observed rating; not projected C121 rating, route profit, or reinforcement marginal"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analyses", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--bounds", action="store_true")
    parser.add_argument("--surviving-growth", action="store_true")
    args = parser.parse_args()
    if args.surviving_growth and not args.bounds:
        parser.error("--surviving-growth requires --bounds")
    analyses = [json.loads(p.read_text(encoding="utf8")) for p in args.analyses]
    report = summarize_bounds(analyses, surviving_growth=args.surviving_growth) if args.bounds else summarize(analyses)
    report["input_sha256"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in args.analyses}
    report["decoder_sha256"] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                for name in ("analyse_station_source_year.py", "station_supply_bounds.py", "station_supply.py")}
    with args.out.open("x", encoding="utf8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({k: report[k] for k in ("metrics", "by_seed", "precision_gate_pass")}, indent=2))
