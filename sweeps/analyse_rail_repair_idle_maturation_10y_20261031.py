"""Decision and physical audit for pre-registered RAIL-IDLE maturation / B.

Require whole games, no forced OD-to-service matching, and no inferred profit
for assets not unambiguously identified. The 5-seed pilot is selected on
observed 1974 successful builds: its statistics are descriptive ONLY.
"""

import argparse
import hashlib
import json
import re
import statistics
from pathlib import Path

from paired_statistics import exact_wilcoxon_signed_rank_p, bootstrap_mean_ci

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = {
    100: {"src": 46958, "dst": 29140, "cargo": "1", "cargo_name": "COAL"},
    512: {"src": 31408, "dst": 39017, "cargo": "8", "cargo_name": "IORE"},
    12345: {"src": 46126, "dst": 50747, "cargo": "6", "cargo_name": "GRAI"},
    54321: {"src": 12108, "dst": 23443, "cargo": "6", "cargo_name": "GRAI"},
    65537: {"src": 42142, "dst": 29270, "cargo": "6", "cargo_name": "GRAI"},
}


def event_date(line):
    match = re.search(r"\b(19\d\d)-(\d{1,2})-(\d{1,2})\b", line)
    return tuple(int(group) for group in match.groups()) if match else None


def event_int(line, name):
    match = re.search(r"\b" + re.escape(name) + r"=(-?\d+)\b", line)
    return int(match.group(1)) if match else None


