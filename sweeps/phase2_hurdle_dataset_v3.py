"""Generate the enriched-feature Phase-2 hurdle dataset v2; no model is trained.

Extends v1 (sweeps/phase2_hurdle_dataset_v1.py, left untouched -- it is the committed record of
the v1 dataset) with the pre-construction features from the backlog in docs/phase3_ml.md 3.2:
station<->town-centre distance, cargo production/acceptance in each station's catchment, engine
specs (speed/capacity/power/price/running cost), Manhattan distance, estimated construction cost,
and a terrain scan (elevation delta, water tiles, unbuildable tiles) along the straight line
between the two towns. All of it is captured by the AI during preflight (before any map mutation)
and posted in signs deferred to after the first real DoCommand, exactly like the existing barrier
panel -- see the comments in ai/TrainLineAI/main.nut around _reportAll() and this.state.*.

100 seeds x the same 20 ranks as v1 = 2000 lines (double the SEEDS, not the ranks per seed: the
train/val/test split is by seed -- docs/phase3_ml.md 3.4 -- so seed diversity is what drives
generalization, not more rows per seed).

Checkpointing / resilience: this campaign runs ~7-8h unattended in a --memory=2g container on a
~3.8GB host. result_processor (keep(), below) runs INSIDE the worker process for one attempt as
soon as that attempt's savegame is parsed -- well before run_experiments()'s own blocking return,
which only happens after ALL 2000 attempts finish. keep() writes a self-contained checkpoint
(raw signs/veh AND the fully parsed row) to data/phase2_hurdle_v3_checkpoints/<attempt_id>.json
immediately, via write-to-temp-then-os.replace (atomic on the same filesystem: a checkpoint file
is either complete or absent, never truncated). A container OOM/kill at any point therefore loses
at most the attempts still in flight, never the ones already checkpointed.

Re-running this script skips attempt_ids that already have a checkpoint file and only submits
what's missing to run_experiments() -- true resume, not just crash-safety. consolidate() rebuilds
the CSV/JSON from every checkpoint present on disk (this invocation's and any earlier partial
run's) every time it runs, so a partial run always yields a usable partial dataset; run the script
again later to fill in the rest.
"""
import csv
import json
import math
import os
import re
import statistics
from openttdlab import bananas_ai_library, local_folder, run_experiments

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
DAYS, INFRA_LIFE_YEARS = 3650, 30
# 100 graines (double de v1), memes 20 rangs. `pair_rank` est volontairement une grille fixe :
# l'IA publie maintenant le nombre de paires reellement disponibles (Q) et consolidate() retire
# les PAIROOR, qui sont des erreurs de configuration par graine, pas des echecs de construction.
# engine_rank <=6 (au-dela, ENGOOR sur certaines graines -- voir info.nut).
SEEDS = tuple(range(1001, 1101))
RANKS = (0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180)
RAW, TABLE = "docs/phase2_hurdle_campaign_v3.json", "data/phase2_hurdle_v3.csv"
CHECKPOINT_DIR = "data/phase2_hurdle_v3_checkpoints"
CONFIGURATION_FAILURES = frozenset(("PAIROOR", "ENGOOR"))

STATUS = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEH = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")
BARRIER = re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")
PREFLIGHT_BUDGET = re.compile(r"^TRLN\|(\d+)\|I(\d+)\|R(\d+)$")
PAIR = re.compile(r"^TRLN\|(\d+)\|P(\d+)-(\d+)\|D(\d+)$")
# Nouveaux panneaux (docs/phase3_ml.md 3.2 backlog) -- voir ai/TrainLineAI/main.nut _code*().
DISTCOST = re.compile(r"^TRLN\|(\d+)\|M(\d+)\|X(-?\d+)$")
ENGSPEC = re.compile(r"^TRLN\|(\d+)\|E(\d+)-(\d+)-(\d+)$")
ENGCOST = re.compile(r"^TRLN\|(\d+)\|F(\d+)-(\d+)$")
STATIONDIST = re.compile(r"^TRLN\|(\d+)\|SA(\d+)-SB(\d+)$")
CARGOA = re.compile(r"^TRLN\|(\d+)\|GA(\d+)-(\d+)$")
CARGOB = re.compile(r"^TRLN\|(\d+)\|GB(\d+)-(\d+)$")
TERRAIN = re.compile(r"^TRLN\|(\d+)\|H(\d+)\|W(\d+)\|U(\d+)$")
CORRIDOR = re.compile(r"^TRLN\|(\d+)\|CH(\d+)\|CW(\d+)\|CU(\d+)$")
PAIRCOUNT = re.compile(r"^TRLN\|(\d+)\|Q(\d+)$")

