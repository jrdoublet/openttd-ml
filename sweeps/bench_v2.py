"""Banc multi-graines de la campagne OpenTTDLab.

Chaque arm joue seule sur les memes graines et la meme configuration. La lecture decisive est la
comparaison appairee : pour une graine donnee, la difficulte de carte touche les deux arms. La
soustraire avant de calculer la moyenne retire donc une grande part de la dispersion inter-graines,
alors que la difference de deux moyennes independantes la conserve.

OpenTTD 15.3 obligatoire, et c'est la seule version possible :
  - AAAHogEx declare GetAPIVersion() = "14", donc il exige OpenTTD >= 14 ;
  - OpenTTDLab 0.0.75 (openttdlab.py:195-204) ne supporte que 12 <= major < 14 (mode autosave)
    et major >= 15 (mode console-script) -- la 14.x leve une exception.
Le binaire >= 15 exige libgomp1 et libglib2.0-0, ajoutes au Dockerfile.

Metrique : PLYR[0]["old_economy"][0] donne company_value, performance_history (score
officiel 0-1000), income et expenses du DERNIER TRIMESTRE CLOTURE. Profit = income + expenses
(expenses deja signe negatif en 15.3). profit_year somme jusqu'a 4 trimestres. Note de gare :
mediane STNN.goods.rating des cargos qui ont une note (status & 1, ramasses). cur_economy a
company_value = 0 : ne pas l'utiliser. max_loan est parse en -9223372036854775808 a cette
version : champ ininterpretable.
"""
import argparse
import functools
import inspect
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics

import openttdlab
from openttdlab import bananas_ai, bananas_ai_library, local_folder, run_experiments

from campaign_freeze import (
    effective_ai_settings,
    parse_ai_setting_specs,
    validate_policy_settings,
)
from physical_counters import decode_stations, decode_vehicles

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
TRAINS_MD5 = "c4c069dc797674e545411b59867ad0c2"  # identique aux scripts phase0
YEARS = 20
SEEDS = (
    42, 100, 7, 999, 2026,
    1, 17, 73, 314, 512, 1024, 1337, 4096, 8191, 12345,
    54321, 65537, 123456, 424242, 8675309,
)
MAX_WORKERS = 3
DEFAULT_ARMS = ("OpexAI", "AAAHogEx", "AdmiralAI", "trAIns")

def make_cfg(starting_year=1970, map_size=8):
    return f"""[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = {starting_year}
map_x = {map_size}
map_y = {map_size}
"""

CFG = make_cfg(1970)

# keep() est execute dans les workers. La valeur est fixee avant la creation du Pool, puis heritee
# par fork : ainsi chaque sauvegarde est durable avant que run_experiments() ne rende sa liste.
CHECKPOINT_PATH = None

# Indicateurs de succes du banc : valeur, score officiel, profit, note de gare.
# performance_history n'est NI le profit NI la note de gare (docs/mecanique_jeu.md Â§6).
SUCCESS_METRICS = (
    "company_value",
    "performance_history",
    "profit",
    "profit_year",
    "median_station_rating",
    "primary_vehicles",
)

# Mesures diagnostiques H5. Ce ne sont PAS des métriques de succès globales :
# elles couvrent seulement les blocs déjà instrumentés/publies par OpexAI.
OBSERVED_OPCODE_METRICS = (
    "observed_opcodes_total",
    "final_profit_year_per_observed_mopcode",
    "company_value_per_observed_mopcode",
)

SCRIPT_FAILURE_MARKERS = (
    "Your script made an error",
    "The script died unexpectedly",
)


def script_failure_reason(output):
    """Retourne le marqueur fatal NoAI trouve dans stdout, sinon None."""
    output = output or ""
    for marker in SCRIPT_FAILURE_MARKERS:
        if marker in output:
            return marker


