"""Diagnostic 1v1 partage mensuel : OpexAI vs AAAHogEx sur carte unique.

En --shared (carte unique OpexAI joueur 0 vs AAAHogEx joueur 1), chaque sauvegarde mensuelle
extrait les deux compagnies separement depuis PLYR/VEHS/STNN. Les chunks existent pour les deux ;
les panneaux OpexAI n'existent que pour nous.

Par mois et par IA :
  - valeur, revenu, depenses, benefice et cargo livre du dernier trimestre clos ;
  - vehicules physiques par mode, capital roulant et profit par vehicule ;
  - gares possedees, cargo en attente et notes.

Pour OpexAI seulement, `monthly_funnel=1` journalise le tunnel
candidats → acceptes → finances → tentes → construits, avec le motif de rejet.
AAAHogEx n'a pas ce tunnel : on lit ses evenements de construction deja emis.

Instrumentation OpexAI (derrière monthly_funnel=0 par défaut) :
  - candidats considérés → projets sélectionnés/financés → projets tentés → constructions réussies → échecs
  - Avec mode et année pour tous ces compteurs

Sortie : un JSON avec une ligne par (IA, graine, mois), et des tableaux mensuels.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from physical_counters import decode_vehicles, decode_stations, VEHICLE_MODES, FACILITY_BITS
from harness import parse_fields

try:
    from bench_v2 import (
        make_cfg,
        observed_opcode_stats,
        portfolio_selection_opcode_stats,
        quarter_profit,
        year_profit,
    )
except ImportError:
    def make_cfg(starting_year=1970, map_size=8):
        return (
            "[difficulty]\nnumber_towns = 3\nindustry_density = 4\n[economy]\n"
            "inflation = false\ntown_growth_rate = 2\n[game_creation]\n"
            f"starting_year = {starting_year}\nmap_x = {map_size}\nmap_y = {map_size}\n"
        )

    def quarter_profit(entry):
        if not isinstance(entry, dict):
            return None
        income = entry.get("income")
        expenses = entry.get("expenses")
        if income is None or expenses is None:
            return None
        return income + expenses

    def year_profit(closed):
        profits = [quarter_profit(entry) for entry in (closed or [])[:4]]
        profits = [value for value in profits if value is not None]
        if not profits:
            return None
        return sum(profits)

    def portfolio_selection_opcode_stats(chunks):
        return {
            "selection_kopcodes_samples": 0,
            "selection_kopcodes_total": None,
            "selection_kopcodes_mean": None,
            "selection_kopcodes_max": None,
        }

    def observed_opcode_stats(chunks):
        return {
            "observed_opcode_schema": "h5.observed-v1",
            "observed_opcodes_total": 0,
            "observed_opcode_samples": 0,
            "observed_opcode_components": {},
            "observed_opcode_complete_cpu": False,
        }

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"
STARTING_YEAR = 1970
ARMS = ("OpexAI", "AAAHogEx")

# Configuration pour les jeux partagés (comme dans diag_c63_c58.py)
CFG_SHARED = """[difficulty]
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

DIAG_SEEDS = (42, 100, 999, 1234, 5678)

SCRIPT_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[\w\] (.*)")
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
HOG_DATE_RE = re.compile(r"^(\d+)-(\d+)-(\d+) (.*)$")
HOG_SUCCESS = ("# RouteBuilder Succeeded", "HgStation.BuildExec succeeded", "Build succeeded")
HOG_FAIL = ("# RouteBuilder Failed", "HgStation.BuildExec failed")
CASH_REASONS = frozenset(("insufficient_cash", "cash_at_build"))
CONSTRUCTION_FAIL = frozenset((
    "build_failed", "plan_failed", "fleet_grow_failed", "unprofitable_after_siting",
))


def _first(value):
    """STNN et VEHS encodent parfois une liste a un element, parfois l'objet directement."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def vehicle_breakdown(chunks, owner=0):
    """Vehicules physiques de la compagnie ; les totaux publies excluent les modes non qualifies."""
    dec = decode_vehicles((chunks or {}).get("VEHS"), target_owner=owner)
    if not dec["chunk_valid"]:
        return {
            "schema_version": dec["schema_version"],
            "qualified_modes": dec["qualified_modes"],
            "chunk_valid": False,
            "chunk_error": dec["chunk_error"],
            "by_mode": None,
            "by_mode_all_primary": None,
            "n_units": None,
            "n_units_all_primary": None,
            "unqualified_primary_vehicles": None,
            "vehicle_pool_entries": None,
            "components_breakdown": None,
            "rolling_capital": None,
            "rolling_capital_all_primary": None,
            "capital_by_mode": None,
            "capital_by_mode_all_primary": None,
            "capacities_by_cargo": None,
            "profit_total": None,
            "profit_total_all_primary": None,
            "profit_by_mode": None,
            "profit_by_mode_all_primary": None,
            "profit_per_vehicle": None,
            "profit_per_vehicle_all_primary": None,
            "fleet_status": None,
        }

    qualified = dec["qualified_modes"]
    by_mode_all = dict(dec["primary_vehicles_by_mode"])
    by_mode = {
        mode: (count if qualified.get(mode) else None)
        for mode, count in by_mode_all.items()
    }
    capital_all = {mode: 0 for mode in VEHICLE_MODES}
    profit_all = {mode: 0 for mode in VEHICLE_MODES}
    capital_qualified = {mode: (0 if qualified.get(mode) else None) for mode in VEHICLE_MODES}
    profit_qualified = {mode: (0 if qualified.get(mode) else None) for mode in VEHICLE_MODES}
    all_profits = []
    qualified_profits = []
    rolling_all = 0
    rolling_qualified = 0

    for vehicle in dec["primary_vehicles_detail"]:
        mode = vehicle["mode"]
        value = vehicle["consist_value"]
        profit = vehicle["profit_this_year"]
        rolling_all += value
        capital_all[mode] += value
        profit_all[mode] += profit
        all_profits.append(profit)
        if qualified.get(mode):
            rolling_qualified += value
            capital_qualified[mode] += value
            profit_qualified[mode] += profit
            qualified_profits.append(profit)

    n_qualified = sum(
        count for mode, count in by_mode_all.items() if qualified.get(mode)
    )
    n_all = dec["primary_vehicles_count"]
    return {
        "schema_version": dec["schema_version"],
        "qualified_modes": qualified,
        "chunk_valid": True,
        "chunk_error": None,
        "by_mode": by_mode,
        "by_mode_all_primary": by_mode_all,
        "n_units": n_qualified,
        "n_units_all_primary": n_all,
        "unqualified_primary_vehicles": n_all - n_qualified,
        "vehicle_pool_entries": dec["vehicle_pool_entries"],
        "components_breakdown": dec["components_breakdown"],
        "rolling_capital": rolling_qualified,
        "rolling_capital_all_primary": rolling_all,
        "capital_by_mode": capital_qualified,
        "capital_by_mode_all_primary": capital_all,
        "capacities_by_cargo": dec["capacities_by_cargo"],
        "profit_total": sum(qualified_profits) if qualified_profits else 0,
        "profit_total_all_primary": sum(all_profits) if all_profits else 0,
        "profit_by_mode": profit_qualified,
        "profit_by_mode_all_primary": profit_all,
        "profit_per_vehicle": (
            statistics.mean(qualified_profits) if qualified_profits else None
        ),
        "profit_per_vehicle_all_primary": (
            statistics.mean(all_profits) if all_profits else None
        ),
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
            "n_rated": None,
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
            continue
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if not isinstance(base, dict) or base.get("owner") != owner:
            continue
        for good in body.get("goods") or []:
            if not isinstance(good, dict):
                continue
            for packet in good.get("cargo") or []:
                if not isinstance(packet, dict):
                    continue
                second = packet.get("second")
                if isinstance(second, list) and second:
                    waiting += int(second[0] or 0)
                elif isinstance(second, (int, float)):
                    waiting += int(second)

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


def station_town_inventory(chunks, owner=0):
    """Inventaire compact des gares d'une compagnie, groupees par TownID."""
    stnn = (chunks or {}).get("STNN")
    if not isinstance(stnn, (dict, list)):
        return None
    records = stnn.items() if isinstance(stnn, dict) else enumerate(stnn)
    towns = defaultdict(lambda: {"count": 0, "stations": []})
    for sid_raw, station in records:
        if not isinstance(station, dict):
            continue
        body = _first(station.get("normal"))
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if not isinstance(base, dict) or base.get("owner") != owner:
            continue
        town = base.get("town")
        if town is None:
            continue
        try:
            sid = int(sid_raw)
            town_id = int(town)
        except (TypeError, ValueError):
            continue
        facilities = int(base.get("facilities") or 0)
        names = [name for bit, name in FACILITY_BITS if facilities & bit]
        item = {"id": sid, "xy": base.get("xy"), "build_date": base.get("build_date"),
                "facilities": names, "airport_tile": body.get("airport.tile")}
        slot = towns[town_id]
        slot["count"] += 1
        slot["stations"].append(item)
    return {str(town_id): value for town_id, value in sorted(towns.items())}


