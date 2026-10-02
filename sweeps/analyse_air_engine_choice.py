"""Choix d'avion : profit par modèle et par distance, OpexAI contre AAAHogEx.

Lit un JSON de campagne dont ``line_telemetry.snapshots[]`` contient des
``lines[]`` (schéma de ``sweeps/bench_1v1_5y_20seeds.py``). Ne lance aucune
partie. Les duels C115 contre C121 au même schéma se lisent sans changement.

La distance demandée est le Manhattan des tuiles d'aéroport. ``map_x`` /
``map_y`` sont les log2 OpenTTD (8 → 256 tuiles), lus dans la configuration
embarquée ou dans le manifeste frère.

Une ligne aérienne est retenue seulement si la même identité
``(duel_policy_id, arm, seed, repeat, line_key_local)`` existait l'année
précédente. Le modèle est la capacité par avion : ``capacité / véhicules``
lorsque chaque cargo se divise exactement, sinon ``mixed``.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


DISTANCE_BANDS = (
    (0, 96),
    (96, 128),
    (128, 160),
    (160, 192),
    (192, 10_000_000),
)

# Capacités : mois où un seul EngineID augmente de N et où le delta de
# capacité est divisible par N, JSONL
# results/lineprofit_default_5x6_20260926.jsonl (recalcul 2026-10-02).
# Noms : results/diag_nuit_air_solo_probe_c82.json, latest_factors.
# Les identifiants sans nom publié restent sans libellé.
SIGNATURE_LABELS = {
    "0:65|2:8": "216",
    "0:90|2:10": "217 FFP_Dart",
    "2:100": "217 FFP_Dart courrier",
    "0:100|2:20": "218 Yate_Haugan",
    "2:120": "218 Yate_Haugan courrier",
    "0:200|2:30": "220",
    "2:230": "220 courrier",
    "0:100|2:15": "221 Bakewell_Luckett_LB-9",
    "2:115": "221 Bakewell_Luckett_LB-9 courrier",
    "0:220|2:40": "223 Bakewell_Luckett_LB-10",
    "2:260": "223 Bakewell_Luckett_LB-10 courrier",
    "0:95|2:10": "225 Yate_Aerospace_YAC_1-11",
    "2:105": "225 Yate_Aerospace_YAC_1-11 courrier",
    "0:170|2:35": "226",
    "2:205": "226 courrier",
    "0:110|2:15": "227 Darwin_200",
    "2:125": "227 Darwin_200 courrier",
    "0:300|2:50": "228 Darwin_300",
    "0:240|2:35": "232",
    "2:275": "232 courrier",
    "2:290": "233 courrier",
}

AI_ORDER = ("OpexAI", "AAAHogEx")


def _round(value, digits=6):
    if value is None:
        return None
    return round(float(value), digits)


def _mean(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return _round(statistics.mean(values)) if values else None


def _median(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return _round(statistics.median(values)) if values else None


def _dist(values):
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": _round(statistics.mean(values)),
        "median": _round(statistics.median(values)),
        "min": _round(min(values)),
        "max": _round(max(values)),
    }


def _idiv(numerator, denominator):
    """Division entière vers zéro, comme ``/`` Squirrel sur des entiers ≥ 0."""
    if denominator == 0:
        raise ZeroDivisionError("division entiere par zero")
    return int(numerator) // int(denominator)


def per_vehicle_signature(capacity_by_cargo, vehicles):
    """Signature de modèle. ``mixed`` si la capacité n'est pas homogène."""
    if not isinstance(vehicles, int) or vehicles <= 0:
        return "unknown"
    if not isinstance(capacity_by_cargo, dict) or not capacity_by_cargo:
        return "empty"
    parts = []
    for cargo, capacity in sorted(capacity_by_cargo.items(), key=lambda item: str(item[0])):
        if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):
            return "mixed"
        if isinstance(capacity, float) and not capacity.is_integer():
            return "mixed"
        capacity = int(capacity)
        if capacity < 0 or capacity % vehicles != 0:
            return "mixed"
        per_vehicle = capacity // vehicles
        if per_vehicle == 0:
            continue
        parts.append(f"{cargo}:{per_vehicle}")
    return "|".join(parts) if parts else "empty"


def is_mail_only(signature):
    if signature in ("mixed", "empty", "unknown"):
        return False
    parts = [part for part in signature.split("|") if part]
    return bool(parts) and all(part.startswith("2:") for part in parts)


def signature_label(signature):
    label = SIGNATURE_LABELS.get(signature)
    if label:
        return f"{signature} ({label})"
    return signature


def distance_band(manhattan):
    if manhattan is None:
        return None
    for low, high in DISTANCE_BANDS:
        if low <= manhattan < high:
            return f"[{low},{high})"
    return None


def _tile_xy(tile, map_width):
    if isinstance(tile, bool) or not isinstance(tile, int) or tile < 0 or map_width <= 0:
        return None
    return tile % map_width, tile // map_width