def parse_opex_variant(name):
    """Retourne les parametres d'une variante OpexAI explicitee sur la ligne de commande."""
    match = re.fullmatch(r"OpexAI\[(.*)\]", name)
    if not match:
        return None
    text = match.group(1)
    if not text:
        raise ValueError("une variante OpexAI doit declarer au moins un reglage")
    setting_specs = parse_ai_setting_specs(ROOT / "ai" / "OpexAI" / "info.nut")
    params = []
    seen = set()
    for assignment in text.split(","):
        if "=" not in assignment:
            raise ValueError(f"reglage OpexAI invalide: {assignment}")
        key, raw_value = assignment.split("=", 1)
        if key in seen:
            raise ValueError(f"reglage OpexAI duplique: {key}")
        seen.add(key)
        try:
            value = int(raw_value)
        except ValueError as error:
            raise ValueError(f"valeur OpexAI invalide: {assignment}") from error
        if key == "debug_signs":
            # Les AISign sont la seule instrumentation recuperee par OpenTTDLab.
            if value != 1:
                raise ValueError("debug_signs doit rester a 1")
        elif key == "pathfinder_sleep_ticks":
            if not 0 <= value <= 10:
                raise ValueError("pathfinder_sleep_ticks doit etre entre 0 et 10")
        elif key == "loan_repay_floor_k":
            # Bornes et pas repris de ai/OpexAI/info.nut : une valeur hors pas serait acceptee par
            # argparse puis silencieusement arrondie par le moteur, et le nom de l'arm mentirait
            # alors sur ce qui a tourne.
            if not 0 <= value <= 2000:
                raise ValueError("loan_repay_floor_k doit etre entre 0 et 2000")
            if value % 50:
                raise ValueError("loan_repay_floor_k doit etre un multiple de 50 (step_size)")
        elif key == "pathfinder_hard_cap_k":
            # Memes bornes et meme pas que ai/OpexAI/info.nut, pour la raison ci-dessus.
            if not 5 <= value <= 100:
                raise ValueError("pathfinder_hard_cap_k doit etre entre 5 et 100")
            if value % 5:
                raise ValueError("pathfinder_hard_cap_k doit etre un multiple de 5 (step_size)")
        elif key == "road_pax_catchment_pct":
            # 0 garde le calibrage historique a 22 %. Une valeur positive est une sonde route
            # uniquement (info.nut) ; 86 = 22 * le ratio median reel/predit 3,91.
            if not 0 <= value <= 100:
                raise ValueError("road_pax_catchment_pct doit etre entre 0 et 100")
        elif key == "project_top_k":
            # Memes bornes que ai/OpexAI/info.nut : docs/taches.md C43/E3, sature a 70-77% des
            # appels de selection au defaut 64 (mesure du 2026-09-08).
            if not 8 <= value <= 128:
                raise ValueError("project_top_k doit etre entre 8 et 128")
            if value % 8:
                raise ValueError("project_top_k doit etre un multiple de 8 (step_size)")
        elif key == "air_fleet_cadence_days":
            if not 0 <= value <= 365:
                raise ValueError("air_fleet_cadence_days doit etre entre 0 et 365")
        elif key == "abandon_cooldown_days":
            if not 0 <= value <= 5000:
                raise ValueError("abandon_cooldown_days doit etre entre 0 et 5000")
        elif key == "unprofitable_streak_threshold":
            if not 1 <= value <= 10:
                raise ValueError("unprofitable_streak_threshold doit etre entre 1 et 10")
        elif key == "air_joined_stop_limit":
            if not 0 <= value <= 2:
                raise ValueError("air_joined_stop_limit doit etre entre 0 et 2")
        elif key == "air_early_slot_target_towns":
            if not 1 <= value <= 16:
                raise ValueError("air_early_slot_target_towns doit etre entre 1 et 16")
        elif key == "air_early_slot_min_pop":
            if not 0 <= value <= 10000 or value % 100:
                raise ValueError("air_early_slot_min_pop doit etre entre 0 et 10000 par pas de 100")
        elif key == "air_early_slot_bonus_pct":
            if not 0 <= value <= 200 or value % 10:
                raise ValueError("air_early_slot_bonus_pct doit etre entre 0 et 200 par pas de 10")
        else:
            spec = setting_specs.get(key)
            if spec is None:
                raise ValueError(f"reglage OpexAI inconnu: {key}")
            if spec["boolean"]:
                if value not in (0, 1):
                    raise ValueError(f"{key} est booleen : 0 ou 1")
            else:
                minimum = spec["min_value"]
                maximum = spec["max_value"]
                step = spec["step_size"]
                if minimum is not None and value < minimum:
                    raise ValueError(f"{key} doit etre >= {minimum}")
                if maximum is not None and value > maximum:
                    raise ValueError(f"{key} doit etre <= {maximum}")
                if step is not None and step > 0:
                    base = minimum if minimum is not None else 0
                    if (value - base) % step:
                        raise ValueError(f"{key} doit respecter un pas de {step} depuis {base}")
        params.append((key, value))
    return tuple(params)


def resolve_opex_arm_settings(name):
    """Resout et epingle tous les reglages OpexAI contre les defauts de info.nut."""
    explicit = parse_opex_variant(name)
    if name != "OpexAI" and explicit is None:
        return None
    return effective_ai_settings(ROOT / "ai" / "OpexAI" / "info.nut", explicit or ())


def resolved_arm_settings(names):
    """Metadonnees de reproductibilite : defauts, explicites et valeurs effectives."""
    resolved = {}
    for name in names:
        settings = resolve_opex_arm_settings(name)
        if settings is None:
            resolved[name] = {"ai": name, "settings": None}
            continue
        defaults = settings["defaults"]
        explicit = settings["explicit"]
        resolved[name] = {
            "ai": "OpexAI",
            "settings": settings,
            "explicit_nondefault": {
                key: value for key, value in explicit.items()
                if defaults.get(key) != value
            },
        }
    return resolved


def comparison_setting_audit(resolved):
    """Detecte un socle hors-defaut partage qui rend un duel non transportable au defaut livre."""
    opex = {
        name: payload for name, payload in resolved.items()
        if payload.get("ai") == "OpexAI" and payload.get("settings")
    }
    shared = []
    pairwise = []
    identical = []
    names = sorted(opex)
    if len(names) >= 2:
        all_keys = set().union(*(set(opex[name]["explicit_nondefault"]) for name in names))
        for key in sorted(all_keys):
            carriers = [
                name for name in names
                if key in opex[name]["explicit_nondefault"]
            ]
            if len(carriers) < 2:
                continue
            values = {opex[name]["explicit_nondefault"][key] for name in carriers}
            if len(values) == 1:
                shared.append({
                    "setting": key,
                    "value": next(iter(values)),
                    "arms": carriers,
                })
        for index, left_name in enumerate(names):
            for right_name in names[index + 1:]:
                left = opex[left_name]["settings"]
                right = opex[right_name]["settings"]
                candidate_keys = set(left["explicit"]) | set(right["explicit"])
                announced = sorted(
                    key for key in candidate_keys
                    if left["effective"].get(key) != right["effective"].get(key)
                )
                differences = validate_policy_settings(
                    left["effective"],
                    right["effective"],
                    intervention_settings=announced,
                ) if announced else {}
                pairwise.append({
                    "arms": [left_name, right_name],
                    "announced_settings": announced,
                    "effective_differences": differences,
                })
                if not differences:
                    identical.append([left_name, right_name])
    return {
        "transportable_to_shipped_defaults": not shared,
        "shared_nondefault_explicit": shared,
        "pairwise_effective_differences": pairwise,
        "identical_effective_arms": identical,
    }


