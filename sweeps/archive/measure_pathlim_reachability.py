"""Scratch-only 300k A* diagnosis of the nine phase2 v3 PATHLIM cases.

Run only through the Docker command documented in the task.  This never edits the
production AI or its checkpoints: each variant is a fresh copy under /tmp.
"""
import atexit
import json
import re
import shutil
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path(__file__).resolve().parents[1]
SOURCE_AI = ROOT / "ai" / "TrainLineAI"
CHECKPOINTS = ROOT / "data" / "phase2_hurdle_v3_checkpoints"
SCRATCH_ROOT = Path("/tmp/openttd-ml-pathlim-300k-20260827")
# This is a generated diagnostic artifact, kept outside all protected data/docs paths.
# Keeping it in /work means Docker's --rm cannot discard completed measurements.
RESULT = ROOT / "results" / "phase3_pathlim_reachability.json"

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
DAYS = 3650
ITERATION_LIMIT = 300000
TARGETS = (
    # seed, rank, expected corridor water, expected straight-line distance
    (1003, 160, 82, 145),
    (1008, 140, 61, 142),
    (1009, 90, 43, 145),
    (1005, 110, 42, 130),
    (1003, 50, 38, 113),
    (1004, 40, 35, 75),
    (1019, 90, 35, 86),
    (1003, 60, 32, 122),
    (1017, 90, 30, 132),
)
KEYS = tuple((seed, rank) for seed, rank, _, _ in TARGETS)

STATUS = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
BARRIER = re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")
WORK = re.compile(r"^TPM\|(\d+)\|I(\d+)\|K(\d+)\|S(\w+)$")
STRUCT = re.compile(r"^TPM\|(\d+)\|B(\d+)-(\d+)\|T(\d+)-(\d+)$")


def selected_checkpoints():
    found = {}
    for checkpoint in CHECKPOINTS.glob("*.json"):
        data = json.loads(checkpoint.read_text())
        parsed = data["parsed"]
        key = (parsed["seed"], parsed["pair_rank"])
        if key not in KEYS:
            continue
        if parsed["failure_reason"] != "PATHLIM":
            raise RuntimeError(f"{key} is not PATHLIM: {parsed['failure_reason']}")
        found[key] = {
            "attempt_id": parsed["attempt_id"],
            "ai_params": data["raw"]["ai_params"],
            "corridor_water": parsed["corridor_water"],
            "distance_straight": parsed["distance_straight"],
        }
    if set(found) != set(KEYS):
        raise RuntimeError(f"missing checkpoints: {sorted(set(KEYS) - set(found))}")
    for seed, rank, water, distance in TARGETS:
        actual = found[(seed, rank)]
        if (actual["corridor_water"], actual["distance_straight"]) != (water, distance):
            raise RuntimeError(f"checkpoint mismatch for {(seed, rank)}: {actual}")
    return found


def replace_once(source, old, new, description):
    if source.count(old) != 1:
        raise RuntimeError(f"unexpected {description} block ({source.count(old)} matches)")
    return source.replace(old, new)


