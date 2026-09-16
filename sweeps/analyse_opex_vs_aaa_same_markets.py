"""Compare OpexAI et AAAHogEx sur les memes marches dans une politique C66.

Le matching inter-IA est fait par ``mode + TownID tries`` (``market_key``), jamais
par ``group_id`` ou par station_id, qui sont locaux a chaque compagnie/partie.

Les profits sont ceux exposes par la telemetrie passive VEHS au checkpoint : somme
de ``profit_this_year / 256`` et ``profit_last_year / 256`` des vehicules encore
presents. Ce script ne reconstruit ni revenu brut ni running cost de ligne.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from analyse_early_slot_lines import aggregate_markets


def _safe_div(num, den):
    return num / den if den else None


def _round(value):
    return round(value, 6) if isinstance(value, (int, float)) else value


def _stats(values):
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None}
    return {
        "n": len(values),
        "mean": _round(statistics.mean(values)),
        "median": _round(statistics.median(values)),
    }


def _snapshot_index(payload):
    snapshots = (payload.get("line_telemetry") or {}).get("snapshots") or []
    return {
        (
            snap.get("duel_policy_id"),
            snap.get("arm"),
            snap.get("seed"),
            snap.get("repeat", 0),
            snap.get("year"),
        ): snap
        for snap in snapshots
    }


def _available_modes(lines):
    return sorted({line.get("mode") for line in (lines or []) if line.get("mode")})


def _capacity_total(market):
    return sum((market.get("capacity_by_cargo") or {}).values())


def _cargo_types(market):
    return sorted((market.get("capacity_by_cargo") or {}).keys(), key=str)


def compare(payload, policy_id=None, requested_mode=None):
    comparison = payload.get("policy_comparison") or {}
    if policy_id is None:
        policy_id = comparison.get("variant_policy_id") or payload.get("policy_id")
    if not policy_id:
        raise ValueError("Impossible de determiner la politique a analyser")

    index = _snapshot_index(payload)
    first_seen = {"OpexAI": {}, "AAAHogEx": {}}
    for (policy, arm, seed, repeat, year), snap in index.items():
        if policy != policy_id or arm not in first_seen or year is None:
            continue
        for mode in _available_modes(snap.get("lines")):
            if requested_mode and mode != requested_mode:
                continue
            for key in aggregate_markets(snap.get("lines"), mode):
                marker = (seed, repeat, mode, key)
                previous = first_seen[arm].get(marker)
                if previous is None or year < previous:
                    first_seen[arm][marker] = year
    pair_years = sorted({
        (seed, repeat, year)
        for policy, arm, seed, repeat, year in index
        if policy == policy_id and arm == "OpexAI" and year is not None
    })

    detailed = []
    pair_mode = []

    for seed, repeat, year in pair_years:
        opex_snap = index.get((policy_id, "OpexAI", seed, repeat, year))
        aaa_snap = index.get((policy_id, "AAAHogEx", seed, repeat, year))
        if not opex_snap or not aaa_snap:
            continue

        modes = sorted(set(_available_modes(opex_snap.get("lines"))) | set(_available_modes(aaa_snap.get("lines"))))
        if requested_mode:
            modes = [mode for mode in modes if mode == requested_mode]

        for mode in modes:
            opex = aggregate_markets(opex_snap.get("lines"), mode)
            aaa = aggregate_markets(aaa_snap.get("lines"), mode)
            shared = sorted(set(opex) & set(aaa))
            opex_only = set(opex) - set(aaa)
            aaa_only = set(aaa) - set(opex)

            totals = {
                "opex_shared_vehicles": 0,
                "aaa_shared_vehicles": 0,
                "opex_shared_capacity": 0,
                "aaa_shared_capacity": 0,
                "opex_shared_profit_this_year_gbp": 0.0,
                "aaa_shared_profit_this_year_gbp": 0.0,
                "opex_shared_profit_last_year_gbp": 0.0,
                "aaa_shared_profit_last_year_gbp": 0.0,
            }
            opex_all_vehicles = sum(market["vehicles"] for market in opex.values())
            aaa_all_vehicles = sum(market["vehicles"] for market in aaa.values())
            opex_all_capacity = sum(_capacity_total(market) for market in opex.values())
            aaa_all_capacity = sum(_capacity_total(market) for market in aaa.values())

            same_cargo = 0
            for key in shared:
                om = opex[key]
                am = aaa[key]
                ocap = _capacity_total(om)
                acap = _capacity_total(am)
                ocargo = _cargo_types(om)
                acargo = _cargo_types(am)
                cargo_match = ocargo == acargo
                marker = (seed, repeat, mode, key)
                opex_first = first_seen["OpexAI"].get(marker)
                aaa_first = first_seen["AAAHogEx"].get(marker)
                same_cargo += int(cargo_match)

                totals["opex_shared_vehicles"] += om["vehicles"]
                totals["aaa_shared_vehicles"] += am["vehicles"]
                totals["opex_shared_capacity"] += ocap
                totals["aaa_shared_capacity"] += acap
                totals["opex_shared_profit_this_year_gbp"] += om["profit_this_year_gbp"]
                totals["aaa_shared_profit_this_year_gbp"] += am["profit_this_year_gbp"]
                totals["opex_shared_profit_last_year_gbp"] += om["profit_last_year_gbp"]
                totals["aaa_shared_profit_last_year_gbp"] += am["profit_last_year_gbp"]

                detailed.append({
                    "policy_id": policy_id,
                    "seed": seed,
                    "repeat": repeat,
                    "year": year,
                    "mode": mode,
                    "market_key": key,
                    "town_ids": om.get("town_ids") or am.get("town_ids"),
                    "cargo_match": cargo_match,
                    "opex_first_seen_year": opex_first,
                    "aaahogex_first_seen_year": aaa_first,
                    "entry_year_delta_opex_minus_aaa": (
                        opex_first - aaa_first
                        if opex_first is not None and aaa_first is not None else None
                    ),
                    "opex": {
                        "cargo_types": ocargo,
                        "capacity_by_cargo": om.get("capacity_by_cargo") or {},
                        "capacity_total": ocap,
                        "vehicles": om["vehicles"],
                        "profit_this_year_gbp": om["profit_this_year_gbp"],
                        "profit_last_year_gbp": om["profit_last_year_gbp"],
                    },
                    "aaahogex": {
                        "cargo_types": acargo,
                        "capacity_by_cargo": am.get("capacity_by_cargo") or {},
                        "capacity_total": acap,
                        "vehicles": am["vehicles"],
                        "profit_this_year_gbp": am["profit_this_year_gbp"],
                        "profit_last_year_gbp": am["profit_last_year_gbp"],
                    },
                    "delta_aaa_minus_opex": {
                        "vehicles": am["vehicles"] - om["vehicles"],
                        "capacity_total": acap - ocap,
                        "profit_this_year_gbp": _round(am["profit_this_year_gbp"] - om["profit_this_year_gbp"]),
                        "profit_last_year_gbp": _round(am["profit_last_year_gbp"] - om["profit_last_year_gbp"]),
                    },
                    "profit_this_year_per_vehicle": {
                        "opex": _round(_safe_div(om["profit_this_year_gbp"], om["vehicles"])),
                        "aaahogex": _round(_safe_div(am["profit_this_year_gbp"], am["vehicles"])),
                    },
                    "profit_this_year_per_capacity": {
                        "opex": _round(_safe_div(om["profit_this_year_gbp"], ocap)),
                        "aaahogex": _round(_safe_div(am["profit_this_year_gbp"], acap)),
                    },
                })

            opex_profit = totals["opex_shared_profit_this_year_gbp"]
            aaa_profit = totals["aaa_shared_profit_this_year_gbp"]
            pair_mode.append({
                "policy_id": policy_id,
                "seed": seed,
                "repeat": repeat,
                "year": year,
                "mode": mode,
                "opex_markets": len(opex),
                "aaahogex_markets": len(aaa),
                "shared_markets": len(shared),
                "opex_only_markets": len(opex_only),
                "aaahogex_only_markets": len(aaa_only),
                "shared_same_cargo_markets": same_cargo,
                "opex_all_vehicles": opex_all_vehicles,
                "aaahogex_all_vehicles": aaa_all_vehicles,
                "opex_all_capacity": opex_all_capacity,
                "aaahogex_all_capacity": aaa_all_capacity,
                "opex_all_vehicles_per_market": _round(_safe_div(opex_all_vehicles, len(opex))),
                "aaahogex_all_vehicles_per_market": _round(_safe_div(aaa_all_vehicles, len(aaa))),
                "opex_all_capacity_per_market": _round(_safe_div(opex_all_capacity, len(opex))),
                "aaahogex_all_capacity_per_market": _round(_safe_div(aaa_all_capacity, len(aaa))),
                **{key: _round(value) for key, value in totals.items()},
                "shared_profit_delta_aaa_minus_opex_gbp": _round(aaa_profit - opex_profit),
                "shared_profit_ratio_aaa_over_opex": _round(_safe_div(aaa_profit, opex_profit)),
                "shared_vehicle_ratio_aaa_over_opex": _round(_safe_div(totals["aaa_shared_vehicles"], totals["opex_shared_vehicles"])),
                "shared_capacity_ratio_aaa_over_opex": _round(_safe_div(totals["aaa_shared_capacity"], totals["opex_shared_capacity"])),
                "opex_shared_profit_per_vehicle": _round(_safe_div(opex_profit, totals["opex_shared_vehicles"])),
                "aaa_shared_profit_per_vehicle": _round(_safe_div(aaa_profit, totals["aaa_shared_vehicles"])),
                "opex_shared_profit_per_capacity": _round(_safe_div(opex_profit, totals["opex_shared_capacity"])),
                "aaa_shared_profit_per_capacity": _round(_safe_div(aaa_profit, totals["aaa_shared_capacity"])),
            })

    metric_fields = (
        "opex_markets", "aaahogex_markets", "shared_markets", "opex_only_markets", "aaahogex_only_markets",
        "opex_shared_vehicles", "aaa_shared_vehicles", "opex_shared_capacity", "aaa_shared_capacity",
        "opex_all_vehicles", "aaahogex_all_vehicles", "opex_all_capacity", "aaahogex_all_capacity",
        "opex_all_vehicles_per_market", "aaahogex_all_vehicles_per_market",
        "opex_all_capacity_per_market", "aaahogex_all_capacity_per_market",
        "opex_shared_profit_this_year_gbp", "aaa_shared_profit_this_year_gbp",
        "shared_profit_delta_aaa_minus_opex_gbp", "shared_profit_ratio_aaa_over_opex",
        "shared_vehicle_ratio_aaa_over_opex", "shared_capacity_ratio_aaa_over_opex",
        "opex_shared_profit_per_vehicle", "aaa_shared_profit_per_vehicle",
        "opex_shared_profit_per_capacity", "aaa_shared_profit_per_capacity",
    )

    annual = []
    groups = defaultdict(list)
    for row in pair_mode:
        groups[(row["year"], row["mode"])].append(row)
    for (year, mode), rows in sorted(groups.items()):
        detail_rows = [row for row in detailed if row["year"] == year and row["mode"] == mode]
        opex_vehicles = sum(row["opex"]["vehicles"] for row in detail_rows)
        aaa_vehicles = sum(row["aaahogex"]["vehicles"] for row in detail_rows)
        opex_capacity = sum(row["opex"]["capacity_total"] for row in detail_rows)
        aaa_capacity = sum(row["aaahogex"]["capacity_total"] for row in detail_rows)
        opex_profit = sum(row["opex"]["profit_this_year_gbp"] for row in detail_rows)
        aaa_profit = sum(row["aaahogex"]["profit_this_year_gbp"] for row in detail_rows)
        opex_last = sum(row["opex"]["profit_last_year_gbp"] for row in detail_rows)
        aaa_last = sum(row["aaahogex"]["profit_last_year_gbp"] for row in detail_rows)
        annual.append({
            "year": year,
            "mode": mode,
            "pairs": len(rows),
            "metrics": {field: _stats([row[field] for row in rows]) for field in metric_fields},
            "pooled_shared_markets": {
                "observations": len(detail_rows),
                "same_cargo_observations": sum(int(row["cargo_match"]) for row in detail_rows),
                "aaahogex_profit_higher": sum(
                    int(row["aaahogex"]["profit_this_year_gbp"] > row["opex"]["profit_this_year_gbp"])
                    for row in detail_rows
                ),
                "opex_profit_higher": sum(
                    int(row["opex"]["profit_this_year_gbp"] > row["aaahogex"]["profit_this_year_gbp"])
                    for row in detail_rows
                ),
                "equal_profit": sum(
                    int(row["opex"]["profit_this_year_gbp"] == row["aaahogex"]["profit_this_year_gbp"])
                    for row in detail_rows
                ),
                "opex_entered_earlier": sum(
                    int(row["entry_year_delta_opex_minus_aaa"] < 0)
                    for row in detail_rows if row["entry_year_delta_opex_minus_aaa"] is not None
                ),
                "same_entry_year": sum(
                    int(row["entry_year_delta_opex_minus_aaa"] == 0)
                    for row in detail_rows if row["entry_year_delta_opex_minus_aaa"] is not None
                ),
                "aaahogex_entered_earlier": sum(
                    int(row["entry_year_delta_opex_minus_aaa"] > 0)
                    for row in detail_rows if row["entry_year_delta_opex_minus_aaa"] is not None
                ),
                "opex_vehicles": opex_vehicles,
                "aaahogex_vehicles": aaa_vehicles,
                "vehicle_ratio_aaa_over_opex": _round(_safe_div(aaa_vehicles, opex_vehicles)),
                "opex_capacity": opex_capacity,
                "aaahogex_capacity": aaa_capacity,
                "capacity_ratio_aaa_over_opex": _round(_safe_div(aaa_capacity, opex_capacity)),
                "opex_profit_this_year_gbp": _round(opex_profit),
                "aaahogex_profit_this_year_gbp": _round(aaa_profit),
                "profit_delta_aaa_minus_opex_gbp": _round(aaa_profit - opex_profit),
                "profit_ratio_aaa_over_opex": _round(_safe_div(aaa_profit, opex_profit)),
                "opex_profit_last_year_gbp": _round(opex_last),
                "aaahogex_profit_last_year_gbp": _round(aaa_last),
                "profit_last_year_delta_aaa_minus_opex_gbp": _round(aaa_last - opex_last),
                "opex_profit_per_vehicle": _round(_safe_div(opex_profit, opex_vehicles)),
                "aaahogex_profit_per_vehicle": _round(_safe_div(aaa_profit, aaa_vehicles)),
                "opex_profit_per_capacity": _round(_safe_div(opex_profit, opex_capacity)),
                "aaahogex_profit_per_capacity": _round(_safe_div(aaa_profit, aaa_capacity)),
                "market_vehicle_ratio_median": _stats([
                    _safe_div(row["aaahogex"]["vehicles"], row["opex"]["vehicles"])
                    for row in detail_rows
                ])["median"],
                "market_capacity_ratio_median": _stats([
                    _safe_div(row["aaahogex"]["capacity_total"], row["opex"]["capacity_total"])
                    for row in detail_rows
                ])["median"],
                "market_profit_delta_median_gbp": _stats([
                    row["aaahogex"]["profit_this_year_gbp"] - row["opex"]["profit_this_year_gbp"]
                    for row in detail_rows
                ])["median"],
                "market_profit_per_vehicle_delta_median_gbp": _stats([
                    _safe_div(row["aaahogex"]["profit_this_year_gbp"], row["aaahogex"]["vehicles"])
                    - _safe_div(row["opex"]["profit_this_year_gbp"], row["opex"]["vehicles"])
                    for row in detail_rows
                    if row["aaahogex"]["vehicles"] and row["opex"]["vehicles"]
                ])["median"],
            },
        })

    return {
        "source_campaign": payload.get("campaign_id"),
        "policy_id": policy_id,
        "requested_mode": requested_mode,
        "matching": "same seed + same year + same mode + same canonical TownID pair (market_key)",
        "profit_scope": (
            "Somme VEHS profit_this_year/256 et profit_last_year/256 des vehicules encore presents au checkpoint; "
            "pas de revenue ni running_cost reconstruits."
        ),
        "pair_year_mode": pair_mode,
        "annual": annual,
        "shared_market_details": detailed,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--policy-id")
    parser.add_argument("--mode", choices=("air", "rail", "road", "water"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    report = compare(payload, policy_id=args.policy_id, requested_mode=args.mode)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("year mode pairs shared opex_mkts aaa_mkts veh_ratio cap_ratio profit_ratio profit_delta")
    for row in report["annual"]:
        m = row["metrics"]
        def mean(field):
            value = m[field]["mean"]
            return "NA" if value is None else f"{value:.3f}"
        print(
            row["year"], row["mode"], row["pairs"],
            mean("shared_markets"), mean("opex_markets"), mean("aaahogex_markets"),
            mean("shared_vehicle_ratio_aaa_over_opex"),
            mean("shared_capacity_ratio_aaa_over_opex"),
            mean("shared_profit_ratio_aaa_over_opex"),
            mean("shared_profit_delta_aaa_minus_opex_gbp"),
        )


if __name__ == "__main__":
    main()