def cargo_delivered(value):
    """Somme le vecteur cargo OpenTTD 15.3 ; un entier legacy est conserve tel quel."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, list):
        total = 0
        for item in value:
            total += int(item or 0)
        return total
    return None


def player_of(chunks, owner):
    players = (chunks or {}).get("PLYR") or {}
    player = players.get(owner)
    if player is None:
        player = players.get(str(owner))
    return player if isinstance(player, dict) and player else None


def extract_company(chunks, owner, arm, seed, date):
    """Une compagnie, un mois : economie PLYR + compteurs physiques qualifies."""
    player = player_of(chunks, owner)
    closed = (player or {}).get("old_economy") or []
    last = closed[0] if closed else None
    income = last.get("income") if isinstance(last, dict) else None
    expenses = last.get("expenses") if isinstance(last, dict) else None
    selection_ops = (
        portfolio_selection_opcode_stats(chunks)
        if arm == "OpexAI"
        else {
            "selection_kopcodes_samples": None,
            "selection_kopcodes_total": None,
            "selection_kopcodes_mean": None,
            "selection_kopcodes_max": None,
        }
    )
    observed_ops = (
        observed_opcode_stats(chunks)
        if arm == "OpexAI"
        else {
            "observed_opcode_schema": None,
            "observed_opcodes_total": None,
            "observed_opcode_samples": None,
            "observed_opcode_components": None,
            "observed_opcode_complete_cpu": None,
        }
    )
    return {
        "arm": arm,
        "owner": owner,
        "seed": seed,
        "date": str(date),
        "economy_ok": player is not None,
        "money": (player or {}).get("money"),
        "current_loan": (player or {}).get("current_loan"),
        "company_value": last.get("company_value") if isinstance(last, dict) else None,
        "performance_history": last.get("performance_history") if isinstance(last, dict) else None,
        "income": income,
        "expenses": expenses,
        "profit": quarter_profit(last) if isinstance(last, dict) else None,
        "profit_year": year_profit(closed) if closed else None,
        "delivered_cargo": cargo_delivered(last.get("delivered_cargo") if isinstance(last, dict) else None),
        "vehicles": vehicle_breakdown(chunks, owner),
        "stations": station_detail(chunks, owner),
        "funnel": None,
        "hogex_builds": None,
        # Nouveaux champs pour l'instrumentation OpexAI
        "funnel_detailed": None,  # Pour le suivi détaillé par mode/année
        "hogex_builds_detailed": None,  # Pour le suivi détaillé si nécessaire
        **selection_ops,
        **observed_ops,
        "selection_kopcodes_month": None,
        "selection_kopcodes_samples_month": None,
        "selection_opcode_state": "pending" if arm == "OpexAI" else "not_applicable",
        "observed_opcodes_month": None,
        "observed_mopcodes_month": None,
        "observed_opcode_components_month": None,
        "observed_opcode_state": "pending" if arm == "OpexAI" else "not_applicable",
    }


def keep(row):
    """Traite une ligne d'expérience pour produire les enregistrements de compagnie.
    Pour les jeux partagés, produit deux enregistrements (un pour chaque IA).
    """
    chunks = row.get("chunks", {})
    date = row.get("date", "")
    seed = row["experiment"]["seed"]
    output = row.get("output", "")
    if row["experiment"].get("shared"):
        rec0 = extract_company(chunks, 0, "OpexAI", seed, date)
        rec1 = extract_company(chunks, 1, "AAAHogEx", seed, date)
        if row["experiment"].get("town_station_detail"):
            rec0["stations_by_town"] = station_town_inventory(chunks, 0)
            rec1["stations_by_town"] = station_town_inventory(chunks, 1)
        rec0["output"] = output
        rec1["output"] = output
        return (rec0, rec1)
    # Cas non-partagé (pour rétrocompatibilité, bien que non utilisé ici)
    arm = row["experiment"]["diag_arm"]
    rec = extract_company(chunks, 0, arm, seed, date)
    rec["output"] = output
    rec["signs"] = [s.get("name", "") for s in (chunks.get("SIGN") or {}).values()]
    return (rec,)


def parse_opex_funnel(output):
    """Agrege MONTHLY_FUNNEL : stocks moyens par passe, flux sommes sur le mois."""
    by_month = defaultdict(lambda: {
        "considered_sum": 0,
        "considered_samples": 0,
        "accepted_sum": 0,
        "accepted_samples": 0,
        "funded": 0,
        "attempted": 0,
        "built": 0,
        "passes": 0,
        "rejects": Counter(),
    })
    for line in (output or "").splitlines():
        sm = SCRIPT_RE.search(line)
        if not sm or int(sm.group(1)) != 0:
            continue
        om = OPEX_RE.match(sm.group(2).strip())
        if not om or om.group(4) != "MONTHLY_FUNNEL":
            continue
        year, month = int(om.group(1)), int(om.group(2))
        fields = parse_fields(om.group(5))
        slot = by_month[f"{year:04d}-{month:02d}"]
        slot["passes"] += 1
        for name in ("considered", "accepted"):
            if name not in fields:
                continue
            value = int(fields.get(name, -1) or 0)
            if value >= 0:
                slot[f"{name}_sum"] += value
                slot[f"{name}_samples"] += 1
        for name in ("funded", "attempted", "built"):
            slot[name] += int(fields.get(name, 0) or 0)
        for key, value in fields.items():
            if key.startswith("r_"):
                slot["rejects"][key[2:]] += int(value or 0)

    result = {}
    for month, slot in by_month.items():
        considered_samples = slot["considered_samples"]
        accepted_samples = slot["accepted_samples"]
        result[month] = {
            "considered": (
                slot["considered_sum"] / considered_samples if considered_samples else None
            ),
            "accepted": (
                slot["accepted_sum"] / accepted_samples if accepted_samples else None
            ),
            "considered_sum": slot["considered_sum"] if considered_samples else None,
            "considered_samples": considered_samples,
            "accepted_sum": slot["accepted_sum"] if accepted_samples else None,
            "accepted_samples": accepted_samples,
            "funded": slot["funded"],
            "attempted": slot["attempted"],
            "built": slot["built"],
            "passes": slot["passes"],
            "rejects": dict(slot["rejects"]),
            "metric_kinds": {
                "considered": "stock_mean_per_pass",
                "accepted": "stock_mean_per_pass",
                "funded": "monthly_flow",
                "attempted": "monthly_flow",
                "built": "monthly_flow",
            },
        }
    return result



def parse_opex_funnel_detailed(output):
    """Agrege MONTHLY_FUNNEL_DETAIL par mode avec la meme separation stock/flux."""
    by_month_mode = defaultdict(lambda: defaultdict(lambda: {
        "considered_sum": 0,
        "considered_samples": 0,
        "accepted_sum": 0,
        "accepted_samples": 0,
        "funded": 0,
        "attempted": 0,
        "built": 0,
        "failed": 0,
        "passes": 0,
        "rejects": Counter(),
    }))
    for line in (output or "").splitlines():
        sm = SCRIPT_RE.search(line)
        if not sm or int(sm.group(1)) != 0:
            continue
        om = OPEX_RE.match(sm.group(2).strip())
        if not om or om.group(4) != "MONTHLY_FUNNEL_DETAIL":
            continue
        year, month = int(om.group(1)), int(om.group(2))
        fields = parse_fields(om.group(5))
        mode = fields.get("mode", "unknown")
        slot = by_month_mode[f"{year:04d}-{month:02d}"][mode]
        slot["passes"] += 1
        for name in ("considered", "accepted"):
            if name not in fields:
                continue
            value = int(fields.get(name, -1) or 0)
            if value >= 0:
                slot[f"{name}_sum"] += value
                slot[f"{name}_samples"] += 1
        for name in ("funded", "attempted", "built", "failed"):
            slot[name] += int(fields.get(name, 0) or 0)
        for key, value in fields.items():
            if key.startswith("r_"):
                slot["rejects"][key[2:]] += int(value or 0)

    result = {}
    for year_month, modes in by_month_mode.items():
        result[year_month] = {}
        for mode, slot in modes.items():
            has_activity = (
                slot["considered_samples"]
                or slot["accepted_samples"]
                or any(slot[name] for name in ("funded", "attempted", "built", "failed"))
                or slot["rejects"]
            )
            if not has_activity:
                continue
            cs = slot["considered_samples"]
            acs = slot["accepted_samples"]
            result[year_month][mode] = {
                "considered": slot["considered_sum"] / cs if cs else None,
                "accepted": slot["accepted_sum"] / acs if acs else None,
                "considered_sum": slot["considered_sum"] if cs else None,
                "considered_samples": cs,
                "accepted_sum": slot["accepted_sum"] if acs else None,
                "accepted_samples": acs,
                "funded": slot["funded"],
                "attempted": slot["attempted"],
                "built": slot["built"],
                "failed": slot["failed"],
                "passes": slot["passes"],
                "rejects": dict(slot["rejects"]),
                "metric_kinds": {
                    "considered": "stock_mean_per_pass",
                    "accepted": "stock_mean_per_pass",
                    "funded": "monthly_flow",
                    "attempted": "monthly_flow",
                    "built": "monthly_flow",
                    "failed": "monthly_flow",
                },
            }
    return result



def parse_hogex_builds(output):
    """Evenements de construction AAAHogEx deja journalises (pas de tunnel interne)."""
    by_month = defaultdict(lambda: {"succeeded": 0, "failed": 0, "try_build": 0})
    for line in (output or "").splitlines():
        sm = SCRIPT_RE.search(line)
        if not sm or int(sm.group(1)) != 1:  # Seulement AAAHogEx (joueur 1)
            continue
        hm = HOG_DATE_RE.match(sm.group(2).strip())
        if not hm:
            continue
        year, month, _day, detail = hm.groups()
        slot = by_month[f"{int(year):04d}-{int(month):02d}"]
        if any(marker in detail for marker in HOG_SUCCESS):
            slot["succeeded"] += 1
        elif any(marker in detail for marker in HOG_FAIL):
            slot["failed"] += 1
        if "TryBuild" in detail:
            slot["try_build"] += 1
    return dict(by_month)


def parse_hogex_builds_detailed(output):
    """Evenements de construction AAAHogEx avec suivi détaillé si nécessaire.
    Pour l'instant, on garde la même structure que parse_hogex_builds car
    AAAHogEx n'a pas de tunnel interne détaillé comme OpexAI.
    """
    return parse_hogex_builds(output)


def parse_c78_slot_events(output):
    """Evenements C78_SLOT, conserves avec leur date exacte et leurs champs."""
    by_month = defaultdict(list)
    for line in (output or "").splitlines():
        sm = SCRIPT_RE.search(line)
        if not sm or int(sm.group(1)) != 0:
            continue
        om = OPEX_RE.match(sm.group(2).strip())
        if not om or om.group(4) != "C78_SLOT":
            continue
        year, month, day = int(om.group(1)), int(om.group(2)), int(om.group(3))
        fields = parse_fields(om.group(5))
        for key, value in list(fields.items()):
            try:
                fields[key] = int(value)
            except (TypeError, ValueError):
                try:
                    fields[key] = float(value)
                except (TypeError, ValueError):
                    pass
        fields["date"] = f"{year:04d}-{month:02d}-{day:02d}"
        by_month[f"{year:04d}-{month:02d}"].append(fields)
    return dict(by_month)



def _iso_to_ottd_day(value):
    try:
        return date.fromisoformat(str(value)).toordinal() + 365
    except (TypeError, ValueError):
        return None


def _ottd_day_to_iso(value):
    try:
        return date.fromordinal(int(value) - 365).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _airport_builds_by_seed_town(rows, arm):
    """Union des aéroports vus dans STNN, avec la plus ancienne build_date par StationID."""
    by_seed = defaultdict(lambda: defaultdict(dict))
    for record in rows:
        if record.get("arm") != arm:
            continue
        seed = record.get("seed")
        inventory = record.get("stations_by_town") or {}
        for town_raw, slot in inventory.items():
            try:
                town_id = int(town_raw)
            except (TypeError, ValueError):
                continue
            for station in (slot or {}).get("stations", []):
                if "airport" not in (station.get("facilities") or []):
                    continue
                try:
                    station_id = int(station.get("id"))
                    build_date = int(station.get("build_date"))
                except (TypeError, ValueError):
                    continue
                previous = by_seed[seed][town_id].get(station_id)
                if previous is None or build_date < previous:
                    by_seed[seed][town_id][station_id] = build_date
    return by_seed


def _airport_first_and_double_by_seed_town(rows, arm):
    """Premier aéroport vu et première coexistence réelle de deux aéroports par ville."""
    by_seed_rows = defaultdict(list)
    for record in rows:
        if record.get("arm") == arm:
            by_seed_rows[record.get("seed")].append(record)

    first = defaultdict(dict)
    doubled = defaultdict(dict)
    for seed, seed_rows in by_seed_rows.items():
        seed_rows.sort(key=lambda record: str(record.get("date", "")))
        for record in seed_rows:
            inventory = record.get("stations_by_town") or {}
            for town_raw, slot in inventory.items():
                try:
                    town_id = int(town_raw)
                except (TypeError, ValueError):
                    continue
                current = []
                for station in (slot or {}).get("stations", []):
                    if "airport" not in (station.get("facilities") or []):
                        continue
                    try:
                        station_id = int(station.get("id"))
                        build_date = int(station.get("build_date"))
                    except (TypeError, ValueError):
                        continue
                    current.append((build_date, station_id))
                    previous = first[seed].get(town_id)
                    if previous is None or (build_date, station_id) < previous:
                        first[seed][town_id] = (build_date, station_id)

                # La première ligne mensuelle avec >=2 aéroports prouve leur coexistence.
                # On prend les deux plus anciens encore présents à cet instant.
                if len(current) >= 2 and town_id not in doubled[seed]:
                    current.sort()
                    doubled[seed][town_id] = {
                        "snapshot_date": record.get("date"),
                        "first": current[0],
                        "second": current[1],
                    }
    return first, doubled


def _flatten_c78_slot_events(rows):
    events = defaultdict(list)
    for record in rows:
        if record.get("arm") != "OpexAI":
            continue
        seed = record.get("seed")
        for event in record.get("c78_slot_events") or []:
            day = _iso_to_ottd_day(event.get("date"))
            if day is None:
                continue
            item = dict(event)
            item["_day"] = day
            for source, target in (("pass", "_pass"), ("tick", "_tick"), ("cycle", "_cycle")):
                try:
                    item[target] = int(item.get(source, -1))
                except (TypeError, ValueError):
                    item[target] = -1
            events[seed].append(item)
    for seed in events:
        events[seed].sort(
            key=lambda e: (e["_day"], e["_pass"], e["_tick"], e["_cycle"], e.get("phase", ""))
        )
    return events


def _c78_air_candidate_group_key(event, fallback_index):
    """Cle de groupe du portefeuille AIR : une paire O/D, independamment de l'equipement."""
    try:
        src = int(event.get("src", -1))
        dst = int(event.get("dst", -1))
    except (TypeError, ValueError):
        return ("event", fallback_index)
    if src < 0 or dst < 0:
        return ("event", fallback_index)
    if src > dst:
        src, dst = dst, src
    return ("air", src, dst)


