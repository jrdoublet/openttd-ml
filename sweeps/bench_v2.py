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
# performance_history n'est NI le profit NI la note de gare (docs/mecanique_jeu.md §6).
SUCCESS_METRICS = (
    "company_value",
    "performance_history",
    "profit",
    "profit_year",
    "median_station_rating",
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
        elif key == "join_max_distance":
            if not 0 <= value <= 200:
                raise ValueError("join_max_distance doit etre entre 0 et 200")
            if value % 5:
                raise ValueError("join_max_distance doit etre un multiple de 5 (step_size)")
        elif key == "transit_cost":
            # Memes bornes et meme pas que ai/OpexAI/info.nut (docs/taches.md C9) : 0 = neutre
            # (defaut), 1000 = cout complet.
            if not 0 <= value <= 2000:
                raise ValueError("transit_cost doit etre entre 0 et 2000")
            if value % 50:
                raise ValueError("transit_cost doit etre un multiple de 50 (step_size)")
        elif key == "road_pax_catchment_pct":
            # 0 garde le calibrage historique a 22 %. Une valeur positive est une sonde route
            # uniquement (info.nut) ; 86 = 22 * le ratio median reel/predit 3,91.
            if not 0 <= value <= 100:
                raise ValueError("road_pax_catchment_pct doit etre entre 0 et 100")
        elif key == "portfolio_floor_pct":
            # Plancher de profit absolu du portefeuille v2, en % du meilleur profit finançable.
            # 0 = tri au seul ratio (le comportement mesure a -24,4 % de valeur le 2026-09-02).
            if not 0 <= value <= 100:
                raise ValueError("portfolio_floor_pct doit etre entre 0 et 100")
            if value % 5:
                raise ValueError("portfolio_floor_pct doit etre un multiple de 5 (step_size)")
        elif key == "project_top_k":
            # Memes bornes que ai/OpexAI/info.nut : docs/taches.md C43/E3, sature a 70-77% des
            # appels de selection au defaut 64 (mesure du 2026-09-08).
            if not 8 <= value <= 128:
                raise ValueError("project_top_k doit etre entre 8 et 128")
            if value % 8:
                raise ValueError("project_top_k doit etre un multiple de 8 (step_size)")
        elif key in ("project_top_k_dynamic", "c41_rail_freight_town_service_cache"):
            if value not in (0, 1):
                raise ValueError(f"{key} est booleen : 0 ou 1")
        elif key == "portfolio_max_batch":
            # Memes bornes que ai/OpexAI/info.nut : sans ce garde, le moteur pourrait borner la
            # valeur sans que le nom de l'arm dans le JSON dise ce qui a vraiment ete joue.
            if not 1 <= value <= 8:
                raise ValueError("portfolio_max_batch doit etre entre 1 et 8")
        elif key == "rail_min_distance":
            # Distance minimale d'un candidat rail. 25 = comportement livre ; 5 rouvre la bande
            # de chevauchement rail/route que les commentaires du fichier decrivent deja.
            if not 5 <= value <= 40:
                raise ValueError("rail_min_distance doit etre entre 5 et 40")
        elif key == "air_fleet_cadence_days":
            if not 0 <= value <= 365:
                raise ValueError("air_fleet_cadence_days doit etre entre 0 et 365")
        elif key == "air_max_distance":
            if not 0 <= value <= 1000:
                raise ValueError("air_max_distance doit etre entre 0 et 1000")
        elif key == "air_fleet_buffer":
            if not -1 <= value <= 500:
                raise ValueError("air_fleet_buffer doit etre entre -1 et 500")
            if value >= 0 and value % 5:
                raise ValueError("air_fleet_buffer doit etre un multiple de 5 (step_size)")
        elif key == "infra_amort_pct":
            if not 0 <= value <= 100:
                raise ValueError("infra_amort_pct doit etre entre 0 et 100")
            if value % 10:
                raise ValueError("infra_amort_pct doit etre un multiple de 10 (step_size)")
        elif key == "feeder_hub_wait_max":
            if not 0 <= value <= 1000:
                raise ValueError("feeder_hub_wait_max doit etre entre 0 et 1000")
        elif key == "feeder_hub_min_days":
            if not 0 <= value <= 365:
                raise ValueError("feeder_hub_min_days doit etre entre 0 et 365")
        elif key == "decision_friction_permille":
            if not 0 <= value <= 1000:
                raise ValueError("decision_friction_permille doit etre entre 0 et 1000")
        elif key == "abandon_cooldown_days":
            if not 0 <= value <= 5000:
                raise ValueError("abandon_cooldown_days doit etre entre 0 et 5000")
        elif key == "unprofitable_streak_threshold":
            if not 1 <= value <= 10:
                raise ValueError("unprofitable_streak_threshold doit etre entre 1 et 10")
        elif key in ("abandon_memory", "abandon_gen_filter", "air_joined_stops", "station_join", "join_place", "origin_sitable", "basin_share", "reborrow", "road_mode", "road_pax_build", "road_refleet", "road_multistop", "astar_cost", "probe_negative", "pax_near", "rail_cost_probe", "rail_expand", "town_growth", "dynamic_cash_reserve", "dynamic_pathfinder_cap", "loop_budget", "fleet_fix", "economy_fix", "growth_yields", "air_margin", "air_abandon", "air_abandon_site", "pricing_road_rating", "pricing_rail_depot", "pricing_road_ops", "pax_full_load", "air_full_load", "complex_cargo", "air_hub", "rail_refleet", "marginal_fleet", "air_cost_probe", "air_presite", "portfolio_fresh_budget", "air_fleet_probe", "fleet_before_new", "air_roi_order", "rail_search_resumable", "rail_segmented_search", "rail_micro_deadline", "decision_log", "reserve_maint_cap", "air_margin_v2", "air_hub_fix", "air_demand_cap", "air_demand_plan", "event_depot_sell", "event_industry_close", "event_subsidy_probe", "event_vehicle_lost", "event_vehicle_autoreplaced", "event_vehicle_crashed", "event_vehicle_unprofitable", "event_catalog_invalidate", "c39_invalidation_probe", "c39_decision_delta_probe", "c39_engine_refresh", "c41_revision_probe", "vivier_ratio_filter", "road_fleet_fix", "air_fleet_line_price", "air_cadence_cap", "road_loading_fix", "clean_density_score", "feeder_unlock", "feeder_pricing", "feeder_town_coverage", "feeder_portfolio", "flat_bonus", "air_portfolio", "fleet_portfolio", "tension_scoring", "feeder_mail_duplicate", "feeder_hub_check", "feeder_candidates", "air_site_cache", "air_cheap_site", "road_cheap_trace", "road_pax_voirie", "road_pax_overlap", "shadow_pricing", "portfolio_cache", "portfolio_dynamic_batch", "abandon_memory_transient_guard", "capital_calibration", "rail_prequote", "rail_prequote_keep_plan", "feeder_enabled", "rail_terrain_probe", "road_cost_probe", "water_lakes_connectivity", "water_lakes_ops_budget", "water_site_catalog", "water_discovery_real_fronts", "save_full_state", "c42_subsidies", "c53_order_nonstop", "c53_order_noload", "c60_town_rating_filter", "c48_indexed_regeneration", "c48_index_shadow", "c46_freight_grid", "c46_freight_grid_shadow"):
            if value not in (0, 1):
                raise ValueError(f"{key} est booleen : 0 ou 1")
        elif key in ("c39_air_reason_probe", "c41_water_refresh", "c41_water_precheck", "c41_water_candidate_probe", "c41_water_plans_profile", "c41_water_site_profile", "c41_slack_ledger", "c41_staleness_ledger", "c41_opportunity_ledger", "c41_admission_ledger", "c41_road_refresh", "c41_road_candidate_profile", "c41_road_freight_profile", "c41_road_freight_served_index", "c41_road_freight_acceptance_index", "c41_rail_candidate_profile", "c41_rail_pax_cruise_cache", "c41_rail_freight_profile", "c41_rail_freight_candidate_profile", "c41_rail_freight_economics_profile", "c41_rail_freight_economics_detail_profile", "c41_rail_freight_economics_setup_profile", "c41_rail_freight_economics_consist_profile", "c41_rail_freight_cruise_profile", "c41_rail_freight_cruise_cache", "c41_rail_freight_speed_detail_profile", "c41_rail_freight_acceleration_cache", "c41_rail_freight_effective_speed_profile", "c41_rail_freight_town_guards_profile", "c41_vehicle_lost_probe", "c41_rail_lost_probe", "c41_rail_lost_topology_probe", "c41_rail_lost_physical_probe", "c41_rail_lost_signal_repair", "c41_rail_lost_connectivity_probe", "c41_rail_lost_junction_repair", "c41_rail_slice_ledger", "c41_rail_cash_release", "c41_rail_domination_probe", "c41_projects_fallthrough_probe", "c39_projects_cadence_probe", "c39_pass_clock_ledger", "c48_project_attempt_ledger", "c49_scarcity_ledger", "c55_origin_relax_probe", "c55_freight_origin_relax", "c55_road_origin_relax", "c55_road_pax_origin_relax", "c55_pax_trace_probe", "c52_autoreplace_log", "c52_event_exposure_probe", "c52_crash_log", "c52_unprofitable_log", "c52_station_first_vehicle_log", "c56_task_trace", "c54_vehicle_orders_probe", "c48_incremental_profile", "cash_reserve_probe", "portfolio_refresh_probe", "c42_subsidy_log", "c60_town_rating_probe"):
            if value not in (0, 1):
                raise ValueError(f"{key} est booleen : 0 ou 1")
        else:
            raise ValueError(f"reglage OpexAI inconnu: {key}")
        params.append((key, value))
    return tuple(params)


def build_arms(names):
    """Construit les arms demandes, y compris les variantes parametrees de notre IA."""
    arms = {}
    for name in names:
        if name in arms:
            raise ValueError(f"arm duplique: {name}")
        opex_params = parse_opex_variant(name)
        if name == "OpexAI" or opex_params is not None:
            arms[name] = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", opex_params or ())
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


def keep(row):
    """Une ligne par sauvegarde mensuelle, persistee immediatement pour survivre a un crash."""
    chunks = row["chunks"]
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    ratings = station_ratings(chunks)
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
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
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


def summarise(rows, expected_last_year=None):
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
        summary.append({
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
            "openttd_output": final["openttd_output"],
            "run_ok": failure_reason is None,
            "failure_reason": failure_reason,
        })
    return summary


def number(value):
    """Evite les NaN JSON et garde les sorties stables pour les petits echantillons."""
    return None if value is None else round(value, 6)


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


def arm_statistics(summary, arm_names):
    """Calcule la dispersion sans melanger les arms."""
    return {
        arm: {
            metric: dispersion([
                r.get(metric) for r in summary if r["arm"] == arm and r.get("run_ok", True)
            ])
            for metric in SUCCESS_METRICS
        }
        for arm in arm_names
    }


def paired_comparisons(summary, arm_names):
    """Compare les moyennes de differences par graine, et non deux moyennes independantes."""
    per_seed = {}
    for arm in arm_names:
        valid = [record for record in summary if record["arm"] == arm and record.get("run_ok", True)]
        for seed in {record["seed"] for record in valid}:
            records = [record for record in valid if record["seed"] == seed]
            per_seed[arm, seed] = {
                metric: statistics.mean([record[metric] for record in records if record[metric] is not None])
                if any(record[metric] is not None for record in records) else None
                for metric in SUCCESS_METRICS
            }
    comparisons = []
    for index, arm_a in enumerate(arm_names):
        for arm_b in arm_names[index + 1:]:
            shared_seeds = sorted(
                seed for arm, seed in per_seed if arm == arm_a and (arm_b, seed) in per_seed
            )
            metrics = {}
            for metric in SUCCESS_METRICS:
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
                metrics[metric] = {
                    "n": count,
                    "mean_difference": number(mean_difference),
                    # Le pourcentage rapporte la moyenne des differences a la moyenne de B.
                    "mean_difference_percent": number(
                        100 * mean_difference / baseline if baseline else None
                    ),
                    "standard_deviation": number(standard_deviation),
                    "standard_error": number(standard_error),
                    "arm_a_beats_arm_b": sum(difference > 0 for difference in differences),
                }
            comparisons.append({
                "arm_a": arm_a,
                "arm_b": arm_b,
                "shared_seeds": shared_seeds,
                "metrics": metrics,
            })
    return comparisons


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
    args = parser.parse_args()
    if args.years <= 0 or args.max_workers <= 0 or args.repeats <= 0:
        parser.error("--years, --max-workers et --repeats doivent etre strictement positifs")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")
    try:
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
    summary = summarise(rows, expected_last_year=args.starting_year + args.years - 1)
    failed_runs = [record for record in summary if not record["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "starting_year": args.starting_year,
        "seeds": args.seeds,
        "arms": args.arms,
        "repeats": args.repeats,
        "openttd_config": cfg,
        "metric": (
            "PLYR[0].old_economy[0] : company_value, performance_history (0-1000), "
            "profit (trimestre), profit_year (4 trimestres) ; "
            "STNN median_station_rating (0-255, cargos ramasses)"
        ),
        "success_metrics": list(SUCCESS_METRICS),
        "paired_reading": (
            "mean(A(seed) - B(seed)); les paires annulent la difficulte inter-graines partagee"
        ),
        "checkpoint": str(CHECKPOINT_PATH),
        "summary": summary,
        "failed_runs": [
            {
                "arm": record["arm"], "seed": record["seed"], "repeat": record["repeat"],
                "failure_reason": record["failure_reason"],
            }
            for record in failed_runs
        ],
        "statistics": arm_statistics(summary, args.arms),
        "paired_comparisons": paired_comparisons(summary, args.arms),
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
    if failed_runs:
        raise SystemExit(f"banc invalide: {len(failed_runs)} run(s) avec une erreur fatale NoAI")


if __name__ == "__main__":
    main()