def _endpoint_tiles(line):
    tiles = []
    for endpoint in line.get("endpoint_cargo_stats") or []:
        airport = endpoint.get("airport") if isinstance(endpoint, dict) else None
        tile = None
        if isinstance(airport, dict) and isinstance(airport.get("tile"), int):
            tile = airport.get("tile")
        elif isinstance(endpoint, dict) and isinstance(endpoint.get("tile"), int):
            tile = endpoint.get("tile")
        if isinstance(tile, int) and tile >= 0 and tile not in tiles:
            tiles.append(tile)
    if len(tiles) >= 2:
        return tiles[:2]
    fallback = []
    for tile in line.get("ordered_station_tiles") or []:
        if isinstance(tile, int) and tile >= 0 and tile not in fallback:
            fallback.append(tile)
    return fallback[:2]


def manhattan_distance(line, map_width):
    tiles = _endpoint_tiles(line)
    if len(tiles) < 2 or map_width is None:
        return None
    first = _tile_xy(tiles[0], map_width)
    second = _tile_xy(tiles[1], map_width)
    if first is None or second is None:
        return None
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def _configuration_map(configuration):
    if not isinstance(configuration, dict):
        return None
    parsed = configuration.get("parsed")
    if isinstance(parsed, dict):
        for section in parsed.values():
            if isinstance(section, dict) and "map_x" in section and "map_y" in section:
                return section.get("map_x"), section.get("map_y"), "configuration.parsed"
    raw = configuration.get("raw")
    if isinstance(raw, str):
        found = {}
        for line in raw.splitlines():
            if "=" not in line or line.strip().startswith(("#", ";")):
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in ("map_x", "map_y"):
                found[key] = value.strip()
        if "map_x" in found and "map_y" in found:
            return found["map_x"], found["map_y"], "configuration.raw"
    return None


def _manifest_candidates(payload, path):
    path = Path(path) if path else None
    names = []
    manifest_path = payload.get("manifest_path") if isinstance(payload, dict) else None
    if isinstance(manifest_path, str) and manifest_path:
        names.append(Path(manifest_path).name)
    campaign_id = payload.get("campaign_id") if isinstance(payload, dict) else None
    if isinstance(campaign_id, str) and campaign_id:
        names.append(campaign_id + ".manifest.json")
    if path is not None:
        names.append(path.name + ".manifest.json")
        if path.suffix:
            names.append(path.with_suffix(".manifest.json").name)
    seen = []
    for name in names:
        if name and name not in seen:
            seen.append(name)
    if path is None:
        return []
    return [path.parent / name for name in seen]


def resolve_map(payload, path=None):
    """``map_x`` log2 → largeur en tuiles. Source embarquée, puis manifeste frère."""
    found = _configuration_map(payload.get("configuration") if isinstance(payload, dict) else None)
    source = None
    map_x = map_y = None
    if found is not None:
        map_x, map_y, source = found
    else:
        for candidate in _manifest_candidates(payload, path):
            if not candidate.is_file():
                continue
            try:
                manifest = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            found = _configuration_map((manifest or {}).get("configuration"))
            if found is not None:
                map_x, map_y, source = found
                source = f"{candidate.name}:{source}"
                break
    if map_x is None or map_y is None:
        return {"map_x": None, "map_y": None, "width": None, "height": None, "source": None}
    try:
        map_x_int = int(str(map_x).strip())
        map_y_int = int(str(map_y).strip())
    except ValueError:
        return {"map_x": None, "map_y": None, "width": None, "height": None, "source": source}
    if not 1 <= map_x_int <= 16 or not 1 <= map_y_int <= 16:
        return {"map_x": map_x_int, "map_y": map_y_int, "width": None, "height": None, "source": source}
    return {
        "map_x": map_x_int,
        "map_y": map_y_int,
        "width": 1 << map_x_int,
        "height": 1 << map_y_int,
        "source": source,
    }


def _snapshots(payload):
    if not isinstance(payload, dict):
        return []
    telemetry = payload.get("line_telemetry")
    if isinstance(telemetry, dict) and isinstance(telemetry.get("snapshots"), list):
        return telemetry["snapshots"]
    if isinstance(payload.get("snapshots"), list):
        return payload["snapshots"]
    return []


def _norm_int(value, default=None):
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return default


def _line_profit(line):
    if "profit_this_year_gbp" not in line:
        return None
    value = line.get("profit_this_year_gbp")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _cargo_endpoint_stats(line, cargo="0"):
    ratings = []
    waitings = []
    for endpoint in line.get("endpoint_cargo_stats") or []:
        goods = (endpoint or {}).get("cargo") or {}
        good = goods.get(cargo)
        if good is None:
            good = goods.get(int(cargo)) if isinstance(cargo, str) and cargo.isdigit() else None
        if not isinstance(good, dict):
            continue
        rating = good.get("rating")
        waiting = good.get("max_waiting_cargo")
        if isinstance(rating, (int, float)) and not isinstance(rating, bool):
            ratings.append(float(rating))
        if isinstance(waiting, (int, float)) and not isinstance(waiting, bool):
            waitings.append(float(waiting))
    return (
        min(ratings) if ratings else None,
        max(waitings) if waitings else None,
    )


