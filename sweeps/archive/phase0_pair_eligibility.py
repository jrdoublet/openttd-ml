"""Measure the exact non-topographic pair pool used by TrainLineAI's selection.

The ephemeral AI reproduces the current selection constants and affordability estimate, then
publishes compact counters through SIGN.  It does not build anything.  Production orders the
disjoint-town check before the other filters; in this single-company probe it has no effect, so
the JSON deliberately records it separately rather than mixing it into the requested sequence.
"""
import atexit
import json
import os
import re
import shutil

from openttdlab import bananas_ai_library, local_folder, run_experiments


SEEDS = (1, 2, 3, 4, 5, 6, 7, 42)
CONFIGS = (
    ("old_d2_y1950", 2, 1950),
    ("new_d3_y1970", 3, 1970),
)
NUM_TRAINS = 2
WAGONS_PER_TRAIN = 2
SCRATCH_AI_DIR = "/tmp/openttd-ml-pair-eligibility-probe"
PROBE_AI_NAME = "PairEligibilityProbe"
OUTPUT_JSON = "results/phase0_pair_eligibility.json"
PAIR_RE = re.compile(r"^PELG\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
NEGATIVE_CLASS_RANKS = (20, 40, 59)


def openttd_config(number_towns, starting_year):
    return f"""
[difficulty]
number_towns = {number_towns}
industry_density = 4

[economy]
inflation = false
town_growth_rate = 2

[game_creation]
starting_year = {starting_year}
map_x = 8
map_y = 8
"""


def make_probe_ai():
    if os.path.exists(SCRATCH_AI_DIR):
        raise RuntimeError(f"Temporary probe already exists: {SCRATCH_AI_DIR}")
    os.makedirs(SCRATCH_AI_DIR)
    with open(os.path.join(SCRATCH_AI_DIR, "info.nut"), "w") as output:
        output.write(f'''class {PROBE_AI_NAME}Info extends AIInfo {{
  function GetAuthor() {{ return "openttd-ml"; }}
  function GetName() {{ return "{PROBE_AI_NAME}"; }}
  function GetDescription() {{ return "Temporary exact pair-pool probe"; }}
  function GetVersion() {{ return 1; }}
  function GetDate() {{ return "2026-08-26"; }}
  function CreateInstance() {{ return "{PROBE_AI_NAME}"; }}
  function GetShortName() {{ return "PELG"; }}
  function GetAPIVersion() {{ return "13"; }}
}}
RegisterAI({PROBE_AI_NAME}Info());
''')
    with open(os.path.join(SCRATCH_AI_DIR, "main.nut"), "w") as output:
        output.write(f'''class {PROBE_AI_NAME} extends AIController {{}}

function {PROBE_AI_NAME}::Start()
{{
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  local rails = AIRailTypeList();
  if (rails.IsEmpty()) return;
  local railType = rails.Begin();
  AIRail.SetCurrentRailType(railType);
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  local candidates = [];
  foreach (town, ignored in towns) candidates.push(town);
  local minDistance = 20;
  local maxDistance = 150;
  local minPopulation = 500;
  local platformLength = ({WAGONS_PER_TRAIN} + 2) / 2 + 1;
  local trackCost = AIRail.GetBuildCost(railType, AIRail.BT_TRACK);
  local stationCost = AIRail.GetBuildCost(railType, AIRail.BT_STATION);
  local depotCost = AIRail.GetBuildCost(railType, AIRail.BT_DEPOT);
  local availableMoney = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local allPairs = candidates.len() * (candidates.len() - 1) / 2;
  local afterDistance = 0;
  local afterAffordability = 0;
  local afterPopulation = 0;
  for (local i = 0; i < candidates.len() - 1; i++) {{
    local a = candidates[i];
    local locA = AITown.GetLocation(a);
    local popA = AITown.GetPopulation(a);
    for (local j = i + 1; j < candidates.len(); j++) {{
      local b = candidates[j];
      local distance = sqrt(AIMap.DistanceSquare(locA, AITown.GetLocation(b)).tofloat()).tointeger();
      if (distance < minDistance || distance > maxDistance) continue;
      afterDistance++;
      local estimate = (distance + 2) * trackCost * 2 + 2 * platformLength * stationCost + depotCost;
      if (estimate > availableMoney) continue;
      afterAffordability++;
      if (popA < minPopulation || AITown.GetPopulation(b) < minPopulation) continue;
      afterPopulation++;
    }}
  }}
  local engines = AIEngineList(AIVehicle.VT_RAIL);
  engines.Valuate(AIEngine.IsWagon); engines.KeepValue(0);
  engines.Valuate(AIEngine.IsBuildable); engines.KeepValue(1);
  /* PELG|all|distance|affordable|population|disjoint_removed|rail_engines */
  local text = "PELG|" + allPairs + "|" + afterDistance + "|" + afterAffordability + "|" +
      afterPopulation + "|0|" + engines.Count();
  AISign.BuildSign(AIMap.GetTileIndex(AIMap.GetMapSizeX() / 2, AIMap.GetMapSizeY() / 2), text);
  while (true) this.Sleep(1000);
}}
''')


def keep_signs(row):
    return ({
        "config_name": row["experiment"]["config_name"], "seed": row["experiment"]["seed"],
        "date": str(row["date"]), "ai_params": dict(row["experiment"]["ais"][0][1]),
        "signs": [s["name"] for s in row["chunks"].get("SIGN", {}).values()],
    },)


if __name__ == "__main__":
    make_probe_ai()
    atexit.register(shutil.rmtree, SCRATCH_AI_DIR, ignore_errors=True)
    results = run_experiments(
        openttd_version="13.4", opengfx_version="7.1", max_workers=3,
        result_processor=keep_signs,
        experiments=tuple({
            "config_name": name, "seed": seed, "days": 365,
            "openttd_config": openttd_config(towns, year),
            "ais": (local_folder(SCRATCH_AI_DIR, PROBE_AI_NAME),),
        } for name, towns, year in CONFIGS for seed in SEEDS),
    )
    latest = {}
    for row in results:
        key = (row["config_name"], row["seed"])
        if key not in latest or row["date"] > latest[key]["date"]:
            latest[key] = row
    records = []
    for name, _, _ in CONFIGS:
        for seed in SEEDS:
            row = latest[(name, seed)]
            matches = [PAIR_RE.match(sign) for sign in row["signs"]]
            matches = [m for m in matches if m]
            if len(matches) != 1:
                raise RuntimeError(f"Expected one PELG sign for {name}/{seed}, got {row['signs']}")
            all_pairs, distance, affordable, population, disjoint_removed, engines = map(int, matches[0].groups())
            records.append({
                "config_name": name, "seed": seed, "capture_date": row["date"],
                "all_pairs": all_pairs, "after_distance": distance,
                "after_affordability": affordable, "after_population_floor": population,
                "disjoint_removed_single_company": disjoint_removed,
                "after_disjoint_single_company": population - disjoint_removed,
                "usable_pair_rank_ceiling": population - 1,
                "buildable_non_wagon_rail_engines": engines,
            })
    payload = {
        "method": "SIGN probe reproducing current main.nut constants/estimate; no construction",
        "selection_order_in_main_nut": ["disjoint", "distance", "affordability", "population_floor"],
        "reported_comparable_filter_sequence": ["all_pairs", "after_distance", "after_affordability", "after_population_floor"],
        "disjoint_note": "In each isolated one-company game, no towns are served at selection, so this filter removes zero pairs and is reported separately.",
        "configs": {name: {"number_towns": towns, "starting_year": year, "town_growth_rate": 2}
                    for name, towns, year in CONFIGS},
        "seeds": list(SEEDS), "records": records,
    }

    # Candidate counts alone prove that ranks remain addressable, but do not label topographic
    # failures.  This small current-AI check therefore tests the historical high-rank band rather
    # than infer the stage-1 negative class from eligibility alone.
    validation = run_experiments(
        openttd_version="13.4", opengfx_version="7.1", max_workers=3,
        result_processor=keep_signs,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
        experiments=tuple({
            "config_name": "new_d3_y1970_rank_probe", "seed": seed, "days": 365 * 10,
            "openttd_config": openttd_config(3, 1970),
            "ais": (local_folder("ai/TrainLineAI", "TrainLineAI", ai_params=(
                ("num_trains", NUM_TRAINS), ("wagons_per_train", WAGONS_PER_TRAIN),
                ("engine_rank", 1), ("pair_rank", rank), ("line_index", 0),
            )),),
        } for seed in SEEDS for rank in NEGATIVE_CLASS_RANKS),
    )
    validated = {}
    for row in validation:
        rank = row["ai_params"]["pair_rank"]
        key = (row["seed"], rank)
        if key not in validated or row["date"] > validated[key]["date"]:
            validated[key] = row
    validation_records = []
    for seed in SEEDS:
        for rank in NEGATIVE_CLASS_RANKS:
            row = validated[(seed, rank)]
            matches = [STATUS_RE.match(sign) for sign in row["signs"]]
            matches = [match for match in matches if match]
            if len(matches) != 1:
                raise RuntimeError(f"Expected one TRLN status for rank probe {seed}/{rank}: {row['signs']}")
            _, stage, reason, built, requested = matches[0].groups()
            validation_records.append({"seed": seed, "pair_rank": rank, "capture_date": row["date"],
                                       "stage": stage, "reason": reason, "built": int(built),
                                       "requested": int(requested)})
    failures = [r for r in validation_records if r["stage"] != "success"]
    payload["negative_class_constructibility_probe_new_config"] = {
        "design": "Current production AI, isolated 10-year games: 8 seeds x ranks 20, 40, 59.",
        "records": validation_records,
        "success_count": len(validation_records) - len(failures), "failure_count": len(failures),
        "failure_reasons": {reason: sum(r["reason"] == reason for r in failures)
                            for reason in sorted({r["reason"] for r in failures})},
        "verdict": ("The negative class survives: high ranks are addressable and include real "
                    "non-success outcomes under the new configuration."
                    if failures else "No negative outcome appeared in this small high-rank probe; "
                    "eligibility remains wide, but the gradient would need a broader label sweep."),
    }
    with open(OUTPUT_JSON, "w") as output:
        json.dump(payload, output, indent=2)
    for record in records:
        print(record)
    print(f"Wrote {OUTPUT_JSON}")
