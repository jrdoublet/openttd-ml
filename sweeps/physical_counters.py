"""physical_counters.py - Décodeur unifié et qualifié des compteurs physiques OpenTTD 15.3.

Ce module fournit un décodage rigoureux et vérifié des structures de chunks OpenTTD 15.3
pour les véhicules (`VEHS`) et les gares (`STNN`), évitant les surcomptages historiques
(wagons de train ou ombres d'avion comptés comme des véhicules indépendants, mélange
des capacités passagers et fret, gares multimodales comptées plusieurs fois).

Schéma de version : 1.1.0
"""
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

SCHEMA_VERSION = "1.1.0"

# Modes de véhicules et correspondance avec le champ `type` du chunk VEHS
# 0: train, 1: roadveh, 2: ship, 3: aircraft, 4: effect, 5: disaster
TYPE_TO_MODE = {
    0: "rail", "0": "rail",
    1: "road", "1": "road",
    2: "water", "2": "water",
    3: "air", "3": "air",
}

TYPE_TO_CHUNK_KEY = {
    0: "train", "0": "train",
    1: "roadveh", "1": "roadveh",
    2: "ship", "2": "ship",
    3: "aircraft", "3": "aircraft",
}

CHUNK_KEY_TO_MODE = {
    "train": "rail",
    "roadveh": "road",
    "ship": "water",
    "aircraft": "air",
}

NON_COMPANY_TYPES = {
    4: "effect", "4": "effect",
    5: "disaster", "5": "disaster",
}

VEHICLE_MODES = ("rail", "road", "air", "water")

# Modes qualifiés sur des chunks OpenTTD 15.3 réels
QUALIFIED_MODES = {
    "rail": True,
    "road": True,
    "air": True,
    "water": False,  # Non exercé sur le banc de contrôle (0 navires construits)
}

# Bits de facilities de gares (OpenTTD station_type.h)
FACILITY_BITS = [
    (1, "rail"),
    (2, "truck"),
    (4, "bus"),
    (8, "airport"),
    (16, "dock"),
]