FIELDS = (
    "attempt_id", "seed", "line_index", "stagger_slot", "pair_rank", "available_pair_count", "engine_rank",
    "num_trains", "wagons_per_train", "pathfinder_iterations_k", "barrier_base_k",
    "town_a", "town_b", "town_a_population", "town_b_population",
    "distance_straight", "distance_manhattan", "estimated_cost",
    "station_a_town_dist", "station_b_town_dist",
    "station_a_cargo_prod", "station_a_cargo_acc", "station_b_cargo_prod", "station_b_cargo_acc",
    "terrain_dh", "terrain_water", "terrain_unbuildable",
    "corridor_dh", "corridor_water", "corridor_unbuildable",
    "engine_max_speed", "engine_power", "engine_price", "engine_running_cost", "wagon_capacity",
    "convoy_capacity",
    "built", "stage", "failure_reason", "barrier_flag", "first_mutation_tick",
    "construction_cost", "vehicle_cost", "infra_cost",
    "n_lead_vehicles", "sum_profit_last_year", "avg_max_age_years",
    "vehicle_amortization_annual", "infra_amortization_annual", "amortization_annual",
    "profit_ligne",
)

# Colonnes de features legitimes (pre-construction) sur lesquelles la sanite calcule des
# correlations avec `built` et des comptes de valeurs uniques -- les 7 de v1 plus le backlog.
FEATURES = (
    "pair_rank", "engine_rank", "num_trains", "wagons_per_train",
    "town_a_population", "town_b_population", "distance_straight", "distance_manhattan",
    "estimated_cost", "station_a_town_dist", "station_b_town_dist",
    "station_a_cargo_prod", "station_a_cargo_acc", "station_b_cargo_prod", "station_b_cargo_acc",
    "terrain_dh", "terrain_water", "terrain_unbuildable",
    "corridor_dh", "corridor_water", "corridor_unbuildable",
    "engine_max_speed", "engine_power", "engine_price", "engine_running_cost",
    "wagon_capacity", "convoy_capacity",
)


def params(seed_i, rank_i, attempt):
    return (
        ("num_trains", 1 + (2 * rank_i + seed_i) % 3),
        ("wagons_per_train", 1 + (5 * rank_i + 2 * seed_i) % 6),
        ("engine_rank", (3 * rank_i + seed_i) % 7),
        ("pair_rank", RANKS[rank_i]),
        ("line_index", attempt),
        ("stagger_slot", 0),
        ("pathfinder_iterations_k", 30),
        ("barrier_base_k", 11),
    )


def veh(chunks):
    total = []
    ages = []
    for v in chunks.get("VEHS", {}).values():
        if v.get("type") != 0:
            continue
        c = v["train"][0]["common"][0]
        if c["owner"] == 0 and c["unitnumber"] != 0:
            total.append(c["profit_last_year"])
            ages.append(c["max_age"])
    if not ages:
        return None
    return {
        "n_lead_vehicles": len(ages),
        "sum_profit_last_year": sum(total),
        "avg_max_age_years": round(sum(ages) / len(ages) / 365, 2),
    }


