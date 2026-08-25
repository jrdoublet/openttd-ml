"""profit_ligne = somme(profit des vehicules de la ligne) - amortissement(cout de construction).

Assemble les deux morceaux verifies separement :
- profit d'exploitation par vehicule (VEHS.<id>.train[0].common[0].profit_this_year, vehicule de
  tete du consist seulement -- voir sweeps/phase2_vehs_explore.py et docs/methode.md),
- cout de construction (panneau de detail TRLN|<idx>|T<a>-<b>|D<dist>|C<cout>, mesure par
  AIAccounting cote AI -- voir ai/TrainLineAI/main.nut).

Horizon d'amortissement : max_age du materiel (deja present dans le savegame, pas une duree
arbitraire ajoutee). Voir docs/methode.md pour la discussion de cette simplification.
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

DAYS = 365 * 3  # meme fenetre que phase2_vehs_explore.py : assez pour un profit_this_year lisible

DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")

# (seed, town_a_rank, town_b_rank, engine_rank, num_trains, wagons_per_train, line_index)
RUNS = [
    (42, 0, 1, 0, 2, 2, 0),
    (7, 1, 6, 1, 2, 2, 1),
    (100, 3, 9, 1, 2, 2, 2),
]


def line_profit(chunks, owner):
    """Somme profit_this_year des vehicules de tete (unitnumber != 0) de cette compagnie, et
    l'age max moyen du materiel (annees) pour l'amortissement."""
    vehs = chunks.get("VEHS", {})
    total_profit = 0
    max_ages_days = []
    n_lead = 0
    for v in vehs.values():
        if v.get("type") != 0:
            continue
        common = v["train"][0]["common"][0]
        if common["owner"] != owner or common["unitnumber"] == 0:
            continue
        total_profit += common["profit_this_year"]
        max_ages_days.append(common["max_age"])
        n_lead += 1
    if n_lead == 0:
        return None
    avg_max_age_years = (sum(max_ages_days) / len(max_ages_days)) / 365.0
    return {
        "n_lead_vehicles": n_lead,
        "sum_profit_this_year": total_profit,
        "avg_max_age_years": round(avg_max_age_years, 2),
    }


def keep_signs_and_vehs(row):
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "ai_params": dict(row["experiment"]["ais"][0][1]),
        "signs": [s["name"] for s in row["chunks"].get("SIGN", {}).values()],
        "veh_summary": line_profit(row["chunks"], owner=0),
    },)


if __name__ == "__main__":
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=3,
        result_processor=keep_signs_and_vehs,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
        experiments=(
            {
                "seed": seed,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": (
                    local_folder("ai/TrainLineAI", "TrainLineAI", ai_params=(
                        ("num_trains", num_trains), ("wagons_per_train", wagons_per_train),
                        ("town_a_rank", town_a_rank), ("town_b_rank", town_b_rank),
                        ("engine_rank", engine_rank), ("line_index", line_index),
                    )),
                ),
            }
            for (seed, town_a_rank, town_b_rank, engine_rank, num_trains, wagons_per_train, line_index) in RUNS
        ),
    )

    by_line = {}
    for r in results:
        idx = r["ai_params"]["line_index"]
        prev = by_line.get(idx)
        if prev is None or r["date"] > prev["date"]:
            by_line[idx] = r

    records = []
    for idx in sorted(by_line):
        r = by_line[idx]
        construction_cost = None
        town_a = town_b = distance = None
        for s in r["signs"]:
            m = DETAIL_RE.match(s)
            if m:
                town_a, town_b, distance, construction_cost = (
                    int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)),
                )

        rec = {
            "line_index": idx,
            "seed": r["seed"],
            "construction_cost": construction_cost,
            "town_a": town_a, "town_b": town_b, "distance": distance,
        }
        veh = r["veh_summary"]
        if construction_cost is not None and veh is not None and veh["avg_max_age_years"] > 0:
            amortization = construction_cost / veh["avg_max_age_years"]
            rec.update(veh)
            rec["amortization_annual"] = round(amortization)
            rec["profit_ligne"] = round(veh["sum_profit_this_year"] - amortization)
        records.append(rec)

    print(f"{len(records)} lignes\n")
    for rec in records:
        print(
            f"line={rec['line_index']} seed={rec['seed']} towns={rec.get('town_a')}-{rec.get('town_b')} "
            f"dist={rec.get('distance')} construction_cost={rec.get('construction_cost')}"
        )
        if "profit_ligne" in rec:
            print(
                f"    n_lead_vehicles={rec['n_lead_vehicles']} sum_profit_this_year={rec['sum_profit_this_year']} "
                f"avg_max_age_years={rec['avg_max_age_years']} amortization_annual={rec['amortization_annual']}"
            )
            print(f"    -> profit_ligne = {rec['sum_profit_this_year']} - {rec['amortization_annual']} = {rec['profit_ligne']}")
        else:
            print("    (donnees incompletes -- pas de profit_ligne calculable)")

    with open("docs/phase2_profit_ligne.json", "w") as f:
        json.dump(records, f, indent=2)
    print("\nEcrit dans docs/phase2_profit_ligne.json")