def _c78_same_pass(event, pass_event):
    if event is None or pass_event is None:
        return False
    event_pass = event.get("_pass", -1)
    pass_id = pass_event.get("_pass", -1)
    if event_pass >= 0 and pass_id >= 0:
        return event_pass == pass_id
    event_cycle = event.get("_cycle", -1)
    pass_cycle = pass_event.get("_cycle", -1)
    if event_cycle >= 0 and pass_cycle >= 0:
        return event_cycle == pass_cycle
    # Un passage projects peut franchir un changement de date sous charge. Les identifiants
    # pass/cycle sont donc prioritaires ; la date ne sert que de repli pour d'anciens logs qui
    # ne les portent pas.
    if event.get("_day") != pass_event.get("_day"):
        return False
    event_tick = event.get("_tick", -1)
    pass_tick = pass_event.get("_tick", -1)
    if event_tick >= 0 and pass_tick >= 0 and event_tick != pass_tick:
        return False
    return True


def summarize_air_slot_intercept(rows):
    """Corrèle 0→1→2 aéroports AAA avec le prochain passage projects d'Opex.

    L'inventaire STNN donne les build_date exactes d'AAAHogEx. Les logs C78_SLOT décrivent
    le vivier AIR au passage projects ; aucune tentative n'est faite d'inspecter une StationID
    adverse depuis NoAI.
    """
    aaa_first, aaa_doubled = _airport_first_and_double_by_seed_town(rows, "AAAHogEx")
    own = _airport_builds_by_seed_town(rows, "OpexAI")
    events = _flatten_c78_slot_events(rows)
    opportunities = []

    for seed, towns in aaa_first.items():
        seed_events = events.get(seed, [])
        pass_events = [e for e in seed_events if e.get("phase") == "projects_pass"]
        build_events = [e for e in seed_events if e.get("phase") == "build"]
        candidate_events = [e for e in seed_events if e.get("phase") == "project_candidate"]
        attempt_events = [e for e in seed_events if e.get("phase") == "air_attempt"]
        outcome_events = [e for e in seed_events if e.get("phase") == "air_outcome"]
        stop_events = [e for e in seed_events if e.get("phase") == "pass_stop"]
        exit_events = [e for e in seed_events if e.get("phase") == "projects_exit"]

        for town_id, first_ever in towns.items():
            first_ever_day, first_ever_station = first_ever
            double = aaa_doubled.get(seed, {}).get(town_id)
            if double is not None:
                first_day, first_station = double["first"]
                second_day, second_station = double["second"]
                double_snapshot_date = double["snapshot_date"]
            else:
                first_day, first_station = first_ever_day, first_ever_station
                second_day = None
                second_station = None
                double_snapshot_date = None

            same_day_passes = [e for e in pass_events if e["_day"] == first_day]
            same_day_builds = [e for e in build_events if e["_day"] == first_day]
            # STNN build_date n'a pas de tick. Un log Opex du meme jour peut donc preceder
            # ou suivre la construction AAA : ne pas le presenter comme reaction prouvee.
            first_pass = next((e for e in pass_events if e["_day"] > first_day), None)
            first_build = next((e for e in build_events if e["_day"] > first_day), None)
            matches = []
            if first_pass is not None:
                pass_day = first_pass["_day"]
                pass_id = first_pass["_pass"]
                pass_tick = first_pass["_tick"]
                pass_cycle = first_pass["_cycle"]
                for event in candidate_events:
                    if event["_day"] != pass_day:
                        continue
                    if pass_id >= 0 and event["_pass"] >= 0:
                        if event["_pass"] != pass_id:
                            continue
                    else:
                        if pass_tick >= 0 and event["_tick"] >= 0 and event["_tick"] != pass_tick:
                            continue
                        if pass_cycle >= 0 and event["_cycle"] >= 0 and event["_cycle"] != pass_cycle:
                            continue
                    try:
                        town_a = int(event.get("townA", -1))
                        town_b = int(event.get("townB", -1))
                    except (TypeError, ValueError):
                        continue
                    if town_a == town_id or town_b == town_id:
                        matches.append(event)

            own_builds = sorted((day, sid) for sid, day in own.get(seed, {}).get(town_id, {}).items())
            own_before_first = next((entry for entry in own_builds if entry[0] < first_day), None)
            own_same_day = next((entry for entry in own_builds if entry[0] == first_day), None)
            own_after_first = next((entry for entry in own_builds if entry[0] > first_day), None)

            grouped_matches = defaultdict(list)
            for idx, event in enumerate(matches):
                grouped_matches[_c78_air_candidate_group_key(event, idx)].append(event)

            affordable_groups = []
            funded_groups = []
            funded_group_keys = []
            for group_key, variants in grouped_matches.items():
                is_affordable = False
                is_funded = False
                for event in variants:
                    try:
                        if int(event.get("affordable", 0) or 0) == 1:
                            is_affordable = True
                    except (TypeError, ValueError):
                        pass
                    try:
                        if int(event.get("rank", -1)) >= 0:
                            is_funded = True
                    except (TypeError, ValueError):
                        pass
                if is_affordable:
                    affordable_groups.append(variants)
                if is_funded:
                    funded_groups.append(variants)
                    funded_group_keys.append(group_key)

            same_pass_attempts = []
            same_pass_outcomes = []
            same_pass_stops = []
            same_pass_exit = None
            if first_pass is not None:
                same_pass_attempts = [e for e in attempt_events if _c78_same_pass(e, first_pass)]
                same_pass_outcomes = [e for e in outcome_events if _c78_same_pass(e, first_pass)]
                same_pass_stops = [e for e in stop_events if _c78_same_pass(e, first_pass)]
                same_pass_exit = next((e for e in exit_events if _c78_same_pass(e, first_pass)), None)

            funded_key_set = set(funded_group_keys)
            funded_attempts = [
                e for idx, e in enumerate(same_pass_attempts)
                if _c78_air_candidate_group_key(e, idx) in funded_key_set
            ]
            funded_outcomes = [
                e for idx, e in enumerate(same_pass_outcomes)
                if _c78_air_candidate_group_key(e, idx) in funded_key_set
            ]
            attempted_funded_keys = {
                _c78_air_candidate_group_key(e, idx) for idx, e in enumerate(funded_attempts)
            }
            built_funded_keys = {
                _c78_air_candidate_group_key(e, idx) for idx, e in enumerate(funded_outcomes)
                if e.get("outcome") == "built"
            }

            best_rank = None
            funded_ranks = []
            for variants in funded_groups:
                for event in variants:
                    try:
                        rank = int(event.get("rank", -1))
                    except (TypeError, ValueError):
                        continue
                    if rank >= 0:
                        funded_ranks.append(rank)
            if funded_ranks:
                best_rank = min(funded_ranks)
            best_affordable_profit = None
            if affordable_groups:
                profits = []
                for variants in affordable_groups:
                    for event in variants:
                        try:
                            profits.append(float(event.get("profit", 0)))
                        except (TypeError, ValueError):
                            pass
                if profits:
                    best_affordable_profit = max(profits)

            pass_day = first_pass["_day"] if first_pass is not None else None
            build_day = first_build["_day"] if first_build is not None else None
            own_day = own_after_first[0] if own_after_first is not None else None
            before_second = lambda d: d is not None and (second_day is None or d < second_day)

            opportunities.append({
                "seed": seed,
                "town": town_id,
                "aaa_first_ever_station": first_ever_station,
                "aaa_first_ever_build_date": first_ever_day,
                "aaa_first_ever_date": _ottd_day_to_iso(first_ever_day),
                "aaa_first_station": first_station,
                "aaa_first_build_date": first_day,
                "aaa_first_date": _ottd_day_to_iso(first_day),
                "aaa_double_snapshot_date": double_snapshot_date,
                "aaa_second_station": second_station,
                "aaa_second_build_date": second_day,
                "aaa_second_date": _ottd_day_to_iso(second_day) if second_day is not None else None,
                "window_days": (second_day - first_day) if second_day is not None else None,
                "same_day_projects_ambiguous": len(same_day_passes),
                "same_day_builds_ambiguous": len(same_day_builds),
                "next_projects_date": first_pass.get("date") if first_pass is not None else None,
                "next_projects_delay_days": (pass_day - first_day) if pass_day is not None else None,
                "next_projects_before_second": before_second(pass_day),
                "candidate_count": len(grouped_matches),
                "candidate_variant_count": len(matches),
                "affordable_candidate_count": len(affordable_groups),
                "funded_candidate_count": len(funded_groups),
                "funded_candidate_attempted_count": len(attempted_funded_keys),
                "funded_candidate_built_count": len(built_funded_keys),
                "best_funded_rank": best_rank,
                "best_affordable_profit": best_affordable_profit,
                "candidates": [
                    {k: v for k, v in e.items() if not k.startswith("_")}
                    for e in matches
                ],
                "funded_air_attempts": [
                    {k: v for k, v in e.items() if not k.startswith("_")}
                    for e in funded_attempts
                ],
                "funded_air_outcomes": [
                    {k: v for k, v in e.items() if not k.startswith("_")}
                    for e in funded_outcomes
                ],
                "pass_stops": [
                    {k: v for k, v in e.items() if not k.startswith("_")}
                    for e in same_pass_stops
                ],
                "projects_exit": (
                    {k: v for k, v in same_pass_exit.items() if not k.startswith("_")}
                    if same_pass_exit is not None else None
                ),
                "next_build_date": first_build.get("date") if first_build is not None else None,
                "next_build_delay_days": (build_day - first_day) if build_day is not None else None,
                "next_build_before_second": before_second(build_day),
                "opex_airport_already_present_before_aaa": own_before_first is not None,
                "opex_airport_same_day_ambiguous": own_same_day is not None,
                "opex_first_airport_after_aaa_date": _ottd_day_to_iso(own_day) if own_day is not None else None,
                "opex_airport_before_second": before_second(own_day),
            })

    opportunities.sort(key=lambda e: (e["seed"], e["aaa_first_build_date"], e["town"]))
    doubled = [e for e in opportunities if e["aaa_second_build_date"] is not None]
    pass_delays = [e["next_projects_delay_days"] for e in doubled if e["next_projects_delay_days"] is not None]
    windows = [e["window_days"] for e in doubled if e["window_days"] is not None]
    funded_cases = [
        e for e in doubled
        if e["next_projects_before_second"] and e["funded_candidate_count"] > 0
    ]
    funded_reject_reasons = Counter()
    funded_stop_reasons = Counter()
    for event in funded_cases:
        for outcome in event["funded_air_outcomes"]:
            if outcome.get("outcome") != "built":
                funded_reject_reasons[str(outcome.get("reason", "unknown"))] += 1
        if event["funded_candidate_attempted_count"] == 0:
            if event["pass_stops"]:
                for stop in event["pass_stops"]:
                    funded_stop_reasons[str(stop.get("reason", "unknown"))] += 1
            elif event["projects_exit"] is not None and event["projects_exit"].get("stop") not in (None, "", "none"):
                funded_stop_reasons[str(event["projects_exit"].get("stop"))] += 1
            else:
                funded_stop_reasons["no_logged_stop"] += 1
    c83_phase_counts = Counter()
    c83_watch_actions = Counter()
    for seed_events in events.values():
        for event in seed_events:
            phase = str(event.get("phase", ""))
            if phase in ("c83_slot_watch", "c83_slot_claimed", "c83_slot_lost"):
                c83_phase_counts[phase] += 1
            if phase == "c83_slot_watch":
                c83_watch_actions[str(event.get("action", "unknown"))] += 1
    summary = {
        "opportunities": len(opportunities),
        "second_airport_cases": len(doubled),
        "same_day_projects_ambiguous": sum(bool(e["same_day_projects_ambiguous"]) for e in doubled),
        "same_day_builds_ambiguous": sum(bool(e["same_day_builds_ambiguous"]) for e in doubled),
        "next_projects_before_second": sum(bool(e["next_projects_before_second"]) for e in doubled),
        "affordable_candidate_before_second": sum(
            bool(e["next_projects_before_second"]) and e["affordable_candidate_count"] > 0
            for e in doubled
        ),
        "funded_candidate_before_second": sum(
            bool(e["next_projects_before_second"]) and e["funded_candidate_count"] > 0
            for e in doubled
        ),
        "funded_candidate_attempted_first_pass": sum(
            e["funded_candidate_attempted_count"] > 0 for e in funded_cases
        ),
        "funded_candidate_built_first_pass": sum(
            e["funded_candidate_built_count"] > 0 for e in funded_cases
        ),
        "funded_candidate_not_attempted_first_pass": sum(
            e["funded_candidate_attempted_count"] == 0 for e in funded_cases
        ),
        "funded_reject_reasons": dict(sorted(funded_reject_reasons.items())),
        "funded_not_attempted_stop_reasons": dict(sorted(funded_stop_reasons.items())),
        "c83_slot_watch": c83_phase_counts["c83_slot_watch"],
        "c83_slot_watch_actions": dict(sorted(c83_watch_actions.items())),
        "c83_slot_claimed": c83_phase_counts["c83_slot_claimed"],
        "c83_slot_lost": c83_phase_counts["c83_slot_lost"],
        "next_build_before_second": sum(bool(e["next_build_before_second"]) for e in doubled),
        "opex_airport_before_second": sum(bool(e["opex_airport_before_second"]) for e in doubled),
        "window_median_days": statistics.median(windows) if windows else None,
        "next_projects_delay_median_days": statistics.median(pass_delays) if pass_delays else None,
    }
    return {"summary": summary, "opportunities": opportunities}