def parse(x):
    st = dt = bt = pb = pt = dc = es = ec = sd = ca = cb = tr = cr = pc = None
    vc = None
    for s in x["signs"]:
        if m := STATUS.match(s):
            st = m.groups()
        elif m := DETAIL.match(s):
            dt = m.groups()
        elif m := VEH.match(s):
            vc = int(m.group(2))
        elif m := BARRIER.match(s):
            bt = m.groups()
        elif m := PREFLIGHT_BUDGET.match(s):
            pb = m.groups()
        elif m := PAIR.match(s):
            pt = m.groups()
        elif m := DISTCOST.match(s):
            dc = m.groups()
        elif m := ENGSPEC.match(s):
            es = m.groups()
        elif m := ENGCOST.match(s):
            ec = m.groups()
        elif m := STATIONDIST.match(s):
            sd = m.groups()
        elif m := CARGOA.match(s):
            ca = m.groups()
        elif m := CARGOB.match(s):
            cb = m.groups()
        elif m := TERRAIN.match(s):
            tr = m.groups()
        elif m := CORRIDOR.match(s):
            cr = m.groups()
        elif m := PAIRCOUNT.match(s):
            pc = m.groups()

    p = x["ai_params"]
    r = {k: None for k in FIELDS}
    r.update(
        attempt_id=x["attempt_id"], seed=x["seed"],
        line_index=p["line_index"], stagger_slot=p["stagger_slot"],
        pair_rank=p["pair_rank"], engine_rank=p["engine_rank"],
        num_trains=p["num_trains"], wagons_per_train=p["wagons_per_train"],
        # Les checkpoints v3 existants ont ete produits avant le panneau, avec les constantes
        # historiques : les annoter explicitement 30/11 permet de les consolider sans ambiguite.
        pathfinder_iterations_k=p.get("pathfinder_iterations_k", 30),
        barrier_base_k=p.get("barrier_base_k", 11),
        built=False,
    )
    if st:
        r.update(stage=st[1], failure_reason=st[2], built=st[1] == "success")
    if pt:
        r.update(town_a_population=int(pt[1]), town_b_population=int(pt[2]),
                 distance_straight=int(pt[3]))
    if dt:
        r.update(town_a=int(dt[1]), town_b=int(dt[2]), distance_straight=int(dt[3]),
                 construction_cost=int(dt[4]), vehicle_cost=vc)
    if bt:
        r.update(first_mutation_tick=int(bt[1]), barrier_flag=bt[2])
    if pb:
        r.update(pathfinder_iterations_k=int(pb[1]), barrier_base_k=int(pb[2]))
    if dc:
        r.update(distance_manhattan=int(dc[1]), estimated_cost=int(dc[2]))
    if es:
        r.update(engine_max_speed=int(es[1]), wagon_capacity=int(es[2]), engine_power=int(es[3]))
    if ec:
        r.update(engine_price=int(ec[1]), engine_running_cost=int(ec[2]))
    if sd:
        r.update(station_a_town_dist=int(sd[1]), station_b_town_dist=int(sd[2]))
    if ca:
        r.update(station_a_cargo_prod=int(ca[1]), station_a_cargo_acc=int(ca[2]))
    if cb:
        r.update(station_b_cargo_prod=int(cb[1]), station_b_cargo_acc=int(cb[2]))
    if tr:
        r.update(terrain_dh=int(tr[1]), terrain_water=int(tr[2]), terrain_unbuildable=int(tr[3]))
    if cr:
        r.update(corridor_dh=int(cr[1]), corridor_water=int(cr[2]), corridor_unbuildable=int(cr[3]))
    if pc:
        r.update(available_pair_count=int(pc[1]))

    if r["construction_cost"] is not None and vc is not None:
        r["infra_cost"] = r["construction_cost"] - vc
    # Capacite totale du convoi = num_trains * wagons_per_train * capacite d'un wagon -- feature
    # derivee (docs/phase3_ml.md 3.2, "a privilegier sur les proprietes moteur prises isolement"),
    # calculee cote Python plutot que par un panneau de plus.
    if r["wagon_capacity"] is not None:
        r["convoy_capacity"] = r["num_trains"] * r["wagons_per_train"] * r["wagon_capacity"]
    if x["veh"] and vc is not None:
        r.update(x["veh"])
        va = vc / r["avg_max_age_years"]
        ia = r["infra_cost"] / INFRA_LIFE_YEARS
        r.update(vehicle_amortization_annual=round(va), infra_amortization_annual=round(ia),
                 amortization_annual=round(va + ia),
                 profit_ligne=round(r["sum_profit_last_year"] - va - ia))
    return r


