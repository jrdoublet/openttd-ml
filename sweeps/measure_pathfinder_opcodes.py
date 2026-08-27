"""Measure RailPathFinder opcode use with the same direct-debug harness as debug_ai.py.

Runs five fixed map seeds at pair ranks 0 and 5, first with FindPath(50), then
with FindPath(500).  The production AI is never edited: each variant is a
temporary copy whose search loop is replaced exactly once.

Run from the repository root, inside the project Docker image:
  docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab \\
    -v "$PWD":/work -w /work openttd-lab python sweeps/measure_pathfinder_opcodes.py
"""
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path


CFG = """[difficulty]
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
SEEDS = (42, 1, 7, 100, 2026)
# Rank 0 is the easy/high-score pair; rank 5 deliberately includes harder paths.
RANKS = (0, 5)
BATCHES = (50, 500)
# debug_ai's null-driver ticks advance faster than AIController.GetTick(); 60k
# gives the known ~10k-tick worst preflight room to finish without a campaign.
TICKS = 60000
AI_LIBRARY = "ai-library/5046524c"
ROOT = Path(__file__).resolve().parents[1]
SOURCE_AI = ROOT / "ai" / "TrainLineAI"
DEBUG_HARNESS = ROOT / "sweeps" / "debug_ai.py"
OUTPUT = ROOT / "docs" / "phase3_pathfinder_opcodes.json"
RAW_LOG_DIR = ROOT / "sweeps" / "pathfinder_opcode_measurement_logs_20260827"

OPS = re.compile(r"PFOPS\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)")
RESULT = re.compile(r"PFRESULT\|(\d+)\|(\d+)\|(\d+)\|([^|]+)\|(-?\d+)\|(-?\d+)\|([^\s|]+)")


def patch_ai(scratch: Path, batch: int) -> str:
    """Copy already exists; replace only the specified production loop and result exits."""
    main = scratch / "main.nut"
    source = main.read_text()
    old_loop = """  local path = false;
  local iterationsLeft = 30000;
  while (path == false && iterationsLeft > 0 && AIController.GetTick() < deadlineTick) {
    path = pathfinder.FindPath(50);
    iterationsLeft -= 50;
    this.Sleep(1);
  }
  if (path == false) return \"path_search_limit\";
  if (path == null) return \"no_path_found\";
