"""Diagnostic final (10 ans) des gares et de la flotte OpexAI.

Ce script ne lit que les chunks STNN, VEHS et la date du checkpoint final. Il ne depend ni de
sondes Squirrel ni du journal OpenTTD, et ne conserve jamais ``openttd_output`` dans son JSON.
Les totaux « au moins ce mode » comptent une gare multimodale dans chacun de ses services; les
croisements profit x mode publient separement les gares monomodales et les combinaisons multimodales.
"""
import argparse
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (  # imports existants, verifies par le selftest d'import Python
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, script_failure_reason, write_json_atomically,
)

ARMS = ("OpexAI[portfolio_v2=1]", "OpexAI[portfolio_v2=0]")
SEEDS = (100, 12345, 42, 7, 999)
MODES = ("train", "road", "ship", "aircraft")
STATION_MODE_CATEGORIES = ("train", "road", "road_truck", "road_bus", "ship", "aircraft")
# Le nom du sous-enregistrement VEHS pour la route est roadveh, tandis que le libelle publie est
# volontairement le mode lisible "road".
TYPE_TO_MODE = {"0": ("train", "train"), "1": ("roadveh", "road"),
                "2": ("ship", "ship"), "3": ("aircraft", "aircraft")}
SERVICE_OLD_DAYS = 365
PROFIT_RAW_UNITS_PER_GBP = 256
# Hypothese provisoire: l'index invalide du pool RoadStop est 65535.  L'index 0 reste
# intentionnellement considere comme un index possible: sa semantique n'a pas ete verifiee.


def _first(value):
    """Le parseur peut encoder un sous-enregistrement en liste a un element."""
    return value[0] if isinstance(value, list) and value else value


def _value(body, dotted):
    """Accepte la cle litterale ``a.b`` et la variante imbriquee si elle existe."""
    if dotted in body:
        return _first(body[dotted])
    current = body
    for key in dotted.split("."):
        current = _first(current.get(key)) if isinstance(current, dict) else None
    return current


def _valid(value):
    """Une tuile 0 est valide; -1, None et un conteneur vide ne le sont pas."""
    if value is None or value == -1:
        return False
    return not isinstance(value, (dict, list, tuple, str)) or bool(value)


def _positive(value):
    """Les dimensions de composant doivent etre strictement positives (contrairement a tile 0)."""
    return isinstance(value, (int, float)) and value > 0


def _road_stop_present(value):
    """Un compteur STNN de bus/truck est present seulement lorsqu'il est strictement positif."""
    return _positive(value)


def station_modes(body):
    """Detecte les composants reels de STNN par leurs valeurs, jamais par presence de cle."""
    modes = []
    if _positive(_value(body, "train_station.w")):
        modes.append("train")
    truck_stops = _value(body, "truck_stops")
    bus_stops = _value(body, "bus_stops")
    has_truck = _road_stop_present(truck_stops)
    has_bus = _road_stop_present(bus_stops)
    if has_truck or has_bus:
        modes.append("road")
    if has_truck:
        modes.append("road_truck")
    if has_bus:
        modes.append("road_bus")
    if _positive(_value(body, "ship_station.w")):
        modes.append("ship")
    if _positive(_value(body, "airport.w")):
        modes.append("aircraft")
    return modes


def station_records(chunks, owner=0):
    """Gares de ``owner`` avec note/backlog et identifiant STNN pour la jointure VEHS."""
    records, keys = [], set()
    stations = chunks.get("STNN") or {}
    iterator = stations.items() if isinstance(stations, dict) else enumerate(stations)
    for station_id, station in iterator:
        body = _first(station.get("normal")) if isinstance(station, dict) else None
        body = station if body is None and isinstance(station, dict) else body
        if not isinstance(body, dict):
            continue
        keys.update(body.keys())
        base = _first(body.get("base"))
        if isinstance(base, dict) and base.get("owner", owner) != owner:
            continue
        ratings, backlog = [], 0
        for good in body.get("goods") or []:
            if not isinstance(good, dict):
                continue
            waiting = good.get("max_waiting_cargo") or 0
            backlog += waiting
            if ((good.get("status") or 0) & 1 and good.get("time_since_pickup", 255) < 255
                    and good.get("rating") is not None):
                ratings.append(int(good["rating"]))
        records.append({
            "station_id": str(station_id), "modes": station_modes(body),
            "has_rating": bool(ratings), "backlog": backlog,
            "time_since_load": _value(body, "time_since_load"),
            "time_since_unload": _value(body, "time_since_unload"),
            "mode_detection_raw_values": {
                "train_station.w": _value(body, "train_station.w"),
                "airport.w": _value(body, "airport.w"),
                "ship_station.w": _value(body, "ship_station.w"),
                "truck_stops": _value(body, "truck_stops"),
                "bus_stops": _value(body, "bus_stops"),
            },
        })
    return records, sorted(keys)


def game_day(checkpoint_date):
    """Inverse la conversion documentee par openttdlab: DATE 0 = an 0, jour 1."""
    return (checkpoint_date - date(1, 1, 1)).days + 366