def _airport_ends(line):
    ends = []
    for endpoint in line.get("endpoint_cargo_stats") or []:
        if not isinstance(endpoint, dict):
            continue
        station_id = endpoint.get("station_id")
        town_id = endpoint.get("town_id")
        airport = endpoint.get("airport") if isinstance(endpoint.get("airport"), dict) else {}
        tile = airport.get("tile") if isinstance(airport.get("tile"), int) else endpoint.get("tile")
        if station_id is None and tile is None:
            continue
        ends.append({
            "station_id": station_id if station_id is not None else f"tile:{tile}",
            "town_id": town_id,
            "airport_type": airport.get("type"),
        })
    if ends:
        return ends
    towns = list(line.get("town_ids") or [])
    for index, tile in enumerate(line.get("ordered_station_tiles") or []):
        if not isinstance(tile, int):
            continue
        ends.append({
            "station_id": f"tile:{tile}",
            "town_id": towns[index] if index < len(towns) else None,
            "airport_type": None,
        })
    return ends


def collect_air_lines(payload, path=None):
    """Lignes aériennes d'au moins un an, une observation par instantané de décembre."""
    map_info = resolve_map(payload, path)
    width = map_info["width"]
    present = set()
    raw = []
    for snapshot in _snapshots(payload):
        if not isinstance(snapshot, dict):
            continue
        year = _norm_int(snapshot.get("year"))
        if year is None:
            continue
        policy = snapshot.get("duel_policy_id")
        arm = snapshot.get("arm")
        seed = snapshot.get("seed")
        repeat = _norm_int(snapshot.get("repeat"), 0)
        for line in snapshot.get("lines") or []:
            if not isinstance(line, dict):
                continue
            if str(line.get("mode") or "").lower() != "air":
                continue
            key = line.get("line_key_local")
            if not key:
                continue
            identity = (str(policy), str(arm), seed, repeat, year, str(key))
            present.add(identity)
            raw.append((identity, line))

    mature = []
    for identity, line in raw:
        policy, arm, seed, repeat, year, key = identity
        if (policy, arm, seed, repeat, year - 1, key) not in present:
            continue
        vehicles = line.get("vehicles")
        if not isinstance(vehicles, int) or isinstance(vehicles, bool) or vehicles <= 0:
            continue
        signature = per_vehicle_signature(line.get("capacity_by_cargo") or {}, vehicles)
        distance = manhattan_distance(line, width)
        profit = _line_profit(line)
        profit_per = None if profit is None else profit / vehicles
        rating, waiting = _cargo_endpoint_stats(line)
        mature.append({
            "duel_policy_id": policy,
            "arm": arm,
            "seed": seed,
            "repeat": repeat,
            "year": year,
            "line_key_local": key,
            "vehicles": vehicles,
            "signature": signature,
            "label": signature_label(signature),
            "mail_only": is_mail_only(signature),
            "manhattan": distance,
            "band": distance_band(distance),
            "profit_gbp": profit,
            "profit_per_aircraft_gbp": profit_per,
            "min_pax_rating": rating,
            "max_pax_waiting": waiting,
            "ends": _airport_ends(line),
        })
    return map_info, mature


def _group_key(row):
    return (str(row["duel_policy_id"]), str(row["arm"]))


def _profit_block(rows):
    per_line = [row["profit_per_aircraft_gbp"] for row in rows if row["profit_per_aircraft_gbp"] is not None]
    profit_sum = 0.0
    vehicle_sum = 0
    valued = 0
    for row in rows:
        if row["profit_gbp"] is None:
            continue
        profit_sum += row["profit_gbp"]
        vehicle_sum += row["vehicles"]
        valued += 1
    weighted = (profit_sum / vehicle_sum) if vehicle_sum else None
    return {
        "lines": len(rows),
        "lines_with_profit": valued,
        "aircraft": sum(row["vehicles"] for row in rows),
        "profit_per_aircraft_line_level": _dist(per_line),
        "profit_per_aircraft_weighted_mean_gbp": _round(weighted),
        "profit_sum_gbp": _round(profit_sum) if valued else None,
    }


def _model_rows(rows):
    by_sig = defaultdict(list)
    for row in rows:
        by_sig[row["signature"]].append(row)
    models = []
    aircraft_total = sum(row["vehicles"] for row in rows) or 0
    for signature, group in sorted(by_sig.items(), key=lambda item: -sum(r["vehicles"] for r in item[1])):
        block = _profit_block(group)
        block.update({
            "signature": signature,
            "label": signature_label(signature),
            "mail_only": bool(group and group[0]["mail_only"]),
            "aircraft_share": _round(block["aircraft"] / aircraft_total) if aircraft_total else None,
        })
        models.append(block)
    return models


def _band_rows(rows):
    by_key = defaultdict(list)
    for row in rows:
        by_key[(row["signature"], row["band"])].append(row)
    bands = []
    for (signature, band), group in sorted(by_key.items(), key=lambda item: (item[0][0], item[0][1] or "")):
        block = _profit_block(group)
        block.update({
            "signature": signature,
            "label": signature_label(signature),
            "distance_band": band,
        })
        bands.append(block)
    return bands


