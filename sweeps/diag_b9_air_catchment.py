"""B9/G4 : analyse passive du catchment et du placement AIR.

Combine les evenements AIR_CATCHMENT_* du probe OpexAI default-off avec la
geometrie STNN des aeroports des deux IA exposee par --line-telemetry.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) (AIR_CATCHMENT_ENDPOINT|AIR_CATCHMENT_BUILD)\s*(.*)$")


def parse_fields(text):
    out = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass
        out[key] = value
    return out


def parse_probe_line(raw):
    match = EVENT_RE.search(raw or "")
    if not match:
        return None
    year, month, day, kind, rest = match.groups()
    return {"date": f"{int(year):04d}-{int(month):02d}-{int(day):02d}",
            "kind": kind, **parse_fields(rest)}


def _game_key(row):
    if row.get("game_id"):
        return str(row["game_id"])
    run = row.get("run") or []
    seed = run[1] if len(run) > 1 else row.get("seed")
    repeat = run[2] if len(run) > 2 else row.get("repeat", 0)
    policy = row.get("duel_policy_id") or row.get("policy_id") or "probe"
    return f"{policy}|s{seed}|r{repeat}"


def collect_probe_events(checkpoint_rows):
    games = defaultdict(list)
    for row in checkpoint_rows:
        if row.get("company_slot") not in (None, 0):
            continue
        run = row.get("run") or []
        if row.get("company_slot") is None and run and not str(run[0]).startswith("OpexAI"):
            continue
        games[_game_key(row)].append(row)
    out = {}
    for game_id, rows in games.items():
        seen, events = set(), []
        for row in sorted(rows, key=lambda item: str(item.get("date") or "")):
            run = row.get("run") or []
            seed = run[1] if len(run) > 1 else row.get("seed")
            for raw in (row.get("openttd_output") or "").splitlines():
                idx = raw.find("OPEX ")
                if idx < 0:
                    continue
                event_text = raw[idx:]
                if event_text in seen:
                    continue
                parsed = parse_probe_line(event_text)
                if parsed is None:
                    continue
                seen.add(event_text)
                parsed["seed"] = seed
                parsed["game_id"] = game_id
                events.append(parsed)
        out[game_id] = events
    return out


def collect_probe_events_from_engine_logs(engine_dir):
    """Relit les logs moteur deja produits par le banc.

    Le harnais duel historique n'attache pas la sortie moteur aux records
    persistes ; les logs complets restent toutefois ecrits par keep().
    """
    out = {}
    engine_dir = Path(engine_dir)
    seed_re = re.compile(r"_seed(\d+)_r(\d+)\.log$")
    for path in sorted(engine_dir.glob("*.log")):
        match = seed_re.search(path.name)
        if not match:
            continue
        seed = int(match.group(1))
        repeat = int(match.group(2))
        game_id = f"engine|s{seed}|r{repeat}"
        seen = set()
        events = []
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            idx = raw.find("OPEX ")
            if idx < 0:
                continue
            event_text = raw[idx:]
            if event_text in seen:
                continue
            parsed = parse_probe_line(event_text)
            if parsed is None:
                continue
            seen.add(event_text)
            parsed["seed"] = seed
            parsed["game_id"] = game_id
            events.append(parsed)
        out[game_id] = events
    return out


def pair_builds(events):
    pending, builds = [], []
    orphan_endpoints = orphan_builds = 0
    for event in events:
        if event["kind"] == "AIR_CATCHMENT_ENDPOINT":
            pending.append(event)
            if len(pending) > 2:
                orphan_endpoints += len(pending) - 2
                pending = pending[-2:]
            continue
        if event["kind"] != "AIR_CATCHMENT_BUILD":
            continue
        endpoints = pending[-2:] if len(pending) >= 2 else []
        if len(endpoints) != 2:
            orphan_builds += 1
        builds.append({**event, "endpoints": endpoints})
        pending = []
    orphan_endpoints += len(pending)
    return builds, orphan_endpoints, orphan_builds


def summary_stats(values):
    values = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {"n": len(values), "mean": round(statistics.mean(values), 6),
            "median": round(statistics.median(values), 6),
            "min": min(values), "max": max(values)}


def summarise_probe(games):
    all_events = [event for events in games.values() for event in events]
    endpoints = [event for event in all_events if event["kind"] == "AIR_CATCHMENT_ENDPOINT"]
    builds, orphan_endpoints, orphan_builds = [], 0, 0
    for events in games.values():
        paired, oe, ob = pair_builds(events)
        builds.extend(paired)
        orphan_endpoints += oe
        orphan_builds += ob
    new_endpoints = [event for event in endpoints if event.get("reused") == 0]
    newpairs = [build for build in builds if build.get("arm") == "newpair"
                and len(build["endpoints"]) == 2
                and build.get("reuse_a") == 0 and build.get("reuse_b") == 0]
    base_vs_union, base_plus_raw_vs_union = [], []
    for build in newpairs:
        union = sum(endpoint.get("union_pax_prod", 0) for endpoint in build["endpoints"])
        base, raw = build.get("base_monthly"), build.get("raw_joined_total")
        if isinstance(base, (int, float)):
            base_vs_union.append(base - union)
        if isinstance(base, (int, float)) and isinstance(raw, (int, float)):
            base_plus_raw_vs_union.append(base + raw - union)
    reserve_delta = [build["reserve_stop_cost"] - build["actual_stop_cost"] for build in builds
                     if isinstance(build.get("reserve_stop_cost"), (int, float))
                     and isinstance(build.get("actual_stop_cost"), (int, float))]
    stop_utilisation = []
    for build in builds:
        limit = build.get("stop_limit")
        if not isinstance(limit, (int, float)):
            continue
        new_airports = 2 - int(build.get("reuse_a", 0) or 0) - int(build.get("reuse_b", 0) or 0)
        reserved_capacity = max(0, new_airports * int(limit))
        actual = int(build.get("stops_a", 0) or 0) + int(build.get("stops_b", 0) or 0)
        stop_utilisation.append((actual, reserved_capacity))
    invariant_failures = []
    for endpoint in endpoints:
        for cargo in ("pax", "mail"):
            airport, union = endpoint.get(f"airport_{cargo}_prod"), endpoint.get(f"union_{cargo}_prod")
            if isinstance(airport, (int, float)) and isinstance(union, (int, float)) and union < airport:
                invariant_failures.append({"game_id": endpoint.get("game_id"),
                    "date": endpoint.get("date"), "endpoint": endpoint.get("endpoint"),
                    "invariant": f"union_{cargo}_prod>=airport_{cargo}_prod",
                    "airport": airport, "union": union})
    return {
        "games_with_probe": sum(bool(events) for events in games.values()),
        "events": len(all_events), "endpoint_events": len(endpoints), "build_events": len(builds),
        "orphan_endpoints": orphan_endpoints, "orphan_builds": orphan_builds,
        "invariant_failures": invariant_failures,
        "airport_types": dict(Counter(str(event.get("airport_type")) for event in endpoints)),
        "airport_width": summary_stats(event.get("airport_w") for event in endpoints),
        "airport_height": summary_stats(event.get("airport_h") for event in endpoints),
        "airport_radius": summary_stats(event.get("airport_radius") for event in endpoints),
        "rect_distance": summary_stats(event.get("rect_distance") for event in endpoints),
        "center_distance": summary_stats(event.get("center_distance") for event in endpoints),
        "town_center_in_airport_share": round(sum(event.get("town_center_airport") == 1 for event in endpoints) / len(endpoints), 6) if endpoints else None,
        "town_center_in_union_share": round(sum(event.get("town_center_union") == 1 for event in endpoints) / len(endpoints), 6) if endpoints else None,
        "airport_pax_prod": summary_stats(event.get("airport_pax_prod") for event in endpoints),
        "union_pax_prod": summary_stats(event.get("union_pax_prod") for event in endpoints),
        "airport_mail_prod": summary_stats(event.get("airport_mail_prod") for event in endpoints),
        "union_mail_prod": summary_stats(event.get("union_mail_prod") for event in endpoints),
        "joined_marginal_pax": summary_stats(event.get("joined_marginal_pax") for event in new_endpoints),
        "raw_joined_pax": summary_stats(event.get("raw_joined_pax") for event in new_endpoints),
        "model_joined_pax": summary_stats(event.get("model_joined_pax") for event in new_endpoints),
        "model_error_pax": summary_stats(event.get("model_error_pax") for event in new_endpoints),
        "model_error_nonzero": sum((event.get("model_error_pax") or 0) != 0 for event in new_endpoints),
        "overlap_overcount_pax": summary_stats(event.get("overlap_overcount_pax") for event in new_endpoints),
        "overlap_overcount_positive": sum((event.get("overlap_overcount_pax") or 0) > 0 for event in new_endpoints),
        "raw_undercount_pax": summary_stats(event.get("raw_undercount_pax") for event in new_endpoints),
        "probe_ops_endpoint": summary_stats(event.get("probe_ops") for event in endpoints),
        "probe_ops_build": summary_stats(build.get("probe_ops") for build in builds),
        "reserve_minus_actual_stop_cost": summary_stats(reserve_delta),
        "reserve_over_actual_count": sum(delta > 0 for delta in reserve_delta),
        "reserve_under_actual_count": sum(delta < 0 for delta in reserve_delta),
        "actual_stops": summary_stats(actual for actual, _ in stop_utilisation),
        "reserved_stop_capacity": summary_stats(capacity for _, capacity in stop_utilisation),
        "underfilled_stop_reserve_count": sum(actual < capacity for actual, capacity in stop_utilisation),
        "newpair_base_minus_union_pax": summary_stats(base_vs_union),
        "newpair_base_plus_raw_minus_union_pax": summary_stats(base_plus_raw_vs_union),
        "base_sources": dict(Counter(str(build.get("base_source")) for build in builds)),
    }


def _tile_xy(tile, map_width):
    if not isinstance(tile, int) or tile < 0 or tile == 0xFFFFFFFF:
        return None
    return tile % map_width, tile // map_width


def _rect_distance(tile, anchor, width, height, map_width):
    point, start = _tile_xy(tile, map_width), _tile_xy(anchor, map_width)
    if point is None or start is None or not width or not height:
        return None
    x, y = point
    left, top = start
    right, bottom = left + int(width) - 1, top + int(height) - 1
    dx = left - x if x < left else (x - right if x > right else 0)
    dy = top - y if y < top else (y - bottom if y > bottom else 0)
    return dx + dy


def extract_airport_snapshots(payload):
    rows, seen = [], set()
    for snap in (payload.get("line_telemetry") or {}).get("snapshots") or []:
        for line in snap.get("lines") or []:
            if line.get("mode") != "air":
                continue
            for endpoint in line.get("endpoint_cargo_stats") or []:
                airport = endpoint.get("airport")
                if not isinstance(airport, dict):
                    continue
                tile, width, height = airport.get("tile"), airport.get("width"), airport.get("height")
                if not isinstance(tile, int) or tile < 0 or tile == 0xFFFFFFFF:
                    continue
                if not isinstance(width, int) or width <= 0 or not isinstance(height, int) or height <= 0:
                    continue
                key = (snap.get("arm"), snap.get("seed"), snap.get("year"), endpoint.get("station_id"))
                if key in seen:
                    continue
                seen.add(key)
                rows.append({"arm": snap.get("arm"), "seed": snap.get("seed"), "year": snap.get("year"),
                             "station_id": endpoint.get("station_id"), "town_id": endpoint.get("town_id"),
                             **airport})
    return rows


def summarise_geometry(payload, probe_games, map_width=256):
    rows = extract_airport_snapshots(payload)
    town_tiles, radius_by_type = {}, {}
    opex_airport_town = {}
    for events in probe_games.values():
        for event in events:
            if event["kind"] != "AIR_CATCHMENT_ENDPOINT":
                continue
            if event.get("seed") is not None and event.get("town") is not None and isinstance(event.get("town_tile"), int):
                town_tiles[(event["seed"], event["town"])] = event["town_tile"]
            if event.get("seed") is not None and isinstance(event.get("airport_tile"), int) and event.get("town") is not None:
                opex_airport_town[(event["seed"], event["airport_tile"])] = event["town"]
            if event.get("airport_type") is not None and isinstance(event.get("airport_radius"), (int, float)):
                radius_by_type[event["airport_type"]] = event["airport_radius"]

    offsets = []
    for row in rows:
        if row.get("arm") != "OpexAI":
            continue
        planned_town = opex_airport_town.get((row.get("seed"), row.get("tile")))
        raw_town = row.get("town_id")
        if isinstance(planned_town, int) and isinstance(raw_town, int):
            offsets.append(raw_town - planned_town)
    offset_counts = Counter(offsets)
    town_id_offset = offset_counts.most_common(1)[0][0] if offset_counts else 0
    offset_matches = sum(value == town_id_offset for value in offsets)
    offset_consistency = round(offset_matches / len(offsets), 6) if offsets else None

    by_arm = {}
    for arm in sorted({row["arm"] for row in rows if row.get("arm") is not None}):
        group = [row for row in rows if row.get("arm") == arm]
        placement, covered = [], []
        for row in group:
            raw_town = row.get("town_id")
            normalized_town = raw_town - town_id_offset if isinstance(raw_town, int) else raw_town
            distance = _rect_distance(town_tiles.get((row.get("seed"), normalized_town)),
                                      row.get("tile"), row.get("width"), row.get("height"), map_width)
            if distance is None:
                continue
            placement.append(distance)
            radius = radius_by_type.get(row.get("type"))
            if radius is not None:
                covered.append(distance <= radius)
        by_arm[arm] = {
            "airport_snapshots": len(group),
            "types": dict(Counter(str(row.get("type")) for row in group)),
            "width": summary_stats(row.get("width") for row in group),
            "height": summary_stats(row.get("height") for row in group),
            "placement_rect_distance_same_town_metadata_subset": summary_stats(placement),
            "town_center_covered_same_town_metadata_subset_share": round(sum(covered) / len(covered), 6) if covered else None,
            "placement_subset_n": len(placement), "coverage_subset_n": len(covered),
        }
    return {"map_width": map_width,
            "radius_by_type_observed_from_opex_probe": {str(k): v for k, v in sorted(radius_by_type.items())},
            "stnn_town_id_offset_inferred": town_id_offset,
            "stnn_town_id_offset_samples": len(offsets),
            "stnn_town_id_offset_counts": dict(Counter(str(value) for value in offsets)),
            "stnn_town_id_offset_consistency": offset_consistency,
            "town_metadata_pairs_from_opex_probe": len(town_tiles), "by_arm": by_arm}


def analyse(source_payload, checkpoint_rows, map_width=256, engine_dir=None):
    probe_games = collect_probe_events(checkpoint_rows)
    if not any(probe_games.values()) and engine_dir is not None:
        probe_games = collect_probe_events_from_engine_logs(engine_dir)
    return {
        "purpose": "B9/G4 measurement-only. No AIR policy/default adoption is authorised by this analysis.",
        "source_campaign": source_payload.get("campaign_id"),
        "source_bundle_sha256": source_payload.get("source_bundle_sha256"),
        "limitations": [
            "Exact pax/mail catchment production is measured only for OpexAI by the default-off NoAI probe.",
            "AAAHogEx geometry comes from STNN; exact AAAHogEx production by coverage tile is unavailable in current chunks.",
            "Cross-AI placement uses only TownID whose town tile was observed by the Opex probe in the same shared map.",
            "base_monthly is a model input; union_*_prod are tile-production measurements and remain separately labelled.",
        ],
        "probe": summarise_probe(probe_games),
        "geometry": summarise_geometry(source_payload, probe_games, map_width=map_width),
    }


def selftest():
    rows = [{"run": ["OpexAI[x]", 42, 0], "date": "1970-01-01",
             "openttd_output": "\n".join([
        "x OPEX 1970-1-1 AIR_CATCHMENT_ENDPOINT endpoint=A station=1 town=7 town_tile=100 town_pop=500 airport_tile=110 airport_type=1 airport_w=6 airport_h=6 airport_radius=5 rect_distance=2 center_distance=4 town_center_airport=1 town_center_union=1 coverage_tiles=120 airport_pax_prod=20 union_pax_prod=30 joined_marginal_pax=10 raw_joined_pax=15 overlap_overcount_pax=5 raw_undercount_pax=0 airport_mail_prod=5 union_mail_prod=7 joined_marginal_mail=2 reused=0 probe_ops=100",
        "x OPEX 1970-1-1 AIR_CATCHMENT_ENDPOINT endpoint=B station=2 town=8 town_tile=200 town_pop=600 airport_tile=210 airport_type=1 airport_w=6 airport_h=6 airport_radius=5 rect_distance=3 center_distance=5 town_center_airport=1 town_center_union=1 coverage_tiles=121 airport_pax_prod=25 union_pax_prod=35 joined_marginal_pax=10 raw_joined_pax=12 overlap_overcount_pax=2 raw_undercount_pax=0 airport_mail_prod=6 union_mail_prod=9 joined_marginal_mail=3 reused=0 probe_ops=110",
        "x OPEX 1970-1-1 AIR_CATCHMENT_BUILD arm=newpair base_source=town_population_share base_monthly=50 reserve_stop_cost=1000 actual_stop_cost=800 stop_limit=2 stops_a=1 stops_b=1 raw_joined_a=15 raw_joined_b=12 raw_joined_total=27 reuse_a=0 reuse_b=0 planned_capital=100000 actual_cost=90000 probe_ops=210"]) }]
    summary = summarise_probe(collect_probe_events(rows))
    assert summary["endpoint_events"] == 2 and summary["build_events"] == 1
    assert summary["overlap_overcount_positive"] == 2
    assert summary["invariant_failures"] == []
    assert summary["reserve_over_actual_count"] == 1
    assert summary["newpair_base_minus_union_pax"]["mean"] == -15
    print("selftest OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--map-width", type=int, default=256)
    parser.add_argument("--engine-dir", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    if args.source is None:
        parser.error("--source est requis")
    checkpoint = args.checkpoint or args.source.with_suffix(".jsonl")
    out = args.out or args.source.with_name(args.source.stem + "_analysis.json")
    payload = json.loads(args.source.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in checkpoint.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = analyse(payload, rows, map_width=args.map_width, engine_dir=args.engine_dir)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Analyse enregistree dans: {out}")


if __name__ == "__main__":
    main()
