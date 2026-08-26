"""Controle isole du decalage de ticks de TrainLineAI.

Deux parties strictement isolees (une seule compagnie chacune), meme graine et meme
construction demandee. Seul `line_index` varie : 0 demarre immediatement, 1 execute le
Sleep(6000) de Start() avant la selection/construction de la ligne. Cela teste directement si
ce decalage temporel suffit a faire diverger le profit, sans introduire de compagnie concurrente.
"""
import json
import re

from openttdlab import bananas_ai_library, local_folder, run_experiments


INFRA_LIFE_YEARS = 30  # hypothese documentee dans docs/methode.md

# Configuration historique volontairement épinglée : docs/phase2_tick_shift_control.json
# a été produit en 1950/densité 2. La config révisée pour les nouveaux travaux est documentée
# dans la table des décisions figées du README.md et la note de révision de docs/methode.md.
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
LINE_INDICES = (0, 1)
OUTPUT_JSON = "docs/phase2_tick_shift_control.json"

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
    """Conserver les seuls chunks necessaires au diagnostic final de chaque partie."""
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "ai_params": dict(row["experiment"]["ais"][0][1]),
        "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()],
        "veh_summary": line_profit(row["chunks"]),
    },)


def parse_record(row):
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
        "line_index": row["ai_params"]["line_index"],
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
                            ("line_index", line_index),
                        ),
                    ),
                ),
            }
            for line_index in LINE_INDICES
        ),
    )

    # Plusieurs savegames sont captures par partie : garder le dernier par decalage de ticks.
    by_line_index = {}
    for result in results:
        line_index = result["ai_params"]["line_index"]
        previous = by_line_index.get(line_index)
        if previous is None or result["date"] > previous["date"]:
            by_line_index[line_index] = result

    records = [parse_record(by_line_index[index]) for index in LINE_INDICES]
    for record in records:
        print(
            f"line_index={record['line_index']} -> {record.get('stage', '?'):8s} "
            f"{record.get('reason', '?'):8s} {record.get('built', '?')}/{record.get('requested', '?')} "
            f"towns={record.get('town_a', '-')}-{record.get('town_b', '-')} "
            f"dist={record.get('distance', '-')} cost={record.get('cost', '-')} "
            f"vehicle_cost={record.get('vehicle_cost', '-')} "
            f"avg_max_age_years={record.get('avg_max_age_years', '-')} "
            f"sum_profit_last_year={record.get('sum_profit_last_year', '-')} "
            f"profit_ligne={record.get('profit_ligne', '-')}"
        )

    construction_fields = ("town_a", "town_b", "distance", "cost", "vehicle_cost", "avg_max_age_years")
    identical = all(records[0].get(field) == records[1].get(field) for field in construction_fields)
    print(f"\nConstruction identique ({', '.join(construction_fields)}): {identical}")
    if all("profit_ligne" in record for record in records):
        print(f"Ecart profit_ligne (line_index=1 - line_index=0): "
              f"{records[1]['profit_ligne'] - records[0]['profit_ligne']}")

    with open(OUTPUT_JSON, "w") as output:
        json.dump(records, output, indent=2)
    print(f"\nEcrit dans {OUTPUT_JSON}")