def _structure(rows):
    """Avions/ligne sur les lignes ; lignes/aéroport et aéroports/ville par instantané, puis moyenne."""
    snapshot_lines = defaultdict(list)
    for row in rows:
        snapshot_lines[(row["seed"], row["repeat"], row["year"])].append(row)
    lines_per_airport_means = []
    airports_per_town_means = []
    towns = []
    airports = []
    max_lines = []
    for group in snapshot_lines.values():
        airport_lines = defaultdict(int)
        airport_town = {}
        for row in group:
            seen_stations = set()
            for end in row["ends"]:
                station_id = end["station_id"]
                if station_id in seen_stations:
                    continue
                seen_stations.add(station_id)
                airport_lines[station_id] += 1
                if end["town_id"] is not None:
                    airport_town[station_id] = end["town_id"]
        if airport_lines:
            counts = list(airport_lines.values())
            lines_per_airport_means.append(statistics.mean(counts))
            max_lines.append(max(counts))
            airports.append(len(airport_lines))
        town_sets = defaultdict(set)
        for station_id, town_id in airport_town.items():
            town_sets[town_id].add(station_id)
        if town_sets:
            airports_per_town_means.append(statistics.mean([len(items) for items in town_sets.values()]))
            towns.append(len(town_sets))
    return {
        "aircraft_per_line": _dist([row["vehicles"] for row in rows]),
        "lines_per_airport": _dist(lines_per_airport_means),
        "lines_per_airport_max_of_snapshot_max": _round(max(max_lines)) if max_lines else None,
        "airports_per_town": _dist(airports_per_town_means),
        "airports_per_snapshot": _dist(airports),
        "towns_per_snapshot": _dist(towns),
        "snapshots": len(snapshot_lines),
    }


def _service(rows):
    return {
        "min_pax_rating": _dist([row["min_pax_rating"] for row in rows if row["min_pax_rating"] is not None]),
        "max_pax_waiting": _dist([row["max_pax_waiting"] for row in rows if row["max_pax_waiting"] is not None]),
        "mail_only_aircraft": sum(row["vehicles"] for row in rows if row["mail_only"]),
        "mail_only_lines": sum(1 for row in rows if row["mail_only"]),
    }


def _year_report(rows):
    by_year = defaultdict(list)
    for row in rows:
        by_year[row["year"]].append(row)
    years = {}
    for year in sorted(by_year):
        group = by_year[year]
        years[str(year)] = {
            "models": _model_rows(group),
            "profit_by_model_and_distance": _band_rows(group),
            "structure": _structure(group),
            "service": _service(group),
            "profit": _profit_block(group),
        }
    return years


def _cell_table(rows, key_fn, unmatched_singletons=False):
    table = {}
    for index, row in enumerate(rows):
        if row["profit_gbp"] is None:
            continue
        key = key_fn(row)
        if key is None or (isinstance(key, tuple) and None in key):
            if not unmatched_singletons:
                continue
            key = ("__sans_cle__", index)
        cell = table.setdefault(key, {"profit": 0.0, "aircraft": 0, "per_aircraft": []})
        cell["profit"] += row["profit_gbp"]
        cell["aircraft"] += row["vehicles"]
        cell["per_aircraft"].append(row["profit_per_aircraft_gbp"])
    return table


def decompose_profit_gap(opex_rows, aaa_rows, key_fn):
    """Décomposition de Kitagawa du profit moyen pondéré par les avions.

    Écart = composition (mix, valorisé au taux Opex) + taux (même cellule) +
    hors support (cellule absente d'un bras). Comptable, pas causal.
    """
    opex = _cell_table(opex_rows, key_fn, unmatched_singletons=True)
    aaa = _cell_table(aaa_rows, key_fn, unmatched_singletons=True)
    opex_aircraft = sum(cell["aircraft"] for cell in opex.values())
    aaa_aircraft = sum(cell["aircraft"] for cell in aaa.values())
    opex_profit = sum(cell["profit"] for cell in opex.values())
    aaa_profit = sum(cell["profit"] for cell in aaa.values())
    mu_opex = (opex_profit / opex_aircraft) if opex_aircraft else None
    mu_aaa = (aaa_profit / aaa_aircraft) if aaa_aircraft else None
    if not opex_aircraft or not aaa_aircraft:
        return {
            "comparable": False,
            "reason": "profit ou avions absents",
        }
    composition = 0.0
    rate = 0.0
    common_aircraft = {"OpexAI": 0, "AAAHogEx": 0}
    outside_profit = {"OpexAI": 0.0, "AAAHogEx": 0.0}
    outside_aircraft = {"OpexAI": 0, "AAAHogEx": 0}
    outside_cells = {"OpexAI": [], "AAAHogEx": []}
    for key in set(opex) | set(aaa):
        left = opex.get(key)
        right = aaa.get(key)
        if left and right and left["aircraft"] and right["aircraft"]:
            mu_o = left["profit"] / left["aircraft"]
            mu_a = right["profit"] / right["aircraft"]
            weight_o = left["aircraft"] / opex_aircraft
            weight_a = right["aircraft"] / aaa_aircraft
            composition += (weight_a - weight_o) * mu_o
            rate += weight_a * (mu_a - mu_o)
            common_aircraft["OpexAI"] += left["aircraft"]
            common_aircraft["AAAHogEx"] += right["aircraft"]
        elif left:
            outside_profit["OpexAI"] += left["profit"]
            outside_aircraft["OpexAI"] += left["aircraft"]
            outside_cells["OpexAI"].append(_cell_name(key))
        elif right:
            outside_profit["AAAHogEx"] += right["profit"]
            outside_aircraft["AAAHogEx"] += right["aircraft"]
            outside_cells["AAAHogEx"].append(_cell_name(key))
    outside = (outside_profit["AAAHogEx"] / aaa_aircraft) - (outside_profit["OpexAI"] / opex_aircraft)
    gap = mu_aaa - mu_opex
    return {
        "comparable": True,
        "kind": "estimation comptable, pas la formule d'AAAHogEx",
        "opex_weighted_mean_gbp": _round(mu_opex),
        "aaa_weighted_mean_gbp": _round(mu_aaa),
        "gap_aaa_minus_opex_gbp": _round(gap),
        "composition_at_opex_rates_gbp": _round(composition),
        "same_cell_rate_gbp": _round(rate),
        "outside_support_gbp": _round(outside),
        "identity_residual_gbp": _round(gap - (composition + rate + outside)),
        "shares_of_gap": _shares(gap, composition, rate, outside),
        "common_support_aircraft": common_aircraft,
        "common_support_aircraft_share": {
            "OpexAI": _round(common_aircraft["OpexAI"] / opex_aircraft),
            "AAAHogEx": _round(common_aircraft["AAAHogEx"] / aaa_aircraft),
        },
        "outside_support_aircraft": outside_aircraft,
        "outside_support_cells": {
            arm: sorted(name for name in names if not str(name).startswith("__sans_cle__"))[:40]
            for arm, names in outside_cells.items()
        },
    }


