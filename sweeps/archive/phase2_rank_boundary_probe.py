"""Locate the constructibility boundary for pair_rank under the revised 1970 configuration."""
import json
import re

from openttdlab import bananas_ai_library, local_folder, run_experiments


OPENTTD_CONFIG = """
[difficulty]
number_towns = 3
industry_density = 4

[economy]
inflation = false
town_growth_rate = 2

[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""
DAYS = 365 * 10
SEEDS = (42, 1, 7, 100, 2026)
RANKS = (50, 100, 200, 300, 400)
OUTPUT_JSON = "results/phase2_rank_boundary_probe.json"
STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
BARRIER_RE = re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")


def keep_row(row):
    return ({"seed": row["experiment"]["seed"], "pair_rank": dict(row["experiment"]["ais"][0][1])["pair_rank"],
             "date": str(row["date"]), "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()]},)


if __name__ == "__main__":
    experiments = tuple(
        {"seed": seed, "days": DAYS, "openttd_config": OPENTTD_CONFIG,
         "ais": (local_folder("ai/TrainLineAI", "TrainLineAI", ai_params=(
             ("num_trains", 2), ("wagons_per_train", 2), ("engine_rank", 1),
             ("pair_rank", rank), ("line_index", index), ("stagger_slot", 0))),)}
        for index, (seed, rank) in enumerate((seed_rank for seed_rank in ((seed, rank) for seed in SEEDS for rank in RANKS)))
    )
    results = run_experiments(
        openttd_version="13.4", opengfx_version="7.1", max_workers=3, result_processor=keep_row,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),), experiments=experiments)
    latest = {}
    for row in results:
        key = (row["seed"], row["pair_rank"])
        if key not in latest or row["date"] > latest[key]["date"]:
            latest[key] = row
    records = []
    for key in sorted(latest):
        row = latest[key]
        status = barrier = None
        for sign in row["signs"]:
            if match := STATUS_RE.match(sign):
                status = match.groups()
            elif match := BARRIER_RE.match(sign):
                barrier = match.groups()
        record = {"seed": row["seed"], "pair_rank": row["pair_rank"], "capture_date": row["date"], "raw_signs": row["signs"]}
        if status:
            record.update({"stage": status[1], "reason": status[2], "built": int(status[3]), "requested": int(status[4])})
        if barrier:
            record.update({"first_mutation_tick": int(barrier[1]), "barrier_flag": barrier[2]})
        records.append(record)
    if len(records) != len(experiments):
        raise RuntimeError(f"Incomplete probe: got {len(records)}, expected {len(experiments)}")
    by_rank = {}
    for rank in RANKS:
        rows = [record for record in records if record["pair_rank"] == rank]
        reasons = {}
        for row in rows:
            reasons[row.get("reason", "NO_STATUS")] = reasons.get(row.get("reason", "NO_STATUS"), 0) + 1
        by_rank[str(rank)] = {"attempted": len(rows), "success": sum(row.get("stage") == "success" for row in rows),
                              "failure_reasons": reasons, "barrier_M": sum(row.get("barrier_flag") == "M" for row in rows),
                              "barrier_O": sum(row.get("barrier_flag") == "O" for row in rows)}
    payload = {"config": {"number_towns": 3, "starting_year": 1970, "town_growth_rate": 2,
                           "industry_density": 4, "inflation": False, "map": "256x256"},
               "design": {"seeds": list(SEEDS), "ranks": list(RANKS), "stagger_slot": 0,
                          "rationale": "Coarse five-seed probe spanning the old ceiling (59), the prior setting cap (99), and the eligibility-count ceiling around 320."},
               "by_rank": by_rank, "records": records}
    with open(OUTPUT_JSON, "w") as output:
        json.dump(payload, output, indent=2)
    print(json.dumps(by_rank, indent=2))
    print(f"Wrote {OUTPUT_JSON}")
