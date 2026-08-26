"""Validate that TrainLineAI's preflight tick barrier absorbs early fixed delays.

All variants are self-cleaning /tmp copies of the current AI.  The scratch-only setting is
injected before any production work in Start(); unlike the historical v2 sweep, it does not
replace the stagger or barrier.  Every record must therefore carry the same first-mutation tick
and an ``M`` barrier flag for its route to count as normalized.
"""
import atexit
from datetime import date, timedelta
import json
import os
import re
import shutil

from openttdlab import bananas_ai_library, local_folder, run_experiments


INFRA_LIFE_YEARS = 30
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
NUM_TRAINS, WAGONS_PER_TRAIN, ENGINE_RANK = 2, 2, 1
DELAYS = (0, 25, 50, 75, 100, 150, 200)
SWEEP_ROUTES = (("seed42_rank0", 42, 0), ("seed1_rank0", 1, 0), ("seed7_rank0", 7, 0))
HISTORICAL_AMPLITUDES = {"seed42_rank0": 1219072, "seed1_rank0": 1583360, "seed7_rank0": 968704}
SOURCE_AI_DIR = "ai/TrainLineAI"
SCRATCH_AI_DIR = "/tmp/openttd-ml-barrier-validation"
SCRATCH_AI_NAME = "TrainLineAIBarrierValidation"
OUTPUT_JSON = "docs/phase2_barrier_validation.json"
STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE_COST_RE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")
BARRIER_RE = re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")


def make_scratch_ai():
    if os.path.exists(SCRATCH_AI_DIR):
        raise RuntimeError(f"Temporary scratch AI already exists: {SCRATCH_AI_DIR}")
    shutil.copytree(SOURCE_AI_DIR, SCRATCH_AI_DIR)
    main_path = os.path.join(SCRATCH_AI_DIR, "main.nut")
    with open(main_path) as source:
        main = source.read()
    insertion_point = "  };\n\n  local setName = function() {"
    delay = '  this.Sleep(AIController.GetSetting("debug_delay_ticks"));\n\n'
    if main.count(insertion_point) != 1:
        raise RuntimeError("Expected Start state/setName boundary exactly once")
    with open(main_path, "w") as output:
        output.write(main.replace(insertion_point, "  };\n\n" + delay + "  local setName = function() {"))
    info_path = os.path.join(SCRATCH_AI_DIR, "info.nut")
    with open(info_path) as source:
        info = source.read()
    old_name = 'function GetName()        { return "TrainLineAI"; }'
    settings_end = "  }\n}\nRegisterAI(TrainLineAIInfo());"
    setting = '''    AddSetting({
      name = "debug_delay_ticks", description = "Scratch-only early fixed delay",
      min_value = 0, max_value = 500, easy_value = 0, medium_value = 0,
      hard_value = 0, custom_value = 0, flags = 0
    });
'''
    if info.count(old_name) != 1 or info.count(settings_end) != 1:
        raise RuntimeError("Expected production AI identity/settings end exactly once")
    info = info.replace(old_name, f'function GetName()        {{ return "{SCRATCH_AI_NAME}"; }}')
    with open(info_path, "w") as output:
        output.write(info.replace(settings_end, setting + settings_end))


def line_profit(chunks):
    total, max_ages, ages, age_field = 0, [], [], True
    for vehicle in chunks.get("VEHS", {}).values():
        if vehicle.get("type") != 0:
            continue
        common = vehicle["train"][0]["common"][0]
        if common["owner"] != 0 or common["unitnumber"] == 0:
            continue
        total += common["profit_last_year"]
        max_ages.append(common["max_age"])
        if "age" in common:
            ages.append(common["age"])
        else:
            age_field = False
    if not max_ages:
        return None
    return {"n_lead_vehicles": len(max_ages), "sum_profit_last_year": total,
            "avg_max_age_years": round(sum(max_ages) / len(max_ages) / 365, 2),
            "lead_vehicle_age_field_available": age_field,
            "lead_vehicle_ages_days": ages if age_field else None}


def keep_row(row):
    experiment = row["experiment"]
    return ({"route_id": experiment["route_id"], "seed": experiment["seed"], "date": str(row["date"]),
             "ai_params": dict(experiment["ais"][0][1]),
             "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()],
             "veh_summary": line_profit(row["chunks"])},)