def _cell_name(key):
    if isinstance(key, tuple):
        return "|".join("" if part is None else str(part) for part in key)
    return str(key)


def _shares(gap, composition, rate, outside):
    if gap == 0:
        return None
    return {
        "composition": _round(composition / gap),
        "same_cell_rate": _round(rate / gap),
        "outside_support": _round(outside / gap),
    }


def matched_profit(opex_rows, aaa_rows, key_fn):
    """Test clé : même signature et même distance, profit par avion des deux IA."""
    opex = _cell_table(opex_rows, key_fn)
    aaa = _cell_table(aaa_rows, key_fn)
    cells = []
    weight_total = 0
    weight_aaa_higher = 0
    for key in sorted(set(opex) & set(aaa), key=lambda item: _cell_name(item)):
        left = opex[key]
        right = aaa[key]
        if not left["aircraft"] or not right["aircraft"]:
            continue
        opex_median = _median(left["per_aircraft"])
        aaa_median = _median(right["per_aircraft"])
        opex_mean = left["profit"] / left["aircraft"]
        aaa_mean = right["profit"] / right["aircraft"]
        weight = min(left["aircraft"], right["aircraft"])
        weight_total += weight
        higher = aaa_median is not None and opex_median is not None and aaa_median > opex_median
        if higher:
            weight_aaa_higher += weight
        signature, distance = key if isinstance(key, tuple) else (key, None)
        cells.append({
            "signature": signature,
            "label": signature_label(signature),
            "distance": distance,
            "opex_aircraft": left["aircraft"],
            "aaa_aircraft": right["aircraft"],
            "opex_median_gbp": opex_median,
            "aaa_median_gbp": aaa_median,
            "median_gap_aaa_minus_opex_gbp": (
                None if aaa_median is None or opex_median is None else _round(aaa_median - opex_median)
            ),
            "opex_weighted_mean_gbp": _round(opex_mean),
            "aaa_weighted_mean_gbp": _round(aaa_mean),
            "weighted_mean_gap_gbp": _round(aaa_mean - opex_mean),
            "aaa_median_strictly_higher": bool(higher),
        })
    opex_aircraft = sum(row["vehicles"] for row in opex_rows if row["profit_gbp"] is not None)
    aaa_aircraft = sum(row["vehicles"] for row in aaa_rows if row["profit_gbp"] is not None)
    matched_opex = sum(cell["opex_aircraft"] for cell in cells)
    matched_aaa = sum(cell["aaa_aircraft"] for cell in cells)
    gaps = [cell["median_gap_aaa_minus_opex_gbp"] for cell in cells if cell["median_gap_aaa_minus_opex_gbp"] is not None]
    higher_cells = sum(1 for cell in cells if cell["aaa_median_strictly_higher"])
    overlap_opex = (matched_opex / opex_aircraft) if opex_aircraft else None
    overlap_aaa = (matched_aaa / aaa_aircraft) if aaa_aircraft else None
    if not cells or overlap_opex is None or overlap_aaa is None or min(overlap_opex, overlap_aaa) < 0.15:
        code = "insufficient_overlap"
    elif weight_total and (weight_aaa_higher / weight_total) > 0.5:
        code = "aaa_higher_inside_cells"
    else:
        code = "aaa_not_higher_inside_cells"
    return {
        "cells": cells,
        "summary": {
            "cell_count": len(cells),
            "cells_aaa_median_strictly_higher": higher_cells,
            "median_of_cell_median_gaps_gbp": _median(gaps),
            "aircraft_weighted_share_of_cells_where_aaa_median_higher": (
                _round(weight_aaa_higher / weight_total) if weight_total else None
            ),
            "matched_aircraft": {"OpexAI": matched_opex, "AAAHogEx": matched_aaa},
            "share_of_arm_aircraft_in_matched_cells": {
                "OpexAI": _round(overlap_opex) if overlap_opex is not None else None,
                "AAAHogEx": _round(overlap_aaa) if overlap_aaa is not None else None,
            },
            "conclusion_code": code,
        },
    }