def attach_logs(rows, funnel_requested=None, slot_requested=False):
    """Attache les journaux mensuels et rend l'etat d'instrumentation explicite."""
    last_output = {}
    for record in rows:
        if record.get("arm") == "OpexAI" and record.get("output"):
            last_output[record["seed"]] = record["output"]
    funnel_by_seed = {seed: parse_opex_funnel(output) for seed, output in last_output.items()}
    funnel_detailed_by_seed = {
        seed: parse_opex_funnel_detailed(output) for seed, output in last_output.items()
    }
    hogex_by_seed = {seed: parse_hogex_builds(output) for seed, output in last_output.items()}
    hogex_detailed_by_seed = {
        seed: parse_hogex_builds_detailed(output) for seed, output in last_output.items()
    }
    c78_slot_by_seed = {
        seed: parse_c78_slot_events(output) for seed, output in last_output.items()
    }
    if funnel_requested is None:
        funnel_requested = any(funnel_by_seed.values()) or any(funnel_detailed_by_seed.values())

    for record in rows:
        record.pop("output", None)
        month = str(record.get("date", ""))[:7]
        seed = record.get("seed")
        if record.get("arm") == "OpexAI":
            funnel_map = funnel_by_seed.get(seed, {})
            detail_map = funnel_detailed_by_seed.get(seed, {})
            slot_map = c78_slot_by_seed.get(seed, {})
            record["funnel"] = funnel_map.get(month)
            record["funnel_detailed"] = detail_map.get(month)
            record["c78_slot_events"] = slot_map.get(month, [])
            if not slot_requested:
                record["c78_slot_state"] = "disabled"
            elif seed not in last_output:
                record["c78_slot_state"] = "missing_log"
            else:
                record["c78_slot_state"] = (
                    "available" if month in slot_map
                    else ("no_activity" if slot_map else "missing_emitter")
                )
            if not funnel_requested:
                record["funnel_state"] = "disabled"
                record["funnel_detailed_state"] = "disabled"
            elif seed not in last_output:
                record["funnel_state"] = "missing_log"
                record["funnel_detailed_state"] = "missing_log"
            else:
                record["funnel_state"] = (
                    "available" if month in funnel_map
                    else ("no_activity" if funnel_map else "missing_emitter")
                )
                record["funnel_detailed_state"] = (
                    "available" if month in detail_map
                    else ("no_activity" if detail_map else "missing_emitter")
                )
        else:
            record["hogex_builds"] = hogex_by_seed.get(seed, {}).get(month)
            record["hogex_builds_detailed"] = hogex_detailed_by_seed.get(seed, {}).get(month)
    return funnel_by_seed, funnel_detailed_by_seed, hogex_by_seed, hogex_detailed_by_seed


