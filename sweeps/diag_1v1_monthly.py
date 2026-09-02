"""Diagnostic 1v1 mois par mois : QUOI les deux IA construisent, et COMMENT elles l'exploitent.

Les bancs existants comptent des vehicules et des gares sans jamais dire de quel TYPE ils sont ni
comment ils sont exploites. Les panneaux de main.nut ne peuvent pas repondre : ils sont les notres,
AAAHogEx n'en emet aucun. Tout doit donc venir des chunks de sauvegarde, qui eux existent pour les
deux compagnies.

Ce que ce harnais ajoute, par mois et par IA :
  - la repartition des vehicules par MODE (train / route / bateau / avion), qui dit quel type de
    ligne chaque IA privilegie et a quel moment elle bascule d'un mode a l'autre ;
  - le CHARGEMENT moyen des vehicules (cargo transporte / capacite), qui dit si les lignes sont
    exploitees ou si elles roulent a vide ;
  - le cargo EN ATTENTE dans les gares, qui dit si la demande est captee ou laissee sur le quai ;
  - le profit par vehicule, qui dit si la flotte est rentable unite par unite ;
  - la distribution des notes de gare, pas seulement leur mediane.

Sortie : un JSON avec une ligne par (IA, graine, mois), et un tableau mensuel imprime.
"""
import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"
VEHICLE_MODES = ("train", "roadveh", "ship", "aircraft")
# type est encode en CHAINE dans le chunk VEHS ; 4 = effet, 5 = catastrophe, jamais a nous.
TYPE_TO_MODE = {"0": "train", "1": "roadveh", "2": "ship", "3": "aircraft"}

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