def _exact_key(row):
    if row["manhattan"] is None:
        return None
    return (row["signature"], row["manhattan"])


def _band_key(row):
    if row["band"] is None:
        return None
    return (row["signature"], row["band"])


def _signature_key(row):
    return (row["signature"],)


def aaa_rank_bidirectional_passenger(engines, route):
    """Transcription statique d'AAAHogEx pour un air passagers aller-retour.

    Estimation de modèle. Elle suit ``GetEngineSetsVt``, ``Estimate`` et
    ``GetValue`` pour la branche ``interval <= 10`` et ``routeIncome >= 0``.
    Elle ne classe pas si l'intervalle entier dépasse 10 : la branche stock
    n'est pas réécrite ici. Les unités de prix, de coût et de tarif sont
    celles fournies par l'appelant, sans table OpenTTD.
    """
    required_route = (
        "dx", "dy", "production", "order_distance", "supports_big",
        "income_pax", "income_mail", "profit_model", "station_date_span",
    )
    missing = [name for name in required_route if name not in route]
    if missing:
        return {"status": "incomplete", "missing": missing, "winner": None, "ranked": []}
    if route["profit_model"] not in ("roi", "building_time", "vehicle"):
        return {"status": "incomplete", "missing": ["profit_model"], "winner": None, "ranked": []}
    ranked = []
    refused = []
    for engine in engines:
        outcome = _aaa_one_engine(engine, route)
        if outcome.get("status") == "ranked":
            ranked.append(outcome)
        else:
            refused.append(outcome)
    ranked.sort(key=lambda item: item["value"], reverse=True)
    winner = None
    tie = False
    if ranked:
        winner = ranked[0]["engine_id"]
        tie = len(ranked) > 1 and ranked[1]["value"] == ranked[0]["value"]
        if tie:
            winner = None
    return {
        "status": "ranked" if ranked else "no_eligible_engine",
        "kind": "estimation de modele",
        "winner": winner,
        "tie": tie,
        "ranked": ranked,
        "refused": refused,
    }


def _aaa_one_engine(engine, route):
    engine_id = engine.get("id")
    needed = ("speed", "running_cost", "price", "pax_capacity", "mail_capacity", "max_order_distance", "is_big")
    missing = [name for name in needed if name not in engine]
    if missing:
        return {"status": "incomplete", "engine_id": engine_id, "missing": missing}
    if engine["is_big"] and not route["supports_big"]:
        return {"status": "refused", "engine_id": engine_id, "reason": "gros_avion_aeroport"}
    max_order = int(engine["max_order_distance"])
    if max_order != 0 and not max_order > int(route["order_distance"]):
        return {"status": "refused", "engine_id": engine_id, "reason": "autonomie"}
    capacity = int(engine["pax_capacity"])
    if capacity <= 0 or int(engine["speed"]) <= 0 or int(route["production"]) <= 0:
        return {"status": "refused", "engine_id": engine_id, "reason": "capacite_ou_production"}
    speed = int(engine["speed"])
    speed_rate = max(_idiv(min(255, speed) - 85, 4), 0)
    if route.get("rich"):
        speed_rate += 26
    station_rate = speed_rate + 170
    dx, dy = int(route["dx"]), int(route["dy"])
    path = int(min(dx, dy) * 0.414 + max(dx, dy))
    real_path = path + 30
    if route.get("breakdowns"):
        real_path += 50
    day_length = int(route.get("day_length") or 1)
    cruise_days = max(1, _idiv(_idiv(_idiv(real_path * 664, speed), 24), day_length))
    loading_time = max(1, _idiv(capacity + 74 - 1, 74))
    days = max(1, (cruise_days + loading_time) * 2)
    span = int(route["station_date_span"])
    if span <= 0:
        return {"status": "refused", "engine_id": engine_id, "reason": "station_date_span"}
    days_est = _idiv(_idiv(path * 664, speed), 24)
    vehicle_length = int(route.get("vehicle_length") or 8)
    max_vehicles = min(_idiv(days_est * 2, span) + 1, _idiv((path + 4) * 16, vehicle_length)) + 2
    room = route.get("vehicles_room")
    if room is not None:
        max_vehicles = max(1, min(max_vehicles, int(room)))
    max_route_capacity = _idiv(30 * capacity, span)
    rated = _idiv(int(route["production"]) * station_rate, 255)
    if rated <= 0:
        return {"status": "refused", "engine_id": engine_id, "reason": "production_notee_nulle"}
    deliverable = min(rated, max_route_capacity)
    vehicles = max(min(max_vehicles, _idiv(deliverable * 12 * days, 365 * capacity) + 1), 1)
    interval = _idiv(cruise_days * 2 + loading_time, vehicles)
    if interval > 10:
        return {"status": "refused", "engine_id": engine_id, "reason": "intervalle_sup_10_non_transcrit"}
    interval_stock = _idiv(_idiv(rated * days, 30), vehicles)
    waiting = max(loading_time, _idiv(max(0, capacity - interval_stock) * 30, rated))
    cargo_income = int(route["income_pax"](int(route.get("total_distance", dx + dy)), cruise_days))
    mail_income = int(route["income_mail"](int(route.get("total_distance", dx + dy)), cruise_days))
    mail_capacity = int(engine["mail_capacity"])
    one_way = (cargo_income * capacity) + (mail_income * mail_capacity)
    income_per_trip = one_way + one_way
    total_days = max(1, cruise_days * 2 + waiting + loading_time)
    income = _idiv(income_per_trip * 365, total_days)
    income = _idiv(int(route.get("future_income_rate") or 100) * income, 100) - int(engine["running_cost"])
    route_income = income * vehicles - int(route.get("infrastructure_cost") or 0)
    if route_income < 0:
        return {"status": "refused", "engine_id": engine_id, "reason": "revenu_ligne_negatif"}
    half = _idiv(route_income, 2)
    lost = _idiv(half * (cruise_days + waiting), 365) + _idiv(
        half * (cruise_days * 2 + loading_time + waiting), 365
    )
    building_cost = int(route.get("building_cost") or 0)
    cost = max(1, int(engine["price"]) * vehicles + building_cost + lost)
    roi = _idiv(route_income * 1000, cost)
    building_time = 300 + vehicles * 3
    per_vehicle = _idiv(route_income, vehicles)
    per_building = _idiv(route_income, building_time)
    model = route["profit_model"]
    if model == "roi":
        value = roi
    elif model == "building_time":
        value = per_building
    else:
        value = per_vehicle
    return {
        "status": "ranked",
        "engine_id": engine_id,
        "value": value,
        "roi": roi,
        "income_per_vehicle": per_vehicle,
        "income_per_building_time": per_building,
        "route_income": route_income,
        "vehicles": vehicles,
        "cruise_days": cruise_days,
        "waiting": waiting,
        "loading_time": loading_time,
    }