def attach_opcode_deltas(rows):
    """Transforme les compteurs opcode cumules en coût mensuel par graine.

    SIGN est cumulatif dans la sauvegarde. Le total lu a un checkpoint contient donc
    tous les panneaux precedents ; la difference avec le checkpoint precedent restitue
    les coûts observés du mois sans ajouter de nouveau panneau.
    """
    by_seed = defaultdict(list)
    for record in rows:
        if record.get("arm") == "OpexAI":
            by_seed[record.get("seed")].append(record)
    for seed_rows in by_seed.values():
        seed_rows.sort(key=lambda record: str(record.get("date", "")))
        previous_total = 0
        previous_samples = 0
        previous_observed = 0
        previous_components = {}
        for record in seed_rows:
            current_total = record.get("selection_kopcodes_total")
            current_samples = record.get("selection_kopcodes_samples")
            if current_total is None or current_samples is None:
                record["selection_opcode_state"] = "missing_ig_opcode_field"
            else:
                delta_total = current_total - previous_total
                delta_samples = current_samples - previous_samples
                if delta_total < 0 or delta_samples < 0:
                    record["selection_opcode_state"] = "counter_regressed"
                    previous_total = current_total
                    previous_samples = current_samples
                else:
                    record["selection_kopcodes_month"] = delta_total
                    record["selection_kopcodes_samples_month"] = delta_samples
                    record["selection_opcode_state"] = "available"
                    previous_total = current_total
                    previous_samples = current_samples
            observed_total = record.get("observed_opcodes_total")
            components = record.get("observed_opcode_components")
            if observed_total is None or components is None:
                record["observed_opcode_state"] = "missing_observed_opcode_fields"
                continue
            observed_delta = observed_total - previous_observed
            if observed_delta < 0:
                record["observed_opcode_state"] = "counter_regressed"
                previous_observed = observed_total
                previous_components = {
                    name: payload.get("opcodes", 0)
                    for name, payload in components.items()
                }
                continue
            component_deltas = {}
            component_regressed = False
            current_components = {}
            for name, payload in components.items():
                current = payload.get("opcodes", 0)
                previous = previous_components.get(name, 0)
                delta = current - previous
                if delta < 0:
                    component_regressed = True
                component_deltas[name] = delta
                current_components[name] = current
            if component_regressed:
                record["observed_opcode_state"] = "component_regressed"
            else:
                record["observed_opcodes_month"] = observed_delta
                record["observed_mopcodes_month"] = observed_delta / 1_000_000.0
                record["observed_opcode_components_month"] = component_deltas
                record["observed_opcode_state"] = "available"
            previous_observed = observed_total
            previous_components = current_components
    return rows


# Nom historique conservé pour les imports/tests existants.
attach_selection_opcode_deltas = attach_opcode_deltas



def build_arms(seeds, years, shared=False, funnel=False, air_town_limit_memory=False,
               town_station_detail=False, air_early_slot=False, air_slot_intercept=False):
    from openttdlab import local_folder
    hogex = local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ())
    if shared:
        opex_params = []
        if funnel or air_slot_intercept:
            opex_params.append(("probe_portfolio", 1))
        if air_town_limit_memory:
            opex_params.append(("air_town_limit_memory", 1))
        if air_early_slot:
            opex_params.extend((
                ("air_early_slot", 1),
                ("air_early_slot_target_towns", 6),
                ("air_early_slot_min_pop", 1000),
                ("air_early_slot_bonus_pct", 50),
            ))
        opex_params = tuple(opex_params)
        opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", opex_params)
        return [
            {
                "seed": seed,
                "days": 365 * years,
                "openttd_config": CFG_SHARED,
                "ais": (opex, hogex),
                "shared": True,
                "diag_arm": "duel",
                "town_station_detail": bool(town_station_detail),
            }
            for seed in seeds
        ]
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("probe_events", 1),))
    return [
        {
            "seed": seed,
            "days": 365 * years,
            "openttd_config": make_cfg(STARTING_YEAR),
            "ais": (ai,),
            "diag_arm": arm,
            "shared": False,
        }
        for seed in seeds
        for arm, ai in (("OpexAI", opex), ("AAAHogEx", hogex))
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--shared", action="store_true",
                        help="OpexAI (joueur 0) vs AAAHogEx (joueur 1) sur la meme carte")
    parser.add_argument("--funnel", action="store_true",
                        help="Arme monthly_funnel=1 (implique --shared et -d script=4)")
    parser.add_argument("--no-funnel", action="store_true",
                        help="En mode --shared, desactive explicitement monthly_funnel")
    parser.add_argument("--air-town-limit-memory", action="store_true",
                        help="Arme air_town_limit_memory=1 sur OpexAI (implique --shared)")
    parser.add_argument("--town-station-detail", action="store_true",
                        help="Conserve l'inventaire STNN par TownID pour diagnostiquer les erreurs 771")
    parser.add_argument("--air-early-slot", action="store_true",
                        help="Arme air_early_slot=1 (cible 6 villes, min 1000 hab, bonus 50%% par slot)")
    parser.add_argument("--air-slot-intercept", action="store_true",
                        help="Arme la sonde C78 du vivier AIR pour correlation avec les build_date adverses")
    parser.add_argument("--selftest", action="store_true",
                        help="Verifie le decodage physique et le rendu face aux chunks invalides")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    import openttdlab
    from openttdlab import bananas_ai_library, local_folder, run_experiments
    from bench_v2 import enable_savegame_cleanup, write_json_atomically

    if args.funnel and args.no_funnel:
        parser.error("--funnel et --no-funnel sont incompatibles")
    shared = (
        args.shared or args.funnel or args.air_town_limit_memory or args.town_station_detail
        or args.air_early_slot or args.air_slot_intercept
    )
    funnel = bool(args.funnel or (shared and not args.no_funnel))
    seeds = args.seeds if args.seeds is not None else (list(DIAG_SEEDS) if shared else [42, 100, 7])
    default_name = (
        f"diag_1v1_shared_monthly_{args.years}y_{len(seeds)}seeds.json"
        if shared else "diag_1v1_monthly.json"
    )
    out = args.out or (ROOT / "results" / default_name)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if shared or funnel:
        real_check = openttdlab.subprocess.check_output

        def check_output_with_script_debug(cmd, *rest, **kwargs):
            cmd = tuple(cmd)
            if any(str(arg).startswith("-vnull") for arg in cmd):
                cmd = cmd[:1] + ("-d", "script=4") + cmd[1:]
            return real_check(cmd, *rest, **kwargs)

        openttdlab.subprocess.check_output = check_output_with_script_debug
        enable_savegame_cleanup()

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=build_arms(seeds, args.years, shared=shared, funnel=funnel,
                               air_town_limit_memory=args.air_town_limit_memory,
                               town_station_detail=args.town_station_detail or args.air_slot_intercept,
                               air_early_slot=args.air_early_slot,
                               air_slot_intercept=args.air_slot_intercept),
        max_workers=args.workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    funnel_by_seed, funnel_detailed_by_seed, hogex_by_seed, hogex_detailed_by_seed = attach_logs(
        rows, funnel_requested=funnel, slot_requested=args.air_slot_intercept
    )
    attach_opcode_deltas(rows)
    expected_months = expected_calendar_months(args.years)
    monthly = render_monthly_report(
        rows,
        expected_seeds=seeds,
        expected_months=expected_months,
    )
    finals = render_final_comparison(rows, seeds)
    slot_intercept = summarize_air_slot_intercept(rows) if args.air_slot_intercept else None
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": seeds,
        "shared_game": shared,
        "funnel": funnel,
        "funnel_explicitly_disabled": bool(args.no_funnel),
        "air_town_limit_memory": bool(args.air_town_limit_memory),
        "town_station_detail": bool(args.town_station_detail or args.air_slot_intercept),
        "air_slot_intercept": bool(args.air_slot_intercept),
        "air_slot_intercept_analysis": slot_intercept,
        "opponent": "AAAHogEx" if shared else None,
        "openttd_config": CFG_SHARED if shared else make_cfg(STARTING_YEAR),
        "rows": rows,
        "monthly": monthly,
        "funnel_by_seed": funnel_by_seed,
        "funnel_detailed_by_seed": funnel_detailed_by_seed,
        "hogex_builds_by_seed": hogex_by_seed,
        "hogex_builds_detailed_by_seed": hogex_detailed_by_seed,
        "finals": finals,
    }
    write_json_atomically(out, payload)
    print(f"\necrit {out}")


def physical_row_ok(record):
    """Une ligne n'est exploitable que si VEHS et STNN sont tous deux valides."""
    vehs = record.get("vehicles") or {}
    stns = record.get("stations") or {}
    return vehs.get("chunk_valid") is True and stns.get("chunk_valid") is True


def expected_calendar_months(years, starting_year=STARTING_YEAR):
    """Mois calendaires attendus pour une campagne de `years` annees pleines."""
    if not years or years < 1:
        return []
    return [
        f"{year}-{month:02d}"
        for year in range(starting_year, starting_year + years)
        for month in range(1, 13)
    ]


def _aggregate_funnel_slots(slots, flow_names):
    """Combine des stocks moyens ponderes par leurs echantillons et des flux additifs."""
    result = {}
    for name in ("considered", "accepted"):
        total = 0.0
        samples = 0
        for slot in slots:
            sample_count = int(slot.get(f"{name}_samples", 0) or 0)
            raw_sum = slot.get(f"{name}_sum")
            if raw_sum is None and slot.get(name) is not None:
                if sample_count <= 0:
                    sample_count = 1
                raw_sum = float(slot[name]) * sample_count
            if raw_sum is not None and sample_count > 0:
                total += float(raw_sum)
                samples += sample_count
        result[name] = total / samples if samples else None
        result[f"{name}_sum"] = total if samples else None
        result[f"{name}_samples"] = samples
    for name in flow_names:
        result[name] = sum(int(slot.get(name, 0) or 0) for slot in slots)
    result["passes"] = sum(int(slot.get("passes", 0) or 0) for slot in slots)
    rejects = Counter()
    for slot in slots:
        rejects.update(slot.get("rejects") or {})
    result["rejects"] = dict(rejects)
    result["metric_kinds"] = {
        "considered": "stock_mean_per_pass",
        "accepted": "stock_mean_per_pass",
        **{name: "monthly_flow" for name in flow_names},
    }
    return result