def manhattan(a, b):
    return abs(a % 256 - b % 256) + abs(a // 256 - b // 256)


def match_service(telemetry, target):
    """Conservative proximity+cargo matching; reject nearby competitor."""
    if not isinstance(telemetry, dict) or not telemetry.get("ok"):
        return {"status": "missing_telemetry"}
    candidates = []
    for service in telemetry["lines"]:
        if service.get("mode") != "rail" or len(service.get("ordered_station_tiles") or []) != 2:
            continue
        if target["cargo"] not in (service.get("cargo_types") or []):
            continue
        tiles = service["ordered_station_tiles"]
        if any(not isinstance(tile, int) for tile in tiles):
            continue
        distance = min(
            manhattan(tiles[0], target["src"]) + manhattan(tiles[1], target["dst"]),
            manhattan(tiles[0], target["dst"]) + manhattan(tiles[1], target["src"]),
        )
        candidates.append((distance, service))
    candidates.sort(key=lambda pair: pair[0])
    if not candidates or candidates[0][0] > 20:
        return {"status": "not_observed", "best_distance": candidates[0][0] if candidates else None}
    if len(candidates) > 1 and candidates[1][0] - candidates[0][0] < 5:
        return {"status": "ambiguous", "distances": [p[0] for p in candidates[:2]]}
    distance, service = candidates[0]
    return {
        "status": "matched", "distance_tiles": distance,
        "station_ids": service["station_ids"],
        "station_tiles": service["ordered_station_tiles"],
        "vehicle_ids": service["vehicle_ids"],
        "vehicles": service["vehicles"],
        "profit_this_year_gbp": service["profit_this_year_gbp"],
        "profit_last_year_gbp": service["profit_last_year_gbp"],
        "vehicle_value_gbp": service["vehicle_value"],
    }


def paired_metrics(payload, expected_seeds):
    seeds = payload["seeds"]
    if seeds != list(expected_seeds):
        raise AssertionError(("seeds", seeds, expected_seeds))
    if len(payload["arms"]) != 2:
        raise AssertionError("Require exactly two arms")
    a, b = payload["arms"]
    by = {(r["arm"], r["seed"], r["repeat"]): r for r in payload["summary"]}
    if payload.get("failed_runs") or len(by) != 2 * len(seeds):
        raise AssertionError("Unhealthy or incomplete games")
    for seed in seeds:
        for arm in (a, b):
            rec = by[(arm, seed, 0)]
            if not (rec["run_ok"] and rec["n_savegames"] == 120 and
                    rec["last_date"] == "1979-12-01" and
                    rec["profit_year_coverage"] == "complete" and
                    rec.get("physical_ok", True)):
                raise AssertionError(("invalid run", seed, arm, rec.get("failure_reason")))
    refs = [by[(a, seed, 0)] for seed in seeds]
    variants = [by[(b, seed, 0)] for seed in seeds]
    deltas = [float(v["profit_year"]) - float(r["profit_year"])
              for r, v in zip(refs, variants)]
    ref_avg = statistics.mean(r["profit_year"] for r in refs)
    var_avg = statistics.mean(v["profit_year"] for v in variants)
    value_avg = statistics.mean(r["company_value"] for r in refs)
    value_variant = statistics.mean(v["company_value"] for v in variants)
    ci = bootstrap_mean_ci(deltas, resamples=20000, seed=0)
    result = {
        "n_pairs": len(seeds), "ref_profit_year_mean": ref_avg,
        "variant_profit_year_mean": var_avg, "delta_mean": statistics.mean(deltas),
        "delta_median": statistics.median(deltas),
        "delta_pct": 100 * (var_avg / ref_avg - 1) if ref_avg else None,
        "wins": sum(d > 0 for d in deltas),
        "losses": sum(d < 0 for d in deltas),
        "ties": sum(d == 0 for d in deltas),
        "wilcoxon_exact_p": exact_wilcoxon_signed_rank_p(deltas),
        "bootstrap_ci95": list(ci), "bootstrap_replays": 20000,
        "value_ref_mean": value_avg, "value_variant_mean": value_variant,
        "value_ratio": value_variant / value_avg if value_avg else None,
        "by_seed": [
            {"seed": seed, "ref": ref["profit_year"],
             "on": var["profit_year"], "delta": delta,
             "ref_value": ref["company_value"], "on_value": var["company_value"]}
            for seed, ref, var, delta in zip(seeds, refs, variants, deltas)
        ],
    }
    return result


def run_pilot(payload, source_hash):
    metrics = paired_metrics(payload, tuple(ORIGINAL))
    ref, on = payload["arms"]
    series = {(r["run"][0], r["run"][1], r["date"]): r
              for r in payload["series"]}
    summaries = {(r["arm"], r["seed"]): r for r in payload["summary"]}
    physical = []
    for seed, target in ORIGINAL.items():
        logs = (summaries[(on, seed)].get("openttd_output") or "").splitlines()
        lines = [line for line in logs if " RAIL_BUILD " in line and
                 "site_repair=1" in line and event_date(line) is not None and
                 event_date(line)[0] <= 1974 and
                 event_int(line, "src") == target["src"] and
                 event_int(line, "dst") == target["dst"] and
                 "cargo=" + target["cargo_name"] in line]
        assert len(lines) <= 1, (seed, lines)
        build = lines[0] if lines else None
        snapshots = {}
        for year in range(1974, 1980):
            date = f"{year}-12-01"
            record = series[(on, seed, date)]
            snapshots[str(year)] = match_service(record.get("line_telemetry"), target)
        # A service is attributed only if it was present after the original
        # build and matches the target; an identically routed service in the
        # reference prohibits claiming exclusivity/causality.
        ref_snapshots = {}
        for year in (1974, 1975, 1979):
            ref_snapshots[str(year)] = match_service(
                series[(ref, seed, f"{year}-12-01")].get("line_telemetry"), target
            )
        mature = [snapshots[str(year)] for year in range(1976, 1980)
                  if snapshots[str(year)]["status"] == "matched"]
        physical.append({
            "seed": seed, **target,
            "reproduced_site_build_1974": build is not None,
            "build_event": build.split(" OPEX ", 1)[-1] if build else None,
            "pred_profit_annual": event_int(build, "pred_profit") if build else None,
            "quoted_cost": event_int(build, "cost") if build else None,
            "on_annual_services": snapshots,
            "ref_service_checks": ref_snapshots,
            "matched_any_1975_1979": any(snapshots[str(y)]["status"] == "matched"
                                         for y in range(1975, 1980)),
            "mature_profit_positive": any(s["profit_this_year_gbp"] > 0 for s in mature),
            "mature_profit_observed": len(mature),
        })

    # Descriptive, overlapping 12-month profit metrics, not independent tests.
    by_year = {}
    for year in range(1970, 1980):
        date = f"{year}-12-01"
        ref_series = [series[(ref, seed, date)] for seed in ORIGINAL]
        on_series = [series[(on, seed, date)] for seed in ORIGINAL]
        by_year[str(year)] = {
            "ref_mean": statistics.mean(r["profit_year"] for r in ref_series),
            "on_mean": statistics.mean(r["profit_year"] for r in on_series),
            "delta_mean": statistics.mean(v["profit_year"] - r["profit_year"]
                                          for r, v in zip(ref_series, on_series)),
        }
    enough_rebuilt = sum(
        p["reproduced_site_build_1974"] and
        (p["on_annual_services"]["1975"]["status"] == "matched" or
         p["on_annual_services"]["1974"]["status"] == "matched")
        for p in physical
    ) >= 3
    positive_mature = sum(p["mature_profit_positive"] for p in physical) >= 3
    positive_global = metrics["delta_mean"] > 0 and metrics["value_ratio"] >= 0.95
    checks = {
        "at_least_three_1974_site_builds_with_unambiguous_service": enough_rebuilt,
        "at_least_three_mature_positive_fleet_profits": positive_mature,
        "positive_company_profit_delta_and_value_ratio_ge_0_95": positive_global,
    }
    return {
        "stage": "pilot", "source_sha256": source_hash,
        "metrics": metrics, "physical": physical,
        "by_year": by_year, "promotion_checks": checks,
        "promising_launch_B": all(checks.values()),
        "economic_interpretation": "Exploratory selected-seed and instrumented; never override failed A",
    }


def run_b(payload, source_hash):
    from bench_v2 import SEEDS
    metrics = paired_metrics(payload, SEEDS)
    checks = {
        "bootstrap_ci95_upper_ge_zero": metrics["bootstrap_ci95"][1] >= 0,
        "company_value_ratio_ge_0_95": metrics["value_ratio"] >= 0.95,
    }
    return {
        "stage": "b", "source_sha256": source_hash, "metrics": metrics,
        "checks": checks,
        "verdict": "B_EXPLORATORY_NON_EROSION_PASS" if all(checks.values())
        else "B_EXPLORATORY_NON_EROSION_NO_GO",
        "warning": "Prior rail-only 40x5 A failed. This B is non-erosion diagnostics, never adoption qualification.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("pilot", "b"))
    args = parser.parse_args()
    source = ROOT / f"results/rail_repair_idle_{args.stage}_10y_20261031.json"
    content = source.read_bytes()
    payload = json.loads(content)
    digest = hashlib.sha256(content).hexdigest()
    output = run_pilot(payload, digest) if args.stage == "pilot" else run_b(payload, digest)
    dest = ROOT / f"docs/rail_repair_idle_{args.stage}_10y_20261031_evidence.json"
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print("STAGE", args.stage, "SOURCE", digest, "PAIRS", output["metrics"]["n_pairs"])
    print("MEAN DELTA", output["metrics"]["delta_mean"], "CI95",
          output["metrics"]["bootstrap_ci95"], "VALUE",
          output["metrics"]["value_ratio"])
    print("PROMOTION" if args.stage == "pilot" else "VERDICT",
          output.get("promotion_checks", output.get("checks")),
          output.get("promising_launch_B", output.get("verdict")))
    if args.stage == "pilot":
        for physical in output["physical"]:
            print("SEED", physical["seed"], "reproduced",
                  physical["reproduced_site_build_1974"], "mature+",
                  physical["mature_profit_positive"], "snapshots",
                  {y: (v.get("status"), v.get("profit_this_year_gbp"))
                      for y, v in physical["on_annual_services"].items()})
    print("EVIDENCE", dest)


if __name__ == "__main__":
    main()
