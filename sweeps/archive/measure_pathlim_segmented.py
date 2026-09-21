"""Mesure Docker scratch-only du prototype segmente sur les neuf PATHLIM.

Le protocole (config, checkpoints, OpenTTD 13.4, 3650 jours, un worker) est celui de
sweeps/measure_pathlim_reachability.py, pour que la comparaison soit directe. L'IA
mesuree est le prototype ai/TrainLineAI-segmented, PAS la production ai/TrainLineAI :
aucun fichier de production, de donnees ou de checkpoint n'est ecrit.

Ce harnais et le prototype ont ete rapatries depuis /tmp le 2026-08-28 -- ils y avaient
ete produits, et /tmp ne survit pas a un redemarrage. Voir docs/journal_2026-08-28.md.
"""
import json
import re
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
SOURCE_AI = ROOT / "ai" / "TrainLineAI-segmented"
CHECKPOINTS = ROOT / "data" / "phase2_hurdle_v3_checkpoints"
RESULT = ROOT / "results" / "phase3_pathlim_segmented.json"
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
    (1003, 160, 82, 145), (1008, 140, 61, 142), (1009, 90, 43, 145),
    (1005, 110, 42, 130), (1003, 50, 38, 113), (1004, 40, 35, 75),
    (1019, 90, 35, 86), (1003, 60, 32, 122), (1017, 90, 30, 132),
)
KEYS = tuple((seed, rank) for seed, rank, _, _ in TARGETS)
STATUS = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
BARRIER = re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")
WORK = re.compile(r"^TPM\|(\d+)\|I(\d+)\|K(\d+)\|S(\w+)$")
SEGMENT = re.compile(r"^TSG\|(\d+)\|N(\d+)\|L(\d+)\|R(\d+)$")


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
            "attempt_id": parsed["attempt_id"], "ai_params": data["raw"]["ai_params"],
            "corridor_water": parsed["corridor_water"], "distance_straight": parsed["distance_straight"],
        }
    if set(found) != set(KEYS):
        raise RuntimeError(f"missing checkpoints: {sorted(set(KEYS) - set(found))}")
    for seed, rank, water, distance in TARGETS:
        actual = found[(seed, rank)]
        if (actual["corridor_water"], actual["distance_straight"]) != (water, distance):
            raise RuntimeError(f"checkpoint mismatch for {(seed, rank)}: {actual}")
    return found


def keep(row):
    experiment = row["experiment"]
    return ({"key": tuple(experiment["pathlim_key"]), "date": str(row["date"]),
             "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()],
             "output": row["output"]},)


def parse(row):
    result = {"seed": row["key"][0], "pair_rank": row["key"][1],
              "raw_signs": row["signs"], "raw_output": row.get("output", "")}
    for sign in row["signs"]:
        if match := STATUS.match(sign):
            _, stage, issue, built, requested = match.groups()
            result.update(stage=stage, issue=issue, trains_built=int(built), trains_requested=int(requested))
        elif match := DETAIL.match(sign):
            _, town_a, town_b, distance, cost = match.groups()
            result.update(town_a=int(town_a), town_b=int(town_b), distance_straight=int(distance), construction_cost=int(cost))
        elif match := BARRIER.match(sign):
            _, tick, flag = match.groups()
            result.update(first_mutation_tick=int(tick), barrier_flag=flag)
        elif match := WORK.match(sign):
            _, iterations, ticks, stop = match.groups()
            stop_names = {"F": "found", "L": "iteration_limit", "D": "preflight_deadline",
                          "B": "backtrack_limit", "E": "open_empty", "N": "no_progress",
                          "W": "time_window_limit", "X": "unknown"}
            result.update(astar_iterations=int(iterations), pathfinding_ticks=int(ticks),
                          stop_reason=stop_names.get(stop, stop))
        elif match := SEGMENT.match(sign):
            _, segments, local_choices, backtracks = match.groups()
            result.update(segments=int(segments), local_choices=int(local_choices), backtracks=int(backtracks))
    required = ("issue", "astar_iterations", "pathfinding_ticks", "stop_reason", "segments")
    missing = [field for field in required if field not in result]
    if missing:
        # Un autosave sans les panneaux signifie que l'IA n'a jamais atteint _reportAll().
        # C'est un resultat de campagne, jamais une raison de jeter les huit autres parties.
        result["report_complete"] = False
        result["missing_report_fields"] = missing
        if "issue" not in result:
            result["issue"] = "NO_REPORT"
    else:
        result["report_complete"] = True
    return result


def main():
    if not (SOURCE_AI / "main.nut").exists():
        raise RuntimeError(f"missing scratch AI: {SOURCE_AI}")
    selected = selected_checkpoints()
    experiments = tuple({
        "seed": key[0], "days": DAYS, "openttd_config": CFG, "pathlim_key": key,
        # The stored checkpoint leaves this AI default at 30k; the reference uses 300k.
        "ais": (local_folder(str(SOURCE_AI), "TrainLineAISegmented20260828",
                              ai_params=tuple(meta["ai_params"].items()) + (("pathfinder_iterations_k", 300),)),),
    } for key, meta in selected.items())
    output = run_experiments(
        openttd_version="13.4", opengfx_version="7.1", max_workers=1, result_processor=keep,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),), experiments=experiments,
    )
    latest = {}
    for row in output:
        if row["key"] not in latest or row["date"] > latest[row["key"]]["date"]:
            latest[row["key"]] = row
    if set(latest) != set(selected):
        raise RuntimeError(f"incomplete: expected {set(selected)}, got {set(latest)}")
    measured = {key: parse(latest[key]) for key in KEYS}
    records = []
    for seed, rank, water, distance in TARGETS:
        key = (seed, rank)
        records.append({"seed": seed, "pair_rank": rank, "corridor_water": water,
                        "distance_straight": distance, "attempt_id": selected[key]["attempt_id"],
                        "ai_params": selected[key]["ai_params"], "segmented": measured[key]})
    payload = {"design": {
        "iterations_limit": ITERATION_LIMIT, "days": DAYS, "max_workers": 1,
        "variant": {"max_cost": 200000, "segment_iterations": 2000,
                    "recovery_segment_iterations": 10000, "frontier_alternatives": 3,
                    "max_backtracks": 4, "time_safe_iterations": 50000,
                    "preflight_margin_ticks": 250,
                    "local_bridge_tunnel_lengths": "3..20 in AITestMode"},
        "pathfinding_ticks": "Ticks from immediately before first segment through final FindPath/Sleep.",
        "astar_iterations": "A* iterations, global cap shared by all segments; FindPath(1) is grouped by 50 sleeps.",
    }, "records": records}
    RESULT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
