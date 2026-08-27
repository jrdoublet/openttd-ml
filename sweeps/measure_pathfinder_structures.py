"""Measure bridge/tunnel jumps in the RailPathFinder path selected by TrainLineAI.

The production AI is never edited.  Every experiment gets a temporary copied AI whose
preflight path is annotated with compact SIGN records, then OpenTTDLab parses those signs.

Run from the repository root:
  docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab \\
    -v "$PWD":/work -w /work openttd-lab python sweeps/measure_pathfinder_structures_20260827.py
"""
import atexit
import json
import re
import shutil
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments


ROOT = Path(__file__).resolve().parents[1]
SOURCE_AI = ROOT / "ai" / "TrainLineAI"
SCRATCH = Path("/tmp/openttd-ml-pathfinder-structures-20260827")
NAME = "TrainLineAIStructureMeasure20260827"
OUTPUT = ROOT / "docs" / "phase3_pathfinder_structures.json"

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

# Four score ranks per five independent maps: includes deliberately high ranks 80 and 120.
SEEDS = (42, 1, 7, 100, 2026)
RANKS = (0, 40, 80, 120)
STRUCT = re.compile(r"^TLDBG\|(\d+)\|Jb(\d+)t(\d+)\|Sb(\d+)t(\d+)\|M(\d+)$")
TILES = re.compile(r"^TLDBG\|(\d+)\|Nb(\d+)t(\d+)$")
STATUS = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")


def patch_ai() -> None:
    if SCRATCH.exists():
        raise RuntimeError(f"scratch already exists: {SCRATCH}")
    shutil.copytree(SOURCE_AI, SCRATCH)
    main = SCRATCH / "main.nut"
    source = main.read_text()

    old_state = """    path_found = false,
    path_length = 0, // diagnostic seulement -- NE PAS utiliser comme feature : resultat du
"""
    new_state = """    path_found = false,
    // DEBUG scratch-only: selected path bridge/tunnel jumps, before any construction.
    path_bridge_jumps = 0,
    path_tunnel_jumps = 0,
    path_bridge_span = 0,
    path_tunnel_span = 0,
    path_structure_max_span = 0,
    path_bridge_nodes = 0,
    path_tunnel_nodes = 0,
    path_length = 0, // diagnostic seulement -- NE PAS utiliser comme feature : resultat du
"""
    if source.count(old_state) != 1:
        raise RuntimeError("expected path state insertion point exactly once")
    source = source.replace(old_state, new_state)

    old_preflight_return = """  if (selectedPlanA == null || selectedPlanB == null) return \"no_path_found\";
  return { tiles = simplifiedTiles, plans_a = [selectedPlanA], plans_b = [selectedPlanB] };
"""
    new_preflight_return = """  if (selectedPlanA == null || selectedPlanB == null) return \"no_path_found\";
  return { tiles = simplifiedTiles, plans_a = [selectedPlanA], plans_b = [selectedPlanB] };
"""
    # Kept as an assertion: instrumentation deliberately happens only after the selected path
    # has been returned to Start(), so it measures exactly the route the AI will build.
    if source.count(old_preflight_return) != 1:
        raise RuntimeError("expected preflight return exactly once")

    old_path_found = """  local tiles = selectedPreflight.tiles;
  this.state.path_found = true;

  /* Features de gare/terrain -- connues des que le preflight a reussi (plans de quai retenus +
"""
    new_path_found = """  local tiles = selectedPreflight.tiles;
  this.state.path_found = true;

  /* DEBUG scratch-only.  A retained bridge/tunnel is represented by a non-adjacent
   * jump.  Tunnel identity follows the same API predicate used by the construction
   * loop below; bridge is the remaining jump kind.  IsBridgeTile/IsTunnelTile count
   * already-existing structure nodes if any are present in the selected trace. */
  foreach (tile in tiles) {
    if (AIBridge.IsBridgeTile(tile)) this.state.path_bridge_nodes++;
    if (AITunnel.IsTunnelTile(tile)) this.state.path_tunnel_nodes++;
  }
  for (local i = 0; i < tiles.len() - 1; i++) {
    local from = tiles[i];
    local to = tiles[i + 1];
    local span = AIMap.DistanceManhattan(from, to);
    if (span <= 1) continue;
    if (AITunnel.GetOtherTunnelEnd(from) == to) {
      this.state.path_tunnel_jumps++;
      this.state.path_tunnel_span += span;
    } else {
      this.state.path_bridge_jumps++;
      this.state.path_bridge_span += span;
    }
    if (span > this.state.path_structure_max_span) this.state.path_structure_max_span = span;
  }

  /* Features de gare/terrain -- connues des que le preflight a reussi (plans de quai retenus +
"""
    if source.count(old_path_found) != 1:
        raise RuntimeError("expected selected path insertion point exactly once")
    source = source.replace(old_path_found, new_path_found)

    old_report = """    if (this.state.path_found) {
      this._report(this._codeStationDist());
"""
    new_report = """    if (this.state.path_found) {
      /* Scratch-only compact records. J=count of retained structure jumps; S=sum of
       * their Manhattan spans; M=largest span; N=pre-existing bridge/tunnel nodes. */
      this._report("TLDBG|" + this.state.line_index + "|Jb" + this.state.path_bridge_jumps +
          "t" + this.state.path_tunnel_jumps + "|Sb" + this.state.path_bridge_span +
          "t" + this.state.path_tunnel_span + "|M" + this.state.path_structure_max_span);
      this._report("TLDBG|" + this.state.line_index + "|Nb" + this.state.path_bridge_nodes +
          "t" + this.state.path_tunnel_nodes);
      this._report(this._codeStationDist());
"""
    if source.count(old_report) != 1:
        raise RuntimeError("expected report insertion point exactly once")
    source = source.replace(old_report, new_report)

    old_barrier = "  local BARRIER_BASE = 11000;"
    if source.count(old_barrier) != 1:
        raise RuntimeError("expected BARRIER_BASE exactly once")
    source = source.replace(old_barrier, "  local BARRIER_BASE = 0;")
    main.write_text(source)

    info = SCRATCH / "info.nut"
    info_source = info.read_text()
    old_name = 'function GetName()        { return "TrainLineAI"; }'
    if info_source.count(old_name) != 1:
        raise RuntimeError("expected AI name exactly once")
    info.write_text(info_source.replace(old_name, f'function GetName()        {{ return "{NAME}"; }}'))


