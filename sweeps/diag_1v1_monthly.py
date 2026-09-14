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
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from physical_counters import decode_vehicles, decode_stations, VEHICLE_MODES

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"

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

    Utilise decode_vehicles de physical_counters pour distinguer les têtes de véhicules
    de leurs composants internes (wagons, ombres) et éviter les surcomptages.
    """
    dec = decode_vehicles((chunks or {}).get("VEHS"), target_owner=owner)
    if not dec["chunk_valid"]:
        return {
            "schema_version": dec["schema_version"],
            "qualified_modes": dec["qualified_modes"],
            "chunk_valid": False,
            "chunk_error": dec["chunk_error"],
            "by_mode": None,
            "n_units": None,
            "vehicle_pool_entries": None,
            "components_breakdown": None,
            "rolling_capital": None,
            "capital_by_mode": None,
            "capacities_by_cargo": None,
            "profit_total": None,
            "profit_by_mode": None,
            "profit_per_vehicle": None,
            "fleet_status": None,
        }

    capital_by_mode = {mode: 0 for mode in VEHICLE_MODES}
    profit_by_mode = {mode: 0 for mode in VEHICLE_MODES}
    profits = []
    capital = 0

    for v in dec["primary_vehicles_detail"]:
        m = v["mode"]
        c_val = v["consist_value"]
        p_yr = v["profit_this_year"]
        capital += c_val
        capital_by_mode[m] += c_val
        profit_by_mode[m] += p_yr
        profits.append(p_yr)

    return {
        "schema_version": dec["schema_version"],
        "qualified_modes": dec["qualified_modes"],
        "chunk_valid": True,
        "by_mode": dec["primary_vehicles_by_mode"],
        "n_units": dec["primary_vehicles_count"],
        "vehicle_pool_entries": dec["vehicle_pool_entries"],
        "components_breakdown": dec["components_breakdown"],
        "rolling_capital": capital,
        "capital_by_mode": capital_by_mode,
        "capacities_by_cargo": dec["capacities_by_cargo"],
        "profit_total": sum(profits) if profits else 0,
        "profit_by_mode": profit_by_mode,
        "profit_per_vehicle": (statistics.mean(profits) if profits else None),
        "fleet_status": dec["fleet_status"],
    }


def station_detail(chunks, owner=0):
    """Gares de la compagnie : nombre physique, cargo en attente, notes.

    Utilise decode_stations pour valider strictement le propriétaire (pas de repli
    silencieux) et compter une gare multimodale comme une seule gare physique.
    """
    stnn = (chunks or {}).get("STNN")
    dec = decode_stations(stnn, target_owner=owner)
    if not dec["chunk_valid"]:
        return {
            "schema_version": dec["schema_version"],
            "chunk_valid": False,
            "chunk_error": dec["chunk_error"],
            "n_stations": None,
            "n_multimodal_stations": None,
            "stations_by_facility": None,
            "cargo_waiting": None,
            "rating_median": None,
            "rating_min": None,
            "n_rated": 0,
            "unresolved_stations": len(dec["unresolved_stations"]),
        }

    waiting = 0
    all_ratings = []
    for sid, ratings in dec["ratings_by_station"].items():
        all_ratings.extend(ratings)

    stnn_list = stnn.values() if isinstance(stnn, dict) else (stnn or [])
    for station in stnn_list:
        if not isinstance(station, dict):
            continue
        body = _first(station.get("normal"))
        if body is None:
            body = station
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if not isinstance(base, dict) or base.get("owner") != owner:
            continue
        for good in body.get("goods") or []:
            if isinstance(good, dict):
                waiting += good.get("waiting") or good.get("cargo_count") or 0

    return {
        "schema_version": dec["schema_version"],
        "chunk_valid": True,
        "n_stations": dec["total_stations"],
        "n_multimodal_stations": dec["n_multimodal_stations"],
        "stations_by_facility": dec["stations_by_facility"],
        "cargo_waiting": waiting,
        "rating_median": (statistics.median(all_ratings) if all_ratings else None),
        "rating_min": (min(all_ratings) if all_ratings else None),
        "n_rated": len(all_ratings),
        "unresolved_stations": len(dec["unresolved_stations"]),
    }


def keep(row):
    chunks = row["chunks"]
    player = (chunks.get("PLYR") or {}).get(0) or (chunks.get("PLYR") or {}).get("0") or {}
    closed = player.get("old_economy") or []
    last = closed[0] if closed else {}
    signs = [s["name"] for s in chunks.get("SIGN", {}).values()]
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
        "signs": signs,
        "output": row.get("output"),
    }
    return (record,)


def build_arms(seeds, years):
    arms = {
        "OpexAI": local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("air_fleet_probe", 1),)),
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
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_1v1_monthly.json")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--selftest", action="store_true", help="Vérifie le décodage physique et le rendu face aux chunks invalides")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

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

    monthly = render_monthly_report(rows)

    args.out.write_text(json.dumps({
        "openttd_version": OPENTTD_VERSION, "years": args.years, "seeds": args.seeds,
        "openttd_config": CFG, "rows": rows, "monthly": monthly,
    }, indent=1))
    print(f"\necrit {args.out}")


def physical_row_ok(record):
    """Une ligne n'est exploitable que si VEHS et STNN sont tous deux valides."""
    vehs = record.get("vehicles") or {}
    stns = record.get("stations") or {}
    return vehs.get("chunk_valid") is True and stns.get("chunk_valid") is True