def aaa_formula_counterfactual(opex_rows, engines=None, route_economics=None):
    """Applique la formule AAA aux routes Opex observées, ou dit ce qui manque.

    ``route_economics`` doit fournir, par route, production, tarifs et modèle
    de valeur. Ces grandeurs ne sont pas dans la télémétrie de ligne.
    """
    routes = [row for row in opex_rows if row.get("manhattan") is not None]
    missing = []
    if not engines:
        missing.append(
            "catalogue 1970-1980 : vitesse, cout d'exploitation, autonomie, "
            "gros avion ou petit avion ; prix publies seulement pour 217 et 223"
        )
    if route_economics is None:
        missing.append("tarif passagers et courrier selon distance et jours")
        missing.append("production mensuelle au moment du choix")
        missing.append("modele de valeur actif : roi, temps de chantier, ou revenu par vehicule")
    if missing:
        return {
            "status": "incomplete",
            "kind": "estimation de modele",
            "routes_with_distance": len(routes),
            "choices": None,
            "missing": missing,
        }
    choices = []
    for index, row in enumerate(routes):
        extra = route_economics(row, index)
        if not extra:
            choices.append({"line_key_local": row["line_key_local"], "status": "incomplete"})
            continue
        route = dict(extra)
        route.setdefault("dx", row["manhattan"])
        route.setdefault("dy", 0)
        route.setdefault("order_distance", row["manhattan"])
        ranked = aaa_rank_bidirectional_passenger(engines, route)
        choices.append({
            "line_key_local": row["line_key_local"],
            "year": row["year"],
            "observed_signature": row["signature"],
            "manhattan": row["manhattan"],
            "status": ranked["status"],
            "winner": ranked["winner"],
            "tie": ranked.get("tie"),
        })
    return {
        "status": "estimated",
        "kind": "estimation de modele",
        "routes_with_distance": len(routes),
        "choices": choices,
        "missing": [],
    }


def _arm_bundle(rows):
    return {
        "by_year": _year_report(rows),
        "pooled": {
            "models": _model_rows(rows),
            "profit_by_model_and_distance": _band_rows(rows),
            "structure": _structure(rows),
            "service": _service(rows),
            "profit": _profit_block(rows),
        },
    }


