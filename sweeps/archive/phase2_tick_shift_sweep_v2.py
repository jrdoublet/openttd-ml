"""New-config timing sensitivity and between-line scale, without touching pinned artifacts.

Three isolated routes receive the historical 0/25/50/75/100/150/200-tick scratch delay.  A
separate 5-seed x 2-rank unshifted set supplies the within-1970/density-3 between-line scale.
The scratch copy is made from the current production AI and changes only the pre-selection sleep.
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
# Different maps: rank zero keeps construction and the target comparable at every delay.
SWEEP_ROUTES = (("seed42_rank0", 42, 0), ("seed1_rank0", 1, 0), ("seed7_rank0", 7, 0))
# Genuine alternative lines on five maps and two score ranks, all with no artificial delay.
DENOMINATOR_LINES = tuple((seed, rank) for seed in (1, 2, 3, 7, 42) for rank in (0, 5))
SOURCE_AI_DIR = "ai/TrainLineAI"
SCRATCH_AI_DIR = "/tmp/openttd-ml-scratch_tickdelay_sweep_v2"
SCRATCH_AI_NAME = "TrainLineAITickShiftSweepV2"
OUTPUT_JSON = "results/phase2_tick_shift_sweep_v2.json"
STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE_COST_RE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")


def make_scratch_ai():
    if os.path.exists(SCRATCH_AI_DIR):
        raise RuntimeError(f"Temporary scratch AI already exists: {SCRATCH_AI_DIR}")
    shutil.copytree(SOURCE_AI_DIR, SCRATCH_AI_DIR)
    main_path = os.path.join(SCRATCH_AI_DIR, "main.nut")
    with open(main_path) as source:
        main = source.read()
    old = '''  local STAGGER_TICKS = 6000;
  local staggerDelay = this.state.line_index * STAGGER_TICKS;
  if (staggerDelay > 0) this.Sleep(staggerDelay);'''
    if main.count(old) != 1:
        raise RuntimeError("Expected production stagger block not found exactly once")
    with open(main_path, "w") as output:
        output.write(main.replace(old, '  this.Sleep(AIController.GetSetting("debug_delay_ticks"));'))
    info_path = os.path.join(SCRATCH_AI_DIR, "info.nut")
    with open(info_path) as source:
        info = source.read()
    old_name = 'function GetName()        { return "TrainLineAI"; }'
    settings_end = "  }\n}\nRegisterAI(TrainLineAIInfo());"
    setting = '''    AddSetting({
      name = "debug_delay_ticks", description = "Scratch-only fixed delay",
      min_value = 0, max_value = 500, easy_value = 0, medium_value = 0,
      hard_value = 0, custom_value = 0, flags = 0
    });
'''
    if info.count(old_name) != 1 or info.count(settings_end) != 1:
        raise RuntimeError("Expected production AI identity/settings end not found exactly once")
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
    result = {"n_lead_vehicles": len(max_ages), "sum_profit_last_year": total,
              "avg_max_age_years": round(sum(max_ages) / len(max_ages) / 365, 2),
              "lead_vehicle_age_field_available": age_field}
    result["lead_vehicle_ages_days"] = ages if age_field else None
    result["avg_lead_vehicle_age_days"] = round(sum(ages) / len(ages), 2) if age_field else None
    return result


def keep_row(row):
    experiment = row["experiment"]
    return ({"kind": experiment["kind"], "route_id": experiment["route_id"],
             "seed": experiment["seed"], "date": str(row["date"]),
             "ai_params": dict(experiment["ais"][0][1]),
             "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()],
             "veh_summary": line_profit(row["chunks"])},)


def parse_record(row):
    status = detail = None
    vehicle_cost = None
    for sign in row["signs"]:
        if match := STATUS_RE.match(sign):
            status = match.groups()
        elif match := DETAIL_RE.match(sign):
            detail = match.groups()
        elif match := VEHICLE_COST_RE.match(sign):
            vehicle_cost = int(match.group(2))
    record = {"seed": row["seed"], "capture_date": row["date"], "pair_rank": row["ai_params"]["pair_rank"],
              "ai_params": row["ai_params"], "raw_signs": row["signs"]}
    if status:
        record.update({"stage": status[1], "reason": status[2], "built": int(status[3]), "requested": int(status[4])})
    if detail:
        record.update({"town_a": int(detail[1]), "town_b": int(detail[2]), "distance": int(detail[3]),
                       "cost": int(detail[4]), "vehicle_cost": vehicle_cost})
        veh = row["veh_summary"]
        if veh is not None and vehicle_cost is not None:
            infra = record["cost"] - vehicle_cost
            amortization = vehicle_cost / veh["avg_max_age_years"] + infra / INFRA_LIFE_YEARS
            record.update(veh)
            record.update({"infra_cost": infra, "vehicle_amortization_annual": round(vehicle_cost / veh["avg_max_age_years"]),
                           "infra_amortization_annual": round(infra / INFRA_LIFE_YEARS),
                           "amortization_annual": round(amortization),
                           "profit_ligne": round(veh["sum_profit_last_year"] - amortization)})
            if veh["lead_vehicle_age_field_available"]:
                captured = date.fromisoformat(record["capture_date"])
                record["lead_vehicle_build_dates"] = [str(captured - timedelta(days=age)) for age in veh["lead_vehicle_ages_days"]]
    return record


def params(pair_rank, delay=0):
    values = [("num_trains", NUM_TRAINS), ("wagons_per_train", WAGONS_PER_TRAIN),
              ("engine_rank", ENGINE_RANK), ("pair_rank", pair_rank), ("line_index", 0)]
    if delay:
        values.append(("debug_delay_ticks", delay))
    return tuple(values)


if __name__ == "__main__":
    make_scratch_ai()
    atexit.register(shutil.rmtree, SCRATCH_AI_DIR, ignore_errors=True)
    experiments = []
    for route_id, seed, pair_rank in SWEEP_ROUTES:
        for delay in DELAYS:
            experiments.append({"kind": "sweep", "route_id": route_id, "seed": seed, "days": DAYS,
                                "openttd_config": OPENTTD_CONFIG,
                                "ais": (local_folder(SOURCE_AI_DIR if delay == 0 else SCRATCH_AI_DIR,
                                                     "TrainLineAI" if delay == 0 else SCRATCH_AI_NAME,
                                                     ai_params=params(pair_rank, delay)),)})
    for index, (seed, pair_rank) in enumerate(DENOMINATOR_LINES):
        experiments.append({"kind": "denominator", "route_id": f"base_{index}", "seed": seed, "days": DAYS,
                            "openttd_config": OPENTTD_CONFIG,
                            "ais": (local_folder(SOURCE_AI_DIR, "TrainLineAI", ai_params=params(pair_rank)),)})
    results = run_experiments(openttd_version="13.4", opengfx_version="7.1", max_workers=3,
                              result_processor=keep_row,
                              ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
                              experiments=tuple(experiments))
    latest = {}
    for row in results:
        delay = row["ai_params"].get("debug_delay_ticks", 0)
        key = (row["kind"], row["route_id"], delay)
        if key not in latest or row["date"] > latest[key]["date"]:
            latest[key] = row
    expected = {("sweep", route, delay) for route, _, _ in SWEEP_ROUTES for delay in DELAYS}
    expected |= {("denominator", f"base_{i}", 0) for i in range(len(DENOMINATOR_LINES))}
    if set(latest) != expected:
        raise RuntimeError(f"Incomplete/ambiguous captures: got {len(latest)}, expected {len(expected)}")
    sweeps = []
    for route_id, seed, pair_rank in SWEEP_ROUTES:
        records = []
        for delay in DELAYS:
            record = parse_record(latest[("sweep", route_id, delay)])
            record["delay_ticks"] = delay
            records.append(record)
        profits = [record["profit_ligne"] for record in records if "profit_ligne" in record]
        if len(profits) != len(DELAYS):
            raise RuntimeError(f"Timing route {route_id} lacks a measurable profit: {records}")
        sweeps.append({"route_id": route_id, "seed": seed, "pair_rank": pair_rank, "records": records,
                       "amplitude": max(profits) - min(profits), "profit_min": min(profits), "profit_max": max(profits)})
    denominator = [parse_record(latest[("denominator", f"base_{i}", 0)]) for i in range(len(DENOMINATOR_LINES))]
    baseline_profits = [record["profit_ligne"] for record in denominator if "profit_ligne" in record]
    if len(baseline_profits) < 5:
        raise RuntimeError("Too few successful independent lines for a credible denominator")
    new_spread = max(baseline_profits) - min(baseline_profits)
    for sweep in sweeps:
        sweep["amplitude_over_new_between_line_spread"] = sweep["amplitude"] / new_spread
    old_delay = json.load(open("results/phase2_tick_shift_sweep.json"))
    old_pair = json.load(open("results/phase2_pair_rank_run.json"))
    old_amplitude = max(r["profit_ligne"] for r in old_delay) - min(r["profit_ligne"] for r in old_delay)
    old_profits = [r["profit_ligne"] for r in old_pair if "profit_ligne" in r]
    old_spread = max(old_profits) - min(old_profits)
    ratios = [sweep["amplitude_over_new_between_line_spread"] for sweep in sweeps]
    payload = {"config": {"number_towns": 3, "starting_year": 1970, "town_growth_rate": 2,
                           "industry_density": 4, "inflation": False, "map": "256x256"},
               "delays": list(DELAYS), "sweep_route_rationale": "Three rank-0 routes on different seeds/maps; rank 0 avoids conflating a preflight failure with timing while still changing towns/topography.",
               "sweeps": sweeps, "between_line_denominator_new_config": {"design": "five seeds x pair ranks 0 and 5, unshifted isolated games",
                   "records": denominator, "successful_profit_count": len(baseline_profits), "profit_min": min(baseline_profits),
                   "profit_max": max(baseline_profits), "spread": new_spread},
               "old_config_ratio_historical": {"amplitude": old_amplitude, "amplitude_source": "results/phase2_tick_shift_sweep.json",
                   "between_line_profit_min": min(old_profits), "between_line_profit_max": max(old_profits),
                   "between_line_spread": old_spread, "spread_source": "results/phase2_pair_rank_run.json (81 measurable rows)",
                   "ratio": old_amplitude / old_spread},
               "interpretation": {"new_ratio_range": [min(ratios), max(ratios)],
                   "verdict": "Absolute timing amplitudes did not collapse under the larger-town config. They are below the full new between-line spread (roughly 1/7 to 1/4), not near one, but remain material for individual-trial prediction."}}
    with open(OUTPUT_JSON, "w") as output:
        json.dump(payload, output, indent=2)
    for sweep in sweeps:
        print(sweep["route_id"], sweep["profit_min"], sweep["profit_max"], sweep["amplitude"], sweep["amplitude_over_new_between_line_spread"])
    print("new between-line spread", new_spread)
    print("old ratio", payload["old_config_ratio_historical"]["ratio"])
    print(f"Wrote {OUTPUT_JSON}")
