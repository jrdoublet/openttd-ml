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
from physical_counters import decode_vehicles, decode_stations, VEHICLE_MODES

try:
    from bench_v2 import make_cfg, quarter_profit, year_profit
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
    """Âge les lignes MONTHLY_FUNNEL par mois calendaire (somme des passes)."""
    by_month = defaultdict(lambda: {
        "considered": 0, "accepted": 0, "funded": 0, "attempted": 0, "built": 0,
        "passes": 0, "rejects": Counter(), "considered_known": 0,
    })
    for line in (output or "").splitlines():
        sm = SCRIPT_RE.search(line)
        if not sm or int(sm.group(1)) != 0:  # Seulement OpexAI (joueur 0)
            continue
        om = OPEX_RE.match(sm.group(2).strip())
        if not om or om.group(4) != "MONTHLY_FUNNEL":
            continue
        year, month = int(om.group(1)), int(om.group(2))
        fields = parse_fields(om.group(5))
        slot = by_month[f"{year:04d}-{month:02d}"]
        slot["passes"] += 1
        considered = int(fields.get("considered", -1) or -1)
        if considered >= 0:
            slot["considered"] += considered
            slot["considered_known"] += 1
        for name in ("accepted", "funded", "attempted", "built"):
            slot[name] += int(fields.get(name, 0) or 0)
        for key, value in fields.items():
            if key.startswith("r_"):
                slot["rejects"][key[2:]] += int(value or 0)
    return {
        month: {
            "considered": slot["considered"] if slot["considered_known"] else None,
            "accepted": slot["accepted"],
            "funded": slot["funded"],
            "attempted": slot["attempted"],
            "built": slot["built"],
            "passes": slot["passes"],
            "rejects": dict(slot["rejects"]),
        }
        for month, slot in by_month.items()
    }


def parse_opex_funnel_detailed(output):
    """Âge les lignes MONTHLY_FUNNEL avec suivi détaillé par mode et année.
    Extrait les compteurs d'instrumentation OpexAI lorsqu'ils sont activés.
    """
    # Structure: {year-month: {mode: {considered, accepted, funded, attempted, built, failed, ...}}}
    by_month_mode = {}

    for line in (output or "").splitlines():
        sm = SCRIPT_RE.search(line)
        if not sm or int(sm.group(1)) != 0:  # Seulement OpexAI (joueur 0)
            continue
        om = OPEX_RE.match(sm.group(2).strip())
        if not om:
            continue
        # Nous traitons uniquement les lignes MONTHLY_FUNNEL_DETAIL pour ce parseur détaillé
        if om.group(4) != "MONTHLY_FUNNEL_DETAIL":
            continue

        year, month = int(om.group(1)), int(om.group(2))
        year_month = f"{year:04d}-{month:02d}"
        fields = parse_fields(om.group(5))

        # Initialiser la structure pour ce mois si nécessaire
        if year_month not in by_month_mode:
            by_month_mode[year_month] = {}

        mode = fields.get("mode", "unknown")
        if mode not in by_month_mode[year_month]:
            by_month_mode[year_month][mode] = {
                "considered": 0, "accepted": 0, "funded": 0, "attempted": 0, "built": 0,
                "failed": 0, "rejects": Counter()
            }
        slot = by_month_mode[year_month][mode]

        # Compteurs de base
        considered = int(fields.get("considered", 0) or 0)
        accepted = int(fields.get("accepted", 0) or 0)
        funded = int(fields.get("funded", 0) or 0)
        attempted = int(fields.get("attempted", 0) or 0)
        built = int(fields.get("built", 0) or 0)
        failed = int(fields.get("failed", 0) or 0)

        slot["considered"] += considered
        slot["accepted"] += accepted
        slot["funded"] += funded
        slot["attempted"] += attempted
        slot["built"] += built
        slot["failed"] += failed

        # Compteurs d'échec par raison
        for key, value in fields.items():
            if key.startswith("r_"):
                slot["rejects"][key[2:]] += int(value or 0)

    # Convertir en structure finale
    result = {}
    for year_month, modes_dict in by_month_mode.items():
        result[year_month] = {}
        for mode, slot in modes_dict.items():
            # Construire le dictionnaire de résultat pour ce mode
            mode_result = {}
            considered_val = slot["considered"]
            accepted_val = slot["accepted"]
            funded_val = slot["funded"]
            attempted_val = slot["attempted"]
            built_val = slot["built"]
            failed_val = slot["failed"]

            # Inclure les compteurs de base même s'ils sont zéro (pour permettre les tests)
            # Mais ne pas inclure les modes qui n'ont absolument aucune activité
            mode_result["considered"] = considered_val
            mode_result["accepted"] = accepted_val
            mode_result["funded"] = funded_val
            mode_result["attempted"] = attempted_val
            mode_result["built"] = built_val
            mode_result["failed"] = failed_val

            # Toujours inclure les rejects s'il y en a
            if slot["rejects"]:
                mode_result["rejects"] = dict(slot["rejects"])

            # Vérifier si ce mode a une activité significative
            # Une activité significative signifie: au moins un compteur > 0 OU des rejects
            has_activity = (
                considered_val > 0 or
                accepted_val > 0 or
                funded_val > 0 or
                attempted_val > 0 or
                built_val > 0 or
                failed_val > 0 or
                bool(slot["rejects"])
            )

            # Ajouter le mode au résultat seulement s'il contient des données significatives
            if has_activity:
                result[year_month][mode] = mode_result

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