def build_arms(names):
    """Construit les arms demandes avec un snapshot explicite des defauts OpexAI."""
    arms = {}
    for name in names:
        if name in arms:
            raise ValueError(f"arm duplique: {name}")
        opex_settings = resolve_opex_arm_settings(name)
        if opex_settings is not None:
            # OpenTTD lit la ligne [ai_players] d'openttd.cfg dans un tampon de ~1 024 caracteres :
            # passer TOUTES les valeurs effectives (55 reglages, 1 168 caracteres le 2026-09-21)
            # faisait ignorer en silence les reglages de fin d'ordre alphabetique (mesure :
            # town_growth=0 lu 1). On ne passe que les ecarts au defaut, comme le harnais C66 ;
            # l'instantane complet reste dans les metadonnees (effective).
            defaults = opex_settings["defaults"]
            params = tuple(
                (key, value) for key, value in opex_settings["effective"].items()
                if defaults.get(key) != value
            )
            arms[name] = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", params)
        elif name == "trAIns":
            arms[name] = bananas_ai("54524149", "trAIns", ai_params=(), md5=TRAINS_MD5)
        elif name == "AdmiralAI":
            arms[name] = local_folder(str(ROOT / "ai" / "AdmiralAI"), "AdmiralAI", ())
        elif name == "AAAHogEx":
            arms[name] = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
        else:
            raise ValueError(f"arm inconnu: {name}")
    return arms


def arm_notes():
    """Conserve pres des declarations les deux corrections locales necessaires a AdmiralAI."""
    # Les trois adversaires sont hors depot (.gitignore) : on les execute, sans lire ni copier leur
    # code dans notre IA. Deux reparations ont ete necessaires cote AdmiralAI, toutes deux dans
    # notre copie locale :
    #   - `version.nut` manquait (fichier genere par son Makefile via `hg id`, donc jamais clone) ;
    #     sans lui `info.nut` ne compile pas et AUCUNE compagnie n'est creee -- l'echec est
    #     silencieux dans les chunks, il ne se voit que dans `row["output"]`.
    #   - il importe `queue.fibonacci_heap` version 2, or BaNaNaS ne publie plus que la 3 ;
    #     l'import a ete passe a 3 dans notre copie.
    return None


def append_checkpoint(record):
    """Ajoute une ligne complete sans reecrire le checkpoint partage par les workers."""
    if CHECKPOINT_PATH is None:
        raise RuntimeError("checkpoint non configure")
    encoded = (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
    # O_APPEND evite que deux workers ecrivent au meme offset. Une ligne est petite et ecrite en
    # un appel : un crash laisse au pire sa derniere ligne incomplete, qu'une relecture ligne a ligne ignore.
    fd = os.open(CHECKPOINT_PATH, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, encoded)
    finally:
        os.close(fd)


def _first(value):
    """STNN encode parfois une liste a un element, parfois un objet unique."""
    if value is None:
        return None
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, dict):
        if "xy" in value or "goods" in value or "base" in value:
            return value
        return next(iter(value.values()), None)
    return value


def quarter_profit(entry):
    """Profit d'un trimestre clos. expenses est negatif dans OpenTTD 15.3."""
    if not entry:
        return None
    income = entry.get("income")
    expenses = entry.get("expenses")
    if income is None or expenses is None:
        return None
    if expenses <= 0:
        return income + expenses
    return income - expenses


def year_profit(closed):
    """Somme des (jusqu'a) quatre derniers trimestres clos."""
    profits = [quarter_profit(entry) for entry in (closed or [])[:4]]
    profits = [value for value in profits if value is not None]
    if not profits:
        return None
    return sum(profits)


def station_ratings(chunks, owner=0):
    """Notes 0-255 des cargos deja ramasses, gares de la compagnie."""
    ratings = []
    stations = chunks.get("STNN") or {}
    for station in stations.values():
        body = _first(station.get("normal") if isinstance(station, dict) else None)
        if body is None and isinstance(station, dict):
            body = station
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if isinstance(base, dict) and base.get("owner", owner) != owner:
            continue
        for good in body.get("goods") or []:
            if not isinstance(good, dict):
                continue
            if (good.get("status") or 0) & 1 == 0:
                continue
            if good.get("time_since_pickup", 255) >= 255:
                continue
            rating = good.get("rating")
            if rating is None:
                continue
            ratings.append(int(rating))
    return ratings


def portfolio_selection_opcode_stats(chunks):
    """Lit le cout de selection publie par les panneaux IG|, en milliers d'opcodes.

    Les anciens IG| ont sept champs et restent valides : ils ne contribuent simplement
    pas a cette mesure. Le huitieme champ est volontairement en k-opcodes afin de tenir
    sous la limite de 31 caracteres d'AISign sans ajouter un nouveau panneau.
    """
    values = []
    signs = (chunks or {}).get("SIGN") or {}
    records = signs.values() if isinstance(signs, dict) else signs
    for sign in records:
        if not isinstance(sign, dict):
            continue
        name = str(sign.get("name", ""))
        if not name.startswith("IG|"):
            continue
        parts = name.split("|")
        if len(parts) < 8:
            continue
        try:
            value = int(parts[7])
        except (TypeError, ValueError):
            continue
        if value >= 0:
            values.append(value)
    return {
        "selection_kopcodes_samples": len(values),
        "selection_kopcodes_total": sum(values) if values else None,
        "selection_kopcodes_mean": (
            number(statistics.mean(values)) if values else None
        ),
        "selection_kopcodes_max": max(values) if values else None,
    }


