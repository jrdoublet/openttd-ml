"""Measure production A* against the segmented prototype on ordinary checkpoints.

Variant A is a temporary instrumented copy: ai/TrainLineAI itself is never edited.
The added signs only expose its existing pathfinder counter and elapsed ticks.  Both
variants use the same experiments; a missing report becomes NO_REPORT and never
interrupts another case.
"""
import atexit
import json
import re
import shutil
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
PRODUCTION_AI = ROOT / "ai" / "TrainLineAI"
SEGMENTED_AI = ROOT / "ai" / "TrainLineAI-segmented"
CHECKPOINTS = ROOT / "data" / "phase2_hurdle_v3_checkpoints"
RESULT = ROOT / "docs" / "phase3_ordinary_segmented.json"
SCRATCH = Path("/tmp/openttd-ml-ordinary-segmented-20260828")
DAYS, PATHFINDER_ITERATIONS_K, INFRA_LIFE_YEARS = 3650, 30, 30
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

# seed, pair_rank, production iterations in the checkpoint, straight-line distance
TARGETS = (
    (1045, 0, 200, 22), (1048, 110, 200, 49), (1054, 30, 200, 21),
    (1058, 0, 200, 25), (1061, 130, 200, 37),
    (1091, 120, 1500, 90), (1099, 110, 1500, 35), (1026, 60, 1550, 51),
    (1065, 90, 1550, 55), (1073, 40, 1550, 54),
    (1090, 50, 4600, 43), (1020, 40, 4650, 71), (1022, 50, 4650, 72),
    (1037, 0, 4650, 31), (1040, 110, 4650, 69),
    (1099, 140, 10900, 60), (1035, 100, 10950, 82), (1087, 140, 10950, 53),
    (1089, 100, 10950, 78), (1068, 150, 11050, 103),
    (1077, 40, 21500, 132), (1064, 100, 21600, 61), (1089, 110, 21650, 72),
    (1099, 20, 21650, 100), (1011, 150, 21750, 106),
)
KEYS = tuple((seed, rank) for seed, rank, _, _ in TARGETS)
STATUS = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")
BARRIER = re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")
WORK = re.compile(r"^TPM\|(\d+)\|I(\d+)\|K(\d+)\|S(\w)$")
SEGMENT = re.compile(r"^TSG\|(\d+)\|N(\d+)\|L(\d+)\|R(\d+)$")
STOPS = {"F": "found", "L": "iteration_limit", "D": "preflight_deadline",
         "B": "backtrack_limit", "E": "open_empty", "N": "no_progress",
         "W": "time_window_limit", "X": "unknown"}


def replace_once(source, old, new, description):
    if source.count(old) != 1:
        raise RuntimeError(f"unexpected {description} block ({source.count(old)} matches)")
    return source.replace(old, new)


def selected_checkpoints():
    found = {}
    for checkpoint in CHECKPOINTS.glob("*.json"):
        data = json.loads(checkpoint.read_text())
        parsed = data["parsed"]
        key = (parsed["seed"], parsed["pair_rank"])
        if key not in KEYS:
            continue
        # This is deliberately an assert-like hard gate: all 25 inputs are ORDINARY/OK.
        if parsed["failure_reason"] != "OK":
            raise RuntimeError(f"{key} is not OK: {parsed['failure_reason']}")
        found[key] = {"attempt_id": parsed["attempt_id"], "ai_params": data["raw"]["ai_params"],
                      "iterations": parsed["pathfinder_iterations_consumed"],
                      "distance": parsed["distance_straight"]}
    if set(found) != set(KEYS):
        raise RuntimeError(f"missing checkpoints: {sorted(set(KEYS) - set(found))}")
    for seed, rank, iterations, distance in TARGETS:
        actual = found[(seed, rank)]
        if (actual["iterations"], actual["distance"]) != (iterations, distance):
            raise RuntimeError(f"checkpoint mismatch for {(seed, rank)}: {actual}")
    return found


def assert_preflight_safety():
    """Guard the no-mutation-before-barrier contract in the two measured sources."""
    production = (PRODUCTION_AI / "main.nut").read_text()
    segmented = (SEGMENTED_AI / "main.nut").read_text()
    for source, search in ((production, "_preflightPair"), (segmented, "_segmentedPath")):
        if "AITestMode()" not in source or f"function TrainLineAI::{search}" not in source:
            raise RuntimeError(f"missing AITestMode search guard for {search}")
        if source.index(f"function TrainLineAI::{search}") > source.index("/* Barriere de preflight"):
            raise RuntimeError(f"{search} is unexpectedly after the construction barrier")