def analyse_campaign(payload, path=None):
    map_info, mature = collect_air_lines(payload, path)
    grouped = defaultdict(list)
    for row in mature:
        grouped[_group_key(row)].append(row)
    by_arm = {}
    for (policy, arm), rows in sorted(grouped.items()):
        by_arm[f"{policy}|{arm}"] = {
            "duel_policy_id": policy,
            "arm": arm,
            **_arm_bundle(rows),
        }
    comparisons = []
    policies = sorted({policy for policy, _arm in grouped})
    for policy in policies:
        opex_rows = grouped.get((policy, "OpexAI"), [])
        aaa_rows = grouped.get((policy, "AAAHogEx"), [])
        if not opex_rows or not aaa_rows:
            continue
        exact = matched_profit(opex_rows, aaa_rows, _exact_key)
        band = matched_profit(opex_rows, aaa_rows, _band_key)
        comparisons.append({
            "duel_policy_id": policy,
            "matched_same_model_same_manhattan": {
                "summary": exact["summary"],
                "cells": exact["cells"],
            },
            "matched_same_model_same_distance_band": {
                "summary": band["summary"],
                "cells": band["cells"],
            },
            "attribution": {
                "by_model": decompose_profit_gap(opex_rows, aaa_rows, _signature_key),
                "by_model_and_distance_band": decompose_profit_gap(opex_rows, aaa_rows, _band_key),
            },
            "aaa_formula_counterfactual": aaa_formula_counterfactual(opex_rows),
        })
    return {
        "schema_version": 1,
        "source": str(path) if path else None,
        "campaign_id": payload.get("campaign_id") if isinstance(payload, dict) else None,
        "policies": payload.get("policies") if isinstance(payload, dict) else None,
        "map": map_info,
        "mature_air_line_rule": (
            "mode air, vehicules > 0, meme line_key_local present l'annee precedente "
            "dans le meme duel, le meme bras, la meme graine et la meme repetition"
        ),
        "distance": "Manhattan des deux premieres tuiles d'aeroport ; map_x log2 donne la largeur",
        "model": "capacite par cargo divisee par le nombre d'avions si la division est entiere, sinon mixed",
        "mature_air_lines": len(mature),
        "by_arm": by_arm,
        "comparisons": comparisons,
    }


def analyse_path(path):
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return analyse_campaign(payload, path)


def _fmt_gbp(value):
    if value is None:
        return "n.d."
    return f"{value:,.0f} £".replace(",", " ")


def _fmt_num(value):
    if value is None:
        return "n.d."
    return f"{value:.3f}".rstrip("0").rstrip(".")


def render_text(report):
    lines = [
        f"Campagne {report.get('campaign_id') or report.get('source')}",
        (
            f"Carte map_x={report['map'].get('map_x')} map_y={report['map'].get('map_y')} "
            f"largeur={report['map'].get('width')} source={report['map'].get('source')}"
        ),
        f"Lignes aériennes d'au moins un an : {report['mature_air_lines']}",
    ]
    for key, arm_report in report["by_arm"].items():
        pooled = arm_report["pooled"]
        profit = pooled["profit"]["profit_per_aircraft_line_level"]
        structure = pooled["structure"]
        lines.append(
            f"{key} : médiane profit/avion {_fmt_gbp(profit['median'])} "
            f"(moyenne {_fmt_gbp(profit['mean'])}, n={profit['n']}) ; "
            f"avions/ligne moyenne {_fmt_num(structure['aircraft_per_line']['mean'])} ; "
            f"lignes/aéroport moyenne des instantanés {_fmt_num(structure['lines_per_airport']['mean'])} ; "
            f"aéroports/ville {_fmt_num(structure['airports_per_town']['mean'])}"
        )
        top = pooled["models"][:6]
        if top:
            bits = [
                f"{item['label']} {item['aircraft']} avions "
                f"médiane {_fmt_gbp(item['profit_per_aircraft_line_level']['median'])}"
                for item in top
            ]
            lines.append("  modèles : " + " ; ".join(bits))
    for comparison in report["comparisons"]:
        summary = comparison["matched_same_model_same_manhattan"]["summary"]
        lines.append(
            f"Test clé {comparison['duel_policy_id']}, même modèle et même Manhattan : "
            f"{summary['cells_aaa_median_strictly_higher']}/{summary['cell_count']} cellules "
            f"où la médiane AAA est plus haute ; part d'avions dans ces cellules "
            f"Opex { _fmt_num(summary['share_of_arm_aircraft_in_matched_cells']['OpexAI']) } "
            f"AAA { _fmt_num(summary['share_of_arm_aircraft_in_matched_cells']['AAAHogEx']) } ; "
            f"code {summary['conclusion_code']}"
        )
        attribution = comparison["attribution"]["by_model"]
        if attribution.get("comparable"):
            shares = attribution.get("shares_of_gap") or {}
            lines.append(
                "  Écart de moyenne pondérée "
                f"{_fmt_gbp(attribution['gap_aaa_minus_opex_gbp'])} : "
                f"composition {_fmt_gbp(attribution['composition_at_opex_rates_gbp'])} "
                f"(part {_fmt_num(shares.get('composition'))}), "
                f"même modèle {_fmt_gbp(attribution['same_cell_rate_gbp'])} "
                f"(part {_fmt_num(shares.get('same_cell_rate'))}), "
                f"hors support {_fmt_gbp(attribution['outside_support_gbp'])} "
                f"(part {_fmt_num(shares.get('outside_support'))})."
            )
        formula = comparison["aaa_formula_counterfactual"]
        lines.append(
            "  Contrefactuel formule AAA : "
            f"{formula['status']} ; routes {formula['routes_with_distance']} ; "
            f"manques : {', '.join(formula['missing']) or 'aucun'}."
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", help="JSON de campagne avec line_telemetry.snapshots")
    parser.add_argument("--json", metavar="PATH", help="rapport machine ; '-' écrit sur stdout")
    args = parser.parse_args(argv)
    report = analyse_path(args.campaign)
    if args.json:
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if args.json == "-":
            print(text)
        else:
            destination = Path(args.json)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text + "\n", encoding="utf-8")
            print(render_text(report))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
