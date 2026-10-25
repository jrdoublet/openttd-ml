#!/usr/bin/env python3
"""Read-only inventory of historical CARTO-1 long campaigns (no Docker).

Time stamps in OpenTTD engine logs are UTC. On 2026-10-24 Europe/Paris is
UTC+2; report local clock intervals explicitly, and do not infer CPU
contention from overlap alone. Never use these observations to tune a
predictor on its intended held-out seeds.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
import argparse
import json
from pathlib import Path
import re

from sweeps.analyze_carto1_long import decode_line

NAMES = (
    "early1024_3x3", "shadow1024_3x3", "shadow1024_3x10",
    "safe1024_1x5", "safety_latest1024_s999_1x3",
)
WALL = re.compile(r"^\[(2026-10-24 \d\d:\d\d:\d\d)\]")
PARIS_CEST = timezone(timedelta(hours=2), name="CEST")


def audit(root, prefix):
    base = root / (prefix + ".json")
    manifest_file = root / (prefix + ".manifest.json")
    result = json.loads(base.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    result_games = {(g["seed"], g["repeat"]): g for g in result["games"]}
    games = []
    for file in sorted((root / (prefix + "_engine")).glob("reference_seed*_r*.log")):
        seed = int(re.search(r"seed(\d+)_", file.name)[1])
        counts = Counter()
        outcomes = Counter()
        sums = Counter()
        setup_ops = 0
        samples = set()
        costs = set()
        asterisk = set()
        first_wall = last_wall = None
        last_summary = None
        safety = []
        max_iterations = 0
        with file.open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                wall = WALL.search(line)
                if wall:
                    stamp = datetime.strptime(wall[1], "%Y-%m-%d %H:%M:%S").replace(
                        tzinfo=timezone.utc
                    )
                    first_wall = min(first_wall, stamp) if first_wall else stamp
                    last_wall = max(last_wall, stamp) if last_wall else stamp
                parsed = decode_line(line)
                if parsed is None:
                    if "CARTO1_LONG_SAFETY" in line:
                        safety.append(line.strip()[-180:])
                    continue
                _, tag, fields = parsed
                counts[tag] += 1
                if tag == "CARTO1_LONG_SAFETY":
                    safety.append(line.strip()[-180:])
                    continue
                sid = fields.get("sample")
                if tag == "CARTO1_LONG_SAMPLE" and sid is not None:
                    samples.add(int(sid))
                if tag == "CARTO1_LONG_COST" and sid is not None:
                    costs.add(int(sid))
                    sums["map_ops"] += int(fields.get("ops", "0"))
                    sums["map_ticks"] += int(fields.get("ticks", "0"))
                if tag == "CARTO1_LONG_ASTAR" and fields.get("phase") == "end":
                    if sid is not None:
                        asterisk.add(int(sid))
                    outcome = fields.get("outcome", "?")
                    outcomes[outcome] += 1
                    sums["search_ops"] += int(fields.get("search_ops", "0"))
                    setup_ops += int(fields.get("setup_ops", "0"))
                    sums["astar_overruns"] += int(fields.get("overruns", "0"))
                    sums["actual_started"] += int(fields.get("started", "0"))
                    max_iterations = max(max_iterations, int(fields.get("iters", "0")))
                if tag == "CARTO1_LONG_SUMMARY":
                    last_summary = fields
                if tag == "RLW04B_ENUM" and fields.get("phase") == "done":
                    sums["rlw_ticks"] = int(fields.get("ticks", "0"))
                    sums["rlw_overruns"] = int(fields.get("overruns", "0"))
                    sums["rlw_pairs"] = int(fields.get("pairs", "0"))
        game = result_games.get((seed, 0), {})
        games.append({
            "seed": seed, "game_status": game.get("game_status"),
            "game_ok": game.get("game_ok"),
            "horizon_complete": game.get("companies", {}).get("OpexAI", {}).get(
                "horizon_complete"
            ),
            "first_utc": first_wall.isoformat() if first_wall else None,
            "last_utc": last_wall.isoformat() if last_wall else None,
            "first_paris": first_wall.astimezone(PARIS_CEST).isoformat() if first_wall else None,
            "last_paris": last_wall.astimezone(PARIS_CEST).isoformat() if last_wall else None,
            "sample_count": len(samples), "cost_count": len(costs),
            "astar_count": len(asterisk), "outcomes": dict(outcomes),
            "counts": dict(counts), "sums": dict(sums),
            "setup_ops": setup_ops,
            "max_astar_iterations": max_iterations,
            "summary": last_summary, "safety": safety,
            "missing_cost": sorted(set(range(30)) - costs),
            "missing_astar": sorted(set(range(30)) - asterisk)
        })
    return {
        "campaign": prefix, "years": manifest["configuration"]["years"],
        "reference": manifest["execution"]["options"]["reference"],
        "created_at_utc": manifest.get("created_at_utc"),
        "games": games
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("results"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    campaigns = [audit(args.root, "carto1_long_" + name + "_20261024") for name in NAMES]
    payload = json.dumps({"campaigns": campaigns}, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
