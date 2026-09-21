"""Balayage fin du decalage temporel de TrainLineAI et controle age/date.

Sept parties isolees, meme graine et meme ligne demandee. Le point 0 utilise l'IA de production
sans modification. Les six autres utilisent une copie ephemere dans /tmp, avec un parametre IA
scratch `debug_delay_ticks` qui commande un Sleep inconditionnel avant la selection de paire.
"""
import atexit
from datetime import date, timedelta
import json
import os
import re
import shutil

from openttdlab import bananas_ai_library, local_folder, run_experiments


INFRA_LIFE_YEARS = 30  # hypothese documentee dans docs/methode.md

# Configuration historique volontairement épinglée : results/phase2_tick_shift_sweep.json
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
DELAYS = (0, 25, 50, 75, 100, 150, 200)
SOURCE_AI_DIR = "ai/TrainLineAI"
SCRATCH_AI_DIR = "/tmp/openttd-ml-scratch_tickdelay_sweep"
SCRATCH_AI_NAME = "TrainLineAITickShiftSweep"
OUTPUT_JSON = "results/phase2_tick_shift_sweep.json"

STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE_COST_RE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")


def make_scratch_ai():
    """Copier l'IA, ajouter le reglable scratch et rendre son archive OpenTTDLab distincte."""
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
        output.write(main.replace(old_stagger, "  this.Sleep(AIController.GetSetting(\"debug_delay_ticks\"));"))

    info_path = os.path.join(SCRATCH_AI_DIR, "info.nut")
    with open(info_path) as source:
        info = source.read()
    old_name = 'function GetName()        { return "TrainLineAI"; }'
    if info.count(old_name) != 1:
        raise RuntimeError("Nom d'IA attendu introuvable ou ambigu dans la copie")
    info = info.replace(old_name, f'function GetName()        {{ return "{SCRATCH_AI_NAME}"; }}')
    settings_end = "  }\n}\nRegisterAI(TrainLineAIInfo());"
    debug_setting = """    AddSetting({
      name = "debug_delay_ticks",
      description = "Scratch-only fixed delay before selecting the line",
      min_value = 0, max_value = 500,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });
"""
    if info.count(settings_end) != 1:
        raise RuntimeError("Fin de GetSettings attendue introuvable ou ambigue dans la copie")
    with open(info_path, "w") as output:
        output.write(info.replace(settings_end, debug_setting + settings_end))


def line_profit(chunks, owner=0):
    """Profit des motrices, duree de vie catalogue et age reel de chaque motrice au savegame."""
    total_profit = 0
    max_ages_days = []
    actual_ages_days = []
    age_field_available = True
    for vehicle in chunks.get("VEHS", {}).values():
        if vehicle.get("type") != 0:
            continue
        common = vehicle["train"][0]["common"][0]
        if common["owner"] != owner or common["unitnumber"] == 0:
            continue
        total_profit += common["profit_last_year"]
        max_ages_days.append(common["max_age"])
        if "age" in common:
            actual_ages_days.append(common["age"])
        else:
            age_field_available = False
    if not max_ages_days:
        return None
    summary = {
        "n_lead_vehicles": len(max_ages_days),
        "sum_profit_last_year": total_profit,
        "avg_max_age_years": round((sum(max_ages_days) / len(max_ages_days)) / 365.0, 2),
        "lead_vehicle_age_field_available": age_field_available,
    }
    if age_field_available:
        summary["lead_vehicle_ages_days"] = actual_ages_days
        summary["avg_lead_vehicle_age_days"] = round(sum(actual_ages_days) / len(actual_ages_days), 2)
    else:
        summary["lead_vehicle_ages_days"] = None
        summary["avg_lead_vehicle_age_days"] = None
    return summary


def keep_signs_and_params(row):
    """Conserver date, signes et resume VEHS de chaque autosave pour choisir le dernier par delai."""
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "ai_params": dict(row["experiment"]["ais"][0][1]),
        "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()],
        "veh_summary": line_profit(row["chunks"]),
    },)


def parse_record(row, delay_ticks):
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
        "delay_ticks": delay_ticks,
        "seed": row["seed"],
        "capture_date": row["date"],
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
            if veh["lead_vehicle_age_field_available"]:
                capture_date = date.fromisoformat(record["capture_date"])
                record["lead_vehicle_build_dates"] = [
                    str(capture_date - timedelta(days=age))
                    for age in veh["lead_vehicle_ages_days"]
                ]
    return record


if __name__ == "__main__":
    make_scratch_ai()
    atexit.register(shutil.rmtree, SCRATCH_AI_DIR, ignore_errors=True)

    def ai_params(delay_ticks):
        params = [
            ("num_trains", NUM_TRAINS),
            ("wagons_per_train", WAGONS_PER_TRAIN),
            ("engine_rank", ENGINE_RANK),
            ("pair_rank", PAIR_RANK),
            ("line_index", LINE_INDEX),
        ]
        if delay_ticks > 0:
            params.append(("debug_delay_ticks", delay_ticks))
        return tuple(params)

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
                        SOURCE_AI_DIR if delay_ticks == 0 else SCRATCH_AI_DIR,
                        "TrainLineAI" if delay_ticks == 0 else SCRATCH_AI_NAME,
                        ai_params=ai_params(delay_ticks),
                    ),
                ),
            }
            for delay_ticks in DELAYS
        ),
    )

    # Les delais non nuls sont des parametres uniques du scratch ; le baseline sans ce parametre
    # est sans ambiguite le point 0. Garder le dernier autosave date de chaque partie isolee.
    by_delay = {}
    for result in results:
        delay_ticks = result["ai_params"].get("debug_delay_ticks", 0)
        previous = by_delay.get(delay_ticks)
        if previous is None or result["date"] > previous["date"]:
            by_delay[delay_ticks] = result
    if set(by_delay) != set(DELAYS):
        raise RuntimeError(f"Delais captures incomplets/ambigus : {sorted(by_delay)}, attendu {list(DELAYS)}")

    records = [parse_record(by_delay[delay_ticks], delay_ticks) for delay_ticks in DELAYS]
    print("delay  profit_ligne  sum_profit_last_year  capture_date  lead_vehicle_ages_days")
    for record in records:
        print(
            f"{record['delay_ticks']:5d}  {record.get('profit_ligne', '-'):>13}  "
            f"{record.get('sum_profit_last_year', '-'):>20}  {record['capture_date']}  "
            f"{record.get('lead_vehicle_ages_days', '-') }"
        )

    with open(OUTPUT_JSON, "w") as output:
        json.dump(records, output, indent=2)
    print(f"\nEcrit dans {OUTPUT_JSON}")
