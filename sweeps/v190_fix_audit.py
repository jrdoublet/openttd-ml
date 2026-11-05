"""Read-only audit of a completed V190-FIX duel JSON, logs and savegames.

No OpenTTD GUI, Docker process, or source file is touched by this script.
Use --saves 12 to follow one year of monthly vehicle locations and profits.
Two-train freight telemetry is a proxy for the V190 line identity; actual
V190 build_double events are counted independently from the script log.
"""

import argparse
import collections
import json
import re
from pathlib import Path


def freight(line):
    return line.get("mode") == "rail" and not (
        {"0", "2"} & set(map(str, line.get("cargo_types", ())))
    )


def local_path(value, root):
    value = str(value or "")
    if value.startswith("/work/"):
        return root / value[len("/work/"):]
    return root / value


def summarize_logs(path):
    if not path.exists():
        return {"log_found": False}
    counts = collections.Counter()
    identifiers = collections.Counter()
    build_dates = []
    for record in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "V190 action=build_double" in record:
            hit = re.search(r"V190 action=build_double line=([^ ]+)", record)
            if hit:
                counts["build_double"] += 1
                if hit.group(1).isdigit():
                    identifiers[hit.group(1)] += 1
                    date = re.search(r"OPEX (\d{4}-\d+-\d+)", record)
                    build_dates.append({"line_id": int(hit.group(1)), "date": date.group(1) if date else None})
                else:
                    counts["build_double_src_dst"] += 1
        if "V190 action=fallback_single" in record:
            counts["fallback_single"] += 1
            if "trains=2 reason=OK" in record:
                counts["false_fallback_2trains"] += 1
        if "RAIL_LOOP action=convert" in record:
            counts["converted_legacy_loop"] += 1
        if "VEHICLE_CRASHED" in record:
            counts["vehicle_crashed_log_hits"] += 1
        if re.search(r"\bLOST\b", record) and "vehicle=" in record:
            counts["lost_log_hits"] += 1
        if "RX|" in record:
            counts["rx_log_hits"] += 1
        if "Fatal" in record or "FATAL" in record:
            counts["fatal_log_hits"] += 1
    return {
        "log_found": True,
        "bytes": path.stat().st_size,
        "counts": dict(counts),
        "line_ids": dict(identifiers),
        "build_dates": build_dates,
    }


def vehicle_motion(folder, ids, save_limit):
    import openttdlab

    paths = sorted(folder.glob("*.sav"))
    if not paths:
        return {"savegame_found": False}
    sampled_paths = paths[-save_limit:] if save_limit > 0 else []
    motions = {str(v): [] for v in ids}
    rx = []
    states = []
    for path in sampled_paths:
        chunks = openttdlab.parse_savegame([path.read_bytes()])["chunks"]
        vehicles = chunks.get("VEHS", {}).get("records", {})
        signs = chunks.get("SIGN", {}).get("records", {})
        rx.extend(
            {"save": path.name, "name": x["name"]}
            for x in signs.values() if x.get("name", "").startswith("RX|")
        )
        states.extend(
            {"save": path.name, "name": x["name"]}
            for x in signs.values() if x.get("name", "").startswith("VS|")
        )
        for vid in motions:
            rec = vehicles.get(vid, {})
            if not rec.get("train"):
                continue
            if not rec["train"][0].get("common"):
                continue
            common = rec["train"][0]["common"][0]
            motions[vid].append({
                "save": path.name,
                "tile": common.get("tile"),
                "speed": common.get("cur_speed"),
                "order_dest": common.get("current_order.dest"),
                "order_index": common.get("cur_real_order_index"),
                "last_station": common.get("last_station_visited"),
                "vehicle_status": common.get("vehstatus"),
                "profit_gbp": round(common.get("profit_this_year", 0) / 256, 2),
            })
    by_vehicle = {}
    for vid, series in motions.items():
        increments = [
            b["profit_gbp"] - a["profit_gbp"]
            for a, b in zip(series, series[1:])
        ]
        by_vehicle[vid] = {
            "samples": len(series),
            "distinct_tiles": len({x["tile"] for x in series}),
            "moving_samples": sum((x["speed"] or 0) > 0 for x in series),
            "positive_profit_increments": sum(p > 500 for p in increments),
            "distinct_last_stations": sorted({x["last_station"] for x in series if x["last_station"] is not None}),
            "path": series,
        }
    return {
        "savegame_found": True,
        "total_savegames": len(paths),
        "sampled_savegames": len(sampled_paths),
        "rx_signs": rx,
        "vs_signs": states,
        "by_vehicle": by_vehicle,
    }