def monthly_aggregates(rows, expected_seeds=None, expected_months=None, expected_arms=None):
    """Agrege un mois seulement si toutes les lignes attendues sont physiquement valides."""
    arms = tuple(expected_arms) if expected_arms else ARMS
    if expected_seeds is not None:
        expected_set = set(expected_seeds)
    else:
        expected_set = {record["seed"] for record in rows if "seed" in record}

    per_month = defaultdict(list)
    for record in rows:
        per_month[(record["arm"], record["date"][:7])].append(record)

    months = sorted(set(expected_months or []) | {date for _, date in per_month})
    cells = []
    for month in months:
        for arm in arms:
            month_rows = per_month.get((arm, month), [])
            present = {record["seed"] for record in month_rows if "seed" in record}
            grouped = defaultdict(list)
            for record in month_rows:
                grouped[record.get("seed")].append(record)
            valid_seeds = {
                seed for seed, seed_rows in grouped.items()
                if seed is not None and seed_rows and all(physical_row_ok(r) for r in seed_rows)
            }
            if expected_set:
                expected_n = len(expected_set)
                valid_n = len(valid_seeds)
                complete = valid_seeds == expected_set and present == expected_set
            else:
                expected_n = len(month_rows)
                valid_n = sum(1 for record in month_rows if physical_row_ok(record))
                complete = expected_n > 0 and valid_n == expected_n

            cell = {
                "month": month,
                "arm": arm,
                "ok": complete,
                "n_valid": valid_n,
                "n_expected": expected_n,
                "qualified_modes": None,
                "qualification_status": None,
                "by_mode": None,
                "by_mode_all_primary": None,
                "n_units": None,
                "n_units_all_primary": None,
                "unqualified_primary_vehicles": None,
                "n_stations": None,
                "cargo_waiting": None,
                "rating_median": None,
                "rolling_capital": None,
                "rolling_capital_all_primary": None,
                "profit_per_vehicle": None,
                "profit_per_vehicle_all_primary": None,
                "company_value": None,
                "income": None,
                "expenses": None,
                "profit": None,
                "delivered_cargo": None,
                "funnel": None,
                "funnel_state": None,
                "funnel_state_counts": None,
                "funnel_detailed": None,
                "funnel_detailed_state": None,
                "funnel_detailed_state_counts": None,
                "hogex_builds": None,
                "hogex_builds_detailed": None,
                "selection_kopcodes": None,
                "selection_kopcodes_samples": None,
                "selection_opcode_state": None,
                "selection_opcode_state_counts": None,
                "observed_opcodes": None,
                "observed_mopcodes": None,
                "observed_opcode_components": None,
                "observed_opcode_state": None,
                "observed_opcode_state_counts": None,
            }

            if arm == "OpexAI" and month_rows:
                for state_key in ("funnel_state", "funnel_detailed_state"):
                    counts = Counter(
                        record.get(state_key, "unknown") for record in month_rows
                    )
                    cell[f"{state_key}_counts"] = dict(counts)
                    cell[state_key] = (
                        next(iter(counts)) if len(counts) == 1 else "mixed"
                    )
                selection_states = Counter(
                    record.get("selection_opcode_state", "unknown")
                    for record in month_rows
                )
                cell["selection_opcode_state_counts"] = dict(selection_states)
                cell["selection_opcode_state"] = (
                    next(iter(selection_states))
                    if len(selection_states) == 1 else "mixed"
                )
                observed_states = Counter(
                    record.get("observed_opcode_state", "unknown")
                    for record in month_rows
                )
                cell["observed_opcode_state_counts"] = dict(observed_states)
                cell["observed_opcode_state"] = (
                    next(iter(observed_states))
                    if len(observed_states) == 1 else "mixed"
                )

            if complete:
                qualification_maps = [
                    record["vehicles"].get("qualified_modes")
                    for record in month_rows
                    if record.get("vehicles", {}).get("qualified_modes") is not None
                ]
                if qualification_maps:
                    first_qualification = qualification_maps[0]
                    if all(item == first_qualification for item in qualification_maps):
                        cell["qualified_modes"] = first_qualification

                mode_totals = {}
                for mode in VEHICLE_MODES:
                    values = [
                        record["vehicles"]["by_mode"].get(mode)
                        for record in month_rows
                        if record["vehicles"].get("by_mode") is not None
                        and record["vehicles"]["by_mode"].get(mode) is not None
                    ]
                    mode_totals[mode] = statistics.mean(values) if values else None
                cell["by_mode"] = mode_totals

                all_mode_totals = {}
                for mode in VEHICLE_MODES:
                    values = [
                        (record["vehicles"].get("by_mode_all_primary") or {}).get(mode)
                        for record in month_rows
                        if (record["vehicles"].get("by_mode_all_primary") or {}).get(mode) is not None
                    ]
                    all_mode_totals[mode] = statistics.mean(values) if values else None
                if any(value is not None for value in all_mode_totals.values()):
                    cell["by_mode_all_primary"] = all_mode_totals

                def mean_vehicle(field):
                    values = [
                        record["vehicles"].get(field)
                        for record in month_rows
                        if record["vehicles"].get(field) is not None
                    ]
                    return statistics.mean(values) if values else None

                cell["n_units"] = mean_vehicle("n_units")
                cell["n_units_all_primary"] = mean_vehicle("n_units_all_primary")
                cell["unqualified_primary_vehicles"] = mean_vehicle("unqualified_primary_vehicles")
                cell["rolling_capital"] = mean_vehicle("rolling_capital")
                cell["rolling_capital_all_primary"] = mean_vehicle("rolling_capital_all_primary")
                cell["profit_per_vehicle"] = mean_vehicle("profit_per_vehicle")
                cell["profit_per_vehicle_all_primary"] = mean_vehicle("profit_per_vehicle_all_primary")

                if arm == "OpexAI":
                    selection_values = [
                        record.get("selection_kopcodes_month")
                        for record in month_rows
                        if record.get("selection_kopcodes_month") is not None
                    ]
                    selection_samples = [
                        record.get("selection_kopcodes_samples_month")
                        for record in month_rows
                        if record.get("selection_kopcodes_samples_month") is not None
                    ]
                    if selection_values:
                        cell["selection_kopcodes"] = statistics.mean(selection_values)
                    if selection_samples:
                        cell["selection_kopcodes_samples"] = statistics.mean(selection_samples)
                    observed_values = [
                        record.get("observed_opcodes_month")
                        for record in month_rows
                        if record.get("observed_opcodes_month") is not None
                    ]
                    if observed_values:
                        cell["observed_opcodes"] = statistics.mean(observed_values)
                        cell["observed_mopcodes"] = cell["observed_opcodes"] / 1_000_000.0
                    component_names = set()
                    for record in month_rows:
                        component_names.update(
                            (record.get("observed_opcode_components_month") or {}).keys()
                        )
                    if component_names:
                        cell["observed_opcode_components"] = {
                            name: statistics.mean([
                                record["observed_opcode_components_month"].get(name, 0)
                                for record in month_rows
                                if record.get("observed_opcode_components_month") is not None
                            ])
                            for name in sorted(component_names)
                        }

                if cell["qualified_modes"] is None:
                    cell["qualification_status"] = "unknown"
                elif cell["unqualified_primary_vehicles"]:
                    cell["qualification_status"] = "qualified_totals_exclude_unqualified_vehicles"
                else:
                    cell["qualification_status"] = "qualified_totals"

                def mean_station(field):
                    values = [
                        record["stations"].get(field)
                        for record in month_rows
                        if record["stations"].get(field) is not None
                    ]
                    return statistics.mean(values) if values else None

                cell["n_stations"] = mean_station("n_stations")
                cell["cargo_waiting"] = mean_station("cargo_waiting")
                cell["rating_median"] = mean_station("rating_median")

                for field, source_field in (
                    ("company_value", "company_value"),
                    ("income", "income"),
                    ("expenses", "expenses"),
                    ("profit", "profit_year"),
                    ("delivered_cargo", "delivered_cargo"),
                ):
                    values = [
                        record.get(source_field)
                        for record in month_rows
                        if record.get(source_field) is not None
                    ]
                    cell[field] = statistics.mean(values) if values else None

                if arm == "OpexAI":
                    funnels = [
                        record.get("funnel") for record in month_rows
                        if record.get("funnel") is not None
                    ]
                    if funnels:
                        cell["funnel"] = _aggregate_funnel_slots(
                            funnels, ("funded", "attempted", "built")
                        )

                    detail_slots = defaultdict(list)
                    for modes in (
                        record.get("funnel_detailed") for record in month_rows
                    ):
                        if not modes:
                            continue
                        for mode, slot in modes.items():
                            if isinstance(slot, dict):
                                detail_slots[mode].append(slot)
                    if detail_slots:
                        cell["funnel_detailed"] = {
                            mode: _aggregate_funnel_slots(
                                slots, ("funded", "attempted", "built", "failed")
                            )
                            for mode, slots in sorted(detail_slots.items())
                        }
                else:
                    builds = [
                        record.get("hogex_builds") for record in month_rows
                        if record.get("hogex_builds")
                    ]
                    if builds:
                        cell["hogex_builds"] = {
                            key: sum(int((slot or {}).get(key, 0) or 0) for slot in builds)
                            for key in ("succeeded", "failed", "try_build")
                        }
                    builds_detailed = [
                        record.get("hogex_builds_detailed") for record in month_rows
                        if record.get("hogex_builds_detailed")
                    ]
                    if builds_detailed:
                        cell["hogex_builds_detailed"] = {
                            key: sum(int((slot or {}).get(key, 0) or 0) for slot in builds_detailed)
                            for key in ("succeeded", "failed", "try_build")
                        }
            cells.append(cell)
    return cells