def monthly_aggregates(rows):
    """Agrège un mois seulement si toutes les lignes attendues sont valides.

    Fail-closed : dès qu'une graine attendue manque ou qu'un chunk est invalide,
    le mois est incomplet. On ne recalcule pas la moyenne sur les survivantes.
    """
    seeds_by_arm = defaultdict(set)
    for record in rows:
        if "seed" in record:
            seeds_by_arm[record["arm"]].add(record["seed"])
    use_seeds = bool(rows) and all("seed" in record for record in rows)

    per_month = defaultdict(list)
    for record in rows:
        per_month[(record["arm"], record["date"][:7])].append(record)

    months = sorted({date for _, date in per_month})
    cells = []
    for month in months:
        for arm in ("OpexAI", "AAAHogEx"):
            month_rows = per_month.get((arm, month), [])
            expected_n = len(seeds_by_arm[arm]) if use_seeds else len(month_rows)
            valid_n = sum(1 for record in month_rows if physical_row_ok(record))
            present = {record["seed"] for record in month_rows} if use_seeds else set()
            complete = (
                expected_n > 0
                and valid_n == expected_n
                and valid_n == len(month_rows)
                and (not use_seeds or present == seeds_by_arm[arm])
            )
            cell = {
                "month": month,
                "arm": arm,
                "ok": complete,
                "n_valid": valid_n,
                "n_expected": expected_n,
                "by_mode": None,
                "n_stations": None,
                "rolling_capital": None,
                "profit_per_vehicle": None,
            }
            if not month_rows:
                cell["n_valid"] = 0
                if not use_seeds:
                    cell["n_expected"] = 0
                cells.append(cell)
                continue
            if complete:
                mode_totals = {
                    mode: statistics.mean([record["vehicles"]["by_mode"][mode] for record in month_rows])
                    for mode in VEHICLE_MODES
                }
                caps = [
                    record["vehicles"]["rolling_capital"]
                    for record in month_rows
                    if record["vehicles"].get("rolling_capital") is not None
                ]
                ppv = [
                    record["vehicles"]["profit_per_vehicle"]
                    for record in month_rows
                    if record["vehicles"].get("profit_per_vehicle") is not None
                ]
                stations = [
                    record["stations"]["n_stations"]
                    for record in month_rows
                    if record["stations"].get("n_stations") is not None
                ]
                cell["by_mode"] = mode_totals
                cell["n_stations"] = statistics.mean(stations) if stations else None
                cell["rolling_capital"] = statistics.mean(caps) if caps else None
                cell["profit_per_vehicle"] = statistics.mean(ppv) if ppv else None
            cells.append(cell)
    return cells


def render_monthly_report(rows):
    """Affiche le rapport mensuel consolidé. Un mois incomplet s'affiche FAIL v/e."""
    monthly = monthly_aggregates(rows)
    by_key = {(cell["arm"], cell["month"]): cell for cell in monthly}
    months = sorted({cell["month"] for cell in monthly})

    print()
    header = (f"{'mois':<8} | {'OpexAI tr/rt/bt/av':>19} {'gares':>5} {'capRoul':>9} {'prof/veh':>9}"
              f" | {'AAAHogEx tr/rt/bt/av':>20} {'gares':>5} {'capRoul':>9} {'prof/veh':>9}")
    print(header)
    print("-" * len(header))
    for month in months:
        line = f"{month:<8} |"
        for arm in ("OpexAI", "AAAHogEx"):
            cell = by_key.get((arm, month))
            if cell is None or (cell["n_expected"] == 0 and cell["n_valid"] == 0):
                line += f" {'-':>19} {'-':>5} {'-':>9} {'-':>9} |"
                continue
            if not cell["ok"]:
                fail = f"FAIL {cell['n_valid']}/{cell['n_expected']}"
                line += f" {fail:>19} {'FAIL':>5} {'FAIL':>9} {'FAIL':>9} |"
                continue
            mix = "/".join(f"{cell['by_mode'][mode]:.0f}" for mode in VEHICLE_MODES)
            st_str = f"{cell['n_stations']:>5.1f}" if cell["n_stations"] is not None else "FAIL"
            cap_str = f"{cell['rolling_capital']:>9,.0f}" if cell["rolling_capital"] is not None else "FAIL"
            ppv_str = f"{cell['profit_per_vehicle']:>9,.0f}" if cell["profit_per_vehicle"] is not None else "FAIL"
            line += f" {mix:>19} {st_str:>5} {cap_str:>9} {ppv_str:>9} |"
        print(line)
    return monthly