def parse_record(row):
    status = detail = barrier = None
    vehicle_cost = None
    for sign in row["signs"]:
        if match := STATUS_RE.match(sign):
            status = match.groups()
        elif match := DETAIL_RE.match(sign):
            detail = match.groups()
        elif match := VEHICLE_COST_RE.match(sign):
            vehicle_cost = int(match.group(2))
        elif match := BARRIER_RE.match(sign):
            barrier = match.groups()
    record = {"seed": row["seed"], "capture_date": row["date"], "pair_rank": row["ai_params"]["pair_rank"],
              "ai_params": row["ai_params"], "raw_signs": row["signs"]}
    if status:
        record.update({"stage": status[1], "reason": status[2], "built": int(status[3]), "requested": int(status[4])})
    if barrier:
        record.update({"first_mutation_tick": int(barrier[1]), "barrier_flag": barrier[2]})
    if detail:
        record.update({"town_a": int(detail[1]), "town_b": int(detail[2]), "distance": int(detail[3]),
                       "cost": int(detail[4]), "vehicle_cost": vehicle_cost})
        veh = row["veh_summary"]
        if veh is not None and vehicle_cost is not None:
            infra = record["cost"] - vehicle_cost
            amortization = vehicle_cost / veh["avg_max_age_years"] + infra / INFRA_LIFE_YEARS
            record.update(veh)
            record.update({"infra_cost": infra, "amortization_annual": round(amortization),
                           "profit_ligne": round(veh["sum_profit_last_year"] - amortization)})
            if veh["lead_vehicle_age_field_available"]:
                captured = date.fromisoformat(record["capture_date"])
                record["lead_vehicle_build_dates"] = [str(captured - timedelta(days=age)) for age in veh["lead_vehicle_ages_days"]]
    return record


if __name__ == "__main__":
    make_scratch_ai()
    atexit.register(shutil.rmtree, SCRATCH_AI_DIR, ignore_errors=True)
    experiments = tuple(
        {"route_id": route_id, "seed": seed, "days": DAYS, "openttd_config": OPENTTD_CONFIG,
         "ais": (local_folder(SCRATCH_AI_DIR, SCRATCH_AI_NAME, ai_params=(
             ("num_trains", NUM_TRAINS), ("wagons_per_train", WAGONS_PER_TRAIN),
             ("engine_rank", ENGINE_RANK), ("pair_rank", pair_rank), ("line_index", 0),
             ("debug_delay_ticks", delay))),)}
        for route_id, seed, pair_rank in SWEEP_ROUTES for delay in DELAYS)
    results = run_experiments(
        openttd_version="13.4", opengfx_version="7.1", max_workers=3, result_processor=keep_row,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),), experiments=experiments)
    latest = {}
    for row in results:
        key = (row["route_id"], row["ai_params"]["debug_delay_ticks"])
        if key not in latest or row["date"] > latest[key]["date"]:
            latest[key] = row
    expected = {(route_id, delay) for route_id, _, _ in SWEEP_ROUTES for delay in DELAYS}
    if set(latest) != expected:
        raise RuntimeError(f"Incomplete/ambiguous captures: got {len(latest)}, expected {len(expected)}")
    sweeps = []
    for route_id, seed, pair_rank in SWEEP_ROUTES:
        records = []
        for delay in DELAYS:
            record = parse_record(latest[(route_id, delay)])
            record["delay_ticks"] = delay
            records.append(record)
        profits = [record["profit_ligne"] for record in records if "profit_ligne" in record]
        ticks = {record.get("first_mutation_tick") for record in records}
        flags = {record.get("barrier_flag") for record in records}
        if len(profits) != len(DELAYS):
            raise RuntimeError(f"Timing route {route_id} lacks a measurable profit: {records}")
        sweeps.append({"route_id": route_id, "seed": seed, "pair_rank": pair_rank, "records": records,
                       "amplitude": max(profits) - min(profits), "profit_min": min(profits), "profit_max": max(profits),
                       "first_mutation_ticks": sorted(ticks), "barrier_flags": sorted(flags),
                       "normalized": len(ticks) == 1 and flags == {"M"},
                       "historical_v2_amplitude": HISTORICAL_AMPLITUDES[route_id]})
    all_normalized = all(sweep["normalized"] for sweep in sweeps)
    all_zero = all(sweep["amplitude"] == 0 for sweep in sweeps)
    payload = {"config": {"number_towns": 3, "starting_year": 1970, "town_growth_rate": 2,
                           "industry_density": 4, "inflation": False, "map": "256x256"},
               "delays": list(DELAYS), "design": "Current production AI copied to /tmp; scratch-only delay executes before all production Start work, while production stagger and barrier remain active.",
               "historical_baseline_source": "docs/phase2_tick_shift_sweep_v2.json",
               "sweeps": sweeps,
               "verdict": {"all_barrier_normalized": all_normalized, "all_profit_amplitudes_zero": all_zero,
                           "conclusion": "Barrier absorbed every tested delay; the sweep no longer changes profit_ligne." if all_normalized and all_zero else "Barrier did not fully normalize this sweep; inspect per-route flags, ticks and amplitudes."}}
    with open(OUTPUT_JSON, "w") as output:
        json.dump(payload, output, indent=2)
    for sweep in sweeps:
        print(sweep["route_id"], sweep["first_mutation_ticks"], sweep["barrier_flags"], sweep["amplitude"], "vs", sweep["historical_v2_amplitude"])
    print(f"Wrote {OUTPUT_JSON}")