def audit(path, save_limit):
    d = json.loads(path.read_text(encoding="utf-8"))
    root = path.resolve().parents[1]
    pol = d["policy_comparison"]
    final_year = d["expected_last_year"]
    snapshots = d["line_telemetry"]["snapshots"]
    variant = pol.get("variant_policy_id", "v190dbl")
    by_seed = {}
    for seed in d["seeds"]:
        snaps = sorted(
            (x for x in snapshots if x["seed"] == seed and x["arm"] == "OpexAI"
             and x["duel_policy_id"] == variant and x.get("ok")),
            key=lambda x: x["year"],
        )
        mature = {
            int(v): year
            for snap in snaps[:-1] for line in snap["lines"] if freight(line)
            for v in line.get("vehicle_ids", [])
            for year in [min(snap["year"], final_year - 1)]
        }
        last = snaps[-1] if snaps else None
        freight_lines = [line for line in last["lines"] if freight(line)] if last else []
        doubles = [line for line in freight_lines if line["vehicles"] >= 2]
        trains = []
        for line in doubles:
            rows = []
            for vf in line.get("vehicle_financials", []):
                vid = int(vf["vehicle_id"])
                rows.append({
                    "id": vid,
                    "profit_this_year_gbp": round(vf.get("profit_this_year_gbp", 0), 2),
                    "seen_in_prior_december": vid in mature,
                    "first_prior_year_observed": mature.get(vid),
                })
                trains.append(vid)
            line["audit_vehicles"] = rows
        log = root / "results" / (path.stem + "_engine") / f"{variant}_seed{seed}_r0.log"
        game_idx = next(
            (i for i, game in enumerate(d["games"]) if game.get("seed") == seed
             and game.get("policy_id") == variant and game.get("repeat", 0) == 0), None
        )
        base = local_path(d.get("retained_savegames", ""), root)
        folder = base / str(game_idx) / "save" if game_idx is not None else base / "-1"
        by_seed[str(seed)] = {
            "final_year": final_year,
            "freight_lines": len(freight_lines),
            "freight_double_lines_proxy": len(doubles),
            "double_lines_proxy": [
                {"service_key": line.get("service_key"),
                 "station_ids": line.get("station_ids"),
                 "profit_this_year_gbp": round(line.get("profit_this_year_gbp", 0), 2),
                 "vehicles": line["audit_vehicles"]}
                for line in doubles
            ],
            "mature_double_trains_nonpositive": [
                x for line in doubles for x in line["audit_vehicles"]
                if x["seen_in_prior_december"] and x["profit_this_year_gbp"] <= 0
            ],
            "log": summarize_logs(log),
            "motion": vehicle_motion(folder, trains, save_limit) if save_limit else {"not_sampled": True},
        }
    return {
        "campaign_id": d["campaign_id"],
        "bundle": d.get("source_bundle_sha256"),
        "manifest": d.get("manifest_sha256"),
        "complete_pairs": pol.get("complete_pairs"),
        "comparison_complete": pol.get("comparison_complete"),
        "verdict": pol.get("verdict"),
        "profit_year_aggregate": pol["aggregates"].get("profit_year"),
        "seed_policy_deltas": {
            str(p["seed"]): p["metrics"]["profit_year"]["policy_delta"]
            for p in pol["per_pair"]
        },
        "seeds": by_seed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=Path)
    parser.add_argument("--saves", type=int, default=0,
                        help="last N monthly savegames to inspect (0 to skip)")
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    args = parser.parse_args()
    report = audit(args.json_path, args.saves)
    print("CAMPAIGN", report["campaign_id"], "bundle", report["bundle"])
    print("COMPLETE_PAIRS", report["complete_pairs"], "verdict", report["verdict"])
    for seed, row in report["seeds"].items():
        print("SEED", seed, "policy_delta", report["seed_policy_deltas"].get(seed),
              "freight_double_lines_proxy", row["freight_double_lines_proxy"],
              "mature_nonpositive", len(row["mature_double_trains_nonpositive"]),
              "build_double", row["log"].get("counts", {}).get("build_double"),
              "line_ids", row["log"].get("line_ids", {}))
        for line in row["double_lines_proxy"]:
            print(" LINE", line["service_key"], [
                (v["id"], v["profit_this_year_gbp"], "mature" if v["seen_in_prior_december"] else "new")
                for v in line["vehicles"]
            ])
    if args.output:
        if args.output.exists():
            raise SystemExit(f"refusing overwrite: {args.output}")
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("OUTPUT", args.output)


if __name__ == "__main__":
    main()
