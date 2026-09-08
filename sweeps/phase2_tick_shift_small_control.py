"""Controle isole d'un petit decalage de ticks de TrainLineAI.

La premiere partie utilise l'IA commitee sans delai (`line_index=0`). La seconde utilise une
copie temporaire de cette IA dans `/tmp`, dont le seul changement executable est
`this.Sleep(100)` inconditionnel au meme endroit de Start(). (La copie a aussi un nom de
registration temporaire distinct, indispensable pour eviter une collision d'archive OpenTTDLab.)
Les deux jeux ont autrement des
parametres d'IA identiques et une seule compagnie isolee.
"""
import atexit
import json
import os
import re
import shutil

from openttdlab import bananas_ai_library, local_folder, run_experiments


INFRA_LIFE_YEARS = 30  # hypothese documentee dans docs/methode.md

# Configuration historique volontairement épinglée : results/phase2_tick_shift_small_control.json
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
LINE_INDEX = 0
FIXED_DELAY_TICKS = 100
SOURCE_AI_DIR = "ai/TrainLineAI"
SCRATCH_AI_DIR = "/tmp/openttd-ml-scratch_tickdelay"
OUTPUT_JSON = "results/phase2_tick_shift_small_control.json"

VARIANTS = (
    ("baseline", "ai/TrainLineAI", "TrainLineAI", 0),
    ("fixed_sleep_100", SCRATCH_AI_DIR, "TrainLineAISmallDelay", FIXED_DELAY_TICKS),
)

STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE_COST_RE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")


def make_scratch_ai():
    """Creer la copie ephemere et verifier que ses seules differences sont attendues.

    GetName change seulement l'identite de packaging : OpenTTDLab indexe les archives locales par
    nom d'IA et ecraserait sinon le tar de production. Le seul changement de comportement est le
    Sleep fixe de 100 ticks.
    """
    if os.path.exists(SCRATCH_AI_DIR):
        raise RuntimeError(f"Copie IA temporaire deja presente : {SCRATCH_AI_DIR}")
    shutil.copytree(SOURCE_AI_DIR, SCRATCH_AI_DIR)

    main_path = os.path.join(SCRATCH_AI_DIR, "main.nut")
    with open(main_path) as source:
        main = source.read()
    old_stagger = """  local STAGGER_TICKS = 6000;
  local staggerDelay = this.state.line_index * STAGGER_TICKS;
  if (staggerDelay > 0) this.Sleep(staggerDelay);"""
    if main.count(old_stagger) != 1:
        raise RuntimeError("Mecanisme STAGGER_TICKS attendu introuvable ou ambigu dans la copie")
    with open(main_path, "w") as output:
        output.write(main.replace(old_stagger, "  this.Sleep(100);"))

    info_path = os.path.join(SCRATCH_AI_DIR, "info.nut")
    with open(info_path) as source:
        info = source.read()
    old_name = 'function GetName()        { return "TrainLineAI"; }'
    if info.count(old_name) != 1:
        raise RuntimeError("Nom d'IA attendu introuvable ou ambigu dans la copie")
    with open(info_path, "w") as output:
        output.write(info.replace(old_name, 'function GetName()        { return "TrainLineAISmallDelay"; }'))


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
    """Conserver les chunks necessaires sans dedupliquer les deux parametres identiques."""
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "ai_params": dict(row["experiment"]["ais"][0][1]),
        "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()],
        "veh_summary": line_profit(row["chunks"]),
    },)


def parse_record(row, variant, fixed_delay_ticks):
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
        "variant": variant,
        "fixed_delay_ticks": fixed_delay_ticks,
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
    make_scratch_ai()
    atexit.register(shutil.rmtree, SCRATCH_AI_DIR, ignore_errors=True)

    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=3,
        result_processor=keep_signs_and_params,
        ai_libraries=(
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
        # Une compagnie par dico : params strictement identiques, seul le dossier IA differe.
        experiments=tuple(
            {
                "seed": SEED,
                "days": DAYS,
                "openttd_config": OPENTTD_CONFIG,
                "ais": (
                    local_folder(
                        ai_dir, ai_name,
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
            for _, ai_dir, ai_name, _ in VARIANTS
        ),
    )

    # OpenTTDLab 0.0.75 renvoie les AsyncResult dans l'ordre d'entree, chacun contenant les
    # autosaves tries. Les params des deux jeux sont volontairement identiques et aucun index
    # d'experience n'est expose dans une ligne : scinder cette sequence apres ces verifications
    # est necessaire pour ne pas ecraser l'un des deux derniers savegames.
    if len(results) == 0 or len(results) % len(VARIANTS) != 0:
        raise RuntimeError(f"Impossible de repartir sans ambiguite {len(results)} savegames sur {len(VARIANTS)} parties")
    autosaves_per_variant = len(results) // len(VARIANTS)
    result_groups = [
        results[index * autosaves_per_variant:(index + 1) * autosaves_per_variant]
        for index in range(len(VARIANTS))
    ]
    for index, group in enumerate(result_groups):
        dates = [row["date"] for row in group]
        if dates != sorted(dates):
            raise RuntimeError(f"Autosaves non tries pour {VARIANTS[index][0]}; ne pas deviner le dernier")

    records = [
        parse_record(max(group, key=lambda row: row["date"]), variant, fixed_delay_ticks)
        for group, (variant, _, _, fixed_delay_ticks) in zip(result_groups, VARIANTS)
    ]
    for record in records:
        print(
            f"{record['variant']} (Sleep={record['fixed_delay_ticks']}) -> "
            f"{record.get('stage', '?'):8s} {record.get('reason', '?'):8s} "
            f"{record.get('built', '?')}/{record.get('requested', '?')} "
            f"towns={record.get('town_a', '-')}-{record.get('town_b', '-')} "
            f"dist={record.get('distance', '-')} cost={record.get('cost', '-')} "
            f"vehicle_cost={record.get('vehicle_cost', '-')} "
            f"avg_max_age_years={record.get('avg_max_age_years', '-')} "
            f"sum_profit_last_year={record.get('sum_profit_last_year', '-')} "
            f"profit_ligne={record.get('profit_ligne', '-')}"
        )

    construction_fields = ("town_a", "town_b", "distance", "cost", "vehicle_cost", "avg_max_age_years")
    construction_identical = all(records[0].get(field) == records[1].get(field) for field in construction_fields)
    print(f"\nConstruction identique ({', '.join(construction_fields)}): {construction_identical}")
    if all("profit_ligne" in record for record in records):
        print(f"Ecart profit_ligne (Sleep=100 - baseline): {records[1]['profit_ligne'] - records[0]['profit_ligne']}")
    if all("sum_profit_last_year" in record for record in records):
        print("Ecart sum_profit_last_year (Sleep=100 - baseline): "
              f"{records[1]['sum_profit_last_year'] - records[0]['sum_profit_last_year']}")

    with open(OUTPUT_JSON, "w") as output:
        json.dump(records, output, indent=2)
    print(f"\nEcrit dans {OUTPUT_JSON}")