def observed_opcode_stats(chunks):
    """Somme les coûts d'opcodes réellement publiés, sans les appeler coût CPU total.

    Périmètre non chevauchant connu :
      - IG|   : sélection du portefeuille (champ H5 en milliers d'opcodes) ;
      - OB|A  : tentative rail, planification + construction mesurées par OpexBudget ;
      - RB|   : planification route + construction route, deux mesures distinctes ;
      - OA|   : planification air seulement (le build n'est pas publié dans ce panneau) ;
      - OM|W  : planification eau seulement, et seulement pour les constructions réussies.

    Les anciens formats restent acceptés : un IG sans huitième champ est simplement exclu
    de la composante sélection ; les autres panneaux gardent leur schéma historique.
    """
    components = {
        "selection": {"samples": 0, "opcodes": 0, "coverage": "IG| field 8; current builds"},
        "rail_attempt": {"samples": 0, "opcodes": 0, "coverage": "OB|A plan+build attempts"},
        "road_planning": {"samples": 0, "opcodes": 0, "coverage": "RB| planning on emitted attempts"},
        "road_build": {"samples": 0, "opcodes": 0, "coverage": "RB| build on emitted attempts"},
        "air_planning": {"samples": 0, "opcodes": 0, "coverage": "OA| planning only"},
        "water_planning": {"samples": 0, "opcodes": 0, "coverage": "OM|W planning; successful builds only"},
    }
    signs = (chunks or {}).get("SIGN") or {}
    records = signs.values() if isinstance(signs, dict) else signs

    def add(component, raw, multiplier=1):
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return
        if value < 0:
            return
        components[component]["samples"] += 1
        components[component]["opcodes"] += value * multiplier

    for sign in records:
        if not isinstance(sign, dict):
            continue
        name = str(sign.get("name", ""))
        parts = name.split("|")
        if name.startswith("IG|") and len(parts) >= 8:
            add("selection", parts[7], 1000)
        elif name.startswith("OB|A|") and len(parts) >= 7:
            add("rail_attempt", parts[5])
        elif name.startswith("RB|") and len(parts) >= 6:
            add("road_planning", parts[4])
            add("road_build", parts[5])
        elif name.startswith("OA|") and len(parts) >= 5:
            add("air_planning", parts[3])
        elif name.startswith("OM|W|") and len(parts) >= 5:
            add("water_planning", parts[4])

    total = sum(item["opcodes"] for item in components.values())
    samples = sum(item["samples"] for item in components.values())
    return {
        "observed_opcode_schema": "h5.observed-v1",
        "observed_opcodes_total": total,
        "observed_opcode_samples": samples,
        "observed_opcode_components": components,
        "observed_opcode_complete_cpu": False,
    }


def keep(row):
    """Une ligne par sauvegarde mensuelle, persistee immediatement pour survivre a un crash."""
    chunks = row["chunks"]
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    ratings = station_ratings(chunks)
    veh_dec = decode_vehicles(chunks.get("VEHS"), target_owner=0)
    stn_dec = decode_stations(chunks.get("STNN"), target_owner=0)
    selection_ops = portfolio_selection_opcode_stats(chunks)
    observed_ops = observed_opcode_stats(chunks)
    air_engine_counts = {}
    air_capacities_by_cargo = {}
    air_vehicle_book_value = 0
    if veh_dec["chunk_valid"]:
        for vehicle in veh_dec["primary_vehicles_detail"]:
            if vehicle.get("mode") != "air":
                continue
            engine_type = vehicle.get("engine_type")
            if engine_type is not None:
                engine = str(engine_type)
                air_engine_counts[engine] = air_engine_counts.get(engine, 0) + 1
            air_vehicle_book_value += int(vehicle.get("consist_value") or 0)
            for cargo, capacity in (vehicle.get("consist_capacities") or {}).items():
                key = str(cargo)
                air_capacities_by_cargo[key] = air_capacities_by_cargo.get(key, 0) + int(capacity)
    qualified_primary = None
    unqualified_primary = None
    if veh_dec["chunk_valid"]:
        qualified_primary = sum(
            veh_dec["primary_vehicles_by_mode"][mode]
            for mode, qualified in veh_dec["qualified_modes"].items()
            if qualified
        )
        unqualified_primary = sum(
            veh_dec["primary_vehicles_by_mode"][mode]
            for mode, qualified in veh_dec["qualified_modes"].items()
            if not qualified
        )
    record = {
        "run": row["experiment"]["bench_run"],
        "date": str(row["date"]),
        "company_value": last_closed.get("company_value"),
        "performance_history": last_closed.get("performance_history"),
        "income_last_year": last_closed.get("income"),
        "expenses_last_year": last_closed.get("expenses"),
        "profit": quarter_profit(last_closed),
        "profit_year": year_profit(closed),
        "median_station_rating": (statistics.median(ratings) if ratings else None),
        "n_station_ratings": len(ratings),
        "money": (player or {}).get("money"),
        "current_loan": (player or {}).get("current_loan"),
        "months_of_bankruptcy": (player or {}).get("months_of_bankruptcy"),
        "n_vehicles": veh_dec["primary_vehicles_count"] if veh_dec["chunk_valid"] else None,
        "n_stations": stn_dec["total_stations"] if stn_dec["chunk_valid"] else None,
        "physical_counters_version": veh_dec["schema_version"],
        "qualified_modes": veh_dec["qualified_modes"],
        "vehs_chunk_valid": veh_dec["chunk_valid"],
        "vehs_chunk_error": veh_dec["chunk_error"],
        "stnn_chunk_valid": stn_dec["chunk_valid"],
        "stnn_chunk_error": stn_dec["chunk_error"],
        "vehicle_pool_entries": veh_dec["vehicle_pool_entries"] if veh_dec["chunk_valid"] else None,
        "total_vehicle_pool_entries": veh_dec["total_pool_entries"] if veh_dec["chunk_valid"] else None,
        "primary_vehicles": veh_dec["primary_vehicles_count"] if veh_dec["chunk_valid"] else None,
        "qualified_primary_vehicles": qualified_primary,
        "unqualified_primary_vehicles": unqualified_primary,
        "primary_vehicles_by_mode": veh_dec["primary_vehicles_by_mode"] if veh_dec["chunk_valid"] else None,
        "air_primary_vehicles": (
            veh_dec["primary_vehicles_by_mode"].get("air", 0)
            if veh_dec["chunk_valid"] else None
        ),
        "air_airports": (
            stn_dec["stations_by_facility"].get("airport", 0)
            if stn_dec["chunk_valid"] else None
        ),
        "air_engine_counts": air_engine_counts if veh_dec["chunk_valid"] else None,
        "air_capacities_by_cargo": air_capacities_by_cargo if veh_dec["chunk_valid"] else None,
        "air_vehicle_book_value": air_vehicle_book_value if veh_dec["chunk_valid"] else None,
        "capacities_by_cargo": veh_dec["capacities_by_cargo"] if veh_dec["chunk_valid"] else None,
        "fleet_status": veh_dec["fleet_status"] if veh_dec["chunk_valid"] else None,
        "unclassified_vehicles": len(veh_dec["unclassified_entries"]),
        "n_multimodal_stations": stn_dec["n_multimodal_stations"] if stn_dec["chunk_valid"] else None,
        "stations_by_facility": stn_dec["stations_by_facility"] if stn_dec["chunk_valid"] else None,
        "unresolved_stations": len(stn_dec["unresolved_stations"]),
        **selection_ops,
        **observed_ops,
        # L'echec de chargement d'une IA est silencieux dans PLYR ; ce log reste donc disponible
        # dans le resume final pour le controle explicite de row["output"].
        "openttd_output": row.get("output"),
    }
    append_checkpoint(record)
    return (record,)