"""
    new_loop = f"""  local path = false;
  local iterationsLeft = 30000;
  local pfCalls = 0;
  while (path == false && iterationsLeft > 0 && AIController.GetTick() < deadlineTick) {{
    local opsBefore = AIController.GetOpsTillSuspend();
    local tickBefore = AIController.GetTick();
    path = pathfinder.FindPath({batch});
    local opsAfter = AIController.GetOpsTillSuspend();
    local tickAfter = AIController.GetTick();
    pfCalls++;
    /* PFOPS fields: call number, ops before/after, tick before/after.  A later
     * ops value means FindPath crossed a VM suspension; Python keeps that case
     * out of the directly-measurable opcode distribution. */
    AILog.Info(\"PFOPS|\" + pfCalls + \"|\" + opsBefore + \"|\" + opsAfter + \"|\" + tickBefore + \"|\" + tickAfter);
    iterationsLeft -= {batch};
    this.Sleep(1);
  }}
  if (path == false) {{
    AILog.Info(\"PFRESULT|{batch}|\" + pfCalls + \"|\" + (30000 - iterationsLeft) + \"|limit|-1|-1|-\");
    return \"path_search_limit\";
  }}
  if (path == null) {{
    AILog.Info(\"PFRESULT|{batch}|\" + pfCalls + \"|\" + (30000 - iterationsLeft) + \"|no_path|-1|-1|-\");
    return \"no_path_found\";
  }}
"""
    if source.count(old_loop) != 1:
        raise RuntimeError("expected original FindPath(50) loop exactly once")
    source = source.replace(old_loop, new_loop)

    old_return = """  if (selectedPlanA == null || selectedPlanB == null) return \"no_path_found\";
  return { tiles = simplifiedTiles, plans_a = [selectedPlanA], plans_b = [selectedPlanB] };
"""
    new_return = f"""  if (selectedPlanA == null || selectedPlanB == null) {{
    AILog.Info(\"PFRESULT|{batch}|\" + pfCalls + \"|\" + (30000 - iterationsLeft) + \"|no_path|-1|-1|-\");
    return \"no_path_found\";
  }}
  /* Exact tile sequence makes the A/B result comparison stronger than cost and
   * length alone. It is emitted only after the measured FindPath calls. */
  local pathTiles = \"\";
  foreach (tile in simplifiedTiles) {{
    if (pathTiles.len() > 0) pathTiles += \",\";
    pathTiles += tile;
  }}
  AILog.Info(\"PFRESULT|{batch}|\" + pfCalls + \"|\" + (30000 - iterationsLeft) +
      \"|found|\" + path.GetCost() + \"|\" + simplifiedTiles.len() + \"|\" + pathTiles);
  return {{ tiles = simplifiedTiles, plans_a = [selectedPlanA], plans_b = [selectedPlanB] }};
"""
    if source.count(old_return) != 1:
        raise RuntimeError("expected final path return exactly once")
    source = source.replace(old_return, new_return)
    main.write_text(source)

    info = scratch / "info.nut"
    info_source = info.read_text()
    old_name = 'function GetName()        { return "TrainLineAI"; }'
    name = f"TrainLineAIOps{batch}"
    if info_source.count(old_name) != 1:
        raise RuntimeError("expected TrainLineAI name exactly once")
    info.write_text(info_source.replace(old_name, f'function GetName()        {{ return "{name}"; }}'))
    return name


def parse_run(output: str, batch: int, seed: int, rank: int) -> dict:
    calls = []
    for call, before, after, tick_before, tick_after in OPS.findall(output):
        calls.append({"call": int(call), "before": int(before), "after": int(after),
                      "tick_before": int(tick_before), "tick_after": int(tick_after)})
    results = RESULT.findall(output)
    if len(results) != 1:
        raise RuntimeError(f"seed={seed} rank={rank} batch={batch}: expected one PFRESULT, got {len(results)}")
    logged_batch, result_calls, iterations, outcome, path_cost, tile_count, tiles = results[0]
    if int(logged_batch) != batch or int(result_calls) != len(calls):
        raise RuntimeError(f"seed={seed} rank={rank} batch={batch}: inconsistent PF log counters")
    if int(iterations) != len(calls) * batch:
        raise RuntimeError(f"seed={seed} rank={rank} batch={batch}: iterations are not calls*batch")
    measurable = [c["before"] - c["after"] for c in calls if c["after"] < c["before"]]
    crossed = [c for c in calls if c["after"] > c["before"]]
    equal = [c for c in calls if c["after"] == c["before"]]
    # Required methodological guard: only strict after < before calls enter this list.
    if any(cost <= 0 for cost in measurable):
        raise RuntimeError("non-positive measurable opcode delta")
    return {
        "seed": seed, "rank": rank, "batch": batch, "findpath_calls": len(calls),
        "iterations_used": int(iterations), "outcome": outcome, "path_cost": int(path_cost),
        "tile_count": int(tile_count), "tile_sequence": None if tiles == "-" else tiles,
        "calls": calls, "measurable_opcode_costs": measurable,
        "crossed_tick_suspensions": len(crossed), "equal_before_after": len(equal),
        "pathfinding_tick_span": (calls[-1]["tick_after"] - calls[0]["tick_before"] + 1) if calls else 0,
    }


def aggregate(records: list[dict]) -> dict:
    costs = [cost for r in records for cost in r["measurable_opcode_costs"]]
    total_calls = sum(r["findpath_calls"] for r in records)
    crossed = sum(r["crossed_tick_suspensions"] for r in records)
    return {
        "attempts": len(records), "measurable_calls": len(costs),
        "opcode_cost_min": min(costs), "opcode_cost_median": statistics.median(costs),
        "opcode_cost_max": max(costs), "crossed_tick_suspensions": crossed,
        "total_findpath_calls": total_calls,
        "crossed_tick_suspension_rate": crossed / total_calls if total_calls else 0,
        "total_iterations_used": sum(r["iterations_used"] for r in records),
        "total_pathfinding_tick_span": sum(r["pathfinding_tick_span"] for r in records),
    }


def main() -> None:
    if RAW_LOG_DIR.exists():
        shutil.rmtree(RAW_LOG_DIR)
    RAW_LOG_DIR.mkdir()
    all_records = {str(batch): [] for batch in BATCHES}
    with tempfile.TemporaryDirectory(prefix="openttd-ml-pathfinder-opcodes-") as temp:
        temp_root = Path(temp)
        for batch in BATCHES:
            for seed in SEEDS:
                for rank in RANKS:
                    scratch = temp_root / f"ai-{batch}-{seed}-{rank}"
                    shutil.copytree(SOURCE_AI, scratch)
                    ai_name = patch_ai(scratch, batch)
                    start = (f"start_ai {ai_name} num_trains=2,wagons_per_train=2,engine_rank=1,"
                             f"pair_rank={rank},line_index=0,stagger_slot=0")
                    cmd = [sys.executable, str(DEBUG_HARNESS), str(scratch), ai_name, start,
                           str(TICKS), str(seed), CFG.replace("\n", "\\n"), AI_LIBRARY]
                    print(f"RUN batch={batch} seed={seed} rank={rank}", flush=True)
                    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=360)
                    output = completed.stdout + completed.stderr
                    raw_log = RAW_LOG_DIR / f"batch{batch}_seed{seed}_rank{rank}.log"
                    raw_log.write_text(output)
                    if completed.returncode != 0:
                        raise RuntimeError(f"debug harness failed ({completed.returncode}); see {raw_log}")
                    record = parse_run(output, batch, seed, rank)
                    all_records[str(batch)].append(record)
                    print(json.dumps({k: record[k] for k in ("seed", "rank", "batch", "findpath_calls", "iterations_used", "outcome", "path_cost", "tile_count", "crossed_tick_suspensions")}, sort_keys=True), flush=True)

    comparisons = []
    by_key_50 = {(r["seed"], r["rank"]): r for r in all_records["50"]}
    for r500 in all_records["500"]:
        r50 = by_key_50[(r500["seed"], r500["rank"])]
        same = (r50["outcome"] == r500["outcome"] and r50["path_cost"] == r500["path_cost"] and
                r50["tile_count"] == r500["tile_count"] and r50["tile_sequence"] == r500["tile_sequence"])
        comparisons.append({"seed": r500["seed"], "rank": r500["rank"], "same_path": same,
                            "batch50": {k: r50[k] for k in ("outcome", "path_cost", "tile_count", "findpath_calls", "iterations_used")},
                            "batch500": {k: r500[k] for k in ("outcome", "path_cost", "tile_count", "findpath_calls", "iterations_used")}})
    result = {
        "design": {"seeds": SEEDS, "ranks": RANKS, "batches": BATCHES, "debug_ticks": TICKS,
                   "same_seed_rank_pairs_in_A_and_B": True,
                   "rank_choice": "0 (easy/high-score) and 5 (harder historical preflight cases)"},
        "batch_50": {"records": all_records["50"], "aggregate": aggregate(all_records["50"])},
        "batch_500": {"records": all_records["500"], "aggregate": aggregate(all_records["500"])},
        "comparisons_batch500_to_batch50": comparisons,
    }
    result["comparisons_all_paths_identical"] = all(x["same_path"] for x in comparisons)
    calls50 = result["batch_50"]["aggregate"]["total_findpath_calls"]
    calls500 = result["batch_500"]["aggregate"]["total_findpath_calls"]
    result["findpath_call_reduction_factor_50_to_500"] = calls50 / calls500 if calls500 else None
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print("RESULT_FILE", OUTPUT)
    print(json.dumps({"batch_50": result["batch_50"]["aggregate"], "batch_500": result["batch_500"]["aggregate"],
                      "all_paths_identical": result["comparisons_all_paths_identical"],
                      "findpath_call_reduction_factor_50_to_500": result["findpath_call_reduction_factor_50_to_500"]}, indent=2))


if __name__ == "__main__":
    main()
