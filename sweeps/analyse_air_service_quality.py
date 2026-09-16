"""Analyse passive de la qualite de service AIR OpexAI vs AAAHogEx.

Utilise uniquement la telemetrie C66 extraite des sauvegardes :
VEHS (profit/capacite/flotte), ORDL/ORDR (route), STNN (TownID, tuile et
STNN.goods). Aucun revenu ni running_cost de ligne n'est reconstruit.

Attention : STNN.goods.max_waiting_cargo est le maximum atteint depuis le
dernier recalcul de note, pas le stock instantane.
"""

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics


DISTANCE_BANDS = (
    (0, 96),
    (96, 128),
    (128, 160),
    (160, 192),
    (192, 10_000),
)


def _mean(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return round(statistics.mean(values), 6) if values else None


def _median(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return round(statistics.median(values), 6) if values else None


def _ratio(num, den):
    return round(num / den, 6) if den else None


def _tile_xy(tile, map_width):
    if not isinstance(tile, int) or tile < 0:
        return None
    return tile % map_width, tile // map_width


def _line_distance(line, map_width):
    coords = []
    for tile in line.get("ordered_station_tiles") or []:
        xy = _tile_xy(tile, map_width)
        if xy is not None and xy not in coords:
            coords.append(xy)
    if len(coords) < 2:
        return None
    a, b = coords[0], coords[1]
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    # L'ancien modele AIR du projet travaille sur une distance de carte;
    # on conserve deux mesures explicites plutot que d'en inventer une unique.
    manhattan = dx + dy
    octile = max(dx, dy) + 0.41421356237 * min(dx, dy)
    euclidean = math.hypot(dx, dy)
    return {
        "dx": dx,
        "dy": dy,
        "manhattan": round(manhattan, 6),
        "octile": round(octile, 6),
        "euclidean": round(euclidean, 6),
    }


def _quality(line):
    observations = []
    for endpoint in line.get("endpoint_cargo_stats") or []:
        for cargo, good in (endpoint.get("cargo") or {}).items():
            observations.append({
                "station_id": endpoint.get("station_id"),
                "town_id": endpoint.get("town_id"),
                "cargo": str(cargo),
                "rated": bool(good.get("rated")),
                "rating": good.get("rating"),
                "time_since_pickup": good.get("time_since_pickup"),
                "max_waiting_cargo": good.get("max_waiting_cargo"),
            })

    rated = [o for o in observations if o["rated"] and isinstance(o["rating"], (int, float))]
    finite_pickup = [
        o["time_since_pickup"] for o in observations
        if isinstance(o["time_since_pickup"], (int, float)) and o["time_since_pickup"] < 255
    ]
    waiting = [
        o["max_waiting_cargo"] for o in observations
        if isinstance(o["max_waiting_cargo"], (int, float))
    ]
    return {
        "endpoint_cargo_observations": len(observations),
        "rated_observations": len(rated),
        "rated_share": _ratio(len(rated), len(observations)),
        "rating_mean": _mean([o["rating"] for o in rated]),
        "rating_median": _median([o["rating"] for o in rated]),
        "rating_min": min((o["rating"] for o in rated), default=None),
        "time_since_pickup_mean": _mean(finite_pickup),
        "time_since_pickup_median": _median(finite_pickup),
        "time_since_pickup_max": max(finite_pickup, default=None),
        "never_picked_observations": sum(
            1 for o in observations
            if isinstance(o["time_since_pickup"], (int, float)) and o["time_since_pickup"] >= 255
        ),
        "never_picked_share": _ratio(
            sum(
                1 for o in observations
                if isinstance(o["time_since_pickup"], (int, float)) and o["time_since_pickup"] >= 255
            ),
            len(observations),
        ),
        "max_waiting_mean": _mean(waiting),
        "max_waiting_median": _median(waiting),
        "max_waiting_max": max(waiting, default=None),
        "max_waiting_sum": sum(waiting),
        "observations": observations,
    }


def _flatten(payload, policy_id, map_width):
    rows = []
    snapshots = (payload.get("line_telemetry") or {}).get("snapshots") or []
    for snap in snapshots:
        if snap.get("duel_policy_id") != policy_id:
            continue
        for line in snap.get("lines") or []:
            if line.get("mode") != "air":
                continue
            distance = _line_distance(line, map_width)
            capacity = sum((line.get("capacity_by_cargo") or {}).values())
            quality = _quality(line)
            rows.append({
                "arm": snap.get("arm"),
                "seed": snap.get("seed"),
                "repeat": snap.get("repeat", 0),
                "year": snap.get("year"),
                "market_key": line.get("market_key"),
                "service_key": line.get("service_key"),
                "line_key_local": line.get("line_key_local"),
                "town_ids": line.get("town_ids") or [],
                "cargo_types": line.get("cargo_types") or [],
                "vehicles": line.get("vehicles") or 0,
                "capacity": capacity,
                "profit_this_year_gbp": line.get("profit_this_year_gbp") or 0,
                "profit_last_year_gbp": line.get("profit_last_year_gbp") or 0,
                "profit_per_vehicle": _ratio(
                    line.get("profit_this_year_gbp") or 0,
                    line.get("vehicles") or 0,
                ),
                "profit_per_capacity": _ratio(
                    line.get("profit_this_year_gbp") or 0,
                    capacity,
                ),
                "max_waiting_per_capacity": _ratio(
                    quality["max_waiting_sum"],
                    capacity,
                ),
                "distance": distance,
                "quality": quality,
            })
    return rows


def _summarise(rows):
    if not rows:
        return {"n_lines": 0}
    total_profit = sum(row["profit_this_year_gbp"] for row in rows)
    total_capacity = sum(row["capacity"] for row in rows)
    total_vehicles = sum(row["vehicles"] for row in rows)
    quality_obs = [
        obs
        for row in rows
        for obs in row["quality"]["observations"]
    ]
    rated = [
        obs for obs in quality_obs
        if obs["rated"] and isinstance(obs["rating"], (int, float))
    ]
    finite_pickup = [
        obs["time_since_pickup"] for obs in quality_obs
        if isinstance(obs["time_since_pickup"], (int, float))
        and obs["time_since_pickup"] < 255
    ]
    waiting = [
        obs["max_waiting_cargo"] for obs in quality_obs
        if isinstance(obs["max_waiting_cargo"], (int, float))
    ]
    octile = [
        row["distance"]["octile"] for row in rows if row["distance"] is not None
    ]
    return {
        "n_lines": len(rows),
        "n_endpoint_cargo_observations": len(quality_obs),
        "vehicles": total_vehicles,
        "capacity": total_capacity,
        "profit_this_year_gbp": round(total_profit, 6),
        "vehicles_per_line": _ratio(total_vehicles, len(rows)),
        "capacity_per_line": _ratio(total_capacity, len(rows)),
        "profit_per_line": _ratio(total_profit, len(rows)),
        "profit_per_vehicle": _ratio(total_profit, total_vehicles),
        "profit_per_capacity": _ratio(total_profit, total_capacity),
        "distance_octile_mean": _mean(octile),
        "distance_octile_median": _median(octile),
        "rated_share": _ratio(len(rated), len(quality_obs)),
        "rating_mean": _mean([obs["rating"] for obs in rated]),
        "rating_median": _median([obs["rating"] for obs in rated]),
        "time_since_pickup_mean": _mean(finite_pickup),
        "time_since_pickup_median": _median(finite_pickup),
        "never_picked_share": _ratio(
            sum(
                1 for obs in quality_obs
                if isinstance(obs["time_since_pickup"], (int, float))
                and obs["time_since_pickup"] >= 255
            ),
            len(quality_obs),
        ),
        "max_waiting_mean": _mean(waiting),
        "max_waiting_median": _median(waiting),
        "max_waiting_per_capacity": _ratio(sum(waiting), total_capacity),
    }


def _distance_band(distance):
    if distance is None:
        return None
    value = distance["octile"]
    for low, high in DISTANCE_BANDS:
        if low <= value < high:
            return f"{low}-{high if high < 10_000 else 'plus'}"
    return None


def analyse(payload, policy_id="early_slot", map_width=256):
    rows = _flatten(payload, policy_id, map_width)

    annual = []
    for (year, arm), group in sorted(
        ((key, list(values)) for key, values in _group(rows, lambda r: (r["year"], r["arm"]))),
        key=lambda item: (item[0][0], item[0][1]),
    ):
        annual.append({"year": year, "arm": arm, **_summarise(group)})

    by_distance = []
    for (year, arm, band), group in sorted(
        ((key, list(values)) for key, values in _group(
            [r for r in rows if _distance_band(r["distance"]) is not None],
            lambda r: (r["year"], r["arm"], _distance_band(r["distance"])),
        )),
        key=lambda item: (item[0][0], item[0][1], item[0][2]),
    ):
        by_distance.append({"year": year, "arm": arm, "distance_band": band, **_summarise(group)})

    by_fleet_size = []
    for (year, arm, fleet), group in sorted(
        ((key, list(values)) for key, values in _group(
            rows,
            lambda r: (r["year"], r["arm"], "1" if r["vehicles"] == 1 else "2plus"),
        )),
        key=lambda item: (item[0][0], item[0][1], item[0][2]),
    ):
        by_fleet_size.append({"year": year, "arm": arm, "fleet_size": fleet, **_summarise(group)})

    # Marches comparables : meme seed, annee et TownID. On garde seulement les
    # marches pour lesquels chaque IA a une seule ligne AIR locale afin de ne pas
    # inventer une aggregation de rating entre groupes heterogenes.
    index = defaultdict(lambda: defaultdict(list))
    for row in rows:
        index[(row["seed"], row["repeat"], row["year"], row["market_key"])][row["arm"]].append(row)

    matched = []
    for key, arms in index.items():
        if len(arms.get("OpexAI", [])) != 1 or len(arms.get("AAAHogEx", [])) != 1:
            continue
        opex = arms["OpexAI"][0]
        aaa = arms["AAAHogEx"][0]
        # Service strict : memes cargos portes par les deux lignes.
        cargo_match = sorted(opex["cargo_types"]) == sorted(aaa["cargo_types"])
        matched.append({
            "seed": key[0],
            "repeat": key[1],
            "year": key[2],
            "market_key": key[3],
            "cargo_match": cargo_match,
            "distance_octile_opex": (
                opex["distance"]["octile"] if opex["distance"] else None
            ),
            "distance_octile_aaahogex": (
                aaa["distance"]["octile"] if aaa["distance"] else None
            ),
            "opex": _row_projection(opex),
            "aaahogex": _row_projection(aaa),
        })

    matched_summary = []
    years = sorted({row["year"] for row in matched})
    for year in years:
        for strict in (False, True):
            group = [
                row for row in matched
                if row["year"] == year and (row["cargo_match"] or not strict)
            ]
            matched_summary.append(
                _matched_summary(year, group, strict)
            )

    return {
        "source_campaign": payload.get("campaign_id"),
        "policy_id": policy_id,
        "map_width": map_width,
        "distance_note": (
            "distance_octile = max(dx,dy)+0.41421356237*min(dx,dy); "
            "Manhattan et euclidean sont aussi conserves par ligne."
        ),
        "goods_note": (
            "rating n'est retenu que si status&1 et time_since_pickup<255; "
            "max_waiting_cargo est le maximum depuis le dernier recalcul de note, "
            "pas le stock instantane."
        ),
        "profit_note": (
            "profit VEHS des vehicules presents au checkpoint; aucun revenu ou "
            "running_cost de ligne reconstruit."
        ),
        "annual": annual,
        "by_distance": by_distance,
        "by_fleet_size": by_fleet_size,
        "matched_markets": matched,
        "matched_summary": matched_summary,
    }


def _group(rows, key_func):
    groups = defaultdict(list)
    for row in rows:
        groups[key_func(row)].append(row)
    return groups.items()


def _row_projection(row):
    q = row["quality"]
    return {
        "vehicles": row["vehicles"],
        "capacity": row["capacity"],
        "profit_this_year_gbp": row["profit_this_year_gbp"],
        "profit_per_vehicle": row["profit_per_vehicle"],
        "profit_per_capacity": row["profit_per_capacity"],
        "rated_share": q["rated_share"],
        "rating_mean": q["rating_mean"],
        "rating_min": q["rating_min"],
        "time_since_pickup_mean": q["time_since_pickup_mean"],
        "time_since_pickup_max": q["time_since_pickup_max"],
        "never_picked_share": q["never_picked_share"],
        "max_waiting_mean": q["max_waiting_mean"],
        "max_waiting_max": q["max_waiting_max"],
        "max_waiting_per_capacity": row["max_waiting_per_capacity"],
    }


def _matched_summary(year, rows, strict):
    fields = (
        "vehicles",
        "capacity",
        "profit_this_year_gbp",
        "profit_per_vehicle",
        "profit_per_capacity",
        "rated_share",
        "rating_mean",
        "rating_min",
        "time_since_pickup_mean",
        "time_since_pickup_max",
        "never_picked_share",
        "max_waiting_mean",
        "max_waiting_max",
        "max_waiting_per_capacity",
    )
    result = {
        "year": year,
        "strict_cargo_match": strict,
        "n_markets": len(rows),
    }
    for arm, key in (("opex", "opex"), ("aaahogex", "aaahogex")):
        result[arm] = {
            field: {
                "mean": _mean([
                    row[key][field] for row in rows
                    if isinstance(row[key][field], (int, float))
                ]),
                "median": _median([
                    row[key][field] for row in rows
                    if isinstance(row[key][field], (int, float))
                ]),
            }
            for field in fields
        }
    comparisons = (
        ("rating_mean", "aaahogex_higher_rating"),
        ("time_since_pickup_mean", "aaahogex_longer_pickup"),
        ("max_waiting_per_capacity", "aaahogex_higher_waiting_pressure"),
        ("profit_per_capacity", "aaahogex_higher_profit_per_capacity"),
    )
    result["pairwise_counts"] = {}
    for field, label in comparisons:
        comparable = [
            row for row in rows
            if isinstance(row["opex"][field], (int, float))
            and isinstance(row["aaahogex"][field], (int, float))
        ]
        result["pairwise_counts"][label] = {
            "n": len(comparable),
            "aaahogex_higher": sum(
                row["aaahogex"][field] > row["opex"][field] for row in comparable
            ),
            "opex_higher": sum(
                row["opex"][field] > row["aaahogex"][field] for row in comparable
            ),
            "equal": sum(
                row["opex"][field] == row["aaahogex"][field] for row in comparable
            ),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--policy-id", default="early_slot")
    parser.add_argument("--map-width", type=int, default=256)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = analyse(payload, args.policy_id, args.map_width)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("year arm n veh/line dist rating pickup wait profit/cap")
    for row in report["annual"]:
        print(
            row["year"], row["arm"], row["n_lines"],
            row["vehicles_per_line"], row["distance_octile_mean"],
            row["rating_mean"], row["time_since_pickup_mean"],
            row["max_waiting_mean"], row["profit_per_capacity"],
        )
    print("matched strict year n rating O/A pickup O/A profit/cap O/A")
    for row in report["matched_summary"]:
        if not row["strict_cargo_match"]:
            continue
        print(
            row["year"], row["n_markets"],
            row["opex"]["rating_mean"]["mean"],
            row["aaahogex"]["rating_mean"]["mean"],
            row["opex"]["time_since_pickup_mean"]["mean"],
            row["aaahogex"]["time_since_pickup_mean"]["mean"],
            row["opex"]["profit_per_capacity"]["mean"],
            row["aaahogex"]["profit_per_capacity"]["mean"],
        )


if __name__ == "__main__":
    main()