def selftest():
    """Vérifie le décodage et la résilience du rendu mensuel face aux erreurs de chunk."""
    fixture_path = ROOT / "sweeps" / "fixtures" / "c66_control_fixture_15_3.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            c66 = json.load(f)
        vb = vehicle_breakdown(c66["chunks"], owner=0)
        assert vb["chunk_valid"] is True
        assert vb["by_mode"]["rail"] == 1
        assert vb["by_mode"]["road"] == 17
        assert vb["by_mode"]["air"] == 3
        sd = station_detail(c66["chunks"], owner=0)
        assert sd["chunk_valid"] is True
        assert sd["n_stations"] == 24

    # Test chunk invalide
    vb_bad = vehicle_breakdown({"VEHS": None}, owner=0)
    assert vb_bad["chunk_valid"] is False
    assert vb_bad["by_mode"] is None
    assert vb_bad["n_units"] is None
    sd_bad = station_detail({"STNN": None}, owner=0)
    assert sd_bad["chunk_valid"] is False
    assert sd_bad["n_stations"] is None

    # Mixte : une graine valide ne doit pas faire moyenne sur les survivantes.
    mock_rows = [
        {
            "arm": "OpexAI", "seed": 42, "date": "1970-02-01",
            "vehicles": {"chunk_valid": True, "by_mode": {"rail": 1, "road": 2, "air": 1, "water": 0}, "rolling_capital": 50000, "profit_per_vehicle": 1200},
            "stations": {"chunk_valid": True, "n_stations": 4},
        },
        {
            "arm": "OpexAI", "seed": 100, "date": "1970-02-01",
            "vehicles": {"chunk_valid": False, "chunk_error": "chunk_missing", "by_mode": None, "rolling_capital": None, "profit_per_vehicle": None},
            "stations": {"chunk_valid": False, "chunk_error": "chunk_missing", "n_stations": None},
        },
        {
            "arm": "AAAHogEx", "seed": 42, "date": "1970-02-01",
            "vehicles": {"chunk_valid": False, "chunk_error": "corrupt", "by_mode": None, "rolling_capital": None, "profit_per_vehicle": None},
            "stations": {"chunk_valid": False, "chunk_error": "corrupt", "n_stations": None},
        },
        {
            "arm": "OpexAI", "seed": 42, "date": "1970-03-01",
            "vehicles": {"chunk_valid": True, "by_mode": {"rail": 2, "road": 4, "air": 2, "water": 0}, "rolling_capital": 80000, "profit_per_vehicle": 1500},
            "stations": {"chunk_valid": True, "n_stations": 6},
        },
        {
            "arm": "OpexAI", "seed": 100, "date": "1970-03-01",
            "vehicles": {"chunk_valid": True, "by_mode": {"rail": 4, "road": 6, "air": 2, "water": 0}, "rolling_capital": 120000, "profit_per_vehicle": 2500},
            "stations": {"chunk_valid": True, "n_stations": 8},
        },
    ]
    mixed = monthly_aggregates(mock_rows)
    feb_opex = next(cell for cell in mixed if cell["month"] == "1970-02" and cell["arm"] == "OpexAI")
    feb_aaa = next(cell for cell in mixed if cell["month"] == "1970-02" and cell["arm"] == "AAAHogEx")
    mar_opex = next(cell for cell in mixed if cell["month"] == "1970-03" and cell["arm"] == "OpexAI")
    assert feb_opex["ok"] is False
    assert feb_opex["n_valid"] == 1 and feb_opex["n_expected"] == 2
    assert feb_opex["by_mode"] is None
    assert feb_aaa["ok"] is False
    assert feb_aaa["n_valid"] == 0 and feb_aaa["n_expected"] == 1
    assert mar_opex["ok"] is True
    assert mar_opex["by_mode"]["rail"] == 3
    assert mar_opex["n_stations"] == 7
    print("Test d'affichage du rapport mensuel avec lignes corrompues :")
    render_monthly_report(mock_rows)
    print("Selftest diag_1v1_monthly.py réussi avec succès !")


if __name__ == "__main__":
    main()