def instrument_production():
    """Copy production and add TPM reporting only; search/construction instructions are intact."""
    scratch = SCRATCH / "variant_a"
    shutil.copytree(PRODUCTION_AI, scratch)
    main = scratch / "main.nut"
    source = main.read_text()
    source = replace_once(
        source,
        "  local pathfinder = RailPathFinder();\n  pathfinder.cost.max_cost = 200000;\n  pathfinder.InitializePath(sources, goals);",
        "  local pathfinder = RailPathFinder();\n  pathfinder.cost.max_cost = 200000;\n  local pathfinderStartTick = AIController.GetTick();\n  pathfinder.InitializePath(sources, goals);",
        "pathfinder start")
    source = replace_once(
        source,
        "  if (path == false) return \"path_search_limit\";\n  if (path == null) return \"no_path_found\";\n\n  local tiles = [];",
        "  this.state.pathfinder_ticks = AIController.GetTick() - pathfinderStartTick;\n  if (path == false) { this.state.pathfinder_stop = AIController.GetTick() >= deadlineTick ? \"preflight_deadline\" : \"iteration_limit\"; return \"path_search_limit\"; }\n  if (path == null) { this.state.pathfinder_stop = \"open_empty\"; return \"no_path_found\"; }\n  this.state.pathfinder_stop = \"found\";\n\n  local tiles = [];",
        "pathfinder result")
    source = replace_once(
        source, "    pathfinder_iterations_consumed = 0,\n    pathfinder_probes = [",
        "    pathfinder_iterations_consumed = 0,\n    pathfinder_ticks = null,\n    pathfinder_stop = null,\n    pathfinder_probes = [", "measurement state")
    source = replace_once(
        source, "  this._report(this._codePathfinderIterationsConsumed());\n  foreach (probe in this.state.pathfinder_probes) {",
        "  this._report(this._codePathfinderIterationsConsumed());\n  if (this.state.pathfinder_ticks != null) {\n    local stop = this.state.pathfinder_stop == \"found\" ? \"F\" : (this.state.pathfinder_stop == \"iteration_limit\" ? \"L\" : (this.state.pathfinder_stop == \"open_empty\" ? \"E\" : \"D\"));\n    this._report(\"TPM|\" + this.state.line_index + \"|I\" + this.state.pathfinder_iterations_consumed + \"|K\" + this.state.pathfinder_ticks + \"|S\" + stop);\n  }\n  foreach (probe in this.state.pathfinder_probes) {", "measurement report")
    main.write_text(source)
    info = scratch / "info.nut"
    info.write_text(replace_once(info.read_text(), 'function GetName()        { return "TrainLineAI"; }',
                                 'function GetName()        { return "TrainLineAIOrdinaryMeasure"; }', "AI name"))
    return scratch, "TrainLineAIOrdinaryMeasure"


def vehicle_summary(chunks):
    profits, max_ages = [], []
    for vehicle in chunks.get("VEHS", {}).values():
        if vehicle.get("type") != 0:
            continue
        common = vehicle["train"][0]["common"][0]
        if common["owner"] == 0 and common["unitnumber"] != 0:
            profits.append(common["profit_last_year"])
            max_ages.append(common["max_age"])
    if not max_ages:
        return None
    return {"sum_profit_last_year": sum(profits),
            "avg_max_age_years": round(sum(max_ages) / len(max_ages) / 365.0, 2)}


def keep(row):
    return ({"key": tuple(row["experiment"]["ordinary_key"]), "date": str(row["date"]),
             "signs": [s["name"] for s in row["chunks"].get("SIGN", {}).values()],
             "veh": vehicle_summary(row["chunks"])},)


def no_report(key, segmented, reason):
    record = {"seed": key[0], "pair_rank": key[1], "issue": "NO_REPORT", "barrier_flag": None,
              "astar_iterations": None, "pathfinding_ticks": None, "construction_cost": None,
              "profit_ligne": None, "report_complete": False, "missing_report_fields": [reason]}
    if segmented:
        record.update(segments=None, local_choices=None, backtracks=None)
    return record


def parse(row, segmented):
    result, vehicle_cost = {"seed": row["key"][0], "pair_rank": row["key"][1], "raw_signs": row["signs"]}, None
    for sign in row["signs"]:
        if match := STATUS.match(sign):
            _, stage, issue, built, requested = match.groups()
            result.update(stage=stage, issue=issue, trains_built=int(built), trains_requested=int(requested))
        elif match := DETAIL.match(sign):
            _, town_a, town_b, distance, cost = match.groups()
            result.update(town_a=int(town_a), town_b=int(town_b), distance_straight=int(distance), construction_cost=int(cost))
        elif match := VEHICLE.match(sign):
            vehicle_cost = int(match.group(2))
        elif match := BARRIER.match(sign):
            _, tick, flag = match.groups()
            result.update(first_mutation_tick=int(tick), barrier_flag=flag)
        elif match := WORK.match(sign):
            _, iterations, ticks, stop = match.groups()
            result.update(astar_iterations=int(iterations), pathfinding_ticks=int(ticks), stop_reason=STOPS.get(stop, stop))
        elif segmented and (match := SEGMENT.match(sign)):
            _, segments, choices, backtracks = match.groups()
            result.update(segments=int(segments), local_choices=int(choices), backtracks=int(backtracks))
    # A valid preflight failure has no construction/barrier sign.  It is still a report,
    # whereas a missing status/pathfinder record is the campaign-level NO_REPORT condition.
    required = ["issue", "astar_iterations", "pathfinding_ticks"]
    if segmented:
        required += ["segments", "local_choices", "backtracks"]
    missing = [field for field in required if field not in result]
    if missing:
        return no_report(row["key"], segmented, ",".join(missing))
    result.setdefault("barrier_flag", None)
    result.setdefault("construction_cost", None)
    result["report_complete"] = True
    veh = row["veh"]
    if vehicle_cost is not None and veh is not None and veh["avg_max_age_years"]:
        infra_cost = result["construction_cost"] - vehicle_cost
        result["profit_ligne"] = round(veh["sum_profit_last_year"] - vehicle_cost / veh["avg_max_age_years"] - infra_cost / INFRA_LIFE_YEARS)
    else:
        result["profit_ligne"] = None
    return result


