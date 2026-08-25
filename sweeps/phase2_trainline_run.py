"""Petite campagne de demonstration pour TrainLineAI : plusieurs graines, plusieurs combinaisons
de rangs (villes/moteur), pour verifier que les deux panneaux (statut + detail) se posent
correctement et que les champs (line_index, paire de villes, distance, cout) sont bien lisibles
via le chunk SIGN d'OpenTTDLab -- pas seulement AILog. Pas encore l'orchestrateur multi-lignes-
par-partie (chaque experience ci-dessous est une partie/compagnie separee) : juste une verification
de bout en bout du format de panneau revise, sur un vrai batch.
"""
import json
import re
from openttdlab import run_experiments, bananas_ai_library, local_folder

OPENTTD_CONFIG = """
[difficulty]
number_towns = 2
industry_density = 4

[economy]
inflation = false

[game_creation]
starting_year = 1950
map_x = 8
map_y = 8
"""

DAYS = 365  # marge confortable au-dessus des ~200 jours observes pour les cas lents en debug

# (seed, town_a_rank, town_b_rank, engine_rank, num_trains, wagons_per_train)
RUNS = [
    (42, 0, 1, 0, 2, 2),
    (42, 2, 8, 1, 2, 2),
    (42, 0, 15, 2, 1, 1),
    (100, 0, 1, 0, 2, 2),
    (100, 3, 9, 1, 2, 2),
    (100, 5, 12, 2, 1, 1),
    (7, 0, 1, 0, 2, 2),
    (7, 1, 6, 1, 2, 2),
    (7, 4, 14, 2, 1, 1),
    (999, 0, 1, 0, 2, 2),
    (999, 2, 10, 1, 2, 2),
    (999, 0, 13, 2, 3, 1),
]

STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")


def keep_signs_and_params(row):
    ai_params = dict(row["experiment"]["ais"][0][1])
    signs = row["chunks"].get("SIGN", {})
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "ai_params": ai_params,
        "signs": [s["name"] for s in signs.values()],
    },)


if __name__ == "__main__":
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=3,
        result_processor=keep_signs_and_params,
        ai_libraries=(
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
        experiments=(
            {
                "seed": seed,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": (
                    local_folder(
                        "ai/TrainLineAI", "TrainLineAI",
                        ai_params=(
                            ("num_trains", num_trains),
                            ("wagons_per_train", wagons_per_train),
                            ("town_a_rank", town_a_rank),
                            ("town_b_rank", town_b_rank),
                            ("engine_rank", engine_rank),
                            ("line_index", i),
                        ),
                    ),
                ),
            }
            for i, (seed, town_a_rank, town_b_rank, engine_rank, num_trains, wagons_per_train) in enumerate(RUNS)
        ),
    )

    # Une seule ligne par experience/graine ici -- garder le dernier savegame de chacune.
    by_seed_line = {}
    for r in results:
        idx = r["ai_params"]["line_index"]
        prev = by_seed_line.get(idx)
        if prev is None or r["date"] > prev["date"]:
            by_seed_line[idx] = r

    records = []
    for idx in sorted(by_seed_line):
        r = by_seed_line[idx]
        status = None
        detail = None
        for s in r["signs"]:
            m = STATUS_RE.match(s)
            if m:
                status = m.groups()
                continue
            m = DETAIL_RE.match(s)
            if m:
                detail = m.groups()
        rec = {
            "line_index": idx,
            "seed": r["seed"],
            "ai_params": r["ai_params"],
            "raw_signs": r["signs"],
        }
        if status:
            rec.update({
                "stage": status[1],
                "reason": status[2],
                "built": int(status[3]),
                "requested": int(status[4]),
            })
        if detail:
            rec.update({
                "town_a": int(detail[1]),
                "town_b": int(detail[2]),
                "distance": int(detail[3]),
                "cost": int(detail[4]),
            })
        records.append(rec)

    print(f"{len(records)} lignes / {len(results)} savegames captures\n")
    for rec in records:
        p = rec["ai_params"]
        print(
            f"line={rec['line_index']:2d} seed={rec['seed']:4d} "
            f"ranks=(A{p['town_a_rank']},B{p['town_b_rank']},E{p['engine_rank']}) "
            f"trains={p['num_trains']}x{p['wagons_per_train']}w -> "
            f"{rec.get('stage','?'):8s} {rec.get('reason','?'):8s} "
            f"{rec.get('built','?')}/{rec.get('requested','?')}  "
            f"towns={rec.get('town_a','-')}-{rec.get('town_b','-')} "
            f"dist={rec.get('distance','-')} cost={rec.get('cost','-')}"
        )

    with open("docs/phase2_trainline_run.json", "w") as f:
        json.dump(records, f, indent=2)
    print("\nEcrit dans docs/phase2_trainline_run.json")