def render_monthly_report(rows, expected_seeds=None, expected_months=None, expected_arms=None):
    """Affiche le rapport mensuel consolide. Un mois incomplet s'affiche FAIL v/e."""
    monthly = monthly_aggregates(
        rows,
        expected_seeds=expected_seeds,
        expected_months=expected_months,
        expected_arms=expected_arms,
    )
    by_key = {(cell["arm"], cell["month"]): cell for cell in monthly}
    months = sorted({cell["month"] for cell in monthly})

    print()
    header = (f"{'mois':<8} | {'OpexAI tr/rt/bt/av':>19} {'gares':>5} {'capRoul':>9} {'prof/veh':>9}"
              f" | {'AAAHogEx tr/rt/bt/av':>20} {'gares':>5} {'capRoul':>9} {'prof/veh':>9}")
    print(header)
    print("-" * len(header))
    for month in months:
        line = f"{month:<8} |"
        for arm in ARMS:
            cell = by_key.get((arm, month))
            if cell is None or (cell["n_expected"] == 0 and cell["n_valid"] == 0):
                line += f" {'-':>19} {'-':>5} {'-':>9} {'-':>9} |"
                continue
            if not cell["ok"]:
                fail = f"FAIL {cell['n_valid']}/{cell['n_expected']}"
                line += f" {fail:>19} {'FAIL':>5} {'FAIL':>9} {'FAIL':>9} |"
                continue
            mix = "/".join(
                "n/a" if cell["by_mode"].get(mode) is None
                else f"{cell['by_mode'][mode]:.0f}"
                for mode in VEHICLE_MODES
            )
            st_str = f"{cell['n_stations']:>5.1f}" if cell["n_stations"] is not None else "FAIL"
            cap_str = f"{cell['rolling_capital']:>9,.0f}" if cell["rolling_capital"] is not None else "FAIL"
            ppv_str = f"{cell['profit_per_vehicle']:>9,.0f}" if cell["profit_per_vehicle"] is not None else "FAIL"
            line += f" {mix:>19} {st_str:>5} {cap_str:>9} {ppv_str:>9} |"
        print(line)

    print()
    eco = (f"{'mois':<8} | {'OpexAI val/rev/dep/prof/cargo':>40}"
           f" | {'AAAHogEx val/rev/dep/prof/cargo':>40}")
    print(eco)
    print("-" * len(eco))
    for month in months:
        line = f"{month:<8} |"
        for arm in ARMS:
            cell = by_key.get((arm, month))
            if cell is None or (cell["n_expected"] == 0 and cell["n_valid"] == 0):
                line += f" {'-':>40} |"
                continue
            if not cell["ok"]:
                line += f" {'FAIL ' + str(cell['n_valid']) + '/' + str(cell['n_expected']):>40} |"
                continue
            parts = []
            for field, width in (("company_value", 9), ("income", 8), ("expenses", 8),
                                 ("profit", 8), ("delivered_cargo", 5)):
                value = cell.get(field)
                parts.append(f"{value:>{width},.0f}" if value is not None else f"{'—':>{width}}")
            line += " " + "/".join(parts) + " |"
        print(line)

    print()
    tun = (f"{'mois':<8} | {'OpexAI cand/acc/fin/tent/ok':>28} {'rejet':>18}"
           f" | {'AAAHogEx ok/fail/try':>20}")
    print(tun)
    print("-" * len(tun))
    for month in months:
        opex = by_key.get(("OpexAI", month), {})
        hogex = by_key.get(("AAAHogEx", month), {})
        if opex.get("ok") and opex.get("funnel"):
            fn = opex["funnel"]
            stock = [
                "n/a" if fn.get(key) is None else f"{float(fn[key]):.1f}"
                for key in ("considered", "accepted")
            ]
            flows = [str(int(fn.get(key) or 0)) for key in ("funded", "attempted", "built")]
            mix = "/".join(stock + flows)
            rejects = fn.get("rejects") or {}
            top = max(rejects, key=rejects.get) if rejects else "—"
            top_s = f"{top}:{rejects[top]}" if rejects else "—"
            opex_s = f"{mix:>28} {top_s:>18}"
        elif opex.get("ok"):
            opex_s = f"{'—':>28} {'—':>18}"
        else:
            opex_s = f"{'FAIL':>28} {'FAIL':>18}"
        if hogex.get("ok") and hogex.get("hogex_builds"):
            hb = hogex["hogex_builds"]
            hog_s = f"{hb.get('succeeded', 0)}/{hb.get('failed', 0)}/{hb.get('try_build', 0)}"
        elif hogex.get("ok"):
            hog_s = "—"
        else:
            hog_s = "FAIL"
        print(f"{month:<8} | {opex_s} | {hog_s:>20}")
    return monthly


def _last_ok_record(rows, arm, seed):
    owned = [record for record in rows
             if record.get("arm") == arm and record.get("seed") == seed and physical_row_ok(record)]
    if not owned:
        return None
    return sorted(owned, key=lambda record: str(record.get("date", "")))[-1]


def render_final_comparison(rows, seeds):
    """Dernier mois valide par graine : volume, rentabilite unitaire, gares."""
    print()
    header = (f"{'graine':<8} | {'valeur O vs A':<28} | {'vehicules O/A':<14} | "
              f"{'gares O/A':<10} | {'prof/veh O/A':<16} | {'attente O/A':<14}")
    print(header)
    print("-" * len(header))
    finals = []
    for seed in seeds:
        opex = _last_ok_record(rows, "OpexAI", seed)
        hogex = _last_ok_record(rows, "AAAHogEx", seed)
        if opex is None or hogex is None:
            print(f"{seed:<8} | FAIL")
            finals.append({"seed": seed, "ok": False})
            continue
        ov, av = opex.get("company_value"), hogex.get("company_value")
        on = (opex.get("vehicles") or {}).get("n_units")
        an = (hogex.get("vehicles") or {}).get("n_units")
        os_ = (opex.get("stations") or {}).get("n_stations")
        as_ = (hogex.get("stations") or {}).get("n_stations")
        op = (opex.get("vehicles") or {}).get("profit_per_vehicle")
        ap = (hogex.get("vehicles") or {}).get("profit_per_vehicle")
        ow = (opex.get("stations") or {}).get("cargo_waiting")
        aw = (hogex.get("stations") or {}).get("cargo_waiting")
        ratio = f"{(ov / av * 100):.0f}%" if ov is not None and av else "—"
        v_str = f"{ov:>10,.0f} vs {av:>10,.0f} {ratio}" if ov is not None and av is not None else "FAIL"
        print(f"{seed:<8} | {v_str:<28} | {on:>3} vs {an:<3}     | {os_:>3} vs {as_:<3}  | "
              f"{(op or 0):>7,.0f} vs {(ap or 0):<6,.0f} | {ow or 0:>5} vs {aw or 0:<5}")
        finals.append({
            "seed": seed,
            "ok": True,
            "date": opex.get("date"),
            "opex": {
                "company_value": ov, "n_units": on, "n_stations": os_,
                "profit_per_vehicle": op, "cargo_waiting": ow,
                "by_mode": (opex.get("vehicles") or {}).get("by_mode"),
                "rolling_capital": (opex.get("vehicles") or {}).get("rolling_capital"),
                "income": opex.get("income"), "delivered_cargo": opex.get("delivered_cargo"),
            },
            "aaahogex": {
                "company_value": av, "n_units": an, "n_stations": as_,
                "profit_per_vehicle": ap, "cargo_waiting": aw,
                "by_mode": (hogex.get("vehicles") or {}).get("by_mode"),
                "rolling_capital": (hogex.get("vehicles") or {}).get("rolling_capital"),
                "income": hogex.get("income"), "delivered_cargo": hogex.get("delivered_cargo"),
            },
        })
    return finals