def checkpoint_path(attempt_id):
    return os.path.join(CHECKPOINT_DIR, f"{attempt_id}.json")


def keep(row):
    """result_processor -- runs INSIDE the worker process, called once per autosave snapshot of
    one attempt (OpenTTD 13.x extraction mode is 'autosave', monthly, keep_all_autosave=true: a
    3650-day/10-year game yields ~120 snapshots per attempt, verified empirically against this
    exact script -- 476 calls for 4 experiments on the smoke test). save_filenames are processed
    in sorted (== chronological) order within one experiment, so successive calls for the same
    attempt_id simply overwrite the same checkpoint file, and the LAST call -- the final/most
    mature snapshot, which is what we want for profit_ligne -- is the one left on disk. This
    mirrors v1's explicit "keep the row with the latest date per attempt_id" dedup, just done by
    natural overwrite order instead of a second pass. Returns () rather than the row: run_experiments()
    accumulates every result_processor return value into one in-memory list before handing it
    back, and with ~120 snapshots x 2000 attempts that list would hold ~240000 entries -- the
    checkpoint file, not that return value, is the persistence mechanism here (see
    still_missing check below for how completeness is verified instead)."""
    e = row["experiment"]
    raw = {
        "attempt_id": e["attempt_id"], "seed": e["seed"], "date": str(row["date"]),
        "ai_params": dict(e["ais"][0][1]),
        "signs": [s["name"] for s in row["chunks"].get("SIGN", {}).values()],
        "veh": veh(row["chunks"]),
    }
    checkpoint = {"raw": raw, "parsed": parse(raw)}
    path = checkpoint_path(e["attempt_id"])
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(checkpoint, f)
    os.replace(tmp, path)  # atomic on the same filesystem: never a truncated checkpoint
    return ()


def corr(xs, ys):
    good = [(x, y) for x, y in zip(xs, ys) if x is not None]
    if len(good) < 2:
        return None
    a, b = zip(*good)
    ma, mb = statistics.mean(a), statistics.mean(b)
    d = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return None if not d else round(sum((x - ma) * (y - mb) for x, y in good) / d, 6)