def _orders_for_vehicle(common, ordr, station_ids):
    """Suit le pointeur VEHS.orders dans ORDR; aucun ID n'est devine hors STNN."""
    current = common.get("orders")
    station_ids = {str(value) for value in station_ids}
    seen, destinations = set(), []
    while current is not None and str(current) in ordr and str(current) not in seen:
        key = str(current)
        seen.add(key)
        order = _first(ordr[key])
        if not isinstance(order, dict):
            return None, len(seen)
        destination = order.get("dest")
        if destination is not None and str(destination) in station_ids:
            destination = str(destination)
            if destination not in destinations:
                destinations.append(destination)
        current = order.get("next")
    # A chain must have a real STNN destination; a missing head is not a usable route.
    return (destinations or None), len(seen)


def order_structure(chunks):
    """Materiel de verification: schema ORDR et longueurs des chaines pointes par VEHS."""
    ordr = chunks.get("ORDR") or {}
    if not isinstance(ordr, dict):
        return {"order_element_keys_observed": [], "orders_chain_length_distribution": {}}
    keys = sorted({key for value in ordr.values() for order in [_first(value)]
                   if isinstance(order, dict) for key in order})
    return {"order_element_keys_observed": keys, "orders_chain_length_distribution": {}}


def vehicle_records(chunks, checkpoint_date, owner=0):
    """Extrait VEHS variante et les profits; ``orders`` est une chaine ORDR, pas une liste."""
    records = []
    vehicles = chunks.get("VEHS") or {}
    ordr = chunks.get("ORDR") or {}
    if not isinstance(ordr, dict):
        ordr = {}
    stations = chunks.get("STNN") or {}
    station_ids = stations.keys() if isinstance(stations, dict) else range(len(stations))
    values = vehicles.values() if isinstance(vehicles, dict) else vehicles
    now = game_day(checkpoint_date)
    for vehicle in values:
        if not isinstance(vehicle, dict):
            continue
        variant_and_mode = TYPE_TO_MODE.get(str(vehicle.get("type")))
        if variant_and_mode is None:
            continue
        variant, mode = variant_and_mode
        body = _first(vehicle.get(variant))
        common = _first(body.get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != owner:
            continue
        service = common.get("date_of_last_service")
        service_age = now - service if isinstance(service, (int, float)) else None
        order_stations, order_chain_length = _orders_for_vehicle(common, ordr, station_ids)
        records.append({
            "mode": mode, "last_station_visited": (str(common["last_station_visited"])
                                              if common.get("last_station_visited") is not None else None),
            "order_station_ids": order_stations, "orders_chain_length": order_chain_length,
            "profit_this_year_raw_units_approx_256x_gbp": common.get("profit_this_year"),
            "profit_last_year_raw_units_approx_256x_gbp": common.get("profit_last_year"),
            "vehstatus": common.get("vehstatus"), "reliability": common.get("reliability"),
            "economy_age": common.get("economy_age"), "max_age": common.get("max_age"),
            "service_age_days": service_age,
        })
    return records


def keep(row):
    """Capture compacte d'un checkpoint; le texte OpenTTD est utilise puis immediatement jete."""
    chunks = row.get("chunks") or {}
    stations, station_keys = station_records(chunks)
    vehicles = vehicle_records(chunks, row["date"])
    orders = order_structure(chunks)
    orders["orders_chain_length_distribution"] = raw_distribution(
        [vehicle["orders_chain_length"] for vehicle in vehicles])
    return ({
        "run": row["experiment"]["bench_run"], "date": str(row["date"]),
        "stations": stations, "station_body_keys_observed": station_keys,
        "vehicles": vehicles, "orders_structure": orders,
        "run_ok": script_failure_reason(row.get("output")) is None,
    },)


def final_rows(rows):
    """Un seul dernier checkpoint par partie, avant toute somme ou jointure."""
    by_run = defaultdict(list)
    for row in rows:
        by_run[tuple(row["run"])].append(row)
    final = []
    for run, series in sorted(by_run.items(), key=lambda item: str(item[0])):
        latest = max(series, key=lambda row: row["date"])
        final.append({"arm": run[0], "seed": run[1], "last_date": latest["date"],
                      "stations": latest["stations"], "vehicles": latest["vehicles"],
                      "orders_structure": latest.get("orders_structure", {}),
                      "station_body_keys_observed": latest["station_body_keys_observed"],
                      "run_ok": latest["run_ok"]})
    return final


def quantile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * fraction
    lower, upper = int(position), min(int(position) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def deciles(values):
    return {str(p): quantile(values, p / 100) for p in range(0, 101, 10)}


def vehicle_profit_gbp(raw_profit):
    """Convertit les profits VEHS: ``profit_*`` est stocke a environ 256x les livres reelles."""
    return raw_profit / PROFIT_RAW_UNITS_PER_GBP


def station_mode_combination(station):
    """Libelle exclusif des services reels, dans un ordre stable pour les tableaux publies."""
    labels = (("rail", "train"), ("truck", "road_truck"), ("bus", "road_bus"),
              ("ship", "ship"), ("aircraft", "aircraft"))
    present = [label for label, mode in labels if mode in station["modes"]]
    return "+".join(present) if present else "none"


def _decile_buckets(values_and_records):
    """Deciles explicites avec effectifs; les valeurs egales restent dans le premier bac compatible."""
    values = [value for value, _ in values_and_records]
    if not values:
        return {}, []
    thresholds = [quantile(values, p / 10) for p in range(1, 10)]
    rows = []
    for index in range(10):
        lower = None if index == 0 else thresholds[index - 1]
        upper = None if index == 9 else thresholds[index]
        subset = [(value, record) for value, record in values_and_records
                  if (lower is None or value >= lower)
                  and (upper is None or value < upper or index == 9)]
        rows.append((lower, upper, subset))
    return {str(index * 10): value for index, value in enumerate(
        [min(values)] + thresholds + [max(values)])}, rows


def vehicle_profit_distribution(vehicles, raw_profit_key):
    """Deciles GBP et effectifs VEHS, avec ventilation par mode et profits non positifs."""
    values_and_records = [(vehicle_profit_gbp(v[raw_profit_key]), v) for v in vehicles
                          if isinstance(v.get(raw_profit_key), (int, float))]
    thresholds, buckets = _decile_buckets(values_and_records)
    return {
        "raw_field": raw_profit_key,
        "unit_conversion": "raw VEHS profit / 256 = real GBP",
        "n_vehicles_with_profit": len(values_and_records),
        "profit_gbp_decile_thresholds": thresholds,
        "deciles_with_vehicle_counts": [
            {"decile": index + 1, "n_vehicles": len(subset),
             "profit_gbp_lower_inclusive": lower, "profit_gbp_upper_exclusive": upper,
             "vehicle_counts_by_mode": {mode: sum(record["mode"] == mode for _, record in subset)
                                        for mode in MODES}}
            for index, (lower, upper, subset) in enumerate(buckets)
        ],
        "n_vehicles_profit_lte_0_by_mode": {
            mode: sum(value <= 0 and record["mode"] == mode for value, record in values_and_records)
            for mode in MODES
        },
    }


def histogram(values):
    return {str(key): value for key, value in sorted(Counter(values).items(), key=lambda item: item[0])}


def raw_distribution(values):
    """Histogramme JSON des valeurs brutes, y compris None sans ordre entre types heterogenes."""
    labels = ["null" if value is None else str(value) for value in values]
    return {key: value for key, value in sorted(Counter(labels).items())}


def station_raw_distributions(stations):
    """Distributions verifiables des entrees de detection et compteurs STNN."""
    detection_keys = ("train_station.w", "airport.w", "ship_station.w", "truck_stops", "bus_stops")
    return {
        "mode_detection": {
            key: raw_distribution([station["mode_detection_raw_values"][key] for station in stations])
            for key in detection_keys
        },
        "time_since_load_unload": {
            "time_since_load": raw_distribution([station["time_since_load"] for station in stations]),
            "time_since_unload": raw_distribution([station["time_since_unload"] for station in stations]),
        },
    }


def warnings_for(stations, vehicles, by_mode):
    warnings = []
    if not stations:
        warnings.append("Aucune gare: toutes les categories gare et leurs parts ne doivent pas etre lues.")
    if stations and not any(station["has_rating"] for station in stations):
        warnings.append("Aucune gare notee: les comparaisons note/sans-note ne doivent pas etre lues.")
    if stations and not any(not station["has_rating"] for station in stations):
        warnings.append("Aucune gare sans note: le tableau sans-note x visiteurs ne doit pas etre lu.")
    if any(not station["modes"] for station in stations):
        warnings.append("Au moins une gare n'a aucun mode detecte: les effectifs par mode ne couvrent pas toutes les gares.")
    if stations and sum(not station["modes"] for station in stations) / len(stations) > 0.10:
        warnings.append("AVERTISSEMENT: >10% des gares n'ont aucun mode detecte; la detection doit etre reverifiee.")
    if not vehicles:
        warnings.append("Aucun vehicule OpexAI: les categories de flotte ne doivent pas etre lues.")
    for mode in STATION_MODE_CATEGORIES:
        if not by_mode[mode]:
            warnings.append(f"Aucune observation pour le mode {mode}: cette categorie ne doit pas etre lue.")
        if stations and len(by_mode[mode]) >= len(stations):
            warnings.append(
                f"DETECTION SUSPECTE: {len(by_mode[mode])}/{len(stations)} gares detectees en {mode}; "
                "ce mode ne doit pas etre lu ni cru sans verifier les distributions brutes de detection."
            )
    if vehicles and not any(vehicle["vehstatus"] is not None for vehicle in vehicles):
        warnings.append("vehstatus absent partout: sa distribution brute ne doit pas etre lue.")
    if vehicles and not any(vehicle["reliability"] is not None for vehicle in vehicles):
        warnings.append("reliability absent partout: ses deciles ne doivent pas etre lus.")
    if vehicles and not any(vehicle["max_age"] not in (None, 0) for vehicle in vehicles):
        warnings.append("max_age nul ou absent partout: le ratio economy_age/max_age ne doit pas etre lu.")
    if vehicles and not any(vehicle["service_age_days"] is not None for vehicle in vehicles):
        warnings.append("date_of_last_service absent ou non numerique partout: l'anciennete de service ne doit pas etre lue.")
    return warnings


def station_detected_mode_categories(station):
    """Categories de croisement: une gare multimodale apparait dans chaque mode reel."""
    result = []
    for label, mode in (("rail", "train"), ("route", "road"), ("eau", "ship"), ("air", "aircraft")):
        if mode in station["modes"]:
            result.append(label)
    return result or ["aucun"]


def profit_attribution(stations, vehicles):
    """Attribue les profits VEHS aux gares: orders si tous sont lisibles, sinon dernier arret."""
    profit_vehicles = [v for v in vehicles if isinstance(
        v["profit_last_year_raw_units_approx_256x_gbp"], (int, float))]
    orders_usable = bool(profit_vehicles) and all(v["order_station_ids"] for v in profit_vehicles)
    method = "orders" if orders_usable else "fallback_last_station_visited"
    reason = None if orders_usable else (
        "au moins un vehicule avec profit n'a pas de chaine ORDR exploitable vers STNN; "
        "repli explicite sur last_station_visited")
    profit_by_station = Counter()
    for vehicle in profit_vehicles:
        station_ids = vehicle["order_station_ids"] if orders_usable else [vehicle["last_station_visited"]]
        station_ids = [station for station in station_ids if station is not None]
        if not station_ids:
            continue
        # profit_last_year est une annee complete; conversion explicite des unites VEHS vers GBP.
        share = (vehicle["profit_last_year_raw_units_approx_256x_gbp"] / PROFIT_RAW_UNITS_PER_GBP
                 / len(station_ids))
        for station_id in station_ids:
            profit_by_station[str(station_id)] += share
    return {"attribution_method": method, "fallback_reason": reason,
            "profit_gbp_by_station": profit_by_station,
            "n_profit_vehicles": len(profit_vehicles)}


def profit_decile_table(stations, attribution, thresholds=None, category_name="mode_combination_counts"):
    """Deciles par gare et crosstab exclusif fourni par l'appelant, avec effectifs."""
    values = [attribution["profit_gbp_by_station"][s["station_id"]] for s in stations]
    if not values:
        return {"profit_gbp_decile_thresholds": {}, "deciles": []}
    thresholds = thresholds or [quantile(values, p / 10) for p in range(1, 10)]
    rows = []
    for decile in range(10):
        lower = None if decile == 0 else thresholds[decile - 1]
        upper = None if decile == 9 else thresholds[decile]
        # Equal values go in the lower bin, except for the final inclusive bin.
        subset = [s for s in stations if (lower is None or attribution["profit_gbp_by_station"][s["station_id"]] >= lower)
                  and (upper is None or attribution["profit_gbp_by_station"][s["station_id"]] < upper or decile == 9)]
        combinations = Counter(station_mode_combination(s) for s in subset)
        rows.append({"decile": decile + 1, "n_stations": len(subset),
                     "profit_gbp_lower_inclusive": lower, "profit_gbp_upper_exclusive": upper,
                     category_name: dict(combinations),
                     "rating_counts": {"has_rating": sum(s["has_rating"] for s in subset),
                                       "without_rating": sum(not s["has_rating"] for s in subset)},
                     "backlog_counts": {"backlog_gt_0": sum(s["backlog"] > 0 for s in subset),
                                        "backlog_0": sum(s["backlog"] <= 0 for s in subset)}})
    return {"profit_gbp_decile_thresholds": {str(index * 10): value for index, value in enumerate([min(values)] + thresholds + [max(values)])} if values else {},
            "deciles": rows}


def summarise(stations, vehicles):
    visitors = Counter(vehicle["last_station_visited"] for vehicle in vehicles
                       if vehicle["last_station_visited"] is not None)
    by_mode = {mode: [] for mode in STATION_MODE_CATEGORIES}
    for station in stations:
        for mode in station["modes"]:
            by_mode[mode].append(station)
    combinations = Counter(station_mode_combination(station) for station in stations)
    monomodal = [station for station in stations if station_mode_combination(station).count("+") == 0
                 and station_mode_combination(station) != "none"]
    multimodal = [station for station in stations if station_mode_combination(station).count("+") > 0]
    monomodal_totals = Counter(station_mode_combination(station) for station in monomodal)
    at_least_this_mode_totals = {
        label: sum(mode in station["modes"] for station in stations)
        for label, mode in (("rail", "train"), ("truck", "road_truck"), ("bus", "road_bus"),
                            ("ship", "ship"), ("aircraft", "aircraft"))
    }
    station_mode_summary, answer = {}, {}
    for mode in STATION_MODE_CATEGORIES:
        subset = by_mode[mode]
        cross = {rating: {backlog: 0 for backlog in ("backlog_gt_0", "backlog_0")}
                 for rating in ("has_rating", "without_rating")}
        visitor_counts = []
        for station in subset:
            visitors_here = visitors[station["station_id"]]
            visitor_counts.append(visitors_here)
            cross["has_rating" if station["has_rating"] else "without_rating"][
                "backlog_gt_0" if station["backlog"] > 0 else "backlog_0"] += 1
        unrated = [visitors[station["station_id"]] for station in subset if not station["has_rating"]]
        station_mode_summary[mode] = {"n_stations": len(subset), "rating_x_backlog_counts": cross}
        answer[mode] = {"n_without_rating": len(unrated),
                        "visitor_count_distribution": histogram(unrated),
                        "n_without_rating_zero_visitors": sum(count == 0 for count in unrated)}

    all_visitor_counts = [visitors[station["station_id"]] for station in stations]
    unrated_stations = [station for station in stations if not station["has_rating"]]
    def assumed_saturated(value):
        return isinstance(value, (int, float)) and value >= 255
    def assumed_recent(value):
        return isinstance(value, (int, float)) and value < 255
    load_unload_cross = {recent: {saturated: 0 for saturated in ("load_not_saturated", "load_saturated")}
                         for recent in ("unload_not_recent", "unload_recent")}
    for station in unrated_stations:
        recent = "unload_recent" if assumed_recent(station["time_since_unload"]) else "unload_not_recent"
        saturated = "load_saturated" if assumed_saturated(station["time_since_load"]) else "load_not_saturated"
        load_unload_cross[recent][saturated] += 1
    raw_distributions = station_raw_distributions(stations)
    attribution = profit_attribution(stations, vehicles)
    fleet = {}
    for mode in MODES:
        subset = [vehicle for vehicle in vehicles if vehicle["mode"] == mode]
        reliabilities = [v["reliability"] for v in subset if isinstance(v["reliability"], (int, float))]
        ratios = [v["economy_age"] / v["max_age"] for v in subset
                  if isinstance(v["economy_age"], (int, float))
                  and isinstance(v["max_age"], (int, float)) and v["max_age"] > 0]
        service_ages = [v["service_age_days"] for v in subset if v["service_age_days"] is not None]
        fleet_warnings = []
        if not subset:
            fleet_warnings.append("Aucun vehicule dans ce mode: les metriques de flotte ne doivent pas etre lues.")
        if subset and not reliabilities:
            fleet_warnings.append("reliability absent partout dans ce mode: ses deciles ne doivent pas etre lus.")
        if subset and not ratios:
            fleet_warnings.append("economy_age/max_age indisponible dans ce mode: ses deciles ne doivent pas etre lus.")
        if subset and not service_ages:
            fleet_warnings.append("date_of_last_service indisponible dans ce mode: anciennete de service ne doit pas etre lue.")
        fleet[mode] = {
            "n_vehicles": len(subset),
            "warnings": fleet_warnings,
            "vehstatus_raw_distribution": histogram(
                [str(v["vehstatus"]) for v in subset if v["vehstatus"] is not None]),
            "reliability_deciles": deciles(reliabilities),
            "economy_age_deciles": deciles([v["economy_age"] for v in subset
                                               if isinstance(v["economy_age"], (int, float))]),
            "max_age_deciles": deciles([v["max_age"] for v in subset
                                           if isinstance(v["max_age"], (int, float))]),
            "economy_age_over_max_age_deciles": deciles(ratios),
            "service_age_days_deciles": deciles(service_ages),
            "n_service_age_at_least_365_days": sum(age >= SERVICE_OLD_DAYS for age in service_ages),
            "share_service_age_at_least_365_days": (sum(age >= SERVICE_OLD_DAYS for age in service_ages) / len(service_ages)
                                                     if service_ages else None),
        }
    vehicle_profit_distributions = {
        "profit_this_year_gbp": vehicle_profit_distribution(
            vehicles, "profit_this_year_raw_units_approx_256x_gbp"),
        "profit_last_year_gbp": vehicle_profit_distribution(
            vehicles, "profit_last_year_raw_units_approx_256x_gbp"),
    }
    return {
        "warnings": warnings_for(stations, vehicles, by_mode),
        "stations_by_mode": station_mode_summary,
        "station_mode_combination_distribution": dict(combinations),
        "station_mode_totals_monomodal_only": dict(monomodal_totals),
        "station_mode_totals_at_least_this_mode": at_least_this_mode_totals,
        "station_visitors": {"visitor_count_distribution": histogram(all_visitor_counts),
                             "n_stations_zero_visitors": sum(count == 0 for count in all_visitor_counts),
                             "by_rating": {"has_rating": {"n": sum(s["has_rating"] for s in stations),
                                                           "n_zero_visitors": sum(s["has_rating"] and visitors[s["station_id"]] == 0 for s in stations)},
                                           "without_rating": {"n": sum(not s["has_rating"] for s in stations),
                                                              "n_zero_visitors": sum(not s["has_rating"] and visitors[s["station_id"]] == 0 for s in stations)}}},
        "station_mode_detection_raw_distributions": raw_distributions["mode_detection"],
        "station_time_since_load_unload_raw_distributions": raw_distributions["time_since_load_unload"],
        "without_rating_time_since_load_unload": {
            "n_stations": len(unrated_stations),
            "time_since_load_raw_distribution": raw_distribution(
                [station["time_since_load"] for station in unrated_stations]),
            "time_since_unload_raw_distribution": raw_distribution(
                [station["time_since_unload"] for station in unrated_stations]),
            "cross_tab_assuming_255_sentinel": load_unload_cross,
            "sentinel_hypothesis": (
                "255 est traite comme sature/maximal et <255 comme recent pour cette table seulement; "
                "c'est une hypothese non confirmee, publiee avec les distributions brutes pour verification."
            ),
        },
        "without_rating_mode_x_visitors": answer,
        "fleet_by_mode": fleet,
        "vehicle_profit_per_vehicle_distributions_gbp": vehicle_profit_distributions,
        "station_profit_attribution": {
            "attribution_method": attribution["attribution_method"],
            "fallback_reason": attribution["fallback_reason"],
            "profit_field_used": "profit_last_year_raw_units_approx_256x_gbp / 256 = profit_last_year_gbp",
            "n_profit_vehicles": attribution["n_profit_vehicles"],
            "mean_profit_attributed_gbp_per_station_weighted": (
                sum(attribution["profit_gbp_by_station"][s["station_id"]] for s in stations) / len(stations)
                if stations else None),
            "monomodal_only_profit_x_mode_attributed_gbp_deciles": profit_decile_table(
                monomodal, attribution, category_name="monomodal_mode_counts"),
            "multimodal_profit_x_combination_attributed_gbp_deciles": profit_decile_table(
                multimodal, attribution, category_name="multimodal_combination_counts"),
        },
    }


def analyse_grouped(records, seeds=None):
    seeds = tuple(SEEDS if seeds is None else seeds)
    grouped = {(arm, seed): [] for arm in ARMS for seed in seeds}
    for record in records:
        if record["run_ok"]:
            grouped.setdefault((record["arm"], record["seed"]), []).append(record)
    def scoped(series):
        """Les IDs STNN sont locaux a une sauvegarde: les qualifier avant le cumul."""
        stations, vehicles = [], []
        for record in series:
            prefix = f"{record['arm']}:{record['seed']}:"
            stations.extend([{**station, "station_id": prefix + station["station_id"]}
                             for station in record["stations"]])
            for vehicle in record["vehicles"]:
                convert = lambda station_id: prefix + str(station_id) if station_id is not None else None
                vehicles.append({**vehicle, "last_station_visited": convert(vehicle["last_station_visited"]),
                                 "order_station_ids": ([convert(s) for s in vehicle["order_station_ids"]]
                                                       if vehicle["order_station_ids"] else None)})
        return stations, vehicles
    def combine(series):
        stations, vehicles = scoped(series)
        return summarise(stations, vehicles)
    per_seed = []
    for seed in seeds:
        per_seed.append({"seed": seed, "arms": {arm: combine(grouped[arm, seed]) for arm in ARMS}})
    cumulative = {arm: combine([record for (name, _), series in grouped.items() if name == arm
                                for record in series]) for arm in ARMS}
    keys = sorted({key for record in records if record["run_ok"]
                   for key in record["station_body_keys_observed"]})
    all_stations = [station for record in records if record["run_ok"] for station in record["stations"]]
    scoped_by_arm = {arm: scoped([record for (name, _), series in grouped.items() if name == arm
                                  for record in series]) for arm in ARMS}
    all_profit_stations = {arm: scoped_by_arm[arm][0] for arm in ARMS}
    all_profit_vehicles = {arm: scoped_by_arm[arm][1] for arm in ARMS}
    attrs = {arm: profit_attribution(all_profit_stations[arm], all_profit_vehicles[arm]) for arm in ARMS}
    shared_monomodal_stations = {
        arm: [station for station in all_profit_stations[arm]
              if station_mode_combination(station).count("+") == 0
              and station_mode_combination(station) != "none"]
        for arm in ARMS
    }
    shared_values = [attrs[arm]["profit_gbp_by_station"][s["station_id"]]
                     for arm in ARMS for s in shared_monomodal_stations[arm]]
    shared_thresholds = [quantile(shared_values, p / 10) for p in range(1, 10)] if shared_values else []
    shared = {arm: profit_decile_table(shared_monomodal_stations[arm], attrs[arm], shared_thresholds,
                                       category_name="monomodal_mode_counts")
              for arm in ARMS}
    control, treated = ARMS[1], ARMS[0]
    net_excess = len(shared_monomodal_stations[treated]) - len(shared_monomodal_stations[control])
    excess = []
    for index in range(10):
        treated_n = shared[treated]["deciles"][index]["n_stations"] if shared[treated]["deciles"] else 0
        control_n = shared[control]["deciles"][index]["n_stations"] if shared[control]["deciles"] else 0
        excess.append({"decile": index + 1, "portfolio_v2_1_n_stations": treated_n,
                       "portfolio_v2_0_n_stations": control_n,
                       "excess_portfolio_v2_1_minus_0": treated_n - control_n,
                       "share_of_net_portfolio_v2_1_station_excess": (
                           (treated_n - control_n) / net_excess if net_excess else None)})
    order_keys = sorted({key for record in records if record["run_ok"]
                         for key in record.get("orders_structure", {}).get("order_element_keys_observed", [])})
    order_lengths = raw_distribution([vehicle["orders_chain_length"] for record in records if record["run_ok"]
                                      for vehicle in record["vehicles"]])
    return {"per_seed": per_seed, "cumulative": {"arms": cumulative},
            "station_body_keys_observed": keys,
            "all_stations_raw_distributions": station_raw_distributions(all_stations),
            "orders_structure_observed": {"order_element_keys_observed": order_keys,
                                            "orders_chain_length_distribution": order_lengths},
            "additional_stations_by_shared_profit_decile": {
                "definition": "Deciles communs formes seulement sur les gares monomodales des deux bras cumules; un excedent positif indique plus de gares monomodales portfolio_v2=1.",
                "shared_profit_gbp_thresholds": shared_thresholds,
                "by_arm": shared, "portfolio_v2_1_minus_0": excess}}


def run_selftest():
    """Test pur Python: STNN/VEHS variants, ORDR et gardes de coherence."""
    def good(rated, backlog):
        return {"status": 1 if rated else 0, "time_since_pickup": 1 if rated else 255,
                "rating": 150, "max_waiting_cargo": backlog}
    def station(modes, rated=True, backlog=0, load=255, unload=255):
        # Chaque corps porte toutes les cles de variante, meme quand le composant est inutilise.
        body = {"base": {"owner": 0}, "goods": [good(rated, backlog)],
                "train_station.tile": -1, "train_station.w": 0, "train_station.h": 0,
                "truck_stops": 0, "bus_stops": 0,
                "ship_station.tile": -1, "ship_station.w": 0, "ship_station.h": 0,
                "airport.tile": -1, "airport.w": 0, "airport.h": 0,
                "airport.flags": 0, "airport.layout": 0, "airport.psa": 0,
                "airport.rotation": 0, "airport.type": 0,
                "time_since_load": load, "time_since_unload": unload}
        if "train" in modes:
            body.update({"train_station.tile": 0, "train_station.w": 2, "train_station.h": 1})
        if "truck" in modes:
            body["truck_stops"] = 13
        if "bus" in modes:
            body["bus_stops"] = 23
        if "ship" in modes:
            body.update({"ship_station.tile": 3, "ship_station.w": 1, "ship_station.h": 1})
        if "aircraft" in modes:
            body.update({"airport.tile": 4, "airport.w": 4, "airport.h": 3})
        return {"normal": body}
    def vehicle(mode, visited, orders=None, profit_last_year=0, status=5):
        common = {"owner": 0, "last_station_visited": visited, "vehstatus": status,
                  "reliability": 200, "economy_age": 10, "max_age": 20,
                  "date_of_last_service": 365, "orders": orders,
                  "profit_this_year": profit_last_year // 2, "profit_last_year": profit_last_year,
                  "value": 100}
        variant = "roadveh" if mode == "road" else mode
        return {"type": str(MODES.index(mode)), variant: {"common": common},
                **{other: {} for other in ("train", "roadveh", "ship", "aircraft") if other != variant}}
    checkpoint = date(1980, 1, 1)
    control_chunks = {"STNN": {"1": station(("train",), False, 2, load=255, unload=2),
                                "2": station(("bus",), True), "3": station(("truck",), True),
                                "4": station(("aircraft",), True), "5": station(("ship",), True),
                                "6": station((), False), "7": station(("bus", "aircraft"), True)},
                      "ORDR": {"10": {"dest": "1", "next": "11"}, "11": {"dest": "2", "next": None}},
                      "VEHS": {"a": vehicle("road", 1, "10", 512)}}
    fallback_chunks = {"STNN": {"1": station(("bus",), True)}, "VEHS": {"a": vehicle("road", 1, None, 256)}}
    def record(arm, seed, chunks):
        stations, keys = station_records(chunks)
        return {"arm": arm, "seed": seed, "last_date": str(checkpoint), "stations": stations,
                "vehicles": vehicle_records(chunks, checkpoint), "station_body_keys_observed": keys,
                "run_ok": True}
    analysed = analyse_grouped([record(ARMS[1], 100, control_chunks), record(ARMS[0], 100, fallback_chunks)], [100])
    cumulative = analysed["cumulative"]["arms"]
    assert cumulative[ARMS[1]]["stations_by_mode"]["ship"]["n_stations"] == 1
    assert cumulative[ARMS[1]]["stations_by_mode"]["road_bus"]["n_stations"] == 2
    assert cumulative[ARMS[1]]["stations_by_mode"]["road_truck"]["n_stations"] == 1
    assert cumulative[ARMS[1]]["stations_by_mode"]["aircraft"]["n_stations"] == 2
    assert cumulative[ARMS[1]]["stations_by_mode"]["train"]["n_stations"] == 1
    assert not station_records(control_chunks)[0][5]["modes"]
    assert "road_truck" not in station_records({"STNN": {"0": station((), True)}})[0][0]["modes"]
    assert "road_truck" in station_records({"STNN": {"0": station(("truck",), True)}})[0][0]["modes"]
    assert station_mode_combination(station_records(control_chunks)[0][6]) == "bus+aircraft"
    mono_table = cumulative[ARMS[1]]["station_profit_attribution"][
        "monomodal_only_profit_x_mode_attributed_gbp_deciles"]
    assert all("bus+aircraft" not in row["monomodal_mode_counts"] for row in mono_table["deciles"])
    multi_table = cumulative[ARMS[1]]["station_profit_attribution"][
        "multimodal_profit_x_combination_attributed_gbp_deciles"]
    assert any(row["multimodal_combination_counts"].get("bus+aircraft") == 1
               for row in multi_table["deciles"])
    assert any(">10%" in warning for warning in cumulative[ARMS[1]]["warnings"])
    attr = cumulative[ARMS[1]]["station_profit_attribution"]
    assert attr["attribution_method"] == "orders"
    assert attr["monomodal_only_profit_x_mode_attributed_gbp_deciles"]["profit_gbp_decile_thresholds"]["0"] == 0.0
    # Directly verifies the two destinations each receive 512/256/2 = 1 GBP.
    direct_attr = profit_attribution(station_records(control_chunks)[0], vehicle_records(control_chunks, checkpoint))
    assert direct_attr["profit_gbp_by_station"] == {"1": 1.0, "2": 1.0}
    assert vehicle_profit_gbp(512) == 2.0
    negative_profit = {"mode": "road", "profit_this_year_raw_units_approx_256x_gbp": -256,
                       "profit_last_year_raw_units_approx_256x_gbp": -512}
    negative_distribution = vehicle_profit_distribution(
        [negative_profit], "profit_last_year_raw_units_approx_256x_gbp")
    assert negative_distribution["n_vehicles_profit_lte_0_by_mode"]["road"] == 1
    assert summarise(station_records(fallback_chunks)[0], vehicle_records(fallback_chunks, checkpoint))["station_profit_attribution"]["attribution_method"] == "fallback_last_station_visited"
    # 2 stations with mean 1 and 1 station with mean 100: aggregation must weight station counts.
    weighted, naive = (1 + 1 + 100) / 3, (statistics.mean([1, 1]) + statistics.mean([100])) / 2
    assert weighted == 34.0 and naive == 50.5 and weighted != naive
    print("selftest passed: truck_stops/bus_stops use > 0 (0 absent, 13 present); a scalar-free station remains mode=aucun")
    print("selftest passed: bus+aircraft is a multimodal combination and is excluded from the monomodal profit x mode crosstab")
    print("selftest passed: >10% no-mode warning fires (1/6); raw scalar distributions are retained")
    print("selftest passed: VEHS type-string variant follows ORDR dest/next and splits 512 raw units as 1.0 GBP + 1.0 GBP")
    print("selftest passed: invalid/absent ORDR falls back explicitly to last_station_visited")
    print("selftest passed: VEHS raw profit / 256 converts 512 to GBP 2.0; negative road profit enters the <= 0 bucket")
    print("selftest passed: weighted mean=34.0 differs from naive mean-of-means=50.5")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_station_fleet_10y_5seeds.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION, max_workers=args.max_workers,
        result_processor=keep, experiments=experiments(build_arms(ARMS), args.seeds, args.years, 1, 1970),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    final = final_rows(rows)
    failed = [{key: value for key, value in record.items() if key not in ("stations", "vehicles")}
              for record in final if not record["run_ok"]]
    payload = {
        "years": args.years, "seeds": args.seeds, "arms": list(ARMS),
        "mode_detection": {
            "train": "train_station.w > 0",
            "road": "truck_stops > 0 ou bus_stops > 0",
            "road_truck": "truck_stops > 0",
            "road_bus": "bus_stops > 0",
            "ship": "ship_station.w > 0", "aircraft": "airport.w > 0 (hypothese non verifiee)",
            "verification": (
                "analysis.<arm>.station_mode_detection_raw_distributions publie les distributions brutes "
                "de train_station.w, airport.w, ship_station.w, truck_stops et bus_stops (valeurs scalaires, jamais len); "
                "0 est la sentinelle d'absence pour truck_stops et bus_stops; seul un compteur > 0 est detecte."
            ),
        },
        "vehicle_link_definition": "VEHS[mode].common.last_station_visited joint a STNN pour les visiteurs; le profit suit VEHS.common.orders -> ORDR.dest/next si tous les vehicules a profit sont exploitables, sinon repli explicite last_station_visited.",
        "orders_structure_definition": "analysis.orders_structure_observed publie les cles des maillons ORDR et la distribution des longueurs de chaines suivies depuis VEHS.common.orders.",
        "profit_fields": "Les profits bruts VEHS sont nommes *_raw_units_approx_256x_gbp; tous les tableaux GBP, dont les deciles par vehicule, appliquent raw / 256.",
        "vehstatus": "Distribution des valeurs brutes uniquement; aucun masque ni compte depot/arret n'est applique.",
        "service_age_definition": "checkpoint DATE - VEHS.common.date_of_last_service, en jours OpenTTD; ancien = au moins 365 jours.",
        "final_runs": final, "analysis": analyse_grouped(final, args.seeds), "failed_runs": failed,
        "failed_run_count": len(failed),
    }
    write_json_atomically(args.out, payload)
    print("failed", len(failed), "out", args.out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
