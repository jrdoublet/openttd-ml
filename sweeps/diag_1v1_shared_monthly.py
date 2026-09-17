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
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from physical_counters import decode_vehicles, decode_stations, VEHICLE_MODES, FACILITY_BITS

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


def parse_fields(rest):
    fields = {}
    for token in (rest or "").split():
        if "=" in token:
            key, _, value = token.partition("=")
            fields[key] = value
    return fields


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


def attach_logs(rows, funnel_requested=None):
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
    if funnel_requested is None:
        funnel_requested = any(funnel_by_seed.values()) or any(funnel_detailed_by_seed.values())

    for record in rows:
        record.pop("output", None)
        month = str(record.get("date", ""))[:7]
        seed = record.get("seed")
        if record.get("arm") == "OpexAI":
            funnel_map = funnel_by_seed.get(seed, {})
            detail_map = funnel_detailed_by_seed.get(seed, {})
            record["funnel"] = funnel_map.get(month)
            record["funnel_detailed"] = detail_map.get(month)
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
               town_station_detail=False, air_early_slot=False):
    from openttdlab import local_folder
    hogex = local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ())
    if shared:
        opex_params = []
        if funnel:
            opex_params.append(("monthly_funnel", 1))
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
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("air_fleet_probe", 1),))
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
    shared = args.shared or args.funnel or args.air_town_limit_memory or args.town_station_detail or args.air_early_slot
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
                               town_station_detail=args.town_station_detail,
                               air_early_slot=args.air_early_slot),
        max_workers=args.workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    funnel_by_seed, funnel_detailed_by_seed, hogex_by_seed, hogex_detailed_by_seed = attach_logs(
        rows, funnel_requested=funnel
    )
    attach_opcode_deltas(rows)
    expected_months = expected_calendar_months(args.years)
    monthly = render_monthly_report(
        rows,
        expected_seeds=seeds,
        expected_months=expected_months,
    )
    finals = render_final_comparison(rows, seeds)

    payload = {
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": seeds,
        "shared_game": shared,
        "funnel": funnel,
        "funnel_explicitly_disabled": bool(args.no_funnel),
        "air_town_limit_memory": bool(args.air_town_limit_memory),
        "town_station_detail": bool(args.town_station_detail),
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