def selftest():
    """Verifie le decodage et la resilience du rendu mensuel face aux erreurs de chunk."""
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
    mixed = monthly_aggregates(mock_rows, expected_seeds=[42, 100])
    feb_opex = next(cell for cell in mixed if cell["month"] == "1970-02" and cell["arm"] == "OpexAI")
    feb_aaa = next(cell for cell in mixed if cell["month"] == "1970-02" and cell["arm"] == "AAAHogEx")
    mar_opex = next(cell for cell in mixed if cell["month"] == "1970-03" and cell["arm"] == "OpexAI")
    assert feb_opex["ok"] is False
    assert feb_opex["n_valid"] == 1 and feb_opex["n_expected"] == 2
    assert feb_opex["by_mode"] is None
    assert feb_aaa["ok"] is False
    assert feb_aaa["n_valid"] == 0 and feb_aaa["n_expected"] == 2
    assert mar_opex["ok"] is True
    assert mar_opex["by_mode"]["rail"] == 3
    assert mar_opex["n_stations"] == 7

    # Graine 100 totalement absente : ne pas conclure 1/1.
    only_42 = [record for record in mock_rows if record.get("seed") != 100]
    missing_seed = monthly_aggregates(only_42, expected_seeds=[42, 100])
    miss_feb = next(cell for cell in missing_seed if cell["month"] == "1970-02" and cell["arm"] == "OpexAI")
    assert miss_feb["ok"] is False
    assert miss_feb["n_valid"] == 1 and miss_feb["n_expected"] == 2
    assert miss_feb["by_mode"] is None

    # Mois calendaire attendu sans aucune ligne.
    with_jan = monthly_aggregates(
        mock_rows, expected_seeds=[42, 100], expected_months=["1970-01", "1970-02"],
    )
    jan_opex = next(cell for cell in with_jan if cell["month"] == "1970-01" and cell["arm"] == "OpexAI")
    assert jan_opex["ok"] is False
    assert jan_opex["n_valid"] == 0 and jan_opex["n_expected"] == 2

    assert cargo_delivered([10, 20, 0, 5]) == 35
    assert cargo_delivered(12) == 12
    assert cargo_delivered(None) is None

    opcode_rows = [
        {
            "arm": "OpexAI", "seed": 42, "date": "1970-01-01",
            "selection_kopcodes_total": 12, "selection_kopcodes_samples": 2,
            "observed_opcodes_total": 15000,
            "observed_opcode_components": {
                "selection": {"opcodes": 12000},
                "road_build": {"opcodes": 3000},
            },
        },
        {
            "arm": "OpexAI", "seed": 42, "date": "1970-02-01",
            "selection_kopcodes_total": 20, "selection_kopcodes_samples": 3,
            "observed_opcodes_total": 26000,
            "observed_opcode_components": {
                "selection": {"opcodes": 20000},
                "road_build": {"opcodes": 6000},
            },
        },
        {
            "arm": "AAAHogEx", "seed": 42, "date": "1970-02-01",
            "selection_kopcodes_total": None, "selection_kopcodes_samples": None,
            "observed_opcodes_total": None, "observed_opcode_components": None,
        },
    ]
    attach_selection_opcode_deltas(opcode_rows)
    assert opcode_rows[0]["selection_kopcodes_month"] == 12
    assert opcode_rows[0]["selection_kopcodes_samples_month"] == 2
    assert opcode_rows[1]["selection_kopcodes_month"] == 8
    assert opcode_rows[1]["selection_kopcodes_samples_month"] == 1
    assert opcode_rows[1]["selection_opcode_state"] == "available"
    assert opcode_rows[0]["observed_opcodes_month"] == 15000
    assert opcode_rows[1]["observed_opcodes_month"] == 11000
    assert opcode_rows[1]["observed_opcode_components_month"]["selection"] == 8000
    assert opcode_rows[1]["observed_opcode_components_month"]["road_build"] == 3000
    assert opcode_rows[1]["observed_opcode_state"] == "available"
    assert opcode_rows[2].get("selection_kopcodes_month") is None

    missing = extract_company({"PLYR": {}, "VEHS": None, "STNN": None}, 1, "AAAHogEx", 42, "1970-02-01")
    assert missing["economy_ok"] is False
    assert missing["company_value"] is None
    assert missing["delivered_cargo"] is None
    assert missing["vehicles"]["chunk_valid"] is False
    assert missing["stations"]["chunk_valid"] is False

    funnel_log = (
        "[script:4] [0] [I] OPEX 1971-3-8 MONTHLY_FUNNEL considered=40 accepted=8 funded=2 "
        "attempted=3 built=1 r_insufficient_cash=1 r_build_failed=1 "
        "r_build_failed_air_BFAIL=1 r_build_error_air_7=1\n"
        "[script:4] [0] [I] OPEX 1971-3-20 MONTHLY_FUNNEL considered=30 accepted=6 funded=1 "
        "attempted=1 built=0 r_town_rating_refusal=1\n"
        "[script:4] [1] [I] 1971-3-9 # RouteBuilder Succeeded foo\n"
        "[script:4] [1] [I] 1971-3-10 HgStation.BuildExec failed AirStation\n"
        "[script:4] [1] [I] 1971-3-11 #### TryBuild\n"
        "[script:4] [0] [I] OPEX 1971-3-12 C78_SLOT phase=project_candidate pass=9 cycle=9 tick=300 "
        "townA=34 townB=52 rank=3 affordable=1 profit=42000 finance=120000 roi=350 score=12 age_days=8 src=100 dst=200\n"
    )
    funnel = parse_opex_funnel(funnel_log)
    mar = funnel["1971-03"]
    assert mar["passes"] == 2
    assert mar["considered"] == 35  # stock moyen par passe: (40 + 30) / 2
    assert mar["accepted"] == 7      # stock moyen par passe: (8 + 6) / 2
    assert mar["funded"] == 3
    assert mar["attempted"] == 4
    assert mar["built"] == 1
    assert mar["rejects"]["insufficient_cash"] == 1
    assert mar["rejects"]["build_failed"] == 1
    assert mar["rejects"]["build_failed_air_BFAIL"] == 1
    assert mar["rejects"]["build_error_air_7"] == 1
    assert mar["rejects"]["town_rating_refusal"] == 1
    hog = parse_hogex_builds(funnel_log)
    assert hog["1971-03"]["succeeded"] == 1
    assert hog["1971-03"]["failed"] == 1
    assert hog["1971-03"]["try_build"] == 1
    slot_events = parse_c78_slot_events(funnel_log)
    assert len(slot_events["1971-03"]) == 1
    assert slot_events["1971-03"][0]["date"] == "1971-03-12"
    assert slot_events["1971-03"][0]["phase"] == "project_candidate"
    assert slot_events["1971-03"][0]["townA"] == 34
    assert slot_events["1971-03"][0]["affordable"] == 1
    assert slot_events["1971-03"][0]["pass"] == 9
    assert slot_events["1971-03"][0]["cycle"] == 9
    assert slot_events["1971-03"][0]["tick"] == 300

    # Corrélation C78 : premier aéroport AAA -> prochain passage projects -> candidat Opex.
    first_day = date(1971, 3, 10).toordinal() + 365
    second_day = date(1971, 8, 10).toordinal() + 365
    synthetic_rows = [
        {
            "seed": 42, "arm": "AAAHogEx", "date": "1971-08-31",
            "stations_by_town": {
                "34": {"count": 2, "stations": [
                    {"id": 91, "build_date": first_day, "facilities": ["airport"]},
                    {"id": 92, "build_date": second_day, "facilities": ["airport"]},
                ]}
            },
        },
        {
            "seed": 42, "arm": "OpexAI", "date": "1971-03-31",
            "stations_by_town": {},
            "c78_slot_events": [
                {"date": "1971-03-12", "phase": "project_candidate", "pass": 9, "cycle": 9, "tick": 300,
                 "townA": 34, "townB": 52, "rank": 3, "affordable": 1,
                 "profit": 42000, "finance": 120000, "src": 100, "dst": 200},
                {"date": "1971-03-12", "phase": "projects_pass", "pass": 9, "cycle": 9, "tick": 300,
                 "air_candidates": 4, "affordable": 2, "funded": 1},
                {"date": "1971-03-12", "phase": "air_attempt", "pass": 9, "cycle": 9, "tick": 301,
                 "townA": 34, "townB": 52, "rank": 3, "src": 100, "dst": 200,
                 "finance": 120000, "available": 150000, "built_before": 0},
                {"date": "1971-03-12", "phase": "air_outcome", "pass": 9, "cycle": 9, "tick": 302,
                 "townA": 34, "townB": 52, "rank": 3, "src": 100, "dst": 200,
                 "outcome": "rejected", "reason": "siteB_unbuildable", "detail": "", "error": 0},
                {"date": "1971-03-12", "phase": "projects_exit", "pass": 9, "cycle": 9, "tick": 303,
                 "built_count": 0, "stop": "none"},
                {"date": "1971-03-15", "phase": "build", "pass": 10, "cycle": 10, "tick": 330,
                 "built_count": 1},
            ],
        },
    ]
    slot_analysis = summarize_air_slot_intercept(synthetic_rows)
    assert slot_analysis["summary"]["second_airport_cases"] == 1
    opp = slot_analysis["opportunities"][0]
    assert opp["next_projects_delay_days"] == 2
    assert opp["candidate_count"] == 1
    assert opp["affordable_candidate_count"] == 1
    assert opp["funded_candidate_count"] == 1
    assert opp["funded_candidate_attempted_count"] == 1
    assert opp["funded_candidate_built_count"] == 0
    assert opp["funded_air_outcomes"][0]["reason"] == "siteB_unbuildable"
    assert slot_analysis["summary"]["funded_candidate_attempted_first_pass"] == 1
    assert slot_analysis["summary"]["funded_reject_reasons"] == {"siteB_unbuildable": 1}
    assert opp["next_build_delay_days"] == 5
    assert opp["next_projects_before_second"] is True

    # Test du funnel détaillé
    funnel_detailed_log = (
        "[script:4] [0] [I] OPEX 1971-3-8 MONTHLY_FUNNEL considered=40 accepted=8 funded=2 "
        "attempted=3 built=1 r_insufficient_cash=1 r_build_failed=1\n"
        "[script:4] [0] [I] OPEX 1971-3-8 MONTHLY_FUNNEL_DETAIL mode=rail considered=20 accepted=4 funded=1 "
        "attempted=2 built=1 r_insufficient_cash=1\n"
        "[script:4] [0] [I] OPEX 1971-3-8 MONTHLY_FUNNEL_DETAIL mode=road considered=10 accepted=2 funded=0 "
        "attempted=1 built=0 r_build_failed=1\n"
        "[script:4] [0] [I] OPEX 1971-3-20 MONTHLY_FUNNEL_DETAIL mode=rail considered=15 accepted=3 funded=1 "
        "attempted=1 built=0 r_town_rating_refusal=1\n"
    )
    funnel_detailed = parse_opex_funnel_detailed(funnel_detailed_log)
    mar_rail = funnel_detailed["1971-03"]["rail"]
    assert mar_rail["considered"] == 17.5  # stock moyen: (20 + 15) / 2
    assert mar_rail["accepted"] == 3.5      # stock moyen: (4 + 3) / 2
    assert mar_rail["funded"] == 2       # 1 + 1
    assert mar_rail["attempted"] == 3    # 2 + 1
    assert mar_rail["built"] == 1        # 1 + 0
    assert mar_rail["rejects"]["insufficient_cash"] == 1
    assert mar_rail["rejects"]["town_rating_refusal"] == 1

    mar_road = funnel_detailed["1971-03"]["road"]
    assert mar_road["considered"] == 10
    assert mar_road["accepted"] == 2
    assert mar_road["funded"] == 0
    assert mar_road["attempted"] == 1
    assert mar_road["built"] == 0
    assert mar_road["failed"] == 0  # Pas de champ failed dans l'exemple, mais on teste la structure
    assert mar_road["rejects"]["build_failed"] == 1

    hog = parse_hogex_builds(funnel_log)
    assert hog["1971-03"]["succeeded"] == 1
    assert hog["1971-03"]["failed"] == 1
    assert hog["1971-03"]["try_build"] == 1

    attached = [
        {"arm": "OpexAI", "owner": 0, "seed": 42, "date": "1971-03-01",
         "output": funnel_log,
         "vehicles": {"chunk_valid": True, "by_mode": {"rail": 1, "road": 2, "air": 1, "water": 0},
                      "rolling_capital": 1, "profit_per_vehicle": 1},
         "stations": {"chunk_valid": True, "n_stations": 4, "cargo_waiting": 10, "rating_median": 80},
         "company_value": 1000, "income": 100, "expenses": -20, "profit": 80, "delivered_cargo": 50},
        {"arm": "AAAHogEx", "owner": 1, "seed": 42, "date": "1971-03-01",
         "vehicles": {"chunk_valid": True, "by_mode": {"rail": 2, "road": 1, "air": 4, "water": 0},
                      "rolling_capital": 2, "profit_per_vehicle": 3},
         "stations": {"chunk_valid": True, "n_stations": 6, "cargo_waiting": 20, "rating_median": 90},
         "company_value": 2000, "income": 200, "expenses": -40, "profit": 160, "delivered_cargo": 80},
    ]
    attach_logs(attached)
    assert "output" not in attached[0]
    assert attached[0]["funnel"]["built"] == 1
    assert attached[1]["hogex_builds"]["succeeded"] == 1
    shared_cells = monthly_aggregates(attached, expected_seeds=[42], expected_months=["1971-03"])
    opex_cell = next(cell for cell in shared_cells if cell["arm"] == "OpexAI")
    hog_cell = next(cell for cell in shared_cells if cell["arm"] == "AAAHogEx")
    assert opex_cell["ok"] is True
    assert opex_cell["company_value"] == 1000
    assert opex_cell["funnel"]["attempted"] == 4
    assert hog_cell["hogex_builds"]["failed"] == 1
    assert hog_cell["n_stations"] == 6

    if fixture_path.exists():
        rec0 = extract_company(c66["chunks"], 0, "OpexAI", 42, "1970-12-01")
        rec1 = extract_company(c66["chunks"], 1, "AAAHogEx", 42, "1970-12-01")
        assert rec0["economy_ok"] is True
        assert rec0["vehicles"]["chunk_valid"] is True
        assert rec0["stations"]["n_stations"] == 24
        assert rec0["delivered_cargo"] is not None
        assert rec1["vehicles"]["chunk_valid"] is True
        assert rec1["vehicles"]["n_units"] == 0
        assert rec1["stations"]["n_stations"] == 0

    keep_shared = keep({
        "chunks": {"PLYR": {}, "VEHS": None, "STNN": None},
        "date": "1970-02-01",
        "output": "",
        "experiment": {"seed": 7, "shared": True},
    })
    assert len(keep_shared) == 2
    assert keep_shared[0]["arm"] == "OpexAI" and keep_shared[0]["owner"] == 0
    assert keep_shared[1]["arm"] == "AAAHogEx" and keep_shared[1]["owner"] == 1

    print("Test d'affichage du rapport mensuel avec lignes corrompues :")
    render_monthly_report(mock_rows, expected_seeds=[42, 100])
    print("Selftest diag_1v1_shared_monthly.py réussi avec succès !")


if __name__ == "__main__":
    main()
