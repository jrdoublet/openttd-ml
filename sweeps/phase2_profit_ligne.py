"""profit_ligne = somme(profit des vehicules de la ligne) - amortissement(cout de construction).

Assemble trois morceaux verifies separement :
- profit d'exploitation par vehicule (VEHS.<id>.train[0].common[0].profit_last_year, vehicule de
  tete du consist seulement -- voir sweeps/phase2_vehs_explore.py et docs/methode.md).
  profit_last_year, pas profit_this_year : ce dernier couvre l'annee EN COURS au moment de la
  sauvegarde (potentiellement partielle si la sauvegarde tombe en milieu d'annee), alors que
  amortization_annual est une figure annuelle complete -- comparer les deux melangerait des
  unites de duree differentes. profit_last_year est toujours une annee complete par construction.
- cout de construction total (panneau de detail TRLN|<idx>|T<a>-<b>|D<dist>|C<cout>, mesure par
  AIAccounting cote AI -- voir ai/TrainLineAI/main.nut),
- part vehicules de ce cout (panneau TRLN|<idx>|V<cout>, mesuree par difference sur le meme
  AIAccounting avant/apres l'achat des vehicules -- PAS par un second AIAccounting imbrique, qui
  ne s'isole pas -- voir docs/methode.md pour le piege trouve et evite).

Deux horizons d'amortissement, separes : le materiel roulant a un max_age connu du jeu (deja
present dans le savegame, pas une duree arbitraire) ; l'infrastructure (voie/gares/depot) n'a pas
d'equivalent -- OpenTTD ne modelise aucune duree de vie pour elle -- d'ou INFRA_LIFE_YEARS,
hypothese explicite documentee dans docs/methode.md plutot que dissimulee dans le calcul.
"""
import json
import re
from openttdlab import run_experiments, bananas_ai_library, local_folder

INFRA_LIFE_YEARS = 30  # hypothese assumee (horizon courant pour de l'infra ferroviaire dans la
                        # vraie vie) -- OpenTTD ne donne aucune duree de vie a amortir pour la
                        # voie/les gares/le depot, contrairement au materiel roulant (max_age).

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

DAYS = 365 * 3  # meme fenetre que phase2_vehs_explore.py : assez pour un profit_last_year lisible

DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE_COST_RE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")

# (seed, town_a_rank, town_b_rank, engine_rank, num_trains, wagons_per_train, line_index)
RUNS = [
    (42, 0, 1, 0, 2, 2, 0),
    (7, 1, 6, 1, 2, 2, 1),
    (100, 3, 9, 1, 2, 2, 2),
]


def line_profit(chunks, owner):
    """Somme profit_last_year (annee complete, voir docstring du module) des vehicules de tete
    (unitnumber != 0) de cette compagnie, et l'age max moyen du materiel (annees) pour
    l'amortissement."""
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
        total_profit += common["profit_last_year"]
        max_ages_days.append(common["max_age"])
        n_lead += 1
    if n_lead == 0:
        return None
    avg_max_age_years = (sum(max_ages_days) / len(max_ages_days)) / 365.0
    return {
        "n_lead_vehicles": n_lead,
        "sum_profit_last_year": total_profit,
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
        construction_cost = vehicle_cost = None
        town_a = town_b = distance = None
        for s in r["signs"]:
            m = DETAIL_RE.match(s)
            if m:
                town_a, town_b, distance, construction_cost = (
                    int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)),
                )
                continue
            m = VEHICLE_COST_RE.match(s)
            if m:
                vehicle_cost = int(m.group(2))

        rec = {
            "line_index": idx,
            "seed": r["seed"],
            "construction_cost": construction_cost,
            "vehicle_cost": vehicle_cost,
            "town_a": town_a, "town_b": town_b, "distance": distance,
        }
        veh = r["veh_summary"]
        if construction_cost is not None and vehicle_cost is not None and veh is not None and veh["avg_max_age_years"] > 0:
            infra_cost = construction_cost - vehicle_cost
            vehicle_amortization = vehicle_cost / veh["avg_max_age_years"]
            infra_amortization = infra_cost / INFRA_LIFE_YEARS
            amortization = vehicle_amortization + infra_amortization
            rec.update(veh)
            rec["infra_cost"] = infra_cost
            rec["vehicle_amortization_annual"] = round(vehicle_amortization)
            rec["infra_amortization_annual"] = round(infra_amortization)
            rec["amortization_annual"] = round(amortization)
            rec["profit_ligne"] = round(veh["sum_profit_last_year"] - amortization)
        records.append(rec)

    print(f"{len(records)} lignes\n")
    for rec in records:
        print(
            f"line={rec['line_index']} seed={rec['seed']} towns={rec.get('town_a')}-{rec.get('town_b')} "
            f"dist={rec.get('distance')} construction_cost={rec.get('construction_cost')} "
            f"vehicle_cost={rec.get('vehicle_cost')} infra_cost={rec.get('infra_cost')}"
        )
        if "profit_ligne" in rec:
            print(
                f"    n_lead_vehicles={rec['n_lead_vehicles']} sum_profit_last_year={rec['sum_profit_last_year']} "
                f"avg_max_age_years={rec['avg_max_age_years']} "
                f"vehicle_amortization_annual={rec['vehicle_amortization_annual']} "
                f"infra_amortization_annual={rec['infra_amortization_annual']} (/{INFRA_LIFE_YEARS}y)"
            )
            print(f"    -> profit_ligne = {rec['sum_profit_last_year']} - {rec['amortization_annual']} = {rec['profit_ligne']}")
        else:
            print("    (donnees incompletes -- pas de profit_ligne calculable)")

    with open("docs/phase2_profit_ligne.json", "w") as f:
        json.dump(records, f, indent=2)
    print("\nEcrit dans docs/phase2_profit_ligne.json")