_ORIGINAL_RUN_EXPERIMENT = None
_RUN_EXPERIMENT_SIGNATURE = None


def _run_experiment_with_savegame_cleanup(*args, **kwargs):
    """Evite que les sauvegardes deja parsees occupent le disque jusqu'a la fin du lot."""
    bound = _RUN_EXPERIMENT_SIGNATURE.bind(*args, **kwargs)
    bound.apply_defaults()
    missing = {"run_dir", "i", "final_screenshot_directory"} - bound.arguments.keys()
    if missing:
        raise RuntimeError(f"OpenTTDLab _run_experiment signature no longer exposes: {missing}")
    # OpenTTDLab relit le dernier autosave pour une capture finale. Ce banc n'en demande pas :
    # refuser ce cas evite d'effacer une dependance amont en silence.
    assert bound.arguments["final_screenshot_directory"] is None, (
        "savegame cleanup requires final_screenshot_directory=None"
    )
    experiment_dir = os.path.join(bound.arguments["run_dir"], str(bound.arguments["i"]))
    try:
        return _ORIGINAL_RUN_EXPERIMENT(*args, **kwargs)
    finally:
        # Ne jamais effacer run_dir : il contient les binaires et OpenGFX partages par les essais.
        try:
            shutil.rmtree(experiment_dir, ignore_errors=True)
        except BaseException:
            pass


def enable_savegame_cleanup():
    """Pool pickle cette reference module : l'accroche doit etre posee avant sa soumission."""
    global _ORIGINAL_RUN_EXPERIMENT, _RUN_EXPERIMENT_SIGNATURE
    if openttdlab._run_experiment is _run_experiment_with_savegame_cleanup:
        return
    _ORIGINAL_RUN_EXPERIMENT = openttdlab._run_experiment
    _RUN_EXPERIMENT_SIGNATURE = inspect.signature(_ORIGINAL_RUN_EXPERIMENT)
    functools.update_wrapper(_run_experiment_with_savegame_cleanup, _ORIGINAL_RUN_EXPERIMENT)
    _run_experiment_with_savegame_cleanup.__signature__ = _RUN_EXPERIMENT_SIGNATURE
    openttdlab._run_experiment = _run_experiment_with_savegame_cleanup


def experiments(arms, seeds, years, repeats, starting_year=1970, map_size=8):
    """Une partie isolee par (arm, graine, repetition)."""
    cfg = make_cfg(starting_year, map_size)
    return [
        {
            "seed": seed,
            "days": 365 * years,
            "openttd_config": cfg,
            "ais": (arms[name],),
            "bench_run": [name, seed, repeat],
        }
        for name in arms
        for seed in seeds
        for repeat in range(repeats)
    ]


def saved_year(date):
    """Extrait l'annee d'un autosave OpenTTD, ou None pour un format inattendu."""
    match = re.match(r"(\d{4})-", str(date))
    return int(match.group(1)) if match else None