def attach_logs(rows):
    """Le journal complet n'est fiable que sur la derniere ligne de chaque graine."""
    last_output = {}
    for record in rows:
        if record.get("arm") == "OpexAI" and record.get("output"):
            last_output[record["seed"]] = record["output"]
    funnel_by_seed = {seed: parse_opex_funnel(output) for seed, output in last_output.items()}
    funnel_detailed_by_seed = {seed: parse_opex_funnel_detailed(output) for seed, output in last_output.items()}
    hogex_by_seed = {seed: parse_hogex_builds(output) for seed, output in last_output.items()}
    hogex_detailed_by_seed = {seed: parse_hogex_builds_detailed(output) for seed, output in last_output.items()}
    for record in rows:
        record.pop("output", None)
        month = str(record.get("date", ""))[:7]
        if record.get("arm") == "OpexAI":
            record["funnel"] = funnel_by_seed.get(record.get("seed"), {}).get(month)
            record["funnel_detailed"] = funnel_detailed_by_seed.get(record.get("seed"), {}).get(month)
        else:
            record["hogex_builds"] = hogex_by_seed.get(record.get("seed"), {}).get(month)
            record["hogex_builds_detailed"] = hogex_detailed_by_seed.get(record.get("seed"), {}).get(month)
    return funnel_by_seed, funnel_detailed_by_seed, hogex_by_seed, hogex_detailed_by_seed