def keep(row):
    experiment = row["experiment"]
    return ({
        "seed": experiment["seed"],
        "rank": dict(experiment["ais"][0][1])["pair_rank"],
        "date": str(row["date"]),
        "signs": [x["name"] for x in row["chunks"].get("SIGN", {}).values()],
    },)


def parse(record: dict) -> dict:
    result = {"seed": record["seed"], "pair_rank": record["rank"], "raw_signs": record["signs"]}
    for sign in record["signs"]:
        if match := STRUCT.match(sign):
            _, bj, tj, bs, ts, maximum = match.groups()
            result.update(bridge_jumps=int(bj), tunnel_jumps=int(tj), bridge_span_tiles=int(bs),
                          tunnel_span_tiles=int(ts), max_structure_span_tiles=int(maximum))
        elif match := TILES.match(sign):
            _, bn, tn = match.groups()
            result.update(existing_bridge_nodes=int(bn), existing_tunnel_nodes=int(tn))
        elif match := STATUS.match(sign):
            _, stage, reason, built, requested = match.groups()
            result.update(stage=stage, reason=reason, trains_built=int(built), trains_requested=int(requested))
        elif match := DETAIL.match(sign):
            _, town_a, town_b, distance, construction_cost = match.groups()
            result.update(town_a=int(town_a), town_b=int(town_b), distance_straight=int(distance),
                          construction_cost=int(construction_cost))
    if "stage" not in result:
        raise RuntimeError(f"missing status sign: {record}")
    if result["stage"] != "failed" and "bridge_jumps" not in result:
        raise RuntimeError(f"path succeeded but missing structure sign: {record}")
    return result


def main() -> None:
    patch_ai()
    atexit.register(shutil.rmtree, SCRATCH, ignore_errors=True)
    runs = [(seed, rank) for seed in SEEDS for rank in RANKS]
    experiments = tuple({
        "seed": seed, "days": 1600, "openttd_config": CFG,
        "ais": (local_folder(str(SCRATCH), NAME, ai_params=(
            ("num_trains", 2), ("wagons_per_train", 2), ("engine_rank", 1),
            ("pair_rank", rank), ("line_index", i), ("stagger_slot", 0),
        )),),
    } for i, (seed, rank) in enumerate(runs))
    output = run_experiments(
        openttd_version="13.4", opengfx_version="7.1", max_workers=3,
        result_processor=keep,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
        experiments=experiments,
    )
    latest = {}
    for row in output:
        key = (row["seed"], row["rank"])
        if key not in latest or row["date"] > latest[key]["date"]:
            latest[key] = row
    records = [parse(latest[key]) for key in sorted(latest)]
    selected = [r for r in records if "bridge_jumps" in r]
    with_structure = [r for r in selected if r["bridge_jumps"] + r["tunnel_jumps"] > 0]
    summary = {
        "attempted": len(records), "path_found": len(selected), "path_not_found_or_preflight_failed": len(records) - len(selected),
        "lines_with_bridge_or_tunnel": len(with_structure),
        "mean_structures_per_path_found": (sum(r["bridge_jumps"] + r["tunnel_jumps"] for r in selected) / len(selected)) if selected else 0,
        "mean_structures_per_line_with_structure": (sum(r["bridge_jumps"] + r["tunnel_jumps"] for r in with_structure) / len(with_structure)) if with_structure else 0,
        "bridge_jumps_total": sum(r.get("bridge_jumps", 0) for r in records),
        "tunnel_jumps_total": sum(r.get("tunnel_jumps", 0) for r in records),
        "max_structure_span_tiles": max((r.get("max_structure_span_tiles", 0) for r in records), default=0),
    }
    payload = {
        "design": {"seeds": SEEDS, "pair_ranks": RANKS, "attempts": len(runs), "days": 1600,
                   "barrier_base_in_scratch": 0, "rail_library": "5046524c Pathfinder.Rail v1"},
        "counter_definition": "J counts non-adjacent selected-path jumps; tunnel is AITunnel.GetOtherTunnelEnd(from)==to, bridge is any other jump. S is sum of each jump Manhattan span. N counts IsBridgeTile/IsTunnelTile nodes already present before construction.",
        "summary": summary, "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