def _first(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _get_common(record: dict, chunk_key: str) -> Optional[dict]:
    body = _first(record.get(chunk_key))
    if not isinstance(body, dict):
        return None
    common = _first(body.get("common"))
    return common if isinstance(common, dict) else None


def decode_vehicles(vehs_chunk: Union[dict, list, None], target_owner: int = 0) -> dict:
    """Décode le chunk VEHS de manière exhaustive et qualifiée.

    Paramètres :
        vehs_chunk : chunk brut VEHS (dict indexé ou liste d'enregistrements).
        target_owner : ID du joueur cible (défaut 0).

    Retourne :
        Dictionnaire conforme au schéma 1.1.0 avec :
        - `schema_version` : version du schéma ("1.1.0").
        - `chunk_valid` : booléen (False si le chunk est absent ou d'un type inattendu).
        - `chunk_error` : None ou chaîne descriptive de l'erreur ("chunk_missing", etc.).
        - `vehicle_pool_entries` : entrées brutes du pool appartenant à target_owner (None si invalid).
        - `total_pool_entries` : total des entrées du chunk VEHS.
        - `primary_vehicles_count` : total d'unités pilotables possédées (None si invalid).
        - `primary_vehicles_by_mode` : unités pilotables par mode (rail, road, air, water).
        - `qualified_modes` : drapeaux de qualification empirique par mode.
        - `components_breakdown` : détail des composants exclus (wagons, ombres, etc.).
        - `unclassified_entries` : entrées suspectes, corrompues ou malformées (doit être vide).
        - `non_company_entries` : effets, désastres, autres compagnies.
        - `capacities_by_cargo` : capacités agrégées par type de cargo ({cargo_id: cap}).
        - `fleet_status` : répartition des observables {stopped, running, hidden, crashed}.
        - `primary_vehicles_detail` : inventaire détaillé de chaque convoi pilotable.
    """
    if vehs_chunk is None or not isinstance(vehs_chunk, (dict, list)):
        err = "chunk_missing" if vehs_chunk is None else "invalid_chunk_type"
        return {
            "schema_version": SCHEMA_VERSION,
            "chunk_valid": False,
            "chunk_error": err,
            "vehicle_pool_entries": None,
            "total_pool_entries": 0,
            "primary_vehicles_count": None,
            "primary_vehicles_by_mode": {mode: None for mode in VEHICLE_MODES},
            "qualified_modes": dict(QUALIFIED_MODES),
            "components_breakdown": {
                "rail_wagons": 0,
                "aircraft_shadows_rotors": 0,
                "road_articulated_parts": 0,
                "water_components": 0,
            },
            "unclassified_entries": [{"reason": err}],
            "non_company_entries": {"effects": 0, "disasters": 0, "other_owners": 0},
            "capacities_by_cargo": {},
            "fleet_status": {
                "stopped": 0,
                "not_stopped": 0,
                "running": 0,
                "hidden": 0,
                "broken": 0,
                "crashed": 0,
            },
            "primary_vehicles_detail": [],
        }

    # Normalisation en liste de tuples (index_int, record)
    if isinstance(vehs_chunk, dict):
        records = []
        for k, v in vehs_chunk.items():
            try:
                idx = int(k)
            except (ValueError, TypeError):
                idx = len(records)
            records.append((idx, v))
        records.sort(key=lambda x: x[0])
    else:
        records = [(i, r) for i, r in enumerate(vehs_chunk)]

    # Table d'accès par index pour le suivi des consistes (pointeur 1-based `next`)
    record_by_index = {idx: rec for idx, rec in records}

    total_pool_entries = len(records)
    vehicle_pool_entries = 0
    primary_counts = {mode: 0 for mode in VEHICLE_MODES}
    components = {
        "rail_wagons": 0,
        "aircraft_shadows_rotors": 0,
        "road_articulated_parts": 0,
        "water_components": 0,
    }
    unclassified_entries = []
    non_company = {
        "effects": 0,
        "disasters": 0,
        "other_owners": 0,
    }
    capacities_by_cargo = defaultdict(int)
    stopped_count = 0
    not_stopped_count = 0
    running_count = 0
    hidden_count = 0
    broken_count = 0
    crashed_count = 0
    primary_details = []

    # Première passe : classification de chaque enregistrement
    for idx, rec in records:
        if not isinstance(rec, dict):
            unclassified_entries.append({"index": idx, "reason": "not_a_dict", "record": str(rec)})
            continue

        raw_type = rec.get("type")
        if raw_type in NON_COMPANY_TYPES:
            kind = NON_COMPANY_TYPES[raw_type]
            if kind == "effect":
                non_company["effects"] += 1
            else:
                non_company["disasters"] += 1
            continue

        if raw_type not in TYPE_TO_CHUNK_KEY:
            unclassified_entries.append({"index": idx, "reason": "unknown_type", "type": raw_type})
            continue

        chunk_key = TYPE_TO_CHUNK_KEY[raw_type]
        mode = CHUNK_KEY_TO_MODE[chunk_key]
        common = _get_common(rec, chunk_key)
        if common is None:
            unclassified_entries.append({"index": idx, "reason": "missing_common", "mode": mode, "chunk_key": chunk_key})
            continue

        owner = common.get("owner")
        if owner is None:
            unclassified_entries.append({"index": idx, "reason": "missing_owner", "mode": mode, "chunk_key": chunk_key})
            continue

        if owner != target_owner:
            non_company["other_owners"] += 1
            continue

        vehicle_pool_entries += 1
        unitnumber = common.get("unitnumber", 0)
        subtype = common.get("subtype", 0)

        # Qualification tête vs composant selon les règles OpenTTD 15.3 :
        # - Rail : (subtype & 1) != 0 -> Front Engine. Wagons ont unitnumber == 0 et subtype == 4.
        # - Road : (subtype & 1) != 0 -> Front Engine. Remorques/parties articulées ont unitnumber == 0.
        # - Air  : subtype in (0, 2) -> Aéronef/Hélicoptère. Ombres (4) et rotors (3) ont unitnumber == 0.
        # - Water: subtype == 0 et unitnumber > 0.
        is_primary = False
        is_component = False

        if mode == "rail":
            if (subtype & 0x01) != 0 and unitnumber > 0:
                is_primary = True
            elif unitnumber == 0 or subtype == 4:
                is_component = True
                components["rail_wagons"] += 1
        elif mode == "road":
            if (subtype & 0x01) != 0 and unitnumber > 0:
                is_primary = True
            elif unitnumber == 0 or (subtype & 0x02) != 0:
                is_component = True
                components["road_articulated_parts"] += 1
        elif mode == "air":
            if subtype in (0, 2) and unitnumber > 0:
                is_primary = True
            elif unitnumber == 0 or subtype in (3, 4):
                is_component = True
                components["aircraft_shadows_rotors"] += 1
        elif mode == "water":
            if subtype == 0 and unitnumber > 0:
                is_primary = True
            elif unitnumber == 0:
                is_component = True
                components["water_components"] += 1

        if not is_primary and not is_component:
            unclassified_entries.append({
                "index": idx,
                "reason": "unresolved_role",
                "mode": mode,
                "unitnumber": unitnumber,
                "subtype": subtype,
            })
            continue

        if not is_primary:
            continue

        # Véhicule pilotable identifié
        primary_counts[mode] += 1

        # Observables OpenTTD 15.3 (src/vehicle_base.h):
        # VehState::Hidden = 0 (1 << 0 = 0x01)
        # VehState::Stopped = 1 (1 << 1 = 0x02)
        # VehState::TrainSlowing = 4 (1 << 4 = 0x10)
        # VehState::AircraftBroken = 6 (1 << 6 = 0x40)
        # VehState::Crashed = 7 (1 << 7 = 0x80)
        vehstatus = common.get("vehstatus", 0)
        is_hidden = bool(vehstatus & 0x01)
        is_stopped = bool(vehstatus & 0x02)
        is_broken = bool(vehstatus & 0x40)
        is_crashed = bool(vehstatus & 0x80)
        is_not_stopped = not is_stopped
        is_running = not (is_stopped or is_hidden or is_broken or is_crashed)

        if is_stopped:
            stopped_count += 1
        else:
            not_stopped_count += 1

        if is_running:
            running_count += 1
        if is_hidden:
            hidden_count += 1
        if is_broken:
            broken_count += 1
        if is_crashed:
            crashed_count += 1

        # Suivi du convoi via le pointeur 1-based `next` (val - 1 = index)
        consist_indices = [idx]
        consist_capacities = defaultdict(int)
        consist_value = common.get("value", 0)

        # Capacité de la tête
        head_cap = common.get("cargo_cap", 0)
        head_cargo = common.get("cargo_type")
        if head_cap > 0 and head_cargo is not None:
            consist_capacities[head_cargo] += head_cap
            capacities_by_cargo[head_cargo] += head_cap

        next_ptr = common.get("next", 0)
        visited = {idx}
        consist_valid = True
        while next_ptr > 0:
            target_idx = next_ptr - 1
            if target_idx in visited:
                unclassified_entries.append({
                    "index": idx,
                    "target_index": target_idx,
                    "reason": "consist_cycle_detected",
                    "mode": mode,
                    "unitnumber": unitnumber,
                })
                consist_valid = False
                break
            visited.add(target_idx)

            comp_rec = record_by_index.get(target_idx)
            if comp_rec is None:
                unclassified_entries.append({
                    "index": idx,
                    "target_index": target_idx,
                    "reason": "corrupted_consist_pointer_missing_target",
                    "mode": mode,
                    "unitnumber": unitnumber,
                })
                consist_valid = False
                break

            comp_raw_type = comp_rec.get("type")
            comp_chunk_key = TYPE_TO_CHUNK_KEY.get(comp_raw_type, chunk_key)
            comp_common = _get_common(comp_rec, comp_chunk_key)
            if comp_common is None:
                unclassified_entries.append({
                    "index": idx,
                    "target_index": target_idx,
                    "reason": "missing_consist_component_common",
                    "mode": mode,
                    "unitnumber": unitnumber,
                })
                consist_valid = False
                break

            consist_indices.append(target_idx)
            c_cap = comp_common.get("cargo_cap", 0)
            c_cargo = comp_common.get("cargo_type")
            if c_cap > 0 and c_cargo is not None:
                consist_capacities[c_cargo] += c_cap
                capacities_by_cargo[c_cargo] += c_cap
            consist_value += comp_common.get("value", 0)
            next_ptr = comp_common.get("next", 0)

        primary_details.append({
            "index": idx,
            "mode": mode,
            "unitnumber": unitnumber,
            "subtype": subtype,
            "vehstatus": vehstatus,
            "is_stopped": is_stopped,
            "is_not_stopped": is_not_stopped,
            "is_running": is_running,
            "is_hidden": is_hidden,
            "is_broken": is_broken,
            "is_crashed": is_crashed,
            "speed": common.get("cur_speed", 0),
            "profit_this_year": common.get("profit_this_year", 0),
            "consist_indices": consist_indices,
            "consist_capacities": dict(consist_capacities),
            "consist_value": consist_value,
            "consist_valid": consist_valid,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "chunk_valid": True,
        "chunk_error": None,
        "vehicle_pool_entries": vehicle_pool_entries,
        "total_pool_entries": total_pool_entries,
        "primary_vehicles_count": sum(primary_counts.values()),
        "primary_vehicles_by_mode": primary_counts,
        "qualified_modes": dict(QUALIFIED_MODES),
        "components_breakdown": components,
        "unclassified_entries": unclassified_entries,
        "non_company_entries": non_company,
        "capacities_by_cargo": dict(capacities_by_cargo),
        "fleet_status": {
            "stopped": stopped_count,
            "not_stopped": not_stopped_count,
            "running": running_count,
            "hidden": hidden_count,
            "broken": broken_count,
            "crashed": crashed_count,
        },
        "primary_vehicles_detail": primary_details,
    }


def decode_stations(stnn_chunk: Union[dict, list, None], target_owner: int = 0) -> dict:
    """Décode le chunk STNN de manière exhaustive et qualifiée.

    Paramètres :
        stnn_chunk : chunk brut STNN (dict indexé ou liste d'enregistrements).
        target_owner : ID du joueur cible (défaut 0).

    Retourne :
        Dictionnaire conforme au schéma 1.1.0 avec :
        - `schema_version` : version du schéma ("1.1.0").
        - `chunk_valid` : booléen (False si chunk manquant ou de type inattendu).
        - `chunk_error` : None ou chaîne descriptive de l'erreur.
        - `total_stations` : total physique de gares possédées (multimodale = 1, None si invalid).
        - `station_ids` : liste des IDs des gares possédées.
        - `stations_by_facility` : présence d'infrastructures par type (rail, truck, bus, airport, dock).
        - `n_multimodal_stations` : nombre de gares combinant plusieurs modes.
        - `multimodal_station_ids` : liste des IDs des gares multimodales.
        - `stations_detail` : inventaire détaillé de chaque gare ({id, facilities, ratings, is_multimodal}).
        - `unresolved_stations` : enregistrements malformés ou sans propriétaire valide.
        - `other_owner_stations` : gares d'autres compagnies.
        - `ratings_by_station` : notes de gare disponibles ({station_id: [ratings]}).
    """
    if stnn_chunk is None or not isinstance(stnn_chunk, (dict, list)):
        err = "chunk_missing" if stnn_chunk is None else "invalid_chunk_type"
        return {
            "schema_version": SCHEMA_VERSION,
            "chunk_valid": False,
            "chunk_error": err,
            "total_stations": None,
            "station_ids": [],
            "stations_by_facility": {name: None for _, name in FACILITY_BITS},
            "n_multimodal_stations": None,
            "multimodal_station_ids": [],
            "stations_detail": [],
            "unresolved_stations": [{"reason": err}],
            "other_owner_stations": 0,
            "ratings_by_station": {},
        }

    if isinstance(stnn_chunk, dict):
        records = []
        for k, v in stnn_chunk.items():
            try:
                sid = int(k)
            except (ValueError, TypeError):
                sid = len(records)
            records.append((sid, v))
        records.sort(key=lambda x: x[0])
    else:
        records = [(i, r) for i, r in enumerate(stnn_chunk)]

    total_stations = 0
    facilities_counts = {name: 0 for _, name in FACILITY_BITS}
    multimodal_ids = []
    station_ids = []
    stations_detail = []
    unresolved = []
    other_owner_stations = 0
    ratings_by_station = {}

    for sid, stn in records:
        if not isinstance(stn, dict):
            unresolved.append({"id": sid, "reason": "not_a_dict", "record": str(stn)})
            continue

        body = _first(stn.get("normal"))
        if body is None:
            body = stn
        if not isinstance(body, dict):
            unresolved.append({"id": sid, "reason": "missing_normal_body"})
            continue

        base = _first(body.get("base"))
        if not isinstance(base, dict):
            unresolved.append({"id": sid, "reason": "missing_base"})
            continue

        owner = base.get("owner")
        if owner is None:
            unresolved.append({"id": sid, "reason": "missing_owner_in_base"})
            continue

        if owner != target_owner:
            other_owner_stations += 1
            continue

        total_stations += 1
        station_ids.append(sid)

        facil = base.get("facilities", 0)
        active_facilities = []
        for bit, name in FACILITY_BITS:
            if (facil & bit) != 0:
                active_facilities.append(name)
                facilities_counts[name] += 1

        is_multimodal = len(active_facilities) > 1
        if is_multimodal:
            multimodal_ids.append(sid)

        # Extraction des notes de gare
        ratings = []
        for good in body.get("goods") or []:
            if isinstance(good, dict):
                r = good.get("rating", 0)
                if r > 0:
                    ratings.append(r)
        if ratings:
            ratings_by_station[sid] = ratings

        stations_detail.append({
            "id": sid,
            "facilities": active_facilities,
            "is_multimodal": is_multimodal,
            "ratings": ratings,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "chunk_valid": True,
        "chunk_error": None,
        "total_stations": total_stations,
        "station_ids": station_ids,
        "stations_by_facility": facilities_counts,
        "n_multimodal_stations": len(multimodal_ids),
        "multimodal_station_ids": multimodal_ids,
        "stations_detail": stations_detail,
        "unresolved_stations": unresolved,
        "other_owner_stations": other_owner_stations,
        "ratings_by_station": ratings_by_station,
    }
