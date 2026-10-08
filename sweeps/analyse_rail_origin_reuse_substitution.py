"""Compare passive rail-passenger line telemetry between two OpexAI policies.

This is a post-processing diagnostic only.  It reads the monthly line telemetry
already embedded in a frozen-harness result and reports the first date where the
reference and variant expose different operated rail-passenger markets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


PASSENGER_CARGO_ID = "0"


def _rail_pax_lines(snapshot: dict) -> list[dict]:
    out: list[dict] = []
    for line in snapshot.get("lines") or []:
        if line.get("mode") != "rail":
            continue
        capacity = line.get("capacity_by_cargo") or {}
        if int(capacity.get(PASSENGER_CARGO_ID, 0) or 0) <= 0:
            continue
        out.append(line)
    return out


def _market_signature(line: dict) -> tuple:
    towns = tuple(sorted(int(t) for t in (line.get("town_ids") or []) if t is not None))
    stations = tuple(sorted(int(s) for s in (line.get("station_ids") or []) if s is not None))
    return (str(line.get("market_key")), towns, stations)


def _line_view(line: dict) -> dict:
    capacity = line.get("capacity_by_cargo") or {}
    return {
        "market_key": line.get("market_key"),
        "town_ids": line.get("town_ids") or [],
        "station_ids": line.get("station_ids") or [],
        "vehicle_ids": line.get("vehicle_ids") or [],
        "passenger_capacity": int(capacity.get(PASSENGER_CARGO_ID, 0) or 0),
    }


def _service_signature(line: dict) -> tuple:
    """Physical service identity without volatile vehicle/profit fields."""
    towns = tuple(int(t) for t in (line.get("ordered_town_ids") or line.get("town_ids") or [])
                  if t is not None)
    return (
        str(line.get("mode")),
        str(line.get("service_key") or line.get("market_key")),
        towns,
    )


def _fleet_signature(line: dict) -> tuple:
    capacity = tuple(sorted((str(k), int(v or 0))
                            for k, v in (line.get("capacity_by_cargo") or {}).items()))
    return _service_signature(line) + (int(line.get("vehicles", 0) or 0), capacity)


def _first_generic_divergence(by_key: dict, reference_policy: str, variant_policy: str,
                              seed: int, dates: list[str], signature) -> dict | None:
    previous_equal = None
    for current_date in dates:
        ref_lines = by_key[(reference_policy, seed, current_date)].get("lines") or []
        var_lines = by_key[(variant_policy, seed, current_date)].get("lines") or []
        ref_map = {signature(line): line for line in ref_lines}
        var_map = {signature(line): line for line in var_lines}
        if set(ref_map) == set(var_map):
            previous_equal = current_date
            continue
        only_ref = sorted(set(ref_map) - set(var_map), key=repr)
        only_var = sorted(set(var_map) - set(ref_map), key=repr)
        return {
            "date": current_date,
            "previous_equal_date": previous_equal,
            "reference_count": len(ref_map),
            "variant_count": len(var_map),
            "reference_only": [_line_view(ref_map[key]) for key in only_ref[:8]],
            "variant_only": [_line_view(var_map[key]) for key in only_var[:8]],
        }
    return None


def _checkpoint_view(row: dict) -> dict:
    return {
        "money": row.get("money"),
        "current_loan": row.get("current_loan"),
        "company_value": row.get("company_value"),
        "income_last_year": row.get("income_last_year"),
        "expenses_last_year": row.get("expenses_last_year"),
        "profit": row.get("profit"),
        "profit_year": row.get("profit_year"),
        "median_station_rating": row.get("median_station_rating"),
        "n_vehicles": row.get("n_vehicles"),
        "primary_vehicles_by_mode": row.get("primary_vehicles_by_mode") or {},
        "air_primary_vehicles": row.get("air_primary_vehicles"),
        "air_passenger_capacity": row.get("air_passenger_capacity"),
        "air_vehicle_book_value": row.get("air_vehicle_book_value"),
        "n_stations": row.get("n_stations"),
        "stations_by_facility": row.get("stations_by_facility") or {},
    }


def _checkpoint_differences(reference: dict, variant: dict) -> dict:
    ref = _checkpoint_view(reference)
    var = _checkpoint_view(variant)
    return {key: {"reference": ref[key], "variant": var[key]}
            for key in ref if ref[key] != var[key]}


def analyse(report: dict, reference_policy: str, variant_policy: str, seeds: list[int] | None,
            checkpoints: list[dict] | None = None) -> dict:
    snapshots = (report.get("line_telemetry") or {}).get("snapshots") or []
    by_key: dict[tuple[str, int, str], dict] = {}
    available_seeds: set[int] = set()
    for snap in snapshots:
        if snap.get("arm") != "OpexAI":
            continue
        policy = str(snap.get("duel_policy_id"))
        if policy not in (reference_policy, variant_policy):
            continue
        seed = int(snap.get("seed"))
        available_seeds.add(seed)
        by_key[(policy, seed, str(snap.get("date")))] = snap

    selected = sorted(available_seeds if seeds is None else (available_seeds & set(seeds)))
    out = []
    for seed in selected:
        dates_ref = {date for policy, s, date in by_key if policy == reference_policy and s == seed}
        dates_var = {date for policy, s, date in by_key if policy == variant_policy and s == seed}
        dates = sorted(dates_ref & dates_var)
        first = None
        previous_equal = None
        differing_dates = 0
        for current_date in dates:
            ref_lines = _rail_pax_lines(by_key[(reference_policy, seed, current_date)])
            var_lines = _rail_pax_lines(by_key[(variant_policy, seed, current_date)])
            ref_map = {_market_signature(line): line for line in ref_lines}
            var_map = {_market_signature(line): line for line in var_lines}
            if set(ref_map) == set(var_map):
                if first is None:
                    previous_equal = {
                        "date": current_date,
                        "markets": [_line_view(ref_map[key]) for key in sorted(ref_map)],
                    }
                continue
            differing_dates += 1
            if first is None:
                only_ref = sorted(set(ref_map) - set(var_map))
                only_var = sorted(set(var_map) - set(ref_map))
                first = {
                    "date": current_date,
                    "reference_count": len(ref_map),
                    "variant_count": len(var_map),
                    "reference_only": [_line_view(ref_map[key]) for key in only_ref],
                    "variant_only": [_line_view(var_map[key]) for key in only_var],
                    "previous_equal": previous_equal,
                }
        first_checkpoint = None
        if checkpoints is not None:
            ck_ref = {str(row.get("date")): row for row in checkpoints
                      if row.get("run") == ["OpexAI", seed, 0]
                      and str(row.get("duel_policy_id")) == reference_policy}
            ck_var = {str(row.get("date")): row for row in checkpoints
                      if row.get("run") == ["OpexAI", seed, 0]
                      and str(row.get("duel_policy_id")) == variant_policy}
            previous_equal = None
            for current_date in sorted(set(ck_ref) & set(ck_var)):
                differences = _checkpoint_differences(ck_ref[current_date], ck_var[current_date])
                if not differences:
                    previous_equal = current_date
                    continue
                first_checkpoint = {
                    "date": current_date,
                    "previous_equal_date": previous_equal,
                    "differences": differences,
                }
                break

        out.append({
            "seed": seed,
            "paired_dates": len(dates),
            "first_market_divergence": first,
            "first_all_service_divergence": _first_generic_divergence(
                by_key, reference_policy, variant_policy, seed, dates, _service_signature),
            "first_all_fleet_divergence": _first_generic_divergence(
                by_key, reference_policy, variant_policy, seed, dates, _fleet_signature),
            "first_checkpoint_divergence": first_checkpoint,
            "differing_dates_from_first_scan": differing_dates,
        })

    return {
        "schema_version": 1,
        "source": "passive monthly line_telemetry",
        "reference_policy": reference_policy,
        "variant_policy": variant_policy,
        "seeds": out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--reference-policy", default="reference")
    parser.add_argument("--variant-policy", default="origin_reuse_pax_only")
    parser.add_argument("--seeds", nargs="*", type=int)
    parser.add_argument("--checkpoints", type=Path,
                        help="optional frozen-harness JSONL checkpoints for cash/fleet divergence")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    checkpoints = None
    if args.checkpoints:
        checkpoints = [json.loads(line) for line in args.checkpoints.read_text(encoding="utf-8").splitlines()
                       if line.strip()]
    result = analyse(report, args.reference_policy, args.variant_policy, args.seeds, checkpoints)
    encoded = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
