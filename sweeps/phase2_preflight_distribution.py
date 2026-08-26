"""Measure the unmasked preflight tail before choosing TrainLineAI's tick barrier.

The production AI already records ``TRLN|<index>|B<first_mutation_tick>|M/O`` after it has
started construction.  This script makes a self-cleaning /tmp copy with BARRIER_BASE=0, so that
the recorded first mutation tick is the natural end of preflight.  It deliberately samples high
pair ranks too: failed preflights are retained as outcomes, while the distribution is over routes
that actually reach a first map mutation.
"""
import atexit
import json
import math
import os
import re
import shutil
import statistics

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
RANKS = (0, 1, 5, 10, 20, 40)
NUM_TRAINS, WAGONS_PER_TRAIN, ENGINE_RANK = 2, 2, 1
SOURCE_AI_DIR = "ai/TrainLineAI"
SCRATCH_AI_DIR = "/tmp/openttd-ml-preflight-distribution"
SCRATCH_AI_NAME = "TrainLineAIPreflightDistribution"
OUTPUT_JSON = "docs/phase2_preflight_distribution.json"
STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
BARRIER_RE = re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")


def make_scratch_ai():
    if os.path.exists(SCRATCH_AI_DIR):
        raise RuntimeError(f"Temporary scratch AI already exists: {SCRATCH_AI_DIR}")
    shutil.copytree(SOURCE_AI_DIR, SCRATCH_AI_DIR)
    main_path = os.path.join(SCRATCH_AI_DIR, "main.nut")
    with open(main_path) as source:
        main = source.read()
    old = "  local BARRIER_BASE = 5000;"
    if main.count(old) != 1:
        raise RuntimeError("Expected provisional production barrier constant exactly once")
    with open(main_path, "w") as output:
        output.write(main.replace(old, "  local BARRIER_BASE = 0;"))
    info_path = os.path.join(SCRATCH_AI_DIR, "info.nut")
    with open(info_path) as source:
        info = source.read()
    old_name = 'function GetName()        { return "TrainLineAI"; }'
    if info.count(old_name) != 1:
        raise RuntimeError("Expected production AI name exactly once")
    with open(info_path, "w") as output:
        output.write(info.replace(old_name, f'function GetName()        {{ return "{SCRATCH_AI_NAME}"; }}'))


def keep_row(row):
    experiment = row["experiment"]
    return ({"route_id": experiment["route_id"], "seed": experiment["seed"],
             "pair_rank": dict(experiment["ais"][0][1])["pair_rank"], "date": str(row["date"]),
             "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()]},)


def percentile_nearest_rank(values, fraction):
    return sorted(values)[math.ceil(fraction * len(values)) - 1]


if __name__ == "__main__":
    make_scratch_ai()
    atexit.register(shutil.rmtree, SCRATCH_AI_DIR, ignore_errors=True)
    experiments = tuple(
        {"route_id": f"seed{seed}_rank{rank}", "seed": seed, "days": DAYS,
         "openttd_config": OPENTTD_CONFIG,
         "ais": (local_folder(SCRATCH_AI_DIR, SCRATCH_AI_NAME, ai_params=(
             ("num_trains", NUM_TRAINS), ("wagons_per_train", WAGONS_PER_TRAIN),
             ("engine_rank", ENGINE_RANK), ("pair_rank", rank), ("line_index", 0))),)}
        for seed in SEEDS for rank in RANKS
    )
    results = run_experiments(
        openttd_version="13.4", opengfx_version="7.1", max_workers=3,
        result_processor=keep_row,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
        experiments=experiments)
    latest = {}
    for row in results:
        if row["route_id"] not in latest or row["date"] > latest[row["route_id"]]["date"]:
            latest[row["route_id"]] = row
    if len(latest) != len(experiments):
        raise RuntimeError(f"Expected {len(experiments)} experiments, found {len(latest)} final captures")
    records = []
    for route_id in sorted(latest):
        row = latest[route_id]
        status = barrier = None
        for sign in row["signs"]:
            if match := STATUS_RE.match(sign):
                status = match.groups()
            elif match := BARRIER_RE.match(sign):
                barrier = match.groups()
        record = {"route_id": route_id, "seed": row["seed"], "pair_rank": row["pair_rank"],
                  "capture_date": row["date"], "raw_signs": row["signs"]}
        if status:
            record.update({"stage": status[1], "reason": status[2]})
        if barrier:
            first_tick = int(barrier[1])
            record.update({"first_mutation_tick": first_tick,
                           "preflight_elapsed_ticks": first_tick - 1,
                           "barrier_flag": barrier[2]})
        records.append(record)
    elapsed = [record["preflight_elapsed_ticks"] for record in records if "preflight_elapsed_ticks" in record]
    summary = {"attempted": len(records), "reached_first_mutation": len(elapsed),
               "preflight_failed_before_mutation": len(records) - len(elapsed)}
    if elapsed:
        summary["successful_preflight_elapsed_ticks"] = {
            "min": min(elapsed), "median": statistics.median(elapsed), "p90_nearest_rank": percentile_nearest_rank(elapsed, .90),
            "max": max(elapsed), "definition": "first_mutation_tick - Start_tick (Start_tick=1); p90 uses ceil(0.90*n) nearest-rank",
        }
    payload = {"config": {"number_towns": 3, "starting_year": 1970, "town_growth_rate": 2,
                           "industry_density": 4, "inflation": False, "map": "256x256"},
               "design": {"seeds": list(SEEDS), "pair_ranks": list(RANKS),
                          "barrier_base_in_scratch": 0,
                          "rationale": "Five maps times ranks 0, 1, 5, 10, 20 and 40; high ranks intentionally sample the expensive/failing tail."},
               "summary": summary, "records": records}
    with open(OUTPUT_JSON, "w") as output:
        json.dump(payload, output, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"Wrote {OUTPUT_JSON}")
