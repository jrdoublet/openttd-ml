"""Offline AIR geometry contact versus frozen passenger forecast errors.

Airport rectangles expanded by 4/6/10 are sensitivity proxies, NOT exact
catchments or producer overlap. Joined facilities and non-AIR rivals are absent.
No correction is fitted and no opponent information becomes a NoAI feature.
"""
import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import re

from analyse_station_supply import analyse, metrics


def allocation_fraction(owner, station_rating, owner_ratings):
    """Engine's continuous allocation, eligible stations only, before rounding."""
    if not 0 < station_rating <= 255:
        return 0.0
    groups = {o: [r for r in values if r > 0] for o, values in owner_ratings.items()}
    groups = {o: values for o, values in groups.items() if values}
    if owner not in groups or station_rating not in groups[owner]:
        raise ValueError("candidate absent from eligible stations")
    if any(r > 255 for values in groups.values() for r in values):
        raise ValueError("invalid rating")
    best = {o: max(values) for o, values in groups.items()}
    return ((max(best.values()) + 1) / 256 * best[owner] / sum(best.values())
            * station_rating / sum(groups[owner]))


def airport_rect(airport, radius, width, height):
    if not isinstance(airport, dict):
        return None
    fields = ("tile", "width", "height")
    if not all(isinstance(airport.get(k), int) and not isinstance(airport[k], bool)
               for k in fields):
        return None
    tile, w, h = (airport[k] for k in fields)
    if not 0 <= tile < width * height or w <= 0 or h <= 0:
        return None
    x, y = tile % width, tile // width
    if x + w > width or y + h > height:
        return None
    return max(0, x - radius), max(0, y - radius), min(width - 1, x + w - 1 + radius), min(height - 1, y + h - 1 + radius)


def intersects(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def endpoints(row, cargo):
    out = {}
    telemetry = row.get("line_telemetry") or {}
    if not telemetry.get("ok"):
        return out
    for line in telemetry.get("lines", []):
        if line.get("mode") != "air":
            continue
        for end in line.get("endpoint_cargo_stats", []):
            good = end.get("cargo", {}).get(str(cargo), {})
            if not good.get("rated") or not isinstance(good.get("rating"), int) or good["rating"] <= 0:
                continue
            station = end["station_id"]
            if station in out and out[station] != end:
                raise ValueError("conflicting endpoint observations")
            out[station] = end
    return out


def summarize(cases):
    result = metrics(cases, "initial_offered_proxy")
    result["overprediction_above_50pct"] = sum(c["initial_offered_proxy"] > 1.5 * c["actual"] for c in cases)
    return result


def contact_analysis(path):
    base = analyse(path)  # Shared provenance, health, exact interval selection.
    if not base["healthy_complete"]:
        raise ValueError("campaign unhealthy/incomplete")
    bench = json.loads(path.read_text(encoding="utf8"))
    manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf8"))
    cfg = manifest["configuration"]["parsed"]["game_creation"]
    width, height = 2 ** int(cfg["map_x"]), 2 ** int(cfg["map_y"])
    cargo_ids = {}
    for game in bench["games"]:
        log = path.parent / "bench_engine" / Path(game["engine_log_path"]).name
        ids = {int(c) for c in re.findall(r"\[1\] \[I\].*?\bid:(\d+) .*?label:PASS\b", log.read_text(encoding="utf8"))}
        if len(ids) != 1:
            raise ValueError("PASS identity ambiguous")
        cargo_ids[game["game_id"]] = ids.pop()
    snapshots = defaultdict(dict)
    with path.with_suffix(".jsonl").open(encoding="utf8") as f:
        for text in f:
            row = json.loads(text)
            key = row["game_id"], row["date"]
            slot = row["company_slot"]
            if slot in snapshots[key]:
                raise ValueError("duplicate company checkpoint")
            snapshots[key][slot] = row
    observations = defaultdict(list)
    for (game, stamp), pair in snapshots.items():
        if set(pair) != {0, 1}:
            continue
        if not all((r.get("line_telemetry") or {}).get("ok") for r in pair.values()):
            continue
        d = date.fromisoformat(stamp)
        month = d.year * 12 + d.month
        own, rival = (endpoints(pair[i], cargo_ids[game]) for i in (0, 1))
        for radius in (4, 6, 10):
            others = [airport_rect(e.get("airport"), radius, width, height) for e in rival.values()]
            others = [r for r in others if r is not None]
            for station, end in own.items():
                rect = airport_rect(end.get("airport"), radius, width, height)
                if rect is not None:
                    observations[game, station, radius].append((month, any(intersects(rect, r) for r in others)))
    result = {}
    for radius in (4, 6, 10):
        groups = defaultdict(list)
        excluded = 0
        for c in base["cases"]:
            anchor = c["anchor_year"] * 12 + 1
            past = [(m, contact) for m, contact in observations[c["game_id"], c["station"], radius]
                    if anchor - 12 <= m < anchor]
            if len(past) < 8:
                excluded += 1
                continue
            label = "potential_air_contact" if any(contact for _, contact in past) else "no_air_contact_in_proxy"
            split = "reserved" if c["seed"] in (73, 314, 512) else "development"
            groups[split + ":" + label].append(c)
        result[str(radius)] = {"excluded_insufficient_past_geometry": excluded,
                              "groups": {k: summarize(v) for k, v in sorted(groups.items())}}
    return {k: base[k] for k in ("campaign", "bundle_sha256", "manifest_sha256", "checkpoint_sha256", "log_hashes")} | {
        "status": "descriptive_airport_rectangle_contact_only", "base_cases": len(base["cases"]),
        "geometry_sensitivity": result, "economic_verdict": "not_evaluated"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bench", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = contact_analysis(args.bench)
    with args.out.open("x", encoding="utf8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "log_hashes"}, indent=2))


if __name__ == "__main__":
    main()