def patch_ai(label, long_structures):
    scratch = SCRATCH_ROOT / label
    shutil.copytree(SOURCE_AI, scratch)
    main = scratch / "main.nut"
    source = main.read_text()

    production_limits = """  local pathfinder = RailPathFinder();
  /* Autoriser les franchissements longs : les plafonds de la bibliotheque sont seulement 6
   * tuiles, alors que certains corridors retenus exigent un pont ou tunnel plus long. */
  pathfinder.cost.max_cost = 250000; // etait 200000
  pathfinder.cost.max_bridge_length = 20; // etait 6 (defaut bibliotheque)
  pathfinder.cost.max_tunnel_length = 20; // etait 6 (defaut bibliotheque)
  pathfinder.InitializePath(sources, goals);"""
    if long_structures:
        limits = """  local pathfinder = RailPathFinder();
  pathfinder.cost.max_cost = 250000;
  pathfinder.cost.max_bridge_length = 20;
  pathfinder.cost.max_tunnel_length = 20;
  local pathfinderStartTick = AIController.GetTick();
  pathfinder.InitializePath(sources, goals);"""
    else:
        # Deliberately do not set bridge/tunnel maxima: Pathfinder.Rail defaults are 6.
        limits = """  local pathfinder = RailPathFinder();
  pathfinder.cost.max_cost = 200000;
  local pathfinderStartTick = AIController.GetTick();
  pathfinder.InitializePath(sources, goals);"""
    source = replace_once(source, production_limits, limits, "production limits")

    old_loop = """  local path = false;
  local iterationsLeft = 30000;
  while (path == false && iterationsLeft > 0 && AIController.GetTick() < deadlineTick) {
    path = pathfinder.FindPath(50);
    iterationsLeft -= 50;
    this.Sleep(1);
  }
  if (path == false) return "path_search_limit";
  if (path == null) return "no_path_found";"""
    new_loop = """  local path = false;
  local iterationsLeft = 300000;
  while (path == false && iterationsLeft > 0 && AIController.GetTick() < deadlineTick) {
    path = pathfinder.FindPath(50);
    iterationsLeft -= 50;
    this.Sleep(1);
  }
  this.state.pathfinder_iterations = 300000 - iterationsLeft;
  this.state.pathfinder_ticks = AIController.GetTick() - pathfinderStartTick;
  if (path != false && path != null) {
    this.state.pathfinder_stop = "found";
  } else if (path == null) {
    this.state.pathfinder_stop = "open_empty";
  } else if (iterationsLeft <= 0) {
    this.state.pathfinder_stop = "iteration_limit";
  } else if (AIController.GetTick() >= deadlineTick) {
    this.state.pathfinder_stop = "preflight_deadline";
  } else {
    this.state.pathfinder_stop = "unknown";
  }
  if (path == false) return "path_search_limit";
  if (path == null) return "no_path_found";"""
    source = replace_once(source, old_loop, new_loop, "A* loop")

    old_state = """    path_found = false,
    path_length = 0, // diagnostic seulement -- NE PAS utiliser comme feature : resultat du
"""
    new_state = """    path_found = false,
    // Scratch-only A* diagnostics.
    pathfinder_iterations = null,
    pathfinder_ticks = null,
    pathfinder_stop = null,
    path_bridge_count = 0,
    path_tunnel_count = 0,
    path_bridge_max_length = 0,
    path_tunnel_max_length = 0,
    path_length = 0, // diagnostic seulement -- NE PAS utiliser comme feature : resultat du
"""
    source = replace_once(source, old_state, new_state, "state insertion")

    old_path = """  local tiles = selectedPreflight.tiles;
  this.state.path_found = true;

  /* Features de gare/terrain -- connues des que le preflight a reussi (plans de quai retenus +
"""
    new_path = """  local tiles = selectedPreflight.tiles;
  this.state.path_found = true;

  /* A non-adjacent retained-path hop is a bridge or tunnel. Its library length is
   * endpoint Manhattan distance + 1. */
  for (local i = 0; i < tiles.len() - 1; i++) {
    local from = tiles[i];
    local to = tiles[i + 1];
    local length = AIMap.DistanceManhattan(from, to) + 1;
    if (length <= 2) continue;
    if (AITunnel.GetOtherTunnelEnd(from) == to) {
      this.state.path_tunnel_count++;
      if (length > this.state.path_tunnel_max_length) this.state.path_tunnel_max_length = length;
    } else {
      this.state.path_bridge_count++;
      if (length > this.state.path_bridge_max_length) this.state.path_bridge_max_length = length;
    }
  }

  /* Features de gare/terrain -- connues des que le preflight a reussi (plans de quai retenus +
"""
    source = replace_once(source, old_path, new_path, "retained path insertion")

    old_report = """  this._report(this._code());
  if (this.state.pair_count != null) this._report(this._codePairCount());
"""
    new_report = """  this._report(this._code());
  /* Scratch-only signs; split to remain below the 31-character sign-name limit. */
  if (this.state.pathfinder_iterations != null) {
    this._report("TPM|" + this.state.line_index + "|I" + this.state.pathfinder_iterations +
        "|K" + this.state.pathfinder_ticks + "|S" + this.state.pathfinder_stop);
  }
  if (this.state.path_found) {
    this._report("TPM|" + this.state.line_index + "|B" + this.state.path_bridge_count +
        "-" + this.state.path_bridge_max_length + "|T" + this.state.path_tunnel_count +
        "-" + this.state.path_tunnel_max_length);
  }
  if (this.state.pair_count != null) this._report(this._codePairCount());
"""
    source = replace_once(source, old_report, new_report, "report insertion")
    main.write_text(source)

    info = scratch / "info.nut"
    name = f"TrainLineAIPathlim300k{label.title()}"
    info_source = info.read_text()
    info_source = replace_once(
        info_source, 'function GetName()        { return "TrainLineAI"; }',
        f'function GetName()        {{ return "{name}"; }}', "AI name")
    info.write_text(info_source)
    return scratch, name