def summarise(rows, expected_last_year=None, expected_savegames=None):
    """Retient le dernier etat de chaque partie et signale une fin prematuree.

    Un script NoAI peut se figer sans que le moteur marque la partie en echec. Le
    dernier autosave reste alors ancien : c'est un echec de protocole, mais les
    donnees sont conservees pour le diagnostic et ne sont jamais retirees du banc.
    """
    by_run = {}
    for row in rows:
        key = tuple(row["run"])
        by_run.setdefault(key, []).append(row)
    summary = []
    for key, series in sorted(by_run.items(), key=lambda item: str(item[0])):
        series.sort(key=lambda row: row["date"])
        final = series[-1]
        last_year = saved_year(final["date"])
        failure_reason = script_failure_reason(final.get("openttd_output"))
        if failure_reason is None and expected_last_year is not None and (
            last_year is None or last_year < expected_last_year
        ):
            failure_reason = (
                "incomplete_run: last autosave year "
                f"{last_year if last_year is not None else 'unknown'} "
                f"< expected {expected_last_year}"
            )
        if failure_reason is None and expected_savegames is not None:
            expected_minimum = int(expected_savegames)
            month_ordinals = []
            for checkpoint in series:
                match = re.match(r"(\d{4})-(\d{2})-", str(checkpoint.get("date", "")))
                if match:
                    month_ordinals.append(int(match.group(1)) * 12 + int(match.group(2)) - 1)
            if len(series) < expected_minimum:
                failure_reason = (
                    f"incomplete_checkpoints: observed {len(series)} "
                    f"< minimum {expected_minimum}"
                )
            elif len(month_ordinals) != len(series) or any(
                current - previous != 1
                for previous, current in zip(month_ordinals, month_ordinals[1:])
            ):
                failure_reason = "incomplete_checkpoints: monthly checkpoint sequence is not contiguous"

        vehs_valid = final.get("vehs_chunk_valid")
        stnn_valid = final.get("stnn_chunk_valid")
        physical_ok = None
        if vehs_valid is not None or stnn_valid is not None:
            physical_ok = (vehs_valid is not False) and (stnn_valid is not False)
            if not physical_ok and failure_reason is None:
                v_err = final.get("vehs_chunk_error") or "invalid_vehs_chunk"
                s_err = final.get("stnn_chunk_error") or "invalid_stnn_chunk"
                err_msg = v_err if vehs_valid is False else s_err
                failure_reason = f"physical_decode_failure: {err_msg}"

        rec = {
            "arm": key[0], "seed": key[1], "repeat": key[2],
            "last_date": final["date"], "last_year": last_year,
            "expected_last_year": expected_last_year,
            "company_value": final["company_value"],
            "performance_history": final["performance_history"],
            "income_last_year": final["income_last_year"],
            "expenses_last_year": final.get("expenses_last_year"),
            "profit": final.get("profit"),
            "profit_year": final.get("profit_year"),
            "median_station_rating": final.get("median_station_rating"),
            "n_station_ratings": final.get("n_station_ratings"),
            "money": final["money"], "current_loan": final["current_loan"],
            "n_vehicles": final["n_vehicles"], "n_stations": final["n_stations"],
            "months_of_bankruptcy": final["months_of_bankruptcy"],
            "n_savegames": len(series),
            "selection_kopcodes_samples": final.get("selection_kopcodes_samples"),
            "selection_kopcodes_total": final.get("selection_kopcodes_total"),
            "selection_kopcodes_mean": final.get("selection_kopcodes_mean"),
            "selection_kopcodes_max": final.get("selection_kopcodes_max"),
            "observed_opcode_schema": final.get("observed_opcode_schema"),
            "observed_opcodes_total": final.get("observed_opcodes_total"),
            "observed_opcode_samples": final.get("observed_opcode_samples"),
            "observed_opcode_components": final.get("observed_opcode_components"),
            "observed_opcode_complete_cpu": final.get("observed_opcode_complete_cpu"),
            "openttd_output": final["openttd_output"],
            "run_ok": failure_reason is None,
            "failure_reason": failure_reason,
        }
        if physical_ok is not None:
            rec.update({
                "physical_counters_version": final.get("physical_counters_version"),
                "qualified_modes": final.get("qualified_modes"),
                "physical_ok": physical_ok,
                "vehs_chunk_valid": vehs_valid,
                "vehs_chunk_error": final.get("vehs_chunk_error"),
                "stnn_chunk_valid": stnn_valid,
                "stnn_chunk_error": final.get("stnn_chunk_error"),
                "vehicle_pool_entries": final.get("vehicle_pool_entries"),
                "total_vehicle_pool_entries": final.get("total_vehicle_pool_entries"),
                "primary_vehicles": final.get("primary_vehicles"),
                "qualified_primary_vehicles": final.get("qualified_primary_vehicles"),
                "unqualified_primary_vehicles": final.get("unqualified_primary_vehicles"),
                "primary_vehicles_by_mode": final.get("primary_vehicles_by_mode"),
                "capacities_by_cargo": final.get("capacities_by_cargo"),
                "fleet_status": final.get("fleet_status"),
                "unclassified_vehicles": final.get("unclassified_vehicles"),
                "n_multimodal_stations": final.get("n_multimodal_stations"),
                "stations_by_facility": final.get("stations_by_facility"),
                "unresolved_stations": final.get("unresolved_stations"),
            })
        observed_total = rec.get("observed_opcodes_total")
        if observed_total and observed_total > 0:
            scale = observed_total / 1_000_000.0
            rec["final_profit_year_per_observed_mopcode"] = number(
                rec.get("profit_year") / scale if rec.get("profit_year") is not None else None
            )
            rec["company_value_per_observed_mopcode"] = number(
                rec.get("company_value") / scale if rec.get("company_value") is not None else None
            )
        else:
            rec["final_profit_year_per_observed_mopcode"] = None
            rec["company_value_per_observed_mopcode"] = None
        summary.append(rec)
    return summary


def number(value):
    """Evite les NaN JSON et garde les sorties stables pour les petits echantillons."""
    return None if value is None else round(value, 6)


def exact_sign_test_p(wins, losses):
    """Test binomial exact bilateral ; les egalites ne portent aucun signe."""
    n = int(wins) + int(losses)
    if n == 0:
        return None
    tail = min(int(wins), int(losses))
    probability = 2 * sum(math.comb(n, k) for k in range(tail + 1)) / (2 ** n)
    return number(min(1.0, probability))


