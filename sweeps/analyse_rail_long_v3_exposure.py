"""Read-only physical exposure check for a retained RAIL-LONG duel.

Example (PowerShell 5.1):
    python -X utf8 sweeps/analyse_rail_long_v3_exposure.py \
        results/rail_long_v2_smoke_4x10_20261103_r1.json --date 1975-12-01

Requires the campaign's _saves/{0,1,...}/save/ monthly archives. Never
substitutes RAIL_BUILD logs for live consists. Fails closed on missing or
misaligned archives. The longest rail-station strip is a site-level proxy,
not proof that a particular vehicle uses that platform.
"""

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import median

import openttdlab
from station_source_map import raw_map_chunks


def _longest_rail_station_strip(raw, width):
    stations = defaultdict(set)
    for tile, tile_type in enumerate(raw["MAPT"]):
        if tile_type >> 4 != 5 or (raw["MAPE"][tile] >> 3) & 15:
            continue
        sid = int.from_bytes(raw["MAP2"][2 * tile:2 * tile + 2], "big")
        stations[sid].add(tile)
    lengths = {}
    for sid, tiles in stations.items():
        longest = 0
        for tile in tiles:
            if tile % width == 0 or tile - 1 not in tiles:
                run = 1
                while tile + run in tiles and (tile + run) % width:
                    run += 1
                longest = max(longest, run)
            if tile // width == 0 or tile - width not in tiles:
                run = 1
                while tile + run * width in tiles:
                    run += 1
                longest = max(longest, run)
        lengths[sid] = longest
    return lengths


def _chain(vehicles, head):
    node, seen, entries = int(head), set(), []
    while len(entries) < 150:
        if node in seen:
            raise ValueError(f"cycle in vehicle chain {head} at {node}")
        seen.add(node)
        record = vehicles.get(str(node))
        if not record or not record.get("train") or not record["train"][0].get("common"):
            raise ValueError(f"unresolved vehicle chain {head} at {node}")
        item = record["train"][0]["common"][0]
        entries.append(item)
        if item["next"] == 0:
            return entries
        node = item["next"] - 1  # OpenTTD savegame vehicle references are 1-based.
    raise ValueError(f"vehicle chain {head} longer than 150")


