"""Controle de determinisme intra-batch de TrainLineAI.

Deux parties OpenTTD distinctes mais strictement identiques sont soumises au meme appel
`run_experiments()`. Chaque partie n'a qu'une compagnie et les deux ont exactement les memes
parametres, y compris `line_index=0` : ce banc controle donc le bruit eventuel lie au lancement
concurrent, sans decalage Sleep intentionnel ni compagnie concurrente.
"""
import json
import re

from openttdlab import bananas_ai_library, local_folder, run_experiments


INFRA_LIFE_YEARS = 30  # hypothese documentee dans docs/methode.md

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

DAYS = 365 * 10
SEED = 42
NUM_TRAINS = 2
WAGONS_PER_TRAIN = 2
ENGINE_RANK = 1
PAIR_RANK = 0
LINE_INDEX = 0
N_RUNS = 2
OUTPUT_JSON = "docs/phase2_determinism_control.json"

STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE_COST_RE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")


def line_profit(chunks, owner=0):
    """Somme des profits annuels des motrices et age max moyen du materiel roulant."""
    total_profit = 0
    max_ages_days = []
    for vehicle in chunks.get("VEHS", {}).values():
        if vehicle.get("type") != 0:
            continue
        common = vehicle["train"][0]["common"][0]
        if common["owner"] != owner or common["unitnumber"] == 0:
            continue
        total_profit += common["profit_last_year"]
        max_ages_days.append(common["max_age"])
    if not max_ages_days:
        return None
    return {
        "n_lead_vehicles": len(max_ages_days),
        "sum_profit_last_year": total_profit,
        "avg_max_age_years": round((sum(max_ages_days) / len(max_ages_days)) / 365.0, 2),
    }


def keep_signs_and_params(row):
    """Conserver les chunks necessaires sans tenter d'identifier une partie par ses parametres."""
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "ai_params": dict(row["experiment"]["ais"][0][1]),
        "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()],
        "veh_summary": line_profit(row["chunks"]),
    },)


def parse_record(row, run_index):
    status = detail = None
    vehicle_cost = None
    for sign in row["signs"]:
        match = STATUS_RE.match(sign)
        if match:
            status = match.groups()
            continue
        match = DETAIL_RE.match(sign)
        if match:
            detail = match.groups()
            continue
        match = VEHICLE_COST_RE.match(sign)
        if match:
            vehicle_cost = int(match.group(2))

    record = {
        "run_index": run_index,
        "seed": row["seed"],
        "pair_rank": row["ai_params"]["pair_rank"],
        "ai_params": row["ai_params"],
        "raw_signs": row["signs"],
    }
    if status:
        record.update({
            "stage": status[1],
            "reason": status[2],
            "built": int(status[3]),
            "requested": int(status[4]),
        })
    if detail:
        record.update({
            "town_a": int(detail[1]),
            "town_b": int(detail[2]),
            "distance": int(detail[3]),
            "cost": int(detail[4]),
            "vehicle_cost": vehicle_cost,
        })
        veh = row["veh_summary"]
        if vehicle_cost is not None and veh is not None and veh["avg_max_age_years"] > 0:
            infra_cost = record["cost"] - vehicle_cost
            vehicle_amortization = vehicle_cost / veh["avg_max_age_years"]
            infra_amortization = infra_cost / INFRA_LIFE_YEARS
            amortization = vehicle_amortization + infra_amortization
            record.update(veh)
            record["infra_cost"] = infra_cost
            record["vehicle_amortization_annual"] = round(vehicle_amortization)
            record["infra_amortization_annual"] = round(infra_amortization)
            record["amortization_annual"] = round(amortization)
            record["profit_ligne"] = round(veh["sum_profit_last_year"] - amortization)
    return record


if __name__ == "__main__":
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=3,
        result_processor=keep_signs_and_params,
        ai_libraries=(
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
        # N_RUNS dicts distincts mais de contenu exactement identique : une IA/compagnie par jeu.
        experiments=tuple(
            {
                "seed": SEED,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": (
                    local_folder(
                        "ai/TrainLineAI", "TrainLineAI",
                        ai_params=(
                            ("num_trains", NUM_TRAINS),
                            ("wagons_per_train", WAGONS_PER_TRAIN),
                            ("engine_rank", ENGINE_RANK),
                            ("pair_rank", PAIR_RANK),
                            ("line_index", LINE_INDEX),
                        ),
                    ),
                ),
            }
            for _ in range(N_RUNS)
        ),
    )

    # OpenTTDLab 0.0.75 aplati les AsyncResult dans l'ordre d'entree des experiences, et chaque
    # _run_experiment renvoie ses autosaves tries par nom. Aucun index n'est inclus dans la ligne
    # retournee ; comme les deux experiences sont volontairement indiscernables, verifier la
    # cardinalite puis scinder strictement cette sequence est le seul rattachement non ambigu.
    if len(results) == 0 or len(results) % N_RUNS != 0:
        raise RuntimeError(f"Impossible de repartir sans ambiguite {len(results)} savegames sur {N_RUNS} parties")
    autosaves_per_run = len(results) // N_RUNS
    result_groups = [
        results[run_index * autosaves_per_run:(run_index + 1) * autosaves_per_run]
        for run_index in range(N_RUNS)
    ]
    for run_index, group in enumerate(result_groups):
        dates = [row["date"] for row in group]
        if dates != sorted(dates):
            raise RuntimeError(f"Autosaves non tries pour la partie {run_index}; ne pas deviner son dernier savegame")

    records = [
        parse_record(max(group, key=lambda row: row["date"]), run_index)
        for run_index, group in enumerate(result_groups)
    ]
    for record in records:
        print(
            f"run={record['run_index']} -> {record.get('stage', '?'):8s} "
            f"{record.get('reason', '?'):8s} {record.get('built', '?')}/{record.get('requested', '?')} "
            f"towns={record.get('town_a', '-')}-{record.get('town_b', '-')} "
            f"dist={record.get('distance', '-')} cost={record.get('cost', '-')} "
            f"vehicle_cost={record.get('vehicle_cost', '-')} "
            f"avg_max_age_years={record.get('avg_max_age_years', '-')} "
            f"sum_profit_last_year={record.get('sum_profit_last_year', '-')} "
            f"profit_ligne={record.get('profit_ligne', '-')}"
        )

    construction_fields = ("town_a", "town_b", "distance", "cost", "vehicle_cost", "avg_max_age_years")
    profit_fields = ("sum_profit_last_year", "profit_ligne")
    construction_identical = all(records[0].get(field) == records[1].get(field) for field in construction_fields)
    profits_identical = all(records[0].get(field) == records[1].get(field) for field in profit_fields)
    print(f"\nConstruction identique ({', '.join(construction_fields)}): {construction_identical}")
    print(f"Profits identiques ({', '.join(profit_fields)}): {profits_identical}")
    if all("profit_ligne" in record for record in records):
        print(f"Ecart profit_ligne (run=1 - run=0): {records[1]['profit_ligne'] - records[0]['profit_ligne']}")
    if all("sum_profit_last_year" in record for record in records):
        print("Ecart sum_profit_last_year (run=1 - run=0): "
              f"{records[1]['sum_profit_last_year'] - records[0]['sum_profit_last_year']}")

    with open(OUTPUT_JSON, "w") as output:
        json.dump(records, output, indent=2)
    print(f"\nEcrit dans {OUTPUT_JSON}")