def dispersion(values):
    """Statistiques descriptives demandees pour un arm et une metrique."""
    values = [value for value in values if value is not None]
    count = len(values)
    if not count:
        return {
            "n": 0, "mean": None, "median": None, "standard_deviation": None,
            "standard_error": None, "standard_error_percent": None,
            "coefficient_of_variation_percent": None,
        }
    mean = statistics.mean(values)
    standard_deviation = statistics.stdev(values) if count > 1 else None
    standard_error = standard_deviation / math.sqrt(count) if standard_deviation is not None else None
    coefficient = (100 * standard_deviation / mean) if standard_deviation is not None and mean else None
    return {
        "n": count,
        "mean": number(mean),
        "median": number(statistics.median(values)),
        "standard_deviation": number(standard_deviation),
        "standard_error": number(standard_error),
        "standard_error_percent": number(100 * standard_error / mean if standard_error is not None and mean else None),
        "coefficient_of_variation_percent": number(coefficient),
    }


def arm_statistics(summary, arm_names, metrics=SUCCESS_METRICS):
    """Calcule la dispersion sans melanger les arms."""
    return {
        arm: {
            metric: dispersion([
                r.get(metric) for r in summary if r["arm"] == arm and r.get("run_ok", True)
            ])
            for metric in metrics
        }
        for arm in arm_names
    }


def paired_comparisons(summary, arm_names, metrics=SUCCESS_METRICS):
    """Compare les moyennes de differences par graine, et non deux moyennes independantes."""
    metric_names = tuple(metrics)
    per_seed = {}
    for arm in arm_names:
        valid = [record for record in summary if record["arm"] == arm and record.get("run_ok", True)]
        for seed in {record["seed"] for record in valid}:
            records = [record for record in valid if record["seed"] == seed]
            per_seed[arm, seed] = {
                metric: statistics.mean([record[metric] for record in records if record[metric] is not None])
                if any(record[metric] is not None for record in records) else None
                for metric in metric_names
            }
    comparisons = []
    for index, arm_a in enumerate(arm_names):
        for arm_b in arm_names[index + 1:]:
            shared_seeds = sorted(
                seed for arm, seed in per_seed if arm == arm_a and (arm_b, seed) in per_seed
            )
            metric_results = {}
            for metric in metric_names:
                pairs = [
                    (per_seed[arm_a, seed][metric], per_seed[arm_b, seed][metric])
                    for seed in shared_seeds
                    if per_seed[arm_a, seed][metric] is not None
                    and per_seed[arm_b, seed][metric] is not None
                ]
                differences = [a - b for a, b in pairs]
                count = len(differences)
                mean_difference = statistics.mean(differences) if differences else None
                standard_deviation = statistics.stdev(differences) if count > 1 else None
                standard_error = (
                    standard_deviation / math.sqrt(count) if standard_deviation is not None else None
                )
                baseline = statistics.mean([b for _, b in pairs]) if pairs else None
                wins = sum(difference > 0 for difference in differences)
                losses = sum(difference < 0 for difference in differences)
                ties = sum(difference == 0 for difference in differences)
                sign_p = exact_sign_test_p(wins, losses)
                metric_results[metric] = {
                    "n": count,
                    "paired_differences": [
                        {
                            "seed": seed,
                            "difference": number(per_seed[arm_a, seed][metric] - per_seed[arm_b, seed][metric]),
                        }
                        for seed in shared_seeds
                        if per_seed[arm_a, seed][metric] is not None
                        and per_seed[arm_b, seed][metric] is not None
                    ],
                    "mean_difference": number(mean_difference),
                    "mean_difference_percent": number(
                        100 * mean_difference / baseline if baseline else None
                    ),
                    "standard_deviation": number(standard_deviation),
                    "standard_error": number(standard_error),
                    "arm_a_beats_arm_b": wins,
                    "arm_a_loses_to_arm_b": losses,
                    "ties": ties,
                    "sign_test_n_excluding_ties": wins + losses,
                    "sign_test_p": sign_p,
                    "protocol_15_of_20_pass": (
                        wins >= 15 and sign_p is not None and sign_p < 0.05
                        if count == 20 else None
                    ),
                }
            comparisons.append({
                "arm_a": arm_a,
                "arm_b": arm_b,
                "shared_seeds": shared_seeds,
                "metrics": metric_results,
            })
    return comparisons


def benchmark_completeness(summary, arm_names, seeds, repeats):
    """Verifie que chaque partie planifiee existe dans le resume final."""
    expected = {
        (arm, int(seed), repeat)
        for arm in arm_names
        for seed in seeds
        for repeat in range(repeats)
    }
    observed = {
        (record["arm"], int(record["seed"]), int(record.get("repeat", 0)))
        for record in summary
    }

    def records(keys):
        return [
            {"arm": arm, "seed": seed, "repeat": repeat}
            for arm, seed, repeat in sorted(keys, key=str)
        ]

    missing = expected - observed
    unexpected = observed - expected
    return {
        "ok": not missing and not unexpected,
        "expected_runs": len(expected),
        "observed_runs": len(observed & expected),
        "missing_runs": records(missing),
        "unexpected_runs": records(unexpected),
    }


