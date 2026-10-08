"""Audit actual shared house sources from retained frozen duel savegames."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import openttdlab
from campaign_freeze import fingerprint_tree
from station_source_map import decode_map, original_house_populations, audit_sources
from station_supply import extract_station_supply, supply_intervals
from analyse_station_supply import metrics


def analyse(bench_path, archive_path, house_table, game_index=0):
    bench_path, archive_path, house_table = map(Path, (bench_path, archive_path, house_table))
    bench = json.loads(bench_path.read_text(encoding="utf8"))
    manifest_path = bench_path.with_suffix(".manifest.json")
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != bench["manifest_sha256"]:
        raise ValueError("manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    bundle = bench_path.parent / Path(manifest["source_bundle"]["path"]).name
    identity = fingerprint_tree(bundle)
    if identity["sha256"] != bench["source_bundle_sha256"]:
        raise ValueError("bundle hash mismatch")
    table_bytes = house_table.read_bytes()
    if hashlib.sha256(table_bytes).hexdigest() != "e8d6962f0212613fa354929c628fc2ce4d377c634690f9983a5c0e6548460679":
        raise ValueError("house table is not the verified original 15.3 source")
    populations = original_house_populations(table_bytes.decode("utf8"))
    planned = manifest["games"][game_index]
    matching = [g for g in bench["games"] if g["game_id"] == planned["game_id"]]
    if len(matching) != 1:
        raise ValueError("archive experiment identity absent/ambiguous")
    game_report = matching[0]
    if not game_report["game_ok"] or not all(c["horizon_complete"] and c["run_ok"]
                                             for c in game_report["companies"].values()):
        raise ValueError("unhealthy or incomplete duel")
    log = bench_path.parent / "bench_engine" / Path(game_report["engine_log_path"]).name
    text = log.read_text(encoding="utf8")
    cargo_ids = {int(m) for m in re.findall(r"\[1\] \[I\].*?\bid:(\d+) .*?label:PASS\b", text)}
    if len(cargo_ids) != 1:
        raise ValueError("PASS runtime identity absent/ambiguous")
    cargo = cargo_ids.pop()
    archive_file = archive_path / str(game_index) / "archive.json"
    archive = json.loads(archive_file.read_text(encoding="utf8"))
    snapshots = []
    for saved in archive["savegames"]:
        path = archive_file.parent / saved["path"]
        data = path.read_bytes()
        if len(data) != saved["bytes"] or hashlib.sha256(data).hexdigest() != saved["sha256"]:
            raise ValueError("raw savegame identity mismatch")
        game = openttdlab.parse_savegame((data,))
        chunks = {k: v["records"] for k, v in game["chunks"].items()}
        if not {"0", "1"}.issubset(chunks["PLYR"]):
            raise ValueError("both companies absent from raw save")
        decoded = decode_map(data, game, populations)
        audit = audit_sources(decoded, game, cargo)
        snapshots.append({"savegame": saved["path"], "sha256": saved["sha256"],
                          "economy_date": chunks["DATE"]["0"]["economy_date"],
                          "house_tiles": len(decoded["houses"]),
                          "station_supply": extract_station_supply(chunks, 0), **audit})
    snapshots.sort(key=lambda s: s["economy_date"])
    if not snapshots:
        raise ValueError("no raw snapshots")
    if len({s["economy_date"] for s in snapshots}) != len(snapshots):
        raise ValueError("duplicate snapshot dates")
    counts = Counter()
    for snapshot in snapshots:
        for row in snapshot["station_sources"].values():
            if row["owner"] == 0 and row["airport"] and row["source_weight"] > 0:
                counts["opex_air_station_snapshots"] += 1
                counts["shared_source_snapshots"] += int(row["shared_rival_weight"] > 0)
    cases, excluded = [], Counter()
    for previous, current in zip(snapshots, snapshots[1:]):
        for interval in supply_intervals(previous["station_supply"], current["station_supply"]):
            if not interval["exact"]:
                excluded[interval["reason"]] += 1
                continue
            if interval["cargo"] != cargo:
                continue
            row = previous["station_sources"].get(interval["station"])
            if (row is None or not row["airport"] or row["all_companies_monthly"] is None
                    or row["b9_visible_monthly"] is None):
                excluded["missing_initial_air_forecast"] += 1
                continue
            cases.append({"game_id": game_report["game_id"], "seed": game_report["seed"],
                          "station": interval["station"], "start_date": interval["start_date"],
                          "actual": interval["monthly_captured"],
                          "own_only": row["own_only_monthly"],
                          "visible_airports": row["visible_airports_monthly"],
                          "b9_own": row["b9_own_monthly"], "b9_visible": row["b9_visible_monthly"],
                          "all_companies": row["all_companies_monthly"]})
    return {"campaign": bench["campaign_id"], "game_id": game_report["game_id"],
            "seed": game_report["seed"], "game_index": game_index,
            "bundle_sha256": bench["source_bundle_sha256"],
            "manifest_sha256": bench["manifest_sha256"],
            "archive_sha256": hashlib.sha256(archive_file.read_bytes()).hexdigest(),
            "runtime_log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            "pass_cargo": cargo, "counts": dict(counts), "snapshots": snapshots,
            "one_step_forecast_cases": cases, "interval_exclusions": dict(excluded),
            "one_step_metrics": {key: metrics(cases, key) for key in ("own_only", "all_companies", "visible_airports", "b9_own", "b9_visible")},
            "limitation": "snapshot continuous mechanism weights, not annual forecast or economic qualification"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bench", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("house_table", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--game-index", type=int, default=0)
    args = parser.parse_args()
    result = analyse(args.bench, args.archive, args.house_table, args.game_index)
    with args.out.open("x", encoding="utf8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"campaign": result["campaign"], "snapshots": len(result["snapshots"]),
                      "counts": result["counts"]}))
