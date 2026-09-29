#!/usr/bin/env python3
"""B9/G4 : qualifie le shadow pre-build de demande capturable contre le post-build."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from diag_b9_air_catchment import collect_probe_events_from_engine_logs


def stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not values:
        return {"n": 0, "mean": None, "median": None, "pstdev": None,
                "p25": None, "p75": None, "iqr": None, "min": None, "max": None}
    if len(values) >= 2:
        p25, _, p75 = statistics.quantiles(values, n=4, method="inclusive")
    else:
        p25 = p75 = values[0]
    return {"n": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values), "pstdev": statistics.pstdev(values),
            "p25": p25, "p75": p75, "iqr": p75 - p25,
            "min": min(values), "max": max(values)}


def _same_plan(shadow, build, endpoints):
    if shadow.get("arm") != build.get("arm") or len(endpoints) != 2:
        return False
    actual = ((endpoints[0].get("town"), endpoints[0].get("airport_tile")),
              (endpoints[1].get("town"), endpoints[1].get("airport_tile")))
    predicted = ((shadow.get("town_a"), shadow.get("anchor_a")),
                 (shadow.get("town_b"), shadow.get("anchor_b")))
    return predicted == actual


def _renormalised_month(predicted_tiles, endpoint):
    town_tiles = endpoint.get("town_pax_tiles")
    produced = endpoint.get("town_pax_month")
    if not isinstance(predicted_tiles, (int, float)):
        return None
    if not isinstance(town_tiles, (int, float)) or town_tiles <= 0:
        return None
    if not isinstance(produced, (int, float)) or produced < 0:
        return None
    usable = min(max(predicted_tiles, 0), town_tiles)
    return produced * usable / town_tiles


def analyse_games(games):
    rows = []
    shadow_count = 0
    unmatched_builds = 0
    for game_id, events in games.items():
        pending_endpoints = []
        prior_shadows = []
        for event in events:
            kind = event.get("kind")
            if kind == "AIR_DEMAND_SHADOW":
                shadow_count += 1
                prior_shadows.append(event)
                continue
            if kind == "AIR_CATCHMENT_ENDPOINT":
                pending_endpoints.append(event)
                if len(pending_endpoints) > 2:
                    pending_endpoints = pending_endpoints[-2:]
                continue
            if kind != "AIR_CATCHMENT_BUILD":
                continue
            endpoints = pending_endpoints[-2:] if len(pending_endpoints) >= 2 else []
            pending_endpoints = []
            match = None
            match_index = None
            for idx in range(len(prior_shadows) - 1, -1, -1):
                if _same_plan(prior_shadows[idx], event, endpoints):
                    match = prior_shadows[idx]
                    match_index = idx
                    break
            if match is None:
                unmatched_builds += 1
                continue
            prior_shadows.pop(match_index)

            pred_tiles = [match.get("union_tiles_a"), match.get("union_tiles_b")]
            actual_tiles = [ep.get("town_union_pax_tiles") for ep in endpoints]
            pred_month = [_renormalised_month(pred_tiles[i], endpoints[i]) for i in range(2)]
            actual_month = [ep.get("union_pax_month_est") for ep in endpoints]
            shadow_div = [match.get("route_div_a", 1), match.get("route_div_b", 1)]
            build_div = [event.get("route_div_a", 1), event.get("route_div_b", 1)]

            pred_alloc = actual_alloc = 0.0
            monthly_valid = True
            for i in range(2):
                if not isinstance(pred_month[i], (int, float)) or not isinstance(actual_month[i], (int, float)):
                    monthly_valid = False
                    break
                sd = shadow_div[i] if isinstance(shadow_div[i], (int, float)) and shadow_div[i] > 0 else 1
                bd = build_div[i] if isinstance(build_div[i], (int, float)) and build_div[i] > 0 else 1
                pred_alloc += pred_month[i] / sd
                actual_alloc += actual_month[i] / bd

            base = event.get("base_monthly")
            row = {
                "game_id": game_id, "arm": event.get("arm"),
                "shadow_date": match.get("date"), "build_date": event.get("date"),
                "base_monthly": base,
                "tile_error_a": (pred_tiles[0] - actual_tiles[0])
                    if all(isinstance(v, (int, float)) for v in (pred_tiles[0], actual_tiles[0])) else None,
                "tile_error_b": (pred_tiles[1] - actual_tiles[1])
                    if all(isinstance(v, (int, float)) for v in (pred_tiles[1], actual_tiles[1])) else None,
                "predicted_allocated_monthly_at_build": pred_alloc if monthly_valid else None,
                "actual_allocated_monthly": actual_alloc if monthly_valid else None,
                "predicted_over_actual": (pred_alloc / actual_alloc)
                    if monthly_valid and actual_alloc > 0 else None,
                "base_over_predicted": (base / pred_alloc)
                    if monthly_valid and pred_alloc > 0 and isinstance(base, (int, float)) else None,
                "base_over_actual": (base / actual_alloc)
                    if monthly_valid and actual_alloc > 0 and isinstance(base, (int, float)) else None,
                "route_div_match": shadow_div == build_div,
                "predicted_stops_a": match.get("predicted_stops_a"),
                "predicted_stops_b": match.get("predicted_stops_b"),
                "actual_stops_a": event.get("stops_a"),
                "actual_stops_b": event.get("stops_b"),
            }
            stop_exact = []
            for suffix in ("a", "b"):
                if event.get(f"reuse_{suffix}") != 0:
                    continue
                pred = match.get(f"predicted_stops_{suffix}")
                actual = event.get(f"stops_{suffix}")
                if isinstance(pred, (int, float)) and isinstance(actual, (int, float)):
                    stop_exact.append(pred == actual)
            row["new_stop_count_exact"] = all(stop_exact) if stop_exact else None
            rows.append(row)

    out = {"shadow_events": shadow_count, "matched_builds": len(rows),
           "unmatched_builds": unmatched_builds, "by_arm": {}}
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row.get("arm") or "unknown")].append(row)
    for arm, group in sorted(grouped.items()):
        tile_errors = [row[key] for row in group for key in ("tile_error_a", "tile_error_b")
                       if isinstance(row.get(key), (int, float))]
        stop_exact = [row["new_stop_count_exact"] for row in group
                      if row["new_stop_count_exact"] is not None]
        exact_stop_ratios = [row["predicted_over_actual"] for row in group
                             if row["new_stop_count_exact"] is True
                             and row["predicted_over_actual"] is not None]
        inexact_stop_ratios = [row["predicted_over_actual"] for row in group
                               if row["new_stop_count_exact"] is False
                               and row["predicted_over_actual"] is not None]
        stop_deltas = []
        if arm == "newpair":
            stop_suffixes = ("a", "b")
        elif arm == "hubsite":
            stop_suffixes = ("b",)
        else:
            stop_suffixes = ()
        for row in group:
            for suffix in stop_suffixes:
                predicted = row.get(f"predicted_stops_{suffix}")
                actual = row.get(f"actual_stops_{suffix}")
                if isinstance(predicted, (int, float)) and isinstance(actual, (int, float)):
                    stop_deltas.append(predicted - actual)
        out["by_arm"][arm] = {
            "n": len(group),
            "tile_error": stats(tile_errors),
            "predicted_over_actual": stats(row["predicted_over_actual"] for row in group
                                           if row["predicted_over_actual"] is not None),
            "base_over_predicted": stats(row["base_over_predicted"] for row in group
                                         if row["base_over_predicted"] is not None),
            "base_over_actual": stats(row["base_over_actual"] for row in group
                                      if row["base_over_actual"] is not None),
            "route_div_match_share": sum(1 for row in group if row["route_div_match"]) / len(group),
            "new_stop_count_exact_share": (
                sum(1 for value in stop_exact if value) / len(stop_exact) if stop_exact else None),
            "predicted_over_actual_when_stop_count_exact": stats(exact_stop_ratios),
            "predicted_over_actual_when_stop_count_inexact": stats(inexact_stop_ratios),
            "new_stop_count_delta_predicted_minus_actual": stats(stop_deltas),
            "new_stop_count_under": sum(1 for value in stop_deltas if value < 0),
            "new_stop_count_equal": sum(1 for value in stop_deltas if value == 0),
            "new_stop_count_over": sum(1 for value in stop_deltas if value > 0),
        }
    out["rows"] = rows
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine_dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = analyse_games(collect_probe_events_from_engine_logs(args.engine_dir))
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
