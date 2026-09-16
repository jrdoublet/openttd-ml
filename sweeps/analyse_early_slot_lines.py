"""Analyse passive des lignes current vs early-slot extraites par C66.

Le fichier d'entree doit avoir ete produit avec --line-telemetry. Les lignes sont
matchees entre parties par mode + TownID (market_key), jamais par group_id car les
IDs de pool sont locaux a chaque partie. Le profit VEHS est un profit de vehicules
encore presents au checkpoint; ce n'est ni un revenu brut ni une comptabilite de
ligne exhaustive apres ventes/remplacements.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


NUMERIC_FIELDS = (
    "reference_markets",
    "variant_markets",
    "shared_markets",
    "reference_only_markets",
    "variant_only_markets",
    "reference_air_profit_gbp",
    "variant_air_profit_gbp",
    "air_profit_delta_gbp",
    "reference_only_profit_gbp",
    "variant_only_profit_gbp",
    "shared_profit_delta_gbp",
    "reference_only_overlap_opex_any",
    "reference_only_overlap_opex_all",
    "reference_only_overlap_profit_gbp",
    "reference_only_nonoverlap_profit_gbp",
    "opex_profit_year_delta_gbp",
    "aaahogex_profit_year_delta_gbp",
)


def _number(value):
    return round(value, 6) if isinstance(value, (int, float)) else value


def _stats(values):
    values = [value for value in values if isinstance(value, (int, float))]
    return {
        "n": len(values),
        "mean": _number(statistics.mean(values)) if values else None,
        "median": _number(statistics.median(values)) if values else None,
    }


def aggregate_markets(lines, mode="air"):
    """Fusionne les groupes locaux qui desservent le meme marche TownID."""
    markets = {}
    for line in lines or []:
        if line.get("mode") != mode:
            continue
        key = line.get("market_key")
        if not key:
            continue
        market = markets.setdefault(key, {
            "market_key": key,
            "mode": mode,
            "town_ids": list(line.get("town_ids") or []),
            "line_keys_local": [],
            "group_ids": [],
            "vehicles": 0,
            "capacity_by_cargo": defaultdict(int),
            "profit_this_year_gbp": 0.0,
            "profit_last_year_gbp": 0.0,
            "vehicle_value": 0,
        })
        local_key = line.get("line_key_local")
        if local_key is not None and local_key not in market["line_keys_local"]:
            market["line_keys_local"].append(local_key)
        group_id = line.get("group_id")
        if group_id is not None and group_id not in market["group_ids"]:
            market["group_ids"].append(group_id)
        market["vehicles"] += line.get("vehicles") or 0
        for cargo, capacity in (line.get("capacity_by_cargo") or {}).items():
            market["capacity_by_cargo"][str(cargo)] += capacity or 0
        market["profit_this_year_gbp"] += line.get("profit_this_year_gbp") or 0
        market["profit_last_year_gbp"] += line.get("profit_last_year_gbp") or 0
        market["vehicle_value"] += line.get("vehicle_value") or 0

    for market in markets.values():
        market["capacity_by_cargo"] = dict(sorted(market["capacity_by_cargo"].items()))
        market["profit_this_year_gbp"] = _number(market["profit_this_year_gbp"])
        market["profit_last_year_gbp"] = _number(market["profit_last_year_gbp"])
    return markets


def _snapshot_index(payload):
    telemetry = payload.get("line_telemetry") or {}
    snapshots = telemetry.get("snapshots") or []
    return {
        (
            snap.get("duel_policy_id"), snap.get("arm"), snap.get("seed"),
            snap.get("repeat", 0), snap.get("year"),
        ): snap
        for snap in snapshots
    }


def compare(payload):
    telemetry = payload.get("line_telemetry") or {}
    if not telemetry.get("snapshots"):
        raise ValueError("Le rapport ne contient pas de line_telemetry; relancer C66 avec --line-telemetry")

    comparison = payload.get("policy_comparison") or {}
    reference_policy = comparison.get("reference_policy_id") or payload.get("policy_id")
    variant_policy = comparison.get("variant_policy_id")
    if not variant_policy:
        raise ValueError("Une comparaison C66.4 reference/variant est requise")

    index = _snapshot_index(payload)
    economic_index = {}
    for pair in comparison.get("per_pair") or []:
        seed = pair.get("seed")
        repeat = pair.get("repeat", 0)
        for row in pair.get("annual_trajectory") or []:
            economic_index[(seed, repeat, row.get("year"))] = {
                "opex_profit_year_delta_gbp": row.get("policy_delta"),
                "aaahogex_profit_year_delta_gbp": (
                    row.get("variant_aaahogex") - row.get("reference_aaahogex")
                    if row.get("variant_aaahogex") is not None
                    and row.get("reference_aaahogex") is not None else None
                ),
            }
    pairs = sorted({
        (seed, repeat, year)
        for policy, arm, seed, repeat, year in index
        if policy == reference_policy and arm == "AAAHogEx" and year is not None
    })

    per_pair = []
    lost_lines = []
    for seed, repeat, year in pairs:
        ref_snap = index.get((reference_policy, "AAAHogEx", seed, repeat, year))
        var_snap = index.get((variant_policy, "AAAHogEx", seed, repeat, year))
        opex_var_snap = index.get((variant_policy, "OpexAI", seed, repeat, year))
        if not ref_snap or not var_snap or not opex_var_snap:
            continue

        ref = aggregate_markets(ref_snap.get("lines"), "air")
        var = aggregate_markets(var_snap.get("lines"), "air")
        opex_var = aggregate_markets(opex_var_snap.get("lines"), "air")
        opex_towns = {
            town
            for market in opex_var.values()
            for town in (market.get("town_ids") or [])
        }
        shared = set(ref) & set(var)
        ref_only = set(ref) - set(var)
        var_only = set(var) - set(ref)

        ref_profit = sum(market["profit_this_year_gbp"] for market in ref.values())
        var_profit = sum(market["profit_this_year_gbp"] for market in var.values())
        ref_only_profit = sum(ref[key]["profit_this_year_gbp"] for key in ref_only)
        var_only_profit = sum(var[key]["profit_this_year_gbp"] for key in var_only)
        shared_delta = sum(
            var[key]["profit_this_year_gbp"] - ref[key]["profit_this_year_gbp"]
            for key in shared
        )

        overlap_any = 0
        overlap_all = 0
        overlap_profit = 0.0
        nonoverlap_profit = 0.0
        for key in sorted(ref_only):
            market = ref[key]
            towns = set(market.get("town_ids") or [])
            any_overlap = bool(towns & opex_towns)
            all_overlap = bool(towns) and towns.issubset(opex_towns)
            overlap_any += int(any_overlap)
            overlap_all += int(all_overlap)
            if any_overlap:
                overlap_profit += market["profit_this_year_gbp"]
            else:
                nonoverlap_profit += market["profit_this_year_gbp"]
            lost_lines.append({
                "seed": seed,
                "repeat": repeat,
                "year": year,
                "market_key": key,
                "town_ids": market.get("town_ids"),
                "reference_profit_this_year_gbp": market["profit_this_year_gbp"],
                "reference_profit_last_year_gbp": market["profit_last_year_gbp"],
                "reference_vehicles": market["vehicles"],
                "reference_capacity_by_cargo": market["capacity_by_cargo"],
                "reference_group_ids": market["group_ids"],
                "variant_opex_occupies_any_town": any_overlap,
                "variant_opex_occupies_all_towns": all_overlap,
            })

        economics = economic_index.get((seed, repeat, year), {})
        per_pair.append({
            "seed": seed,
            "repeat": repeat,
            "year": year,
            "reference_markets": len(ref),
            "variant_markets": len(var),
            "shared_markets": len(shared),
            "reference_only_markets": len(ref_only),
            "variant_only_markets": len(var_only),
            "reference_air_profit_gbp": _number(ref_profit),
            "variant_air_profit_gbp": _number(var_profit),
            "air_profit_delta_gbp": _number(var_profit - ref_profit),
            "reference_only_profit_gbp": _number(ref_only_profit),
            "variant_only_profit_gbp": _number(var_only_profit),
            "shared_profit_delta_gbp": _number(shared_delta),
            "reference_only_overlap_opex_any": overlap_any,
            "reference_only_overlap_opex_all": overlap_all,
            "reference_only_overlap_profit_gbp": _number(overlap_profit),
            "reference_only_nonoverlap_profit_gbp": _number(nonoverlap_profit),
            "reference_only_overlap_market_share": _number(
                overlap_any / len(ref_only) if ref_only else 0.0
            ),
            "reference_only_overlap_profit_share": _number(
                overlap_profit / ref_only_profit if ref_only_profit else 0.0
            ),
            "opex_profit_year_delta_gbp": economics.get("opex_profit_year_delta_gbp"),
            "aaahogex_profit_year_delta_gbp": economics.get("aaahogex_profit_year_delta_gbp"),
            "reference_unresolved_vehicles": len(ref_snap.get("unresolved_vehicles") or []),
            "variant_unresolved_vehicles": len(var_snap.get("unresolved_vehicles") or []),
        })

    annual = []
    for year in sorted({row["year"] for row in per_pair}):
        rows = [row for row in per_pair if row["year"] == year]
        annual.append({
            "year": year,
            "pairs": len(rows),
            "metrics": {field: _stats([row[field] for row in rows]) for field in NUMERIC_FIELDS},
            "unresolved": {
                "reference": sum(row["reference_unresolved_vehicles"] for row in rows),
                "variant": sum(row["variant_unresolved_vehicles"] for row in rows),
            },
        })

    def correlation(rows, x_field, y_field):
        pairs_xy = [
            (row.get(x_field), row.get(y_field))
            for row in rows
            if isinstance(row.get(x_field), (int, float)) and isinstance(row.get(y_field), (int, float))
        ]
        if len(pairs_xy) < 2:
            return None
        xs = [pair[0] for pair in pairs_xy]
        ys = [pair[1] for pair in pairs_xy]
        mean_x = statistics.mean(xs)
        mean_y = statistics.mean(ys)
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs_xy)
        denom_x = sum((x - mean_x) ** 2 for x in xs)
        denom_y = sum((y - mean_y) ** 2 for y in ys)
        if denom_x <= 0 or denom_y <= 0:
            return None
        return _number(numerator / (denom_x * denom_y) ** 0.5)

    correlations = []
    for year in sorted({row["year"] for row in per_pair}):
        rows = [row for row in per_pair if row["year"] == year]
        correlations.append({
            "year": year,
            "n": len(rows),
            "opex_gain_vs_lost_overlap_profit": correlation(
                rows, "opex_profit_year_delta_gbp", "reference_only_overlap_profit_gbp"
            ),
            "opex_gain_vs_aaa_air_profit_delta": correlation(
                rows, "opex_profit_year_delta_gbp", "air_profit_delta_gbp"
            ),
            "opex_gain_vs_aaa_company_profit_delta": correlation(
                rows, "opex_profit_year_delta_gbp", "aaahogex_profit_year_delta_gbp"
            ),
        })

    lost_lines.sort(key=lambda row: row["reference_profit_this_year_gbp"], reverse=True)
    return {
        "source_campaign": payload.get("campaign_id"),
        "reference_policy_id": reference_policy,
        "variant_policy_id": variant_policy,
        "profit_scope": (
            "Somme VEHS profit_this_year/256 des vehicules encore presents au checkpoint; "
            "vehicules vendus et revenus/couts bruts de ligne non observables ici."
        ),
        "per_pair_year": per_pair,
        "annual": annual,
        "correlations": correlations,
        "top_reference_only_aaahogex_air_markets": lost_lines[:100],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    report = compare(payload)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("year pairs ref_air early_air ref_only ref_only_profit early-ref_profit overlap_opex")
    for item in report["annual"]:
        m = item["metrics"]
        print(
            f"{item['year']} {item['pairs']} "
            f"{m['reference_markets']['mean']:.2f} {m['variant_markets']['mean']:.2f} "
            f"{m['reference_only_markets']['mean']:.2f} "
            f"{m['reference_only_profit_gbp']['mean']:.0f} "
            f"{m['air_profit_delta_gbp']['mean']:.0f} "
            f"{m['reference_only_overlap_opex_any']['mean']:.2f}"
        )


if __name__ == "__main__":
    main()