def write_json_atomically(path, payload):
    """Le JSON final est toujours complet, meme si le processus tombe pendant son ecriture."""
    temporary = path.with_name(f"{path.name}.tmp{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=1) + "\n")
    os.replace(temporary, path)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", default=list(DEFAULT_ARMS), help="arms ou variantes OpexAI[cle=valeur]")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS), help="graines OpenTTD")
    parser.add_argument("--years", type=int, default=YEARS, help="duree de chaque partie")
    parser.add_argument("--starting-year", type=int, default=1970, help="annee de depart de la partie")
    parser.add_argument("--out", type=Path, default=Path("results/bench_v2.json"), help="JSON final")
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS, help="taille du Pool")
    parser.add_argument("--repeats", type=int, default=1, help="repetitions par arm et graine")
    parser.add_argument("--map-size", type=int, default=8, help="taille de la carte en puissance de 2 (8=256, 10=1024)")
    parser.add_argument(
        "--allow-shared-nondefault", action="store_true",
        help="autorise explicitement un reglage hors-defaut identique sur plusieurs arms OpexAI",
    )
    args = parser.parse_args()
    if args.years <= 0 or args.max_workers <= 0 or args.repeats <= 0:
        parser.error("--years, --max-workers et --repeats doivent etre strictement positifs")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")
    try:
        args.resolved_arm_settings = resolved_arm_settings(args.arms)
        args.setting_audit = comparison_setting_audit(args.resolved_arm_settings)
        if args.setting_audit["shared_nondefault_explicit"] and not args.allow_shared_nondefault:
            details = ", ".join(
                f"{item['setting']}={item['value']}"
                for item in args.setting_audit["shared_nondefault_explicit"]
            )
            parser.error(
                "reglage(s) hors-defaut epingle(s) identiquement dans plusieurs arms OpexAI: "
                f"{details}; utiliser --allow-shared-nondefault pour un essai conditionnel explicite"
            )
        if args.setting_audit["identical_effective_arms"]:
            pairs = ", ".join(
                f"{left} == {right}"
                for left, right in args.setting_audit["identical_effective_arms"]
            )
            parser.error(
                "bras OpexAI distincts mais reglages effectifs identiques: "
                f"{pairs}; comparaison causale impossible"
            )
        args.built_arms = build_arms(args.arms)
    except ValueError as error:
        parser.error(str(error))
    return args


def main():
    global CHECKPOINT_PATH
    arm_notes()
    args = parse_args()
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    cfg = make_cfg(args.starting_year, args.map_size)
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(args.built_arms, args.seeds, args.years, args.repeats, args.starting_year, args.map_size),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(
        rows,
        expected_last_year=args.starting_year + args.years - 1,
        expected_savegames=args.years * 12,
    )
    completeness = benchmark_completeness(summary, args.arms, args.seeds, args.repeats)
    failed_runs = [record for record in summary if not record["run_ok"]]
    missing_failures = [
        {**record, "failure_reason": "missing_run:no_rows"}
        for record in completeness["missing_runs"]
    ]
    unexpected_failures = [
        {**record, "failure_reason": "unexpected_run"}
        for record in completeness["unexpected_runs"]
    ]
    protocol_failures = failed_runs + missing_failures + unexpected_failures
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "starting_year": args.starting_year,
        "seeds": args.seeds,
        "arms": args.arms,
        "resolved_arms": args.resolved_arm_settings,
        "setting_audit": {
            **args.setting_audit,
            "shared_nondefault_allowed": bool(args.allow_shared_nondefault),
        },
        "repeats": args.repeats,
        "openttd_config": cfg,
        "metric": (
            "PLYR[0].old_economy[0] : company_value, performance_history (0-1000), "
            "profit (trimestre), profit_year (4 trimestres) ; "
            "STNN median_station_rating (0-255, cargos ramasses)"
        ),
        "success_metrics": list(SUCCESS_METRICS),
        "opcode_observation": {
            "schema": "h5.observed-v1",
            "complete_cpu_measurement": False,
            "metric_names": list(OBSERVED_OPCODE_METRICS),
            "scope": {
                "selection": "IG| field 8; portfolio selection only",
                "rail_attempt": "OB|A; measured plan+build attempt cost",
                "road_planning": "RB| planning cost on emitted attempts",
                "road_build": "RB| build cost on emitted attempts",
                "air_planning": "OA| planning only; air build opcodes are not published",
                "water_planning": "OM|W planning only and successful builds only",
            },
            "ratio_semantics": (
                "final_profit_year_per_observed_mopcode divides the final rolling-year profit "
                "by cumulative observed opcodes. Compare only equal horizons and identical "
                "instrumentation; it is not total-CPU profit/opcode."
            ),
        },
        "paired_reading": (
            "mean(A(seed) - B(seed)); les paires annulent la difficulte inter-graines partagee"
        ),
        "checkpoint": str(CHECKPOINT_PATH),
        "summary": summary,
        "completeness": completeness,
        "failed_runs": [
            {
                "arm": record["arm"], "seed": record["seed"], "repeat": record["repeat"],
                "failure_reason": record["failure_reason"],
            }
            for record in protocol_failures
        ],
        "statistics": arm_statistics(summary, args.arms),
        "paired_comparisons": paired_comparisons(summary, args.arms),
        "opcode_statistics": arm_statistics(summary, args.arms, OBSERVED_OPCODE_METRICS),
        "paired_opcode_comparisons": paired_comparisons(
            summary, args.arms, OBSERVED_OPCODE_METRICS
        ),
        "series": [{key: value for key, value in row.items() if key != "openttd_output"} for row in rows],
    }
    write_json_atomically(out, payload)
    for record in summary:
        print(
            f"{record['arm']:>36} seed={record['seed']:<8} rep={record['repeat']} "
            f"value={record['company_value']} score={record['performance_history']} "
            f"profit={record.get('profit_year')} st_rating={record.get('median_station_rating')} "
            f"veh={record['n_vehicles']} st={record['n_stations']} "
            f"status={'OK' if record['run_ok'] else 'FAILED'}"
        )
    print("checkpoint", CHECKPOINT_PATH)
    print("ecrit", out)
    if protocol_failures:
        raise SystemExit(
            f"banc invalide: {len(protocol_failures)} run(s) en echec, absent(s) ou inattendu(s)"
        )


if __name__ == "__main__":
    main()
