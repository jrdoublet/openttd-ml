"""Validate passenger throughput forecasts without changing AI decisions.

Reuse C117 measured legs and the shared parser. Forecasts use only past
windows; a full aircraft is censored demand, never a complete demand label.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median

from harness import parse_fields
from diag_c117_air_throughput import enrich

TRAIN_SEEDS = {42, 100, 7, 999, 2026}
TEST_SEEDS = {1, 17, 73, 314, 512}
ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0)


def numeric_fields(text):
    fields = parse_fields(text)
    for key, value in list(fields.items()):
        try:
            fields[key] = float(value) if "." in value or "e" in value.lower() else int(value)
        except ValueError:
            pass
    return fields


def measured_rate(events):
    days = sum(e["period_days"] for e in events)
    return sum(e["pax"] for e in events) * 30.4 / days if days > 0 else None


def quality(event):
    required = ("period_days", "pax", "samples", "live_avg", "live_last", "engine",
                "mixed_engine_samples", "invalid_order_samples", "unobserved_transitions")
    if any(not isinstance(event.get(k), (int, float)) or not math.isfinite(event[k]) for k in required):
        return False
    if not 20 <= event["period_days"] <= 40 or event["pax"] < 0:
        return False
    if event["samples"] < event["period_days"] / 4 or event["live_last"] < 1:
        return False
    if any(event.get(k, -1) != 0 for k in ("mixed_engine_samples", "invalid_order_samples", "unobserved_transitions", "engine_changes")):
        return False
    return abs(event["live_avg"] - event["live_last"]) < 1e-6


def metrics(rows, field):
    rows = [r for r in rows if isinstance(r.get(field), (int, float)) and math.isfinite(r[field])]
    if not rows:
        return {"n": 0, "wape": None, "bias_pct": None}
    total = sum(r["actual"] for r in rows)
    errors = [r[field] - r["actual"] for r in rows]
    return {"n": len(rows), "lines": len({(r["seed"], r["line"]) for r in rows}),
        "seeds": sorted({r["seed"] for r in rows}),
        "wape": sum(abs(e) for e in errors) / total if total > 0 else None,
        "bias_pct": 100 * sum(errors) / total if total > 0 else None,
        "mae_pax_month": mean(abs(e) for e in errors), "median_error_pax_month": median(errors)}


def forecast_cases(events, routes=None, exploratory_partial=False):
    groups = defaultdict(dict)
    for e in events:
        groups[(e["seed"], e["line"])][int(e["age_bucket"])] = e
    cases = []
    excluded = Counter()
    for (seed, line), months in groups.items():
        for anchor in (24, 36, 48, 60, 72, 84, 96):
            # Bucket anchor is the first future window. All features precede it.
            window = [months.get(i) for i in range(anchor - 12, anchor + 12)]
            if any(e is None for e in window):
                excluded["missing_window"] += 1
                continue
            if not exploratory_partial and not all(quality(e) for e in window):
                excluded["unqualified_measurement"] += 1
                continue
            if len({(e["live_last"], e["engine"]) for e in window}) != 1:
                excluded["fleet_or_engine_changed"] += 1
                continue
            past, future = window[:12], window[12:]
            recent_90, recent_180 = past[-3:], past[-6:]
            if exploratory_partial:
                past, future = [e for e in past if quality(e)], [e for e in future if quality(e)]
                if min(len(past), len(future)) < 6:
                    excluded["insufficient_qualified_months"] += 1
                    continue
            elif not all(330 <= sum(e["period_days"] for e in part) <= 390 for part in (past, future)):
                excluded["incomplete_duration"] += 1
                continue
            last = past[-1]
            baseline = last.get("c121_actual_pax_pm")
            initial_match = (last.get("c121_actual_n") == last["live_last"]
                             and last.get("build_engine") == last["engine"])
            if not isinstance(baseline, (int, float)) or baseline < 0:
                excluded["missing_build_prediction"] += 1
                continue
            row = {"seed": seed, "line": line, "anchor": anchor, "arm": last.get("arm"),
                "actual": measured_rate(future), "model_build": baseline,
                "initial_fleet_match": initial_match,
                "observed_90": measured_rate(recent_90) if all(quality(e) for e in recent_90) else None,
                "observed_180": measured_rate(recent_180) if all(quality(e) for e in recent_180) else None,
                "observed_360": measured_rate(past),
                "past_capacity_censored": any(enrich(e)["limit_class"] == "capacity_limited" for e in past),
                "future_demand_limited": all(enrich(e)["limit_class"] == "demand_limited" for e in future),
                "live": last["live_last"], "engine": last["engine"],
                "future_pax_total": sum(e["pax"] for e in future),
                "future_days": sum(e["period_days"] for e in future)}
            row["past_qualified_months"] = len(past)
            row["future_qualified_months"] = len(future)
            if routes is not None:
                # Yearly C98 snapshots describe hub sharing; no future routes in predictors.
                relevant = routes.get((seed, line), [])
                start = past[0].get("date", "")
                end = future[-1].get("date", "")
                counts = [(r.get("live_routes_a"), r.get("live_routes_b"))
                          for r in relevant if start <= r["date"] <= end]
                row["hub_growth"] = "unknown" if len(counts) < 2 else (
                    "stable" if len(set(counts)) == 1 else "changed")
            cases.append(row)
    return cases, dict(excluded)


def fit_blend(training):
    """Train arm-specific observation weight; evaluate unchanged on test seeds."""
    weights = {}
    for arm in ("newpair", "hubsite", "hubhub"):
        rows = [r for r in training if r["arm"] == arm and r["initial_fleet_match"]]
        if not rows:
            weights[arm] = None
            continue
        weights[arm] = min(ALPHAS, key=lambda a: sum(abs(
            a * r["observed_360"] + (1 - a) * r["model_build"] - r["actual"]) for r in rows))
    return weights


def mature_description(events):
    """Descriptive exposure only: qualified months, initial fleet unchanged."""
    groups = defaultdict(list)
    for e in events:
        if (quality(e) and e["age_bucket"] >= 24
                and e.get("c121_actual_n") == e["live_last"]
                and e.get("build_engine") == e["engine"]
                and isinstance(e.get("c121_actual_pax_pm"), (int, float))
                and e["c121_actual_pax_pm"] >= 0):
            groups[(e["seed"], e["line"])].append(e)
    rows = []
    for (seed, line), months in groups.items():
        days = sum(e["period_days"] for e in months)
        if days < 180:
            continue
        rows.append({"seed": seed, "line": line, "arm": months[0]["arm"],
            "actual": measured_rate(months),
            "model_build": sum(e["c121_actual_pax_pm"] * e["period_days"] for e in months) / days,
            "qualified_months": len(months), "qualified_days": days,
            "demand_limited": all(enrich(e)["limit_class"] == "demand_limited" for e in months)})
    return {"all": metrics(rows, "model_build"),
        "demand_limited": metrics([r for r in rows if r["demand_limited"]], "model_build"),
        "by_arm": {a: metrics([r for r in rows if r["arm"] == a], "model_build")
                   for a in ("newpair", "hubsite", "hubhub")}, "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bench", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--exploratory-partial", action="store_true",
                        help="Post hoc exploration: at least six qualified months per year; not full-year validation")
    args = parser.parse_args()
    data = json.loads(args.bench.read_text(encoding="utf-8"))
    assert data["campaign_id"] == "c121_pax_flux_diag_10x10_20261007"
    assert data["years"] == 10 and set(data["seeds"]) == TRAIN_SEEDS | TEST_SEEDS
    assert len(data["games"]) == 10 and all(g["game_ok"] and g["game_status"] == "complete" for g in data["games"])
    manifest = args.bench.with_suffix(".manifest.json")
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == data["manifest_sha256"]
    events = {}
    builds = {}
    routes = defaultdict(list)
    log_hashes = {}
    log_dir = args.bench.parent / "bench_engine"
    logs = sorted(log_dir.glob("c121_pax_flux_current_seed*_r0.log"))
    assert len(logs) == 10
    import re
    for log in logs:
        seed = int(re.search(r"_seed(\d+)_r0", log.name)[1])
        log_hashes[log.name] = hashlib.sha256(log.read_bytes()).hexdigest()
        for text in log.read_text(encoding="utf-8").splitlines():
            if "[0] [I]" not in text:
                continue
            if "C121_BUILD " in text:
                b = numeric_fields(text.split("C121_BUILD ", 1)[1])
                builds[(seed, b["line"])] = b
            elif "C117_AIR_THROUGHPUT " in text:
                e = numeric_fields(text.split("C117_AIR_THROUGHPUT ", 1)[1])
                stamp = re.search(r"OPEX (\d+)-(\d+)-(\d+) C117", text)
                if stamp:
                    e["date"] = "-".join(f"{int(v):02d}" for v in stamp.groups())
                e["seed"] = seed
                events[(seed, e["line"], e["age_bucket"])] = e
            elif "C98_AIR_REALIZED " in text:
                r = numeric_fields(text.split("C98_AIR_REALIZED ", 1)[1])
                r["date"] = f'{r["year"]:04d}-01-01'
                routes[(seed, r["line"])].append(r)
    # Normal builds omit rich line scalars to keep Save() bounded. The original
    # C121_BUILD event is the exact source, never a reconstruction from the future.
    for e in events.values():
        b = builds.get((e["seed"], e["line"]))
        if b is not None:
            e["c121_actual_pax_pm"] = b.get("actual_pax")
            e["c121_actual_n"] = b.get("actual_n")
    cases, excluded = forecast_cases(list(events.values()), routes, args.exploratory_partial)
    train = [r for r in cases if r["seed"] in TRAIN_SEEDS]
    test = [r for r in cases if r["seed"] in TEST_SEEDS]
    weights = fit_blend(train)
    for row in cases:
        alpha = weights.get(row["arm"])
        row["blend"] = row["observed_360"] if alpha is None else (
            alpha * row["observed_360"] + (1 - alpha) * row["model_build"])
    fields = ("model_build", "observed_90", "observed_180", "observed_360", "blend")
    matched = [r for r in test if r["initial_fleet_match"]]
    summary = {"campaign": data["campaign_id"], "bundle_sha256": data["source_bundle_sha256"],
        "manifest_sha256": data["manifest_sha256"], "logs_sha256": log_hashes,
        "unique_windows": len(events), "quality_windows": sum(quality(e) for e in events.values()),
        "excluded_forecasts": excluded, "training_cases": len(train), "test_cases": len(test),
        "analysis_mode": "post_hoc_partial_months" if args.exploratory_partial else "preregistered_complete_years",
        "mature_descriptive_exposure": mature_description(list(events.values())),
        "blend_observation_weights_trained": weights,
        "test_initial_fleet_model_comparable": {f: metrics(matched, f) for f in fields},
        "test_all_stable_fleets": {f: metrics(test, f) for f in fields if f.startswith("observed")},
        "by_arm_initial_match": {arm: {f: metrics([r for r in matched if r["arm"] == arm], f)
            for f in fields} for arm in weights},
        "by_seed_initial_match": {str(s): {f: metrics([r for r in matched if r["seed"] == s], f)
            for f in fields} for s in sorted(TEST_SEEDS)},
        "test_demand_limited_initial_match": {f: metrics([r for r in matched if r["future_demand_limited"]], f)
            for f in fields},
        "by_hub_growth_initial_match": {kind: {f: metrics([r for r in matched if r.get("hub_growth") == kind], f)
            for f in fields} for kind in ("stable", "changed", "unknown")},
        "cases": cases,
        "limits": "Forecast observed transport, not unlimited demand. Stable surviving fleets are selected. Probe perturbation, unseen rivals, cargo losses and future network growth are not causally separated."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("cases", "logs_sha256", "by_arm_initial_match", "by_seed_initial_match")}, indent=2))


if __name__ == "__main__":
    main()