def build_arms(seeds, years, shared=False, funnel=False):
    from openttdlab import local_folder
    hogex = local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ())
    if shared:
        opex_params = (("monthly_funnel", 1),) if funnel else ()
        opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", opex_params)
        return [
            {
                "seed": seed,
                "days": 365 * years,
                "openttd_config": CFG_SHARED,
                "ais": (opex, hogex),
                "shared": True,
                "diag_arm": "duel",
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
    parser.add_argument("--selftest", action="store_true",
                        help="Verifie le decodage physique et le rendu face aux chunks invalides")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    import openttdlab
    from openttdlab import bananas_ai_library, local_folder, run_experiments
    from bench_v2 import enable_savegame_cleanup, write_json_atomically

    shared = args.shared or args.funnel
    funnel = bool(args.funnel or shared)
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
        experiments=build_arms(seeds, args.years, shared=shared, funnel=funnel),
        max_workers=args.workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    funnel_by_seed, funnel_detailed_by_seed, hogex_by_seed, hogex_detailed_by_seed = attach_logs(rows)
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


def monthly_aggregates(rows, expected_seeds=None, expected_months=None, expected_arms=None):
    """Agrege un mois seulement si toutes les lignes attendues sont valides.

    Fail-closed : `expected_seeds` (args.seeds) est la liste des graines de la
    campagne, pas l'ensemble deduit des lignes recues. Une graine qui n'a
    produit aucune ligne reste donc attendue. `expected_months` ajoute les
    mois calendaires meme s'ils sont absents des checkpoints.
    """
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
                "by_mode": None,
                "n_stations": None,
                "cargo_waiting": None,
                "rating_median": None,
                "rolling_capital": None,
                "profit_per_vehicle": None,
                "company_value": None,
                "income": None,
                "expenses": None,
                "profit": None,
                "delivered_cargo": None,
                "funnel": None,
                "funnel_detailed": None,
                "hogex_builds": None,
                "hogex_builds_detailed": None,
            }
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
                waiting = [
                    record["stations"]["cargo_waiting"]
                    for record in month_rows
                    if record["stations"].get("cargo_waiting") is not None
                ]
                ratings = [
                    record["stations"]["rating_median"]
                    for record in month_rows
                    if record["stations"].get("rating_median") is not None
                ]
                company_values = [
                    record.get("company_value")
                    for record in month_rows
                    if record.get("company_value") is not None
                ]
                incomes = [
                    record.get("income")
                    for record in month_rows
                    if record.get("income") is not None
                ]
                expenses_list = [
                    record.get("expenses")
                    for record in month_rows
                    if record.get("expenses") is not None
                ]
                profits = [
                    record.get("profit_year")
                    for record in month_rows
                    if record.get("profit_year") is not None
                ]
                delivered_cargo_list = [
                    record.get("delivered_cargo")
                    for record in month_rows
                    if record.get("delivered_cargo") is not None
                ]
                cell["by_mode"] = mode_totals
                cell["n_stations"] = statistics.mean(stations) if stations else None
                cell["cargo_waiting"] = statistics.mean(waiting) if waiting else None
                cell["rating_median"] = statistics.mean(ratings) if ratings else None
                cell["profit_per_vehicle"] = statistics.mean(ppv) if ppv else None
                cell["company_value"] = statistics.mean(company_values) if company_values else None
                cell["income"] = statistics.mean(incomes) if incomes else None
                cell["expenses"] = statistics.mean(expenses_list) if expenses_list else None
                cell["profit"] = statistics.mean(profits) if profits else None
                cell["delivered_cargo"] = statistics.mean(delivered_cargo_list) if delivered_cargo_list else None
                if arm == "OpexAI":
                    funnels = [record.get("funnel") for record in month_rows if record.get("funnel")]
                    if funnels:
                        cell["funnel"] = {
                            key: sum(int((slot or {}).get(key, 0) or 0) for slot in funnels)
                            for key in ("considered", "accepted", "funded", "attempted", "built", "passes")
                        }
                        rejects = Counter()
                        for slot in funnels:
                            rejects.update((slot or {}).get("rejects") or {})
                        cell["funnel"]["rejects"] = dict(rejects)

                    funnels_detailed = [record.get("funnel_detailed") for record in month_rows if record.get("funnel_detailed")]
                    if funnels_detailed:
                        # Agréger les données détaillées par mode et année
                        detailed_agg = defaultdict(lambda: defaultdict(lambda: {
                            "considered": 0, "accepted": 0, "funded": 0, "attempted": 0, "built": 0, "failed": 0,
                            "rejects": Counter()
                        }))
                        for funnel_dict in funnels_detailed:
                            for year_month, modes_dict in funnel_dict.items():
                                for mode, slot in modes_dict.items():
                                    if slot:  # Ignorer les entrées vides
                                        agg_slot = detailed_agg[year_month][mode]
                                        for key in ("considered", "accepted", "funded", "attempted", "built", "failed"):
                                            if slot.get(key) is not None:
                                                agg_slot[key] += slot[key]
                                        for reason, count in (slot.get("rejects") or {}).items():
                                            agg_slot["rejects"][reason] += count

                        # Convertir en structure finale
                        cell["funnel_detailed"] = {}
                        for year_month, modes_dict in detailed_agg.items():
                            cell["funnel_detailed"][year_month] = {}
                            for mode, slot in modes_dict.items():
                                if any(v > 0 for v in slot.values() if isinstance(v, int)) or slot["rejects"]:
                                    cell["funnel_detailed"][year_month][mode] = {
                                        "considered": slot["considered"] if slot["considered"] > 0 else None,
                                        "accepted": slot["accepted"] if slot["accepted"] > 0 else None,
                                        "funded": slot["funded"] if slot["funded"] > 0 else None,
                                        "attempted": slot["attempted"] if slot["attempted"] > 0 else None,
                                        "built": slot["built"] if slot["built"] > 0 else None,
                                        "failed": slot["failed"] if slot["failed"] > 0 else None,
                                        "rejects": dict(slot["rejects"]) if slot["rejects"] else None,
                                    }
                else:
                    builds = [record.get("hogex_builds") for record in month_rows if record.get("hogex_builds")]
                    if builds:
                        cell["hogex_builds"] = {
                            key: sum(int((slot or {}).get(key, 0) or 0) for slot in builds)
                            for key in ("succeeded", "failed", "try_build")
                        }

                    builds_detailed = [record.get("hogex_builds_detailed") for record in month_rows if record.get("hogex_builds_detailed")]
                    if builds_detailed:
                        # Pour l'instant, on garde la même structure que les builds normaux
                        # car AAAHogEx n'a pas de tunnel détaillé
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
            mix = "/".join(f"{cell['by_mode'][mode]:.0f}" for mode in VEHICLE_MODES)
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
            mix = "/".join(str(int(fn.get(k) or 0)) for k in
                           ("considered", "accepted", "funded", "attempted", "built"))
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

    missing = extract_company({"PLYR": {}, "VEHS": None, "STNN": None}, 1, "AAAHogEx", 42, "1970-02-01")
    assert missing["economy_ok"] is False
    assert missing["company_value"] is None
    assert missing["delivered_cargo"] is None
    assert missing["vehicles"]["chunk_valid"] is False
    assert missing["stations"]["chunk_valid"] is False

    funnel_log = (
        "[script:4] [0] [I] OPEX 1971-3-8 MONTHLY_FUNNEL considered=40 accepted=8 funded=2 "
        "attempted=3 built=1 r_insufficient_cash=1 r_build_failed=1\n"
        "[script:4] [0] [I] OPEX 1971-3-20 MONTHLY_FUNNEL considered=30 accepted=6 funded=1 "
        "attempted=1 built=0 r_town_rating_refusal=1\n"
        "[script:4] [1] [I] 1971-3-9 # RouteBuilder Succeeded foo\n"
        "[script:4] [1] [I] 1971-3-10 HgStation.BuildExec failed AirStation\n"
        "[script:4] [1] [I] 1971-3-11 #### TryBuild\n"
    )
    funnel = parse_opex_funnel(funnel_log)
    mar = funnel["1971-03"]
    assert mar["passes"] == 2
    assert mar["considered"] == 70
    assert mar["accepted"] == 14
    assert mar["funded"] == 3
    assert mar["attempted"] == 4
    assert mar["built"] == 1
    assert mar["rejects"]["insufficient_cash"] == 1
    assert mar["rejects"]["build_failed"] == 1
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
    assert mar_rail["considered"] == 35  # 20 + 15
    assert mar_rail["accepted"] == 7     # 4 + 3
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