def keep(row):
    experiment = row["experiment"]
    return ({
        "key": tuple(experiment["pathlim_key"]),
        "date": str(row["date"]),
        "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()],
    },)


def parse(row):
    result = {"seed": row["key"][0], "pair_rank": row["key"][1], "raw_signs": row["signs"]}
    for sign in row["signs"]:
        if match := STATUS.match(sign):
            _, stage, issue, built, requested = match.groups()
            result.update(stage=stage, issue=issue, trains_built=int(built), trains_requested=int(requested))
        elif match := DETAIL.match(sign):
            _, town_a, town_b, distance, cost = match.groups()
            result.update(town_a=int(town_a), town_b=int(town_b), distance_straight=int(distance),
                          construction_cost=int(cost))
        elif match := BARRIER.match(sign):
            _, tick, flag = match.groups()
            result.update(first_mutation_tick=int(tick), barrier_flag=flag)
        elif match := WORK.match(sign):
            _, iterations, ticks, stop = match.groups()
            result.update(astar_iterations=int(iterations), pathfinding_ticks=int(ticks), stop_reason=stop)
        elif match := STRUCT.match(sign):
            _, bridges, bridge_max, tunnels, tunnel_max = match.groups()
            result.update(bridges=int(bridges), max_bridge_length=int(bridge_max),
                          tunnels=int(tunnels), max_tunnel_length=int(tunnel_max))
    required = ("issue", "astar_iterations", "pathfinding_ticks", "stop_reason")
    missing = [field for field in required if field not in result]
    if missing:
        raise RuntimeError(f"missing {missing} in {result['seed']}/{result['pair_rank']}: {row['signs']}")
    # The status issue covers later construction too (and may therefore be TRKFAIL or
    # STNFAIL after a successful preflight).  The instrumented A* stop is authoritative.
    found = result["stop_reason"] == "found"
    if found and "bridges" not in result:
        raise RuntimeError(f"successful route lacks structures: {result}")
    return result


def run_variant(label, long_structures, selected):
    scratch, name = patch_ai(label, long_structures)
    experiments = tuple({
        "seed": key[0], "days": DAYS, "openttd_config": CFG, "pathlim_key": key,
        "ais": (local_folder(str(scratch), name, ai_params=tuple(meta["ai_params"].items())),),
    } for key, meta in selected.items())
    output = run_experiments(
        openttd_version="13.4", opengfx_version="7.1", max_workers=1,
        result_processor=keep,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
        experiments=experiments,
    )
    latest = {}
    for row in output:
        if row["key"] not in latest or row["date"] > latest[row["key"]]["date"]:
            latest[row["key"]] = row
    if set(latest) != set(selected):
        raise RuntimeError(f"incomplete {label}: expected {set(selected)}, got {set(latest)}")
    return {key: parse(latest[key]) for key in KEYS}


def main():
    if SCRATCH_ROOT.exists():
        raise RuntimeError(f"scratch already exists: {SCRATCH_ROOT}")
    atexit.register(shutil.rmtree, SCRATCH_ROOT, ignore_errors=True)
    selected = selected_checkpoints()
    short = run_variant("short", False, selected)
    # Preserve completed A results if B encounters a runner error.
    RESULT.write_text(json.dumps({"design": {"iterations_limit": ITERATION_LIMIT},
                                  "variant_a_short_partial": [short[key] for key in KEYS]},
                                 indent=2) + "\n")
    long = run_variant("long", True, selected)
    records = []
    for seed, rank, water, distance in TARGETS:
        key = (seed, rank)
        records.append({
            "seed": seed, "pair_rank": rank, "corridor_water": water, "distance_straight": distance,
            "attempt_id": selected[key]["attempt_id"], "ai_params": selected[key]["ai_params"],
            "variant_a_short": short[key], "variant_b_long": long[key],
        })
    payload = {
        "design": {
            "iterations_limit": ITERATION_LIMIT,
            "days": DAYS,
            "max_workers": 1,
            "variant_a": {"max_cost": 200000, "max_bridge_length": "library default 6", "max_tunnel_length": "library default 6"},
            "variant_b": {"max_cost": 250000, "max_bridge_length": 20, "max_tunnel_length": 20},
            "pathfinding_ticks": "AIController ticks from immediately before InitializePath through the final FindPath/Sleep loop iteration.",
            "astar_iterations": "requested A* iterations in production's FindPath(50) granularity.",
            "stop_reason": {"found": "path found", "iteration_limit": "300000 exhausted", "preflight_deadline": "preflightDeadline reached", "open_empty": "open queue empty / permanently unreachable"},
        },
        "records": records,
    }
    RESULT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
