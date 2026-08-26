"""Fresh Phase-2 baseline: revised 1970 configuration, slot-0 timing barrier, rank transition."""
import json
import re
import statistics

from openttdlab import bananas_ai_library, local_folder, run_experiments


INFRA_LIFE_YEARS = 30
OPENTTD_CONFIG = """
[difficulty]
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
DAYS = 365 * 10
SEEDS = (42, 1, 7, 100, 2026)
# Five ranks per bucket, repeated on five different maps: 100 isolated lines total. The 50/100
# probe found the constructibility transition here, while ranks >=200 made successful lines O.
RANKS = (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100, 110)
RANK_BUCKETS = (("0-24", 0, 24), ("25-49", 25, 49), ("50-74", 50, 74), ("75-120", 75, 120))
OUTPUT_JSON = "docs/phase2_baseline_v2.json"
STATUS_RE = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL_RE = re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEHICLE_COST_RE = re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")
BARRIER_RE = re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")


def line_profit(chunks):
    total, max_ages = 0, []
    for vehicle in chunks.get("VEHS", {}).values():
        if vehicle.get("type") != 0:
            continue
        common = vehicle["train"][0]["common"][0]
        if common["owner"] != 0 or common["unitnumber"] == 0:
            continue
        total += common["profit_last_year"]
        max_ages.append(common["max_age"])
    if not max_ages:
        return None
    return {"n_lead_vehicles": len(max_ages), "sum_profit_last_year": total,
            "avg_max_age_years": round(sum(max_ages) / len(max_ages) / 365.0, 2)}


def keep_row(row):
    experiment = row["experiment"]
    return ({"seed": experiment["seed"], "date": str(row["date"]),
             "ai_params": dict(experiment["ais"][0][1]),
             "signs": [sign["name"] for sign in row["chunks"].get("SIGN", {}).values()],
             "veh_summary": line_profit(row["chunks"])},)


def parse_record(row):
    status = detail = barrier = None
    vehicle_cost = None
    for sign in row["signs"]:
        if match := STATUS_RE.match(sign):
            status = match.groups()
        elif match := DETAIL_RE.match(sign):
            detail = match.groups()
        elif match := VEHICLE_COST_RE.match(sign):
            vehicle_cost = int(match.group(2))
        elif match := BARRIER_RE.match(sign):
            barrier = match.groups()
    record = {"line_index": row["ai_params"]["line_index"], "seed": row["seed"],
              "pair_rank": row["ai_params"]["pair_rank"], "stagger_slot": row["ai_params"]["stagger_slot"],
              "capture_date": row["date"], "ai_params": row["ai_params"], "raw_signs": row["signs"]}
    if status:
        record.update({"stage": status[1], "reason": status[2], "built": int(status[3]), "requested": int(status[4])})
    if barrier:
        record.update({"first_mutation_tick": int(barrier[1]), "barrier_flag": barrier[2]})
    if detail:
        record.update({"town_a": int(detail[1]), "town_b": int(detail[2]), "distance": int(detail[3]),
                       "cost": int(detail[4]), "vehicle_cost": vehicle_cost})
        veh = row["veh_summary"]
        if veh is not None and vehicle_cost is not None:
            infra = record["cost"] - vehicle_cost
            amortization = vehicle_cost / veh["avg_max_age_years"] + infra / INFRA_LIFE_YEARS
            record.update(veh)
            record.update({"infra_cost": infra, "vehicle_amortization_annual": round(vehicle_cost / veh["avg_max_age_years"]),
                           "infra_amortization_annual": round(infra / INFRA_LIFE_YEARS),
                           "amortization_annual": round(amortization),
                           "profit_ligne": round(veh["sum_profit_last_year"] - amortization)})
    return record


def distribution(records):
    values = [record["profit_ligne"] for record in records if "profit_ligne" in record]
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    return {"count": len(values), "min": min(values), "p25": statistics.quantiles(ordered, n=4, method="inclusive")[0],
            "median": statistics.median(ordered), "mean": round(statistics.mean(ordered), 2),
            "p75": statistics.quantiles(ordered, n=4, method="inclusive")[2], "max": max(values)}


if __name__ == "__main__":
    runs = tuple((seed, rank) for seed in SEEDS for rank in RANKS)
    experiments = tuple(
        {"seed": seed, "days": DAYS, "openttd_config": OPENTTD_CONFIG,
         "ais": (local_folder("ai/TrainLineAI", "TrainLineAI", ai_params=(
             ("num_trains", 2), ("wagons_per_train", 2), ("engine_rank", 1),
             ("pair_rank", rank), ("line_index", index), ("stagger_slot", 0))),)}
        for index, (seed, rank) in enumerate(runs))
    if any(len(experiment["ais"]) != 1 for experiment in experiments):
        raise RuntimeError("Baseline invariant violated: each experiment must contain exactly one AI/company")
    results = run_experiments(
        openttd_version="13.4", opengfx_version="7.1", max_workers=3, result_processor=keep_row,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),), experiments=experiments)
    latest = {}
    for row in results:
        key = row["ai_params"]["line_index"]
        if key not in latest or row["date"] > latest[key]["date"]:
            latest[key] = row
    if len(latest) != len(runs):
        raise RuntimeError(f"Incomplete baseline: got {len(latest)}, expected {len(runs)}")
    records = [parse_record(latest[index]) for index in sorted(latest)]
    reasons, barriers = {}, {"M": 0, "O": 0, "none_before_first_mutation": 0}
    for record in records:
        reason = record.get("reason", "NO_STATUS")
        reasons[reason] = reasons.get(reason, 0) + 1
        flag = record.get("barrier_flag")
        if flag in ("M", "O"):
            barriers[flag] += 1
        else:
            barriers["none_before_first_mutation"] += 1
    by_bucket = {}
    for name, low, high in RANK_BUCKETS:
        rows = [record for record in records if low <= record["pair_rank"] <= high]
        by_bucket[name] = {"attempted": len(rows), "success": sum(row.get("stage") == "success" for row in rows),
                           "success_rate": round(sum(row.get("stage") == "success" for row in rows) / len(rows), 3),
                           "barrier_M": sum(row.get("barrier_flag") == "M" for row in rows),
                           "barrier_O": sum(row.get("barrier_flag") == "O" for row in rows)}
    success = [record for record in records if record.get("stage") == "success"]
    normalized_success = [record for record in success if record.get("barrier_flag") == "M"]
    payload = {"config": {"number_towns": 3, "starting_year": 1970, "town_growth_rate": 2,
                           "industry_density": 4, "inflation": False, "map": "256x256", "barrier_base_tick": 5000},
               "design": {"seeds": list(SEEDS), "ranks_per_seed": list(RANKS), "line_count": len(records),
                          "fixed_train_settings": {"num_trains": 2, "wagons_per_train": 2, "engine_rank": 1},
                          "stagger_slot": 0,
                          "rationale": "The rank probe located failures from rank 50; 0-110 keeps five equal rank buckets around that transition and avoids the predominantly O successful tail at rank 200+."},
               "summary": {"success": len(success), "failure": len(records) - len(success), "failure_reasons": {key: value for key, value in reasons.items() if key != "OK"},
                           "barrier": barriers, "success_by_rank_bucket": by_bucket,
                           "profit_ligne_built_all": distribution(success),
                           "profit_ligne_built_normalized_M_only": distribution(normalized_success)},
               "records": records}
    with open(OUTPUT_JSON, "w") as output:
        json.dump(payload, output, indent=2)
    print(json.dumps(payload["summary"], indent=2))
    print(f"Wrote {OUTPUT_JSON}")