def consolidate(requested_count):
    """Rebuilds the CSV + campaign JSON from every checkpoint file currently on disk -- this
    invocation's and any earlier partial run's. Always produces a usable dataset, even if
    incomplete: re-run the script later to fill in the rest, this function re-reads whatever
    exists at call time."""
    rows = {}
    if os.path.isdir(CHECKPOINT_DIR):
        for fname in os.listdir(CHECKPOINT_DIR):
            if not fname.endswith(".json") or ".tmp" in fname:
                continue
            with open(os.path.join(CHECKPOINT_DIR, fname)) as f:
                data = json.load(f)
            rows[data["parsed"]["attempt_id"]] = data["parsed"]
    all_ordered = [rows[i] for i in sorted(rows)]
    configuration = [r for r in all_ordered if r["failure_reason"] in CONFIGURATION_FAILURES]
    ordered = [r for r in all_ordered if r["failure_reason"] not in CONFIGURATION_FAILURES]

    os.makedirs("data", exist_ok=True)
    with open(TABLE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(ordered)

    reasons = {}
    configuration_reasons = {}
    flags = {"M": 0, "O": 0, "missing": 0}
    for r in ordered:
        reasons[r["failure_reason"]] = reasons.get(r["failure_reason"], 0) + 1
        flags[r["barrier_flag"] or "missing"] += 1
    for r in configuration:
        configuration_reasons[r["failure_reason"]] = configuration_reasons.get(r["failure_reason"], 0) + 1
    sanity = {
        "row_count": len(ordered),
        "checkpoint_count": len(all_ordered),
        "requested_count": requested_count,
        "seed_count": len(set(r["seed"] for r in ordered)),
        "built": sum(r["built"] for r in ordered),
        "not_built": sum(not r["built"] for r in ordered),
        "failure_reasons": {k: v for k, v in reasons.items() if k != "OK"},
        "configuration_failures": configuration_reasons,
        "configuration_failure_count": len(configuration),
        "barrier": flags,
        "missing_by_column": {k: sum(r[k] is None for r in ordered) for k in FIELDS},
        "unique_feature_values": {k: len(set(r[k] for r in ordered if r[k] is not None)) for k in FEATURES},
        "feature_built_correlations": {k: corr([r[k] for r in ordered], [int(r["built"]) for r in ordered]) for k in FEATURES},
    }
    raw = {
        "design": {
            "seeds": SEEDS, "ranks": RANKS, "line_count": len(ordered),
            "requested_line_count": requested_count,
            "parameter_design": "deterministic balanced cycles: engine 0..6, trains 1..3, "
                                 "wagons 1..6; one AI/company and stagger_slot=0 per game",
            "barrier_base_tick": 11000,
        },
        "sanity": sanity,
        "records": ordered,
    }
    with open(RAW, "w") as f:
        json.dump(raw, f, indent=2)
    print(json.dumps(sanity, indent=2))
    print(TABLE)
    return len(ordered)


if __name__ == "__main__":
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    runs = [(si, ri) for si in range(len(SEEDS)) for ri in range(len(RANKS))]
    all_attempt_ids = list(range(len(runs)))
    missing = [i for i in all_attempt_ids if not os.path.exists(checkpoint_path(i))]
    print(f"{len(all_attempt_ids) - len(missing)}/{len(all_attempt_ids)} attempts already "
          f"checkpointed on disk; submitting {len(missing)} more to run_experiments().")

    if missing:
        ex = tuple(
            {
                "attempt_id": i, "seed": SEEDS[runs[i][0]], "days": DAYS,
                "openttd_config": CFG,
                "ais": (local_folder("ai/TrainLineAI", "TrainLineAI",
                                      ai_params=params(runs[i][0], runs[i][1], i)),),
            }
            for i in missing
        )
        if any(len(e["ais"]) != 1 for e in ex):
            raise RuntimeError("one company per game invariant violated")
        run_experiments(
            openttd_version="13.4", opengfx_version="7.1", max_workers=3,
            result_processor=keep,
            ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
            experiments=ex,
        )
        # Invariant preserved from v1 ("the number of attempts recovered must equal the number
        # requested, or the missing ones are counted, not silently dropped"), adapted to check
        # checkpoint files on disk instead of run_experiments()'s return value (which keep()
        # deliberately leaves empty -- see its docstring). A missing checkpoint here means that
        # attempt's game produced zero autosave snapshots at all (e.g. the OpenTTD subprocess
        # itself crashed) -- a real silent death, not just an AI-side failure (which still
        # posts an OK/failed status sign and therefore still checkpoints normally).
        still_missing = [i for i in missing if not os.path.exists(checkpoint_path(i))]
        if still_missing:
            raise RuntimeError(f"{len(still_missing)}/{len(missing)} attempts produced no "
                                f"checkpoint this run: {still_missing}")

    total = consolidate(len(all_attempt_ids))
    checkpoint_total = sum(os.path.exists(checkpoint_path(i)) for i in all_attempt_ids)
    if checkpoint_total != len(all_attempt_ids):
        print(f"PARTIAL DATASET: {checkpoint_total}/{len(all_attempt_ids)} attempts checkpointed; "
              f"{total} construction/configuration-valid rows in CSV. "
              f"Re-run this script to fill in the rest -- already-checkpointed attempts are "
              f"skipped, only the missing ones are resubmitted.")
    else:
        print(f"COMPLETE: {checkpoint_total} attempts checkpointed; {total} "
              f"construction/configuration-valid rows in CSV.")