def analyse(campaign_path, saves_root, checkpoint, min_wagons, min_capacity):
    campaign = json.loads(campaign_path.read_text(encoding="utf8"))
    seeds = campaign["seeds"]
    if not campaign_path.is_file() or not saves_root.is_dir():
        raise ValueError("campaign or retained saves absent")
    policies = [item["id"] for item in campaign["policies"]]
    if len(policies) != 2 or "reference" not in policies:
        raise ValueError("expected a 1v1 reference/variant campaign")
    variant = next(item for item in policies if item != "reference")
    year, month, day = map(int, checkpoint.split("-"))
    if month != 12 or day != 1:
        raise ValueError("this tool requires a December 1 checkpoint")
    expected_idx = (year - int(campaign["start_year"])) * 12 + 10
    if expected_idx < 0:
        raise ValueError("checkpoint precedes campaign start")
    snaps = {
        (item["duel_policy_id"], int(item["seed"])): item
        for item in campaign["line_telemetry"]["snapshots"]
        if item["arm"] == "OpexAI" and item["date"] == checkpoint and item["ok"]
    }
    output = {}
    for i, seed in enumerate(seeds):
        for policy, offset in (("reference", 0), (variant, 1)):
            archive = saves_root / str(i * 2 + offset) / "save" / f"{expected_idx:09d}.sav"
            if not archive.is_file():
                raise ValueError(f"missing retained save: {archive}")
            game = openttdlab.parse_savegame((archive.read_bytes(),))
            chunks = game["chunks"]
            raw_date = chunks["DATE"]["records"]["0"]["date"]
            if date.fromordinal(raw_date - 365).isoformat() != checkpoint:
                raise ValueError(f"checkpoint mismatch in {archive}")
            snapshot = snaps.get((policy, int(seed)))
            if not snapshot:
                raise ValueError(f"missing OpexAI line snapshot {policy} seed {seed}")
            vehicles = chunks["VEHS"]["records"]
            heads = {
                int(vid) for vid, record in vehicles.items()
                if record.get("train") and record["train"][0].get("common")
                and record["train"][0]["common"][0]["owner"] == 0
                and (record["train"][0]["common"][0]["subtype"] & 9) == 9
            }
            expected = {
                int(vid) for line in snapshot["lines"] if line["mode"] == "rail"
                for vid in line["vehicle_ids"]
            }
            if heads != expected:
                raise ValueError(
                    f"head identity mismatch for {archive}: "
                    f"snapshot={len(expected)} physical={len(heads)}"
                )
            widths = _longest_rail_station_strip(
                raw_map_chunks(archive.read_bytes()),
                chunks["MAPS"]["records"]["0"]["dim_x"],
            )
            sample = output.setdefault(policy, {
                "wagons": [], "locomotives": [], "capacity": [],
                "platform_bottleneck": [], "source_rating_percent": [],
                "profit_gbp": [], "identified_freight_services": 0,
                "freight_consists": 0, "at_least_8_and_200": 0,
            })
            for line in snapshot["lines"]:
                freight = set(map(str, line.get("cargo_types", []))) - {"0", "2"}
                if line["mode"] != "rail" or not freight:
                    continue
                sample["identified_freight_services"] += 1
                stations = line.get("station_ids", [])
                if len(stations) == 2 and all(x in widths for x in stations):
                    sample["platform_bottleneck"].append(min(widths[x] for x in stations))
                if len(freight) == 1:
                    cargo = next(iter(freight))
                    matches = [
                        point["cargo"][cargo]["rating"]
                        for point in line.get("endpoint_cargo_stats", [])
                        if point["cargo"].get(cargo, {}).get("rated")
                        and not point["cargo"][cargo].get("accepts")
                        and point["cargo"][cargo].get("rating") is not None
                    ]
                    if len(matches) == 1:
                        sample["source_rating_percent"].append(matches[0] * 100.0 / 255.0)
                financial = {
                    int(x["vehicle_id"]): x.get("profit_this_year_gbp")
                    for x in line.get("vehicle_financials", [])
                }
                for head in line["vehicle_ids"]:
                    parts = _chain(vehicles, head)
                    wagons = sum(bool(x["subtype"] & 4) for x in parts)
                    locos = len(parts) - wagons
                    capacity = sum(
                        x["cargo_cap"] for x in parts
                        if (x["subtype"] & 4) and str(x["cargo_type"]) in freight
                    )
                    sample["wagons"].append(wagons)
                    sample["locomotives"].append(locos)
                    sample["capacity"].append(capacity)
                    sample["freight_consists"] += 1
                    sample["at_least_8_and_200"] += int(
                        wagons >= min_wagons and capacity >= min_capacity
                    )
                    if financial.get(int(head)) is not None:
                        sample["profit_gbp"].append(financial[int(head)])
    metrics = ("wagons", "locomotives", "capacity", "platform_bottleneck",
               "source_rating_percent", "profit_gbp")
    return {
        "campaign": campaign["campaign_id"], "checkpoint": checkpoint,
        "wagon_threshold": min_wagons, "capacity_threshold": min_capacity,
        "arms": {
            policy: {
                **{k: {"median": median(entry[k]) if entry[k] else None,
                       "samples": len(entry[k]),
                       "max": max(entry[k]) if entry[k] else None}
                   for k in metrics},
                **{k: entry[k] for k in (
                    "identified_freight_services", "freight_consists",
                    "at_least_8_and_200")},
                "revenue_per_train": None,
                "station_strip_caveat": "longest contiguous strip per StationID; not assigned platform",
            }
            for policy, entry in output.items()
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--saves", type=Path, default=None)
    parser.add_argument("--date", default="1975-12-01")
    parser.add_argument("--min-wagons", type=int, default=8)
    parser.add_argument("--min-capacity", type=int, default=200)
    args = parser.parse_args()
    saves = args.saves or args.campaign.with_name(args.campaign.stem + "_saves")
    print(json.dumps(
        analyse(args.campaign, saves, args.date, args.min_wagons, args.min_capacity),
        ensure_ascii=False, indent=2,
    ))