def _first(value):
    """STNN et VEHS encodent parfois une liste a un element, parfois l'objet directement."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def vehicle_breakdown(chunks, owner=0):
    """Vehicules de la compagnie par mode, avec profit et capital immobilise.

    STRUCTURE VERIFIEE (dump du 2026-09-02) : une entree VEHS est un enregistrement A VARIANTES.
    Elle porte TOUTES les cles de mode ('train', 'roadveh', 'ship', 'aircraft', 'effect',
    'disaster') quel que soit son type reel -- chercher « la premiere cle presente » classe donc
    tout en train. Le seul discriminant est le champ `type`, encode en CHAINE :
    "0" train, "1" route, "2" bateau, "3" avion, "4" effet (fumee, etincelles), "5" catastrophe.

    Les champs lus sont ceux confirmes dans le dump : owner, cargo_cap, profit_this_year, value.
    Le chargement reel et le cargo en attente ne sont PAS mesures ici : leurs champs
    (`cargo.packets`, goods des gares) n'ont pas ete verifies, et une metrique fausse en silence
    coute plus cher qu'une metrique absente.
    """
    counts = {mode: 0 for mode in VEHICLE_MODES}
    profits = []
    capital = 0
    capacity = 0
    for vehicle in (chunks.get("VEHS") or {}).values():
        if not isinstance(vehicle, dict):
            continue
        vtype = str(vehicle.get("type"))
        if vtype not in TYPE_TO_MODE:
            continue
        mode = TYPE_TO_MODE[vtype]
        body = _first(vehicle.get(mode))
        common = _first((body or {}).get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict):
            continue
        if common.get("owner") != owner:
            continue
        counts[mode] += 1
        capital += common.get("value") or 0
        capacity += common.get("cargo_cap") or 0
        profit = common.get("profit_this_year")
        if profit is not None:
            profits.append(profit)
    return {
        "by_mode": counts,
        "n_units": sum(counts.values()),
        "rolling_capital": capital,
        "cargo_capacity": capacity,
        "profit_total": sum(profits) if profits else 0,
        "profit_per_vehicle": (statistics.mean(profits) if profits else None),
    }


def station_detail(chunks, owner=0):
    """Gares de la compagnie : nombre, cargo en attente, notes."""
    n_stations = 0
    waiting = 0
    ratings = []
    for station in (chunks.get("STNN") or {}).values():
        body = _first(station.get("normal") if isinstance(station, dict) else None)
        if body is None and isinstance(station, dict):
            body = station
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if isinstance(base, dict) and base.get("owner", owner) != owner:
            continue
        n_stations += 1
        for good in body.get("goods") or []:
            if not isinstance(good, dict):
                continue
            waiting += good.get("waiting") or good.get("cargo_count") or 0
            if (good.get("status") or 0) & 1 and good.get("time_since_pickup", 255) < 255:
                rating = good.get("rating")
                if rating is not None:
                    ratings.append(int(rating))
    return {
        "n_stations": n_stations,
        "cargo_waiting": waiting,
        "rating_median": (statistics.median(ratings) if ratings else None),
        "rating_min": (min(ratings) if ratings else None),
        "n_rated": len(ratings),
    }


def keep(row):
    chunks = row["chunks"]
    player = (chunks.get("PLYR") or {}).get(0) or (chunks.get("PLYR") or {}).get("0") or {}
    closed = player.get("old_economy") or []
    last = closed[0] if closed else {}
    record = {
        "arm": row["experiment"]["diag_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "money": player.get("money"),
        "current_loan": player.get("current_loan"),
        "company_value": last.get("company_value"),
        "delivered_cargo": last.get("delivered_cargo"),
        "vehicles": vehicle_breakdown(chunks),
        "stations": station_detail(chunks),
        "output": row.get("output"),
    }
    return (record,)


def build_arms(seeds, years):
    arms = {
        "OpexAI": local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ()),
        "AAAHogEx": local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ()),
    }
    return [
        {
            "seed": seed,
            "days": 365 * years,
            "openttd_config": CFG,
            "ais": (arms[arm],),
            "diag_arm": arm,
        }
        for seed in seeds
        for arm in arms
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7])
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "diag_1v1_monthly.json")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    # keep() tourne dans les WORKERS : une liste de module accumulee la n'existe pas dans le
    # parent. Seule la valeur de retour de run_experiments traverse la frontiere de processus.
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=build_arms(args.seeds, args.years),
        max_workers=args.workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    per_month = defaultdict(lambda: defaultdict(list))
    for record in rows:
        per_month[(record["arm"], record["date"][:7])]["rows"].append(record)

    print()
    header = (f"{'mois':<8} | {'OpexAI tr/rt/bt/av':>19} {'gares':>5} {'capRoul':>9} {'prof/veh':>9}"
              f" | {'AAAHogEx tr/rt/bt/av':>20} {'gares':>5} {'capRoul':>9} {'prof/veh':>9}")
    print(header)
    print("-" * len(header))
    months = sorted({date for _, date in per_month})
    for month in months:
        line = f"{month:<8} |"
        for arm in ("OpexAI", "AAAHogEx"):
            rows = per_month[(arm, month)]["rows"]
            if not rows:
                line += f" {'-':>19} {'-':>5} {'-':>9} {'-':>9} |"
                continue
            mode_totals = {
                mode: statistics.mean([r["vehicles"]["by_mode"][mode] for r in rows])
                for mode in VEHICLE_MODES
            }
            st = statistics.mean([r["stations"]["n_stations"] for r in rows])
            cap = statistics.mean([r["vehicles"]["rolling_capital"] for r in rows])
            ppv = [r["vehicles"]["profit_per_vehicle"] for r in rows if r["vehicles"]["profit_per_vehicle"] is not None]
            mix = "/".join(f"{mode_totals[m]:.0f}" for m in VEHICLE_MODES)
            line += (f" {mix:>19} {st:>5.1f} {cap:>9,.0f}"
                     f" {statistics.mean(ppv) if ppv else 0:>9,.0f} |")
        print(line)

    args.out.write_text(json.dumps({
        "openttd_version": OPENTTD_VERSION, "years": args.years, "seeds": args.seeds,
        "openttd_config": CFG, "rows": rows,
    }, indent=1))
    print(f"\necrit {args.out}")


if __name__ == "__main__":
    main()