def run_variant(source, name, selected, segmented):
    experiments = tuple({
        "seed": key[0], "days": DAYS, "openttd_config": CFG, "ordinary_key": key,
        "ais": (local_folder(str(source), name, ai_params=tuple(meta["ai_params"].items()) +
                              (("pathfinder_iterations_k", PATHFINDER_ITERATIONS_K),)),),
    } for key, meta in selected.items())
    try:
        output = run_experiments(openttd_version="13.4", opengfx_version="7.1", max_workers=1,
            result_processor=keep, ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
            experiments=experiments)
    except Exception as error:
        return {key: no_report(key, segmented, f"runner_error:{type(error).__name__}") for key in KEYS}
    latest = {}
    for row in output:
        if row["key"] not in latest or row["date"] > latest[row["key"]]["date"]:
            latest[row["key"]] = row
    return {key: parse(latest[key], segmented) if key in latest else no_report(key, segmented, "missing_row")
            for key in KEYS}


def quintile_summary(records):
    result = []
    for index in range(5):
        group, summary = records[index * 5:(index + 1) * 5], {"quintile": f"Q{index + 1}", "cases": 5}
        for field, label in (("astar_iterations", "iterations"), ("pathfinding_ticks", "ticks"),
                             ("construction_cost", "construction_cost"), ("profit_ligne", "profit")):
            pairs = [(r["variant_a"][field], r["variant_b"][field]) for r in group
                     if r["variant_a"][field] is not None and r["variant_b"][field] is not None]
            summary[f"delta_{label}_b_minus_a"] = sum(b - a for a, b in pairs) if pairs else None
            summary[f"paired_{label}_cases"] = len(pairs)
        result.append(summary)
    return result


def profit_per_iteration(records, variant):
    measured = [r[variant] for r in records if r[variant]["astar_iterations"] is not None]
    iterations = sum(r["astar_iterations"] for r in measured)
    profit = sum(r["profit_ligne"] or 0 for r in measured)
    return {"measured_cases": len(measured), "total_astar_iterations": iterations,
            "total_profit_ligne_with_missing_profit_as_zero": profit,
            "profit_per_iteration": round(profit / iterations, 6) if iterations else None}


def main():
    if SCRATCH.exists():
        raise RuntimeError(f"scratch already exists: {SCRATCH}")
    atexit.register(shutil.rmtree, SCRATCH, ignore_errors=True)
    assert_preflight_safety()
    selected = selected_checkpoints()
    production_scratch, production_name = instrument_production()
    # Identical OpenTTD/config/days/params/library/single-worker protocol for A and B.
    variant_a = run_variant(production_scratch, production_name, selected, False)
    variant_b = run_variant(SEGMENTED_AI, "TrainLineAISegmented20260828", selected, True)
    records = []
    for index, (seed, rank, iterations, distance) in enumerate(TARGETS):
        key = (seed, rank)
        records.append({"quintile": f"Q{index // 5 + 1}", "seed": seed, "pair_rank": rank,
                        "iterations_production_reference": iterations, "distance_straight": distance,
                        "attempt_id": selected[key]["attempt_id"], "ai_params": selected[key]["ai_params"],
                        "variant_a": variant_a[key], "variant_b": variant_b[key]})
    payload = {
        "design": {"cases": 25, "days": DAYS, "pathfinder_iterations_k": PATHFINDER_ITERATIONS_K,
                   "max_workers": 1, "variant_a": "production copy in /tmp, instrumented for TPM only",
                   "variant_b": "ai/TrainLineAI-segmented", "search_safety": "pre-barrier AITestMode; no mutation before barrier",
                   "profit_per_iteration": "sum(profit_ligne; missing profit=0) / sum(measured A* iterations)"},
        "records": records, "per_quintile_summary": quintile_summary(records),
        "decisive_profit_per_iteration": {"variant_a": profit_per_iteration(records, "variant_a"),
                                            "variant_b": profit_per_iteration(records, "variant_b")}}
    RESULT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
