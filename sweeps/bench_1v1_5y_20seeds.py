"""Banc de référence 1v1 en carte partagée OpexAI vs AAAHogEx (20 graines x 5 ans).

Post-09/09 Reference Benchmark :
- OpexAI (Player 0) contre AAAHogEx (Player 1) sur la même carte.
- 20 graines x 5 ans (1970-1975).
- Mesure les métriques standard (company_value, profit_year, performance_history,
  n_vehicles, n_stations, median_station_rating) et produit la comparaison appariée.
- Sortie : results/bench_1v1_5y_20seeds_reference.json (+ checkpoint .jsonl)
"""
import argparse
from collections import defaultdict
import inspect
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys


def _force_utf8_stdio():
    """Keep Rich/openttdlab progress output portable on Windows cp1252 consoles.

    openttdlab renders a Unicode check mark when its progress context closes.
    On Windows hosts whose inherited stdout/stderr are cp1252, that final render
    can raise UnicodeEncodeError after every OpenTTD job has completed, before
    run_experiments() returns its rows. Reconfigure only text encoding; the
    benchmark protocol and Docker execution are unchanged.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (OSError, ValueError):
                pass


_force_utf8_stdio()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    SEEDS,
    SEEDS_EXTRA_20,
    SEEDS_40,
    SUCCESS_METRICS,
    arm_statistics,
    make_cfg,
    paired_comparisons,
    parse_opex_variant,
    quarter_profit,
    station_ratings,
    summarise,
    year_profit_metrics,
)
from physical_counters import decode_vehicles, decode_stations
from game_health import (
    DEFAULT_ENGINE_TIMEOUT_SEC,
    assess_game,
    annotate_summary,
    enable_engine_failure_capture,
    engine_log_path_for,
    expected_last_checkpoint,
    expected_last_year,
    reconcile_assessment,
    write_engine_log,
)
import bench_v2
from frozen_harness import launch_frozen_campaign
from campaign_freeze import (
    default_campaign_id,
    fingerprint_tree,
    parse_ai_settings,
    prepare_frozen_campaign,
    validate_policy_settings,
)

STARTING_YEAR = 1970
DEFAULT_YEARS = 5
AAAHOGEX_DIR = "AAAHogEx-115"
CHECKPOINT_PATH = None
ENGINE_LOG_DIR = None
LINE_TELEMETRY = False
PROFIT_RAW_UNITS_PER_GBP = 256.0
VEHICLE_VARIANT_BY_MODE = {
    "rail": "train",
    "road": "roadveh",
    "water": "ship",
    "air": "aircraft",
}

ARMS = ("OpexAI", "AAAHogEx")
PRIMARY_METRIC = "profit_year"
VALUE_GUARD_METRIC = "company_value"
AIR_SLOT_METRICS = (
    "airport_slots_opex",
    "airport_slots_aaahogex",
    "airport_towns_opex_present",
    "airport_towns_aaahogex_present",
    "airport_towns_aaahogex_2_opex_0",
    "airport_towns_opex_2_aaahogex_0",
    "airport_towns_shared_1_1",
)
AIR_EARLY_SLOT_DIAG_METRICS = (
    "air_error_771_signs",
    "early_slot_select_signs",
    "early_slot_build_signs",
    "early_slot_build_claims",
)
AIR_STRUCTURAL_METRICS = AIR_SLOT_METRICS + AIR_EARLY_SLOT_DIAG_METRICS
TOWN_GROWTH_SUMMARY_METRICS = (
    "town_growth_builds_sign_total",
    "town_growth_builds_sign_by_year",
    "town_growth_signs_invalid",
)
C75_BYPASS_SUMMARY_METRICS = (
    "c75_bypass_events",
    "c75_bypass_consumed_signs",
    "c75_bypass_consumed_by_mode",
    "c75_bypass_consumed_by_kind",
    "c75_bypass_consumed_by_year",
    "c75_bypass_years",
)

LIBRARY_SPECS = (
    {"unique_id": "51554648", "name": "Queue.FibonacciHeap"},
    {"unique_id": "5046524c", "name": "Pathfinder.Rail"},
)

CAMPAIGN_HARNESS_FILES = (
    "sweeps/bench_1v1_5y_20seeds.py",
    "sweeps/bench_v2.py",
    "sweeps/campaign_freeze.py",
    "sweeps/frozen_harness.py",
    "sweeps/game_health.py",
    "sweeps/physical_counters.py",
    "sweeps/run_c66_reference.py",
    "sweeps/fixtures/c66_control_fixture_15_3.json",
    "Dockerfile",
    "requirements.txt",
    "requirements-ml.txt",
)


def append_checkpoint(record):
    global CHECKPOINT_PATH
    if CHECKPOINT_PATH is None:
        return
    encoded = (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(CHECKPOINT_PATH, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, encoded)
    finally:
        os.close(fd)


def _first(value):
    if value is None:
        return None
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, dict):
        if "owner" in value or "common" in value or "base" in value or "goods" in value or "xy" in value:
            return value
        return next(iter(value.values()), None)
    return value


def vehicle_owner(vehicle):
    if not isinstance(vehicle, dict):
        return None
    for kind in ("train", "roadveh", "ship", "aircraft"):
        body = _first(vehicle.get(kind))
        if not isinstance(body, dict):
            continue
        common = _first(body.get("common"))
        if isinstance(common, dict):
            return common.get("owner")
    return None


def station_owner(station):
    if not isinstance(station, dict):
        return None
    body = _first(station.get("normal"))
    if body is None:
        body = station
    if not isinstance(body, dict):
        return None
    base = _first(body.get("base"))
    return base.get("owner") if isinstance(base, dict) else None


def airport_slot_metrics(chunks):
    """Compte les slots aeroportuaires physiques par TownID dans STNN."""
    stnn = (chunks or {}).get("STNN")
    if not isinstance(stnn, (dict, list)):
        return {metric: None for metric in AIR_SLOT_METRICS}

    records = stnn.values() if isinstance(stnn, dict) else stnn
    by_owner = {0: defaultdict(int), 1: defaultdict(int)}
    for station in records:
        if not isinstance(station, dict):
            continue
        body = _first(station.get("normal"))
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if not isinstance(base, dict):
            continue
        owner = base.get("owner")
        if owner not in by_owner:
            continue
        try:
            facilities = int(base.get("facilities") or 0)
            town_id = int(base.get("town"))
        except (TypeError, ValueError):
            continue
        if facilities & 8 == 0:
            continue
        by_owner[owner][town_id] += 1

    opex = by_owner[0]
    aaa = by_owner[1]
    towns = set(opex) | set(aaa)
    return {
        "airport_slots_opex": sum(opex.values()),
        "airport_slots_aaahogex": sum(aaa.values()),
        "airport_towns_opex_present": len(opex),
        "airport_towns_aaahogex_present": len(aaa),
        "airport_towns_aaahogex_2_opex_0": sum(
            aaa.get(town, 0) >= 2 and opex.get(town, 0) == 0 for town in towns
        ),
        "airport_towns_opex_2_aaahogex_0": sum(
            opex.get(town, 0) >= 2 and aaa.get(town, 0) == 0 for town in towns
        ),
        "airport_towns_shared_1_1": sum(
            opex.get(town, 0) == 1 and aaa.get(town, 0) == 1 for town in towns
        ),
    }


def early_slot_sign_metrics(chunks):
    """Instrumentation durable via SIGN, disponible meme sans logs script."""
    signs = (chunks or {}).get("SIGN") or {}
    records = signs.values() if isinstance(signs, dict) else signs
    names = [
        sign.get("name", "")
        for sign in records
        if isinstance(sign, dict) and isinstance(sign.get("name", ""), str)
    ]
    build_claims = 0
    for name in names:
        if not name.startswith("SB|"):
            continue
        parts = name.split("|")
        if len(parts) >= 5:
            try:
                build_claims += int(parts[4])
            except ValueError:
                pass
    return {
        "air_error_771_signs": sum(name == "OE|A|771" for name in names),
        "early_slot_select_signs": sum(name.startswith("SK|") for name in names),
        "early_slot_build_signs": sum(name.startswith("SB|") for name in names),
        "early_slot_build_claims": build_claims,
    }


def town_growth_sign_metrics(chunks, *, current_year=STARTING_YEAR, target_owner=0):
    """One durable TG|yy|town|before|after sign per successful growth build.

    Missing SIGN stays unknown; an available empty chunk is an observed zero.
    The two-digit year is resolved in the century ending at current_year.
    Counts describe retained signs, not station increments or repeated snapshots.
    """
    signs = (chunks or {}).get("SIGN")
    if not isinstance(signs, (dict, list)):
        return {metric: None for metric in TOWN_GROWTH_SUMMARY_METRICS}
    records = signs.values() if isinstance(signs, dict) else signs
    by_year = {}
    invalid = 0
    for sign in records:
        if not isinstance(sign, dict):
            continue
        if "owner" in sign and str(sign["owner"]) != str(target_owner):
            continue
        name = sign.get("name")
        if not isinstance(name, str) or not name.startswith("TG|"):
            continue
        match = re.fullmatch(r"TG\|([0-9]{1,2})\|[0-9]+\|[0-9]+\|[0-9]+", name)
        if match is None:
            invalid += 1
            continue
        year = int(current_year) // 100 * 100 + int(match[1])
        if year > int(current_year):
            year -= 100
        key = str(year)
        by_year[key] = by_year.get(key, 0) + 1
    return {
        "town_growth_builds_sign_total": sum(by_year.values()),
        "town_growth_builds_sign_by_year": dict(sorted(by_year.items())),
        "town_growth_signs_invalid": invalid,
    }


def _town_growth_policy_metrics(reference, variant, starting_year, years):
    def pair(ref, var):
        return {"reference": ref, "variant": var,
                "policy_delta": var - ref if ref is not None and var is not None else None}

    reference = reference or {}
    variant = variant or {}
    ref_years = reference.get("town_growth_builds_sign_by_year")
    var_years = variant.get("town_growth_builds_sign_by_year")
    return {
        "builds_total": pair(reference.get("town_growth_builds_sign_total"),
                            variant.get("town_growth_builds_sign_total")),
        "invalid_signs": pair(reference.get("town_growth_signs_invalid"),
                             variant.get("town_growth_signs_invalid")),
        "builds_by_year": {
            str(year): pair(ref_years.get(str(year), 0) if ref_years is not None else None,
                            var_years.get(str(year), 0) if var_years is not None else None)
            for year in range(int(starting_year), int(starting_year) + int(years))
        },
    }


def c75_bypass_sign_metrics(chunks):
    """Telemetry C75 bis durable lue depuis SIGN, sans dependance a stdout script."""
    signs = (chunks or {}).get("SIGN") or {}
    records = signs.values() if isinstance(signs, dict) else signs
    names = [
        sign.get("name", "")
        for sign in records
        if isinstance(sign, dict) and isinstance(sign.get("name", ""), str)
    ]
    events = []
    years = {}
    for name in names:
        parts = name.split("|")
        if name.startswith("C7C|") and len(parts) == 7:
            try:
                events.append({
                    "year": 1900 + int(parts[1]),
                    "mode": parts[2],
                    "kind": parts[3],
                    "capital_k": int(parts[4]),
                    "available_k": int(parts[5]),
                    "k_pass_k": int(parts[6]),
                })
            except ValueError:
                continue
        elif name.startswith("C7Y|") and len(parts) == 5:
            try:
                yy = int(parts[1])
                years.setdefault(str(1900 + yy), {}).update({
                    "eligible": int(parts[2]),
                    "consumed": int(parts[3]),
                    "fleet_consumed": int(parts[4]),
                })
            except ValueError:
                continue
        elif name.startswith("C7S|") and len(parts) == 7:
            try:
                yy = int(parts[1])
                years.setdefault(str(1900 + yy), {}).update({
                    "stop_k_pass": int(parts[2]),
                    "stop_cash": int(parts[3]),
                    "stop_rail_search": int(parts[4]),
                    "stop_list_end": int(parts[5]),
                    "stop_other": int(parts[6]),
                })
            except ValueError:
                continue
    by_mode = {}
    by_kind = {}
    by_year = {}
    for event in events:
        by_mode[event["mode"]] = by_mode.get(event["mode"], 0) + 1
        by_kind[event["kind"]] = by_kind.get(event["kind"], 0) + 1
        key = str(event["year"])
        by_year[key] = by_year.get(key, 0) + 1
    return {
        "c75_bypass_events": events,
        "c75_bypass_consumed_signs": len(events),
        "c75_bypass_consumed_by_mode": by_mode,
        "c75_bypass_consumed_by_kind": by_kind,
        "c75_bypass_consumed_by_year": by_year,
        "c75_bypass_years": years,
    }


def project_build_sign_metrics(chunks):
    """Somme les chantiers deja publies par IB|...|B<n>, sans nouvelle sonde IA."""
    signs = (chunks or {}).get("SIGN") or {}
    records = signs.values() if isinstance(signs, dict) else signs
    total = 0
    parsed = 0
    by_year = {}
    for sign in records:
        if not isinstance(sign, dict):
            continue
        name = str(sign.get("name", ""))
        if not name.startswith("IB|"):
            continue
        parts = name.split("|")
        if len(parts) < 5 or not parts[-1].startswith("B"):
            continue
        try:
            yy = 1900 + int(parts[1])
            built = int(parts[-1][1:])
        except ValueError:
            continue
        parsed += 1
        total += built
        key = str(yy)
        by_year[key] = by_year.get(key, 0) + built
    return {
        "project_builds_sign_total": total,
        "project_build_signs_parsed": parsed,
        "project_builds_sign_by_year": by_year,
    }


def c118_sign_metrics(chunks):
    """Telemetry C118 durable : couverture catchment reelle et decisions moteur."""
    signs = (chunks or {}).get("SIGN") or {}
    records = signs.values() if isinstance(signs, dict) else signs
    names = [
        sign.get("name", "")
        for sign in records
        if isinstance(sign, dict) and isinstance(sign.get("name", ""), str)
    ]
    coverage = []
    decisions = {}
    for name in names:
        parts = name.split("|")
        try:
            if name.startswith("C8V|") and len(parts) == 6:
                coverage.append({
                    "year": 1900 + int(parts[1]), "month": int(parts[2]), "day": int(parts[3]),
                    "towns": int(parts[4]), "airports": int(parts[5]),
                })
            elif name.startswith("C8D|") and len(parts) == 6:
                seq = int(parts[1])
                decisions.setdefault(seq, {}).update({
                    "seq": seq, "year": 1900 + int(parts[2]), "month": int(parts[3]),
                    "day": int(parts[4]), "new_towns": int(parts[5]),
                })
            elif name.startswith("C8R|") and len(parts) == 4:
                seq = int(parts[1])
                decisions.setdefault(seq, {}).update({
                    "seq": seq, "src_town": int(parts[2]), "dst_town": int(parts[3]),
                })
            elif name.startswith("C8E|") and len(parts) == 5:
                seq = int(parts[1])
                decisions.setdefault(seq, {}).update({
                    "seq": seq, "c68_engine": int(parts[2]), "chosen_engine": int(parts[3]),
                    "next_town": int(parts[4]),
                })
            elif name.startswith("C8C|") and len(parts) == 5:
                seq = int(parts[1])
                decisions.setdefault(seq, {}).update({
                    "seq": seq, "c68_cash_after_k": int(parts[2]), "cash_after_k": int(parts[3]),
                    "next_capital_k": int(parts[4]),
                })
            elif name.startswith("C8F|") and len(parts) == 4:
                seq = int(parts[1])
                decisions.setdefault(seq, {}).update({
                    "seq": seq, "c68_flow_after": int(parts[2]), "flow_after": int(parts[3]),
                })
            elif name.startswith("C8T|") and len(parts) == 4:
                seq = int(parts[1])
                decisions.setdefault(seq, {}).update({
                    "seq": seq, "c68_time_days": int(parts[2]), "time_days": int(parts[3]),
                })
        except ValueError:
            continue
    coverage.sort(key=lambda item: (item["year"], item["month"], item["day"], item["towns"], item["airports"]))
    decision_list = [decisions[key] for key in sorted(decisions)]
    return {
        "c118_coverage_events": coverage,
        "c118_coverage_event_count": len(coverage),
        "c118_decisions": decision_list,
        "c118_decision_count": len(decision_list),
    }


def c120_sign_metrics(chunks):
    """Telemetry C120 durable : selection territoriale et motif d'execution."""
    signs = (chunks or {}).get("SIGN") or {}
    records = signs.values() if isinstance(signs, dict) else signs
    names = [
        sign.get("name", "")
        for sign in records
        if isinstance(sign, dict) and isinstance(sign.get("name", ""), str)
    ]
    decisions = {}
    for name in names:
        parts = name.split("|")
        try:
            if name.startswith("C0S|") and len(parts) == 7:
                seq = int(parts[1])
                decisions.setdefault(seq, {}).update({
                    "seq": seq,
                    "year": 1900 + int(parts[2]),
                    "month": int(parts[3]),
                    "day": int(parts[4]),
                    "available_k": int(parts[5]),
                    "air_candidates": int(parts[6]),
                })
            elif name.startswith("C0T|") and len(parts) == 6:
                seq = int(parts[1])
                decisions.setdefault(seq, {}).update({
                    "seq": seq,
                    "territorial": int(parts[2]),
                    "funded_territorial": int(parts[3]),
                    "best_new_towns": int(parts[4]),
                    "best_cost_k": int(parts[5]),
                })
            elif name.startswith("C0P|") and len(parts) in (7, 9):
                seq = int(parts[1])
                fields = {
                    "seq": seq,
                    "selected_new_towns": int(parts[2]),
                    "selected_cost_k": int(parts[3]),
                    "selected_engine": int(parts[4]),
                    "air_attempts": int(parts[5]),
                    "air_built": int(parts[6]),
                }
                if len(parts) == 9:
                    fields.update({
                        "selected_src": int(parts[7]),
                        "selected_dst": int(parts[8]),
                    })
                decisions.setdefault(seq, {}).update(fields)
            elif name.startswith("C0R|") and len(parts) in (3, 5):
                seq = int(parts[1])
                fields = {
                    "seq": seq,
                    "stop_reason": parts[2],
                }
                if len(parts) == 5:
                    fields.update({
                        "reject_reason": parts[3],
                        "pass_stop_reason": parts[4],
                    })
                decisions.setdefault(seq, {}).update(fields)
            elif name.startswith("C0C|") and len(parts) in (5, 8):
                seq = int(parts[1])
                cache_fields = {
                    "seq": seq,
                    "coverage_cache_hits": int(parts[2]),
                    "coverage_cache_misses": int(parts[3]),
                    "coverage_cache_entries": int(parts[4]),
                }
                if len(parts) == 8:
                    cache_fields.update({
                        "station_coverage_cache_hits": int(parts[5]),
                        "station_coverage_cache_misses": int(parts[6]),
                        "station_coverage_cache_entries": int(parts[7]),
                    })
                decisions.setdefault(seq, {}).update(cache_fields)
        except ValueError:
            continue
    decision_list = [decisions[key] for key in sorted(decisions)]
    return {
        "c120_decisions": decision_list,
        "c120_decision_count": len(decision_list),
    }


def _station_route_index(chunks):
    """Index passif station -> ville/proprietaire/facilities/qualite cargo depuis STNN."""
    stnn = (chunks or {}).get("STNN") or {}
    records = stnn.items() if isinstance(stnn, dict) else enumerate(stnn)
    result = {}
    for station_id, station in records:
        if not isinstance(station, dict):
            continue
        body = _first(station.get("normal"))
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if not isinstance(base, dict):
            continue
        try:
            sid = int(station_id)
        except (TypeError, ValueError):
            continue
        result[sid] = {
            "town": base.get("town"),
            "owner": base.get("owner"),
            "facilities": base.get("facilities", 0),
            "xy": base.get("xy"),
            "airport": {
                "tile": body.get("airport.tile"),
                "width": body.get("airport.w"),
                "height": body.get("airport.h"),
                "type": body.get("airport.type"),
                "layout": body.get("airport.layout"),
                "rotation": body.get("airport.rotation"),
            } if int(base.get("facilities") or 0) & 8 else None,
            "goods": {
                str(cargo_id): {
                    "rated": bool(
                        ((good.get("status") or 0) & 1)
                        and good.get("time_since_pickup", 255) < 255
                        and good.get("rating") is not None
                    ),
                    "rating": (
                        int(good["rating"])
                        if (
                            ((good.get("status") or 0) & 1)
                            and good.get("time_since_pickup", 255) < 255
                            and good.get("rating") is not None
                        )
                        else None
                    ),
                    "time_since_pickup": good.get("time_since_pickup"),
                    # OpenTTD: maximum atteint depuis le dernier recalcul de note,
                    # pas le stock instantane.
                    "max_waiting_cargo": good.get("max_waiting_cargo"),
                }
                for cargo_id, good in enumerate(body.get("goods") or [])
                if isinstance(good, dict)
            },
        }
    return result


def _raw_vehicle_common(chunks, vehicle_index, mode):
    """Retrouve le common brut correspondant a un vehicule primaire qualifie."""
    vehs = (chunks or {}).get("VEHS") or {}
    record = None
    if isinstance(vehs, dict):
        record = vehs.get(vehicle_index)
        if record is None:
            record = vehs.get(str(vehicle_index))
    elif isinstance(vehs, list) and 0 <= vehicle_index < len(vehs):
        record = vehs[vehicle_index]
    if not isinstance(record, dict):
        return None
    variant = VEHICLE_VARIANT_BY_MODE.get(mode)
    body = _first(record.get(variant)) if variant else None
    common = _first(body.get("common")) if isinstance(body, dict) else None
    return common if isinstance(common, dict) else None


def _vehicle_station_orders(chunks, common):
    """Resout les destinations de gare via ORDL, avec ORDR en repli."""
    raw_head = _first(common.get("orders")) if isinstance(common, dict) else None
    if raw_head in (None, -1, 65535):
        return {"readable": False, "reason": "missing_order_head", "order_list_id": None,
                "station_ids": []}

    ordl = (chunks or {}).get("ORDL")
    if isinstance(ordl, dict):
        try:
            ordl_key = str(int(raw_head) - 1)
        except (TypeError, ValueError):
            ordl_key = None
        entry = ordl.get(ordl_key) if ordl_key is not None else None
        if isinstance(entry, list):
            entry = entry[0] if entry else None
        raw_orders = entry.get("orders") if isinstance(entry, dict) else None
        if isinstance(raw_orders, list):
            station_ids = []
            for raw_order in raw_orders:
                if not isinstance(raw_order, dict):
                    return {"readable": False, "reason": "invalid_ordl_order",
                            "order_list_id": ordl_key, "station_ids": []}
                raw_type = raw_order.get("type")
                if not isinstance(raw_type, int) or (raw_type & 0x0F) != 1:
                    continue
                dest = raw_order.get("dest")
                try:
                    dest = int(dest)
                except (TypeError, ValueError):
                    continue
                if dest not in station_ids:
                    station_ids.append(dest)
            if station_ids:
                return {"readable": True, "reason": None, "order_list_id": ordl_key,
                        "station_ids": station_ids}

    ordr = (chunks or {}).get("ORDR")
    if isinstance(ordr, dict):
        current = raw_head
        seen = set()
        station_ids = []
        for _ in range(128):
            key = str(current)
            if key in seen:
                break
            seen.add(key)
            order = ordr.get(key)
            if isinstance(order, list):
                order = order[0] if order else None
            if not isinstance(order, dict):
                break
            dest = order.get("dest")
            try:
                dest = int(dest)
            except (TypeError, ValueError):
                dest = None
            if dest is not None and dest not in station_ids:
                station_ids.append(dest)
            nxt = order.get("next")
            if nxt is None:
                break
            current = nxt
        if station_ids:
            return {"readable": True, "reason": None, "order_list_id": str(raw_head),
                    "station_ids": station_ids}

    return {"readable": False, "reason": "unresolved_order_list",
            "order_list_id": str(raw_head), "station_ids": []}


def extract_line_telemetry(chunks, owner):
    """Reconstruit passivement les lignes exploitees d'une compagnie."""
    decoded = decode_vehicles((chunks or {}).get("VEHS"), target_owner=owner)
    if not decoded.get("chunk_valid"):
        return {
            "ok": False,
            "error": decoded.get("chunk_error"),
            "lines": [],
            "unresolved_vehicles": [],
        }

    stations = _station_route_index(chunks)
    groups = {}
    unresolved = []
    for detail in decoded.get("primary_vehicles_detail") or []:
        vehicle_id = detail.get("index")
        mode = detail.get("mode")
        common = _raw_vehicle_common(chunks, vehicle_id, mode)
        if common is None:
            unresolved.append({"vehicle_id": vehicle_id, "mode": mode, "reason": "missing_common"})
            continue

        orders = _vehicle_station_orders(chunks, common)
        if not orders["readable"]:
            unresolved.append({
                "vehicle_id": vehicle_id,
                "mode": mode,
                "reason": orders["reason"],
                "order_list_id": orders.get("order_list_id"),
            })
            continue

        station_ids = [
            sid for sid in orders["station_ids"]
            if sid in stations and stations[sid].get("owner") == owner
        ]
        if not station_ids:
            unresolved.append({
                "vehicle_id": vehicle_id,
                "mode": mode,
                "reason": "orders_without_known_station",
                "order_list_id": orders.get("order_list_id"),
            })
            continue

        ordered_station_ids = []
        for sid in station_ids:
            if sid not in ordered_station_ids:
                ordered_station_ids.append(sid)
        canonical_station_ids = tuple(sorted(ordered_station_ids))
        ordered_station_tiles = [stations[sid].get("xy") for sid in ordered_station_ids]
        ordered_town_ids = [stations[sid].get("town") for sid in ordered_station_ids]
        canonical_town_ids = tuple(sorted(
            int(town) for town in ordered_town_ids if town is not None
        ))
        cargo_signature = tuple(sorted(str(cargo) for cargo in (detail.get("consist_capacities") or {})))
        group_id = common.get("group_id")
        valid_group = group_id not in (None, -1, 65535)
        if owner == 1 and valid_group:
            # AAAHogEx cree un AIGroup par Route et y place tous ses vehicules.
            # C'est donc son meilleur line_id local; TownID reste la cle inter-parties.
            local_key = "group:" + str(group_id)
            key = ("group", str(group_id))
        else:
            local_key = mode + "|" + ",".join(str(value) for value in canonical_station_ids)
            key = (mode, canonical_station_ids)
        market_key = mode + "|" + ",".join(str(value) for value in canonical_town_ids)
        service_key = market_key + "|cargo=" + ",".join(cargo_signature)

        if key not in groups:
            groups[key] = {
                "line_key_local": local_key,
                "group_id": group_id if valid_group else None,
                "market_key": market_key,
                "service_key": service_key,
                "mode": mode,
                "station_ids": list(canonical_station_ids),
                "ordered_station_ids": list(ordered_station_ids),
                "ordered_station_tiles": ordered_station_tiles,
                "town_ids": list(canonical_town_ids),
                "ordered_town_ids": ordered_town_ids,
                "origin_town": ordered_town_ids[0] if ordered_town_ids else None,
                "destination_town": ordered_town_ids[1] if len(ordered_town_ids) > 1 else None,
                "endpoint_towns": list(canonical_town_ids),
                "vehicle_ids": [],
                "unitnumbers": [],
                "order_list_ids": [],
                "vehicles": 0,
                "capacity_by_cargo": defaultdict(int),
                "profit_this_year_gbp": 0.0,
                "profit_last_year_gbp": 0.0,
                "vehicle_value": 0,
            }
        line = groups[key]
        line["vehicles"] += 1
        line["vehicle_ids"].append(vehicle_id)
        line["unitnumbers"].append(common.get("unitnumber"))
        order_list_id = orders.get("order_list_id")
        if order_list_id is not None and order_list_id not in line["order_list_ids"]:
            line["order_list_ids"].append(order_list_id)
        for cargo, capacity in (detail.get("consist_capacities") or {}).items():
            line["capacity_by_cargo"][str(cargo)] += capacity
        raw_this = common.get("profit_this_year")
        raw_last = common.get("profit_last_year")
        if isinstance(raw_this, (int, float)):
            line["profit_this_year_gbp"] += raw_this / PROFIT_RAW_UNITS_PER_GBP
        if isinstance(raw_last, (int, float)):
            line["profit_last_year_gbp"] += raw_last / PROFIT_RAW_UNITS_PER_GBP
        line["vehicle_value"] += detail.get("consist_value") or 0

    lines = []
    for line in groups.values():
        line["capacity_by_cargo"] = dict(sorted(line["capacity_by_cargo"].items()))
        line["cargo_types"] = sorted(line["capacity_by_cargo"].keys(), key=str)
        endpoint_cargo_stats = []
        for sid in line["ordered_station_ids"]:
            station = stations.get(sid) or {}
            cargo_stats = {}
            station_goods = station.get("goods") or {}
            for cargo in line["cargo_types"]:
                good = station_goods.get(str(cargo))
                if good is not None:
                    cargo_stats[str(cargo)] = dict(good)
            endpoint_cargo_stats.append({
                "station_id": sid,
                "town_id": station.get("town"),
                "tile": station.get("xy"),
                "airport": station.get("airport"),
                "cargo": cargo_stats,
            })
        line["endpoint_cargo_stats"] = endpoint_cargo_stats
        line["profit_this_year_gbp"] = round(line["profit_this_year_gbp"], 6)
        line["profit_last_year_gbp"] = round(line["profit_last_year_gbp"], 6)
        lines.append(line)
    lines.sort(key=lambda item: (item["mode"], item["market_key"], item["line_key_local"]))
    return {"ok": True, "error": None, "lines": lines, "unresolved_vehicles": unresolved}


def _annual_line_checkpoint(date):
    return re.match(r"^\d{4}-12-", str(date)) is not None


def build_line_telemetry_report(rows):
    """Rassemble les snapshots annuels de lignes sans modifier le jeu."""
    snapshots = []
    for row in rows:
        telemetry = row.get("line_telemetry")
        if not telemetry:
            continue
        run = row.get("run") or []
        year_match = re.match(r"^(\d{4})-", str(row.get("date") or ""))
        snapshots.append({
            "duel_policy_id": row.get("duel_policy_id"),
            "arm": run[0] if run else None,
            "seed": run[1] if len(run) > 1 else None,
            "repeat": run[2] if len(run) > 2 else 0,
            "year": int(year_match.group(1)) if year_match else None,
            "date": row.get("date"),
            "ok": telemetry.get("ok"),
            "error": telemetry.get("error"),
            "unresolved_vehicles": telemetry.get("unresolved_vehicles", []),
            "lines": telemetry.get("lines", []),
        })
    return {
        "schema_version": 1,
        "scope": "annual December savegame post-processing; no NoAI behavior change",
        "observed_fields": [
            "mode", "station_ids", "town_ids", "vehicles", "capacity_by_cargo",
            "profit_this_year_gbp", "profit_last_year_gbp", "vehicle_value",
            "endpoint_cargo_stats.airport.{tile,width,height,type,layout,rotation}",
        ],
        "unavailable_fields": ["revenue", "running_cost"],
        "snapshots": snapshots,
    }


def extract_company_record(chunks, owner, run_key, date, output=None):
    players = chunks.get("PLYR") or {}
    player = players.get(owner)
    if player is None:
        player = players.get(str(owner))
    company_present = isinstance(player, dict) and bool(player)
    player = player or {}
    closed = player.get("old_economy")
    last_closed = (
        closed[0] if isinstance(closed, (list, tuple)) and closed
        and isinstance(closed[0], dict) else {}
    )
    ratings = station_ratings(chunks, owner=owner)
    veh_dec = decode_vehicles(chunks.get("VEHS"), target_owner=owner)
    stn_dec = decode_stations(chunks.get("STNN"), target_owner=owner)

    vehs_valid = veh_dec["chunk_valid"]
    stnn_valid = stn_dec["chunk_valid"]

    air_engine_counts = {}
    air_capacities_by_cargo = {}
    air_vehicle_book_value = 0
    if vehs_valid:
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

    # Configuration de campagne vanilla temperee : CargoID 0 == PASS.
    # Le detail par CargoID reste publie pour rendre cette lecture auditable.
    air_passenger_capacity = air_capacities_by_cargo.get("0", 0) if vehs_valid else None

    return {
        "run": run_key,
        "date": str(date),
        "company_value": last_closed.get("company_value", 0),
        "performance_history": last_closed.get("performance_history", 0),
        "income_last_year": last_closed.get("income", 0),
        "expenses_last_year": last_closed.get("expenses", 0),
        "profit": quarter_profit(last_closed),
        **year_profit_metrics(closed),
        "median_station_rating": (statistics.median(ratings) if ratings else None),
        "n_station_ratings": len(ratings),
        "money": player.get("money", 0),
        "current_loan": player.get("current_loan", 0),
        "months_of_bankruptcy": player.get("months_of_bankruptcy", 0),
        "physical_counters_version": veh_dec["schema_version"],
        "qualified_modes": veh_dec["qualified_modes"],
        "vehs_chunk_valid": vehs_valid,
        "vehs_chunk_error": veh_dec["chunk_error"],
        "stnn_chunk_valid": stnn_valid,
        "stnn_chunk_error": stn_dec["chunk_error"],
        "n_vehicles": veh_dec["primary_vehicles_count"] if vehs_valid else None,
        "vehicle_pool_entries": veh_dec["vehicle_pool_entries"] if vehs_valid else None,
        "total_vehicle_pool_entries": veh_dec["total_pool_entries"] if vehs_valid else None,
        "primary_vehicles": veh_dec["primary_vehicles_count"] if vehs_valid else None,
        "primary_vehicles_by_mode": veh_dec["primary_vehicles_by_mode"] if vehs_valid else None,
        "capacities_by_cargo": veh_dec["capacities_by_cargo"] if vehs_valid else None,
        "air_primary_vehicles": (
            veh_dec["primary_vehicles_by_mode"].get("air", 0) if vehs_valid else None
        ),
        "air_airports": (
            stn_dec["stations_by_facility"].get("airport", 0) if stnn_valid else None
        ),
        "air_engine_counts": air_engine_counts if vehs_valid else None,
        "air_capacities_by_cargo": air_capacities_by_cargo if vehs_valid else None,
        "air_passenger_capacity": air_passenger_capacity,
        "air_vehicle_book_value": air_vehicle_book_value if vehs_valid else None,
        "fleet_status": veh_dec["fleet_status"] if vehs_valid else None,
        "unclassified_vehicles": len(veh_dec["unclassified_entries"]),
        "n_stations": stn_dec["total_stations"] if stnn_valid else None,
        "n_multimodal_stations": stn_dec["n_multimodal_stations"] if stnn_valid else None,
        "stations_by_facility": stn_dec["stations_by_facility"] if stnn_valid else None,
        "unresolved_stations": len(stn_dec["unresolved_stations"]),
        "company_present": company_present,
        "engine_log_path": None,
        "openttd_output": None,
    }


def keep(row):
    chunks = row.get("chunks", {})
    date = row.get("date", "")
    output = row.get("output", "")
    experiment = row["experiment"]
    seed = experiment["seed"]
    repeat = experiment.get("repeat", 0)
    duel_policy_id = experiment.get("policy_id", "reference")

    log_path = experiment.get("engine_log_path")
    if not log_path:
        engine_log_dir = globals().get("ENGINE_LOG_DIR")
        engine_log_path_fn = globals().get("engine_log_path_for")
        if engine_log_dir is not None and engine_log_path_fn is not None:
            log_path = str(engine_log_path_fn(
                engine_log_dir, seed, repeat, policy_id=duel_policy_id
            ))
    if log_path:
        with open(log_path, "w", encoding="utf-8") as handle:
            handle.write(output)

    rec0 = extract_company_record(chunks, 0, ["OpexAI", seed, repeat], date)
    rec1 = extract_company_record(chunks, 1, ["AAAHogEx", seed, repeat], date)
    if LINE_TELEMETRY and _annual_line_checkpoint(date):
        rec0["line_telemetry"] = extract_line_telemetry(chunks, 0)
        rec1["line_telemetry"] = extract_line_telemetry(chunks, 1)
    structural = {}
    structural.update(airport_slot_metrics(chunks))
    structural.update(early_slot_sign_metrics(chunks))
    sign_year = int(date[:4]) if str(date)[:4].isdigit() else STARTING_YEAR
    structural.update(town_growth_sign_metrics(chunks, current_year=sign_year))
    structural.update(c75_bypass_sign_metrics(chunks))
    structural.update(project_build_sign_metrics(chunks))
    structural.update(c118_sign_metrics(chunks))
    structural.update(c120_sign_metrics(chunks))
    rec0.update(structural)
    rec1.update(structural)
    shared_identity = {
        "campaign_id": experiment.get("campaign_id"),
        "game_id": experiment.get("game_id"),
        "source_bundle_sha256": experiment.get("source_bundle_sha256"),
        "duel_policy_id": duel_policy_id,
    }
    rec0.update(shared_identity)
    rec1.update(shared_identity)
    rec0["policy_id"] = experiment.get("policy_id", "reference")
    rec1["policy_id"] = "AAAHogEx"
    rec0["company_slot"] = 0
    rec1["company_slot"] = 1
    rec0["engine_log_path"] = log_path
    rec1["engine_log_path"] = log_path
    rec0["engine_failure"] = row.get("engine_failure")
    rec1["engine_failure"] = row.get("engine_failure")
    append_checkpoint(rec0)
    append_checkpoint(rec1)
    return (rec0, rec1)


def make_experiments_plan(seeds, years, repeats=1, campaign=None, policy_id="reference", policies=None):
    from openttdlab import local_folder
    cfg = campaign.manifest["configuration"]["raw"] if campaign is not None else make_cfg(STARTING_YEAR)
    days = 365 * years
    opex_dir = campaign.opex_dir if campaign is not None else ROOT / "ai" / "OpexAI"
    aaahogex_dir = campaign.aaahogex_dir if campaign is not None else ROOT / "ai" / AAAHOGEX_DIR
    aaahogex = local_folder(str(aaahogex_dir), "AAAHogEx", ())
    if policies is None:
        policies = ({"id": policy_id, "explicit_settings": ()},)

    exps = []
    for repeat in range(repeats):
        for s in seeds:
            for policy in policies:
                current_policy_id = policy["id"]
                opex = local_folder(
                    str(opex_dir), "OpexAI", tuple(policy.get("explicit_settings", ()))
                )
                campaign_id = campaign.campaign_id if campaign is not None else None
                game_id = (
                    f"{campaign_id}:policy={current_policy_id}:s{s}:r{repeat}" if campaign_id else None
                )
                exps.append({
                    "seed": s,
                    "days": days,
                    "openttd_config": cfg,
                    "ais": (opex, aaahogex),
                    "bench_arm": "duel",
                    "is_duel": True,
                    "repeat": repeat,
                    "campaign_id": campaign_id,
                    "policy_id": current_policy_id,
                    "game_id": game_id,
                    "source_bundle_sha256": campaign.bundle_sha256 if campaign is not None else None,
                })
    return exps


def validate_paired_experiments(experiments, policy_ids):
    """Refuse toute paire C66.4 qui diffère hors politique OpexAI annoncée."""
    policy_ids = tuple(policy_ids)
    if len(policy_ids) < 2:
        return
    if len(policy_ids) != 2:
        raise ValueError("C66.4 attend exactement deux politiques")
    grouped = defaultdict(dict)
    for experiment in experiments:
        key = (experiment.get("seed"), experiment.get("repeat", 0))
        current_policy = experiment.get("policy_id")
        if current_policy in grouped[key]:
            raise ValueError(f"partie C66.4 dupliquée pour {key} / {current_policy}")
        grouped[key][current_policy] = experiment

    invariant_keys = (
        "seed", "repeat", "days", "openttd_config", "bench_arm", "is_duel",
        "campaign_id", "source_bundle_sha256",
    )
    for key, by_policy in grouped.items():
        if set(by_policy) != set(policy_ids):
            raise ValueError(f"paire C66.4 incomplète pour {key}: {sorted(by_policy)}")
        reference = by_policy[policy_ids[0]]
        variant = by_policy[policy_ids[1]]
        differences = [name for name in invariant_keys if reference.get(name) != variant.get(name)]
        if differences:
            raise ValueError(f"paire C66.4 diffère hors intervention pour {key}: {differences}")
        if reference.get("game_id") == variant.get("game_id"):
            raise ValueError(f"game_id C66.4 non unique pour {key}")
        ref_ais = reference.get("ais") or ()
        var_ais = variant.get("ais") or ()
        if len(ref_ais) != 2 or len(var_ais) != 2:
            raise ValueError(f"slots IA invalides pour {key}")
        if ref_ais[1] is not var_ais[1]:
            raise ValueError(f"AAAHogEx n'est pas le même descripteur gelé pour {key}")


def attach_campaign_identity(summary, rows):
    """Propage l'identite C66.3 que bench_v2.summarise ne connait pas."""
    identities = {}
    for row in rows:
        key = tuple(row.get("run") or ())
        if len(key) != 3:
            continue
        identity = {
            "campaign_id": row.get("campaign_id"),
            "policy_id": row.get("policy_id"),
            "duel_policy_id": row.get("duel_policy_id"),
            "game_id": row.get("game_id"),
            "company_slot": row.get("company_slot"),
            "source_bundle_sha256": row.get("source_bundle_sha256"),
        }
        previous = identities.get(key)
        if previous is not None and previous != identity:
            raise ValueError(f"identite de campagne instable pour {key}: {previous} != {identity}")
        identities[key] = identity
    for record in summary:
        key = (record["arm"], record["seed"], record.get("repeat", 0))
        identity = identities.get(key)
        if identity is None:
            raise ValueError(f"identite C66.3 absente pour {key}")
        record.update(identity)
    return summary


def _number(value):
    return None if value is None else round(float(value), 6)


def exact_sign_test_p(wins, losses):
    """Test binomial exact bilatéral, en excluant explicitement les égalités."""
    n = int(wins) + int(losses)
    if n == 0:
        return None
    tail = min(int(wins), int(losses))
    probability = 2 * sum(math.comb(n, k) for k in range(tail + 1)) / (2 ** n)
    return _number(min(1.0, probability))


# Table exacte précalculée du quantile bilatéral 95% (t_{0.975, df}) pour df = 1 à 40.
# Source : intégration numérique de la densité de Student-t (résultats identiques aux tables NIST/Fisher-Yates).
_STUDENT_T_95_TABLE = (
    12.706205, 4.302653, 3.182446, 2.776445, 2.570582,
    2.446912, 2.364624, 2.306004, 2.262157, 2.228139,
    2.200985, 2.178813, 2.160369, 2.144787, 2.131450,
    2.119905, 2.109816, 2.100922, 2.093024, 2.085963,
    2.079614, 2.073873, 2.068658, 2.063899, 2.059539,
    2.055529, 2.051831, 2.048407, 2.045230, 2.042272,
    2.039513, 2.036933, 2.034515, 2.032245, 2.030108,
    2.028094, 2.026192, 2.024394, 2.022691, 2.021075,
)


def student_t_ci95_critical_value(df: int) -> float:
    """Valeur critique bilatérale à 95% (quantile 0.975) de Student-t pour df degrés de liberté.

    Calcul pur Python sans scipy. Utilise la table exacte pour df in 1..40 (dont df=39 pour 40 graines,
    df=19 pour 20 graines) et une expansion de Cornish-Fisher d'ordre 4 pour df > 40 (erreur < 1e-6).
    """
    if df < 1:
        raise ValueError(f"df doit être >= 1 (reçu {df})")
    if df <= len(_STUDENT_T_95_TABLE):
        return _STUDENT_T_95_TABLE[df - 1]
    # Approximation de Cornish-Fisher d'ordre 4 depuis le quantile normal z = 1.959963984540054
    z = 1.959963984540054
    inv_df = 1.0 / df
    inv_df2 = inv_df * inv_df
    inv_df3 = inv_df2 * inv_df
    inv_df4 = inv_df3 * inv_df
    term1 = (z**3 + z) / 4.0 * inv_df
    term2 = (5.0 * z**5 + 16.0 * z**3 + 3.0 * z) / 96.0 * inv_df2
    term3 = (3.0 * z**7 + 19.0 * z**5 + 17.0 * z**3 - 15.0 * z) / 384.0 * inv_df3
    term4 = (79.0 * z**9 + 776.0 * z**7 + 1482.0 * z**5 - 1920.0 * z**3 - 945.0 * z) / 92160.0 * inv_df4
    return round(z + term1 + term2 + term3 + term4, 6)


def delta_statistics(values):
    """Statistiques appariées sur les deltas, jamais différence de deux moyennes."""
    values = [float(value) for value in values if value is not None]
    n = len(values)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    ties = sum(value == 0 for value in values)
    mean = statistics.mean(values) if values else None
    median = statistics.median(values) if values else None
    standard_deviation = statistics.stdev(values) if n > 1 else None
    standard_error = standard_deviation / math.sqrt(n) if standard_deviation is not None else None
    if standard_error is not None:
        margin = 1.959963984540054 * standard_error
        ci95 = [_number(mean - margin), _number(mean + margin)]
        t_crit = student_t_ci95_critical_value(n - 1) if n > 1 else None
        margin_t = t_crit * standard_error if t_crit is not None else None
        student_ci95 = [_number(mean - margin_t), _number(mean + margin_t)] if margin_t is not None else None
    else:
        ci95 = None
        student_ci95 = None
    return {
        "n": n,
        "mean": _number(mean),
        "median": _number(median),
        "standard_deviation": _number(standard_deviation),
        "standard_error": _number(standard_error),
        "mean_normal_95pct_ci": ci95,
        "mean_student_t_95pct_ci": student_ci95,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "sign_test_n_excluding_ties": wins + losses,
        "sign_test_p": exact_sign_test_p(wins, losses),
    }


def ratio_statistics(pairs):
    """Distingue rapport de moyennes et moyenne des rapports ; dénominateur > 0 obligatoire."""
    valid = [(float(variant), float(reference)) for variant, reference in pairs
             if variant is not None and reference is not None and reference > 0]
    excluded = len(pairs) - len(valid)
    if not valid:
        return {
            "n_positive_denominator": 0,
            "excluded_nonpositive_or_missing_denominator": excluded,
            "ratio_of_means": None,
            "ratio_of_means_percent_change": None,
            "mean_of_ratios": None,
            "mean_of_ratios_percent_change": None,
        }
    mean_variant = statistics.mean(variant for variant, _ in valid)
    mean_reference = statistics.mean(reference for _, reference in valid)
    ratios = [variant / reference for variant, reference in valid]
    ratio_of_means = mean_variant / mean_reference if mean_reference > 0 else None
    mean_of_ratios = statistics.mean(ratios)
    return {
        "n_positive_denominator": len(valid),
        "excluded_nonpositive_or_missing_denominator": excluded,
        "ratio_of_means": _number(ratio_of_means),
        "ratio_of_means_percent_change": _number(100 * (ratio_of_means - 1)) if ratio_of_means is not None else None,
        "mean_of_ratios": _number(mean_of_ratios),
        "mean_of_ratios_percent_change": _number(100 * (mean_of_ratios - 1)),
    }


def _annual_final_records(rows, starting_year, years):
    """Dernier checkpoint disponible de chaque année cible, par politique/compagnie/graine."""
    target_years = set(range(int(starting_year), int(starting_year) + int(years)))
    annual = {}
    for row in rows:
        date = str(row.get("date") or "")
        match = re.match(r"(\d{4})-\d{2}-\d{2}", date)
        run = row.get("run") or ()
        if not match or len(run) < 3:
            continue
        year = int(match.group(1))
        if year not in target_years:
            continue
        key = (row.get("duel_policy_id"), run[0], run[1], run[2], year)
        previous = annual.get(key)
        if previous is None or str(previous.get("date")) < date:
            annual[key] = row
    return annual


def _stamp_structural_metrics(summary_records, raw_records):
    """Propage le dernier snapshot structurel partagé dans les deux résumés."""
    if not raw_records:
        return summary_records
    opex_rows = [
        row for row in raw_records
        if (row.get("run") or [None])[0] == "OpexAI"
    ]
    source = max(opex_rows or raw_records, key=lambda row: str(row.get("date") or ""))
    for record in summary_records:
        for metric in AIR_STRUCTURAL_METRICS:
            record[metric] = source.get(metric)
        for metric in C75_BYPASS_SUMMARY_METRICS:
            record[metric] = source.get(metric)
        for metric in TOWN_GROWTH_SUMMARY_METRICS:
            record[metric] = source.get(metric)
    return summary_records


def policy_adoption_eligibility(seeds, repeats, years, decision_rule):
    """Sépare le protocole d'adoption des statistiques diagnostiques par paire.

    Les répétitions d'une même carte ne sont pas des graines indépendantes.
    Elles restent descriptives tant qu'aucune inférence regroupée par graine
    n'est définie. Le protocole courant impose exactement dix ans.
    """
    required_seeds = {"signs20": 20, "mean40": 40}
    if decision_rule not in required_seeds:
        raise ValueError(f"règle d'adoption inconnue: {decision_rule}")
    required = required_seeds[decision_rule]
    distinct_seeds = len(set(seeds))
    reasons = []
    if distinct_seeds != len(seeds):
        reasons.append("duplicate_seeds")
    if distinct_seeds != required:
        reasons.append("distinct_seed_count")
    if repeats != 1:
        reasons.append("repeated_seeds")
    if years != 10:
        reasons.append("horizon_not_10_years")
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "required_distinct_seeds": required,
        "distinct_seeds": distinct_seeds,
        "required_years": 10,
        "years": years,
        "required_repeats": 1,
        "repeats": repeats,
        "independent_seed_sample": distinct_seeds == len(seeds) and repeats == 1,
    }


def build_policy_comparison(
    summary,
    rows,
    *,
    seeds,
    repeats,
    reference_policy_id,
    variant_policy_id,
    primary_metric,
    min_useful_primary_delta,
    value_guard_max_loss_pct,
    starting_year,
    years,
    decision_rule="signs20",
):
    """Rapport C66.4 fail-closed pour deux politiques jouant chacune contre AAAHogEx."""
    adoption_protocol = policy_adoption_eligibility(seeds, repeats, years, decision_rule)
    adoption_sample_complete = adoption_protocol["eligible"]
    index = {}
    for record in summary:
        key = (
            record.get("duel_policy_id"), record.get("arm"),
            record.get("seed"), record.get("repeat", 0),
        )
        if key in index:
            raise ValueError(f"résumé C66.4 dupliqué pour {key}")
        index[key] = record

    annual = _annual_final_records(rows, starting_year, years)
    pairs = []
    complete_pairs = []
    for repeat in range(repeats):
        for seed in seeds:
            records = {
                "reference_opex": index.get((reference_policy_id, "OpexAI", seed, repeat)),
                "reference_aaahogex": index.get((reference_policy_id, "AAAHogEx", seed, repeat)),
                "variant_opex": index.get((variant_policy_id, "OpexAI", seed, repeat)),
                "variant_aaahogex": index.get((variant_policy_id, "AAAHogEx", seed, repeat)),
            }
            statuses = {
                name: {
                    "present": record is not None,
                    "run_ok": record.get("run_ok") if record else None,
                    "game_ok": record.get("game_ok") if record else None,
                    "status": record.get("status") if record else "missing",
                    "failure_reason": record.get("failure_reason") if record else "missing_summary",
                    "game_id": record.get("game_id") if record else None,
                }
                for name, record in records.items()
            }
            healthy = all(
                record is not None and record.get("run_ok") is True and record.get("game_ok") is True
                for record in records.values()
            )
            decision_metrics_present = all(
                record is not None
                and record.get(primary_metric) is not None
                and record.get(VALUE_GUARD_METRIC) is not None
                for record in records.values()
            )
            complete = healthy and decision_metrics_present

            metric_payload = {}
            for metric in SUCCESS_METRICS:
                ref_o = records["reference_opex"].get(metric) if records["reference_opex"] else None
                var_o = records["variant_opex"].get(metric) if records["variant_opex"] else None
                ref_a = records["reference_aaahogex"].get(metric) if records["reference_aaahogex"] else None
                var_a = records["variant_aaahogex"].get(metric) if records["variant_aaahogex"] else None
                ref_gap = ref_o - ref_a if ref_o is not None and ref_a is not None else None
                var_gap = var_o - var_a if var_o is not None and var_a is not None else None
                metric_payload[metric] = {
                    "reference_opex": ref_o,
                    "variant_opex": var_o,
                    "policy_delta": var_o - ref_o if var_o is not None and ref_o is not None else None,
                    "reference_aaahogex": ref_a,
                    "variant_aaahogex": var_a,
                    "reference_duel_gap": ref_gap,
                    "variant_duel_gap": var_gap,
                    "duel_gap_evolution": var_gap - ref_gap if var_gap is not None and ref_gap is not None else None,
                }

            structural_payload = {}
            for metric in AIR_STRUCTURAL_METRICS:
                ref_value = records["reference_opex"].get(metric) if records["reference_opex"] else None
                var_value = records["variant_opex"].get(metric) if records["variant_opex"] else None
                structural_payload[metric] = {
                    "reference": ref_value,
                    "variant": var_value,
                    "policy_delta": (
                        var_value - ref_value
                        if var_value is not None and ref_value is not None else None
                    ),
                }

            town_growth_payload = _town_growth_policy_metrics(
                records["reference_opex"], records["variant_opex"], starting_year, years
            )
            trajectory = []
            for year in range(int(starting_year), int(starting_year) + int(years)):
                def annual_value(policy, arm, metric):
                    row = annual.get((policy, arm, seed, repeat, year))
                    return row.get(metric) if row else None

                ref_o = annual_value(reference_policy_id, "OpexAI", primary_metric)
                var_o = annual_value(variant_policy_id, "OpexAI", primary_metric)
                ref_a = annual_value(reference_policy_id, "AAAHogEx", primary_metric)
                var_a = annual_value(variant_policy_id, "AAAHogEx", primary_metric)
                annual_structural = {}
                for metric in AIR_STRUCTURAL_METRICS:
                    ref_value = annual_value(reference_policy_id, "OpexAI", metric)
                    var_value = annual_value(variant_policy_id, "OpexAI", metric)
                    annual_structural[metric] = {
                        "reference": ref_value,
                        "variant": var_value,
                        "policy_delta": (
                            var_value - ref_value
                            if var_value is not None and ref_value is not None else None
                        ),
                    }
                trajectory.append({
                    "year": year,
                    "primary_metric": primary_metric,
                    "reference_opex": ref_o,
                    "variant_opex": var_o,
                    "policy_delta": var_o - ref_o if var_o is not None and ref_o is not None else None,
                    "reference_aaahogex": ref_a,
                    "variant_aaahogex": var_a,
                    "reference_duel_gap": ref_o - ref_a if ref_o is not None and ref_a is not None else None,
                    "variant_duel_gap": var_o - var_a if var_o is not None and var_a is not None else None,
                    "air_structural_metrics": annual_structural,
                    "town_growth_builds": town_growth_payload["builds_by_year"][str(year)],
                })

            pair = {
                "seed": seed,
                "repeat": repeat,
                "complete": complete,
                "statuses": statuses,
                "metrics": metric_payload,
                "air_structural_metrics": structural_payload,
                "town_growth_metrics": town_growth_payload,
                "annual_trajectory": trajectory,
            }
            pairs.append(pair)
            if complete:
                complete_pairs.append(pair)

    aggregates = {}
    for metric in SUCCESS_METRICS:
        policy_deltas = [pair["metrics"][metric]["policy_delta"] for pair in complete_pairs]
        gap_evolution = [pair["metrics"][metric]["duel_gap_evolution"] for pair in complete_pairs]
        ref_gaps = [pair["metrics"][metric]["reference_duel_gap"] for pair in complete_pairs]
        var_gaps = [pair["metrics"][metric]["variant_duel_gap"] for pair in complete_pairs]
        policy_value_pairs = [
            (pair["metrics"][metric]["variant_opex"], pair["metrics"][metric]["reference_opex"])
            for pair in complete_pairs
        ]
        aggregates[metric] = {
            "policy_delta": delta_statistics(policy_deltas),
            "policy_ratio": ratio_statistics(policy_value_pairs),
            "reference_opex_minus_aaahogex": delta_statistics(ref_gaps),
            "variant_opex_minus_aaahogex": delta_statistics(var_gaps),
            "duel_gap_evolution": delta_statistics(gap_evolution),
        }
    structural_aggregates = {
        metric: delta_statistics([
            pair["air_structural_metrics"][metric]["policy_delta"]
            for pair in complete_pairs
        ])
        for metric in AIR_STRUCTURAL_METRICS
    }

    planned = len(seeds) * int(repeats)
    incomplete_pairs = [
        {"seed": pair["seed"], "repeat": pair["repeat"], "statuses": pair["statuses"]}
        for pair in pairs if not pair["complete"]
    ]
    primary_stats = aggregates[primary_metric]["policy_delta"]
    guard_stats = aggregates[VALUE_GUARD_METRIC]["policy_ratio"]
    guard_ratio = guard_stats["ratio_of_means_percent_change"]
    metric_coverage_complete = (
        primary_stats["n"] == planned
        and guard_stats["n_positive_denominator"] == planned
    )
    comparison_complete = (
        len(complete_pairs) == planned
        and not incomplete_pairs
        and metric_coverage_complete
    )
    if decision_rule == "mean40":
        primary_ci95 = primary_stats.get("mean_student_t_95pct_ci")
        ci_lower_positive = (
            primary_ci95 is not None
            and primary_ci95[0] is not None
            and primary_ci95[0] > 0
        )
        ci_pass = (
            bool(ci_lower_positive)
            if adoption_sample_complete and comparison_complete else None
        )
        sign_pass = None
        primary_mean_pass = (
            primary_stats["mean"] is not None
            and primary_stats["mean"] >= float(min_useful_primary_delta)
            if comparison_complete else None
        )
        primary_pass = (
            bool(ci_pass and primary_mean_pass)
            if adoption_sample_complete and comparison_complete else None
        )
        decision_rule_record = {
            "rule": "mean40",
            "required_pairs": 40,
            "confidence_level": 0.95,
            "min_useful_primary_delta": float(min_useful_primary_delta),
            "value_guard_max_loss_pct": float(value_guard_max_loss_pct),
            "primary_rule": (
                "all planned pairs required (40); "
                "student_t_ci95_lower(variant-reference) > 0; "
                "then mean(variant-reference) >= min_useful_primary_delta"
            ),
            "value_guard_rule": (
                "all 40 reference denominators must be positive; then "
                "ratio_of_means(company_value) percent change >= -value_guard_max_loss_pct"
            ),
            "all_planned_pairs_required_for_verdict": True,
        }
    else:
        sign_pass = (
            primary_stats["wins"] >= 15
            and primary_stats["sign_test_p"] is not None
            and primary_stats["sign_test_p"] < 0.05
            if adoption_sample_complete and comparison_complete else None
        )
        ci_pass = None
        primary_mean_pass = (
            primary_stats["mean"] is not None
            and primary_stats["mean"] >= float(min_useful_primary_delta)
            if comparison_complete else None
        )
        primary_pass = (
            bool(sign_pass and primary_mean_pass)
            if adoption_sample_complete and comparison_complete else None
        )
        decision_rule_record = {
            "required_pairs": 20,
            "required_wins": 15,
            "max_sign_test_p_exclusive": 0.05,
            "min_useful_primary_delta": float(min_useful_primary_delta),
            "value_guard_max_loss_pct": float(value_guard_max_loss_pct),
            "primary_rule": (
                "first wins>=15/20 and exact two-sided sign-test p<0.05; "
                "then mean(variant-reference) >= min_useful_primary_delta"
            ),
            "value_guard_rule": (
                "all 20 reference denominators must be positive; then "
                "ratio_of_means(company_value) percent change >= -value_guard_max_loss_pct"
            ),
            "all_planned_pairs_required_for_verdict": True,
        }

    guard_pass = (
        guard_ratio is not None
        and guard_ratio >= -float(value_guard_max_loss_pct)
        if comparison_complete else None
    )
    if not comparison_complete:
        verdict = "incomplete"
    elif not adoption_sample_complete:
        verdict = "diagnostic_only"
    elif primary_pass and guard_pass:
        verdict = "pass"
    elif not primary_pass and not guard_pass:
        verdict = "fail_primary_and_value_guard"
    elif not primary_pass:
        verdict = "fail_primary"
    else:
        verdict = "fail_value_guard"

    return {
        "protocol": "C66.4 paired policies, separate shared-map duels versus same frozen AAAHogEx",
        "reference_policy_id": reference_policy_id,
        "variant_policy_id": variant_policy_id,
        "primary_metric": primary_metric,
        "value_guard_metric": VALUE_GUARD_METRIC,
        "decision_rule": decision_rule_record,
        "planned_pairs": planned,
        "complete_pairs": len(complete_pairs),
        "comparison_complete": comparison_complete,
        "adoption_sample_complete": adoption_sample_complete,
        "adoption_protocol": adoption_protocol,
        "metric_coverage_complete": metric_coverage_complete,
        "incomplete_pairs": incomplete_pairs,
        "statistical_incompleteness": {
            "primary_metric_n": primary_stats["n"],
            "value_guard_positive_denominators": guard_stats["n_positive_denominator"],
            "value_guard_excluded": guard_stats["excluded_nonpositive_or_missing_denominator"],
        },
        "per_pair": pairs,
        "aggregates": aggregates,
        "air_structural_aggregates": structural_aggregates,
        "town_growth_aggregates": {
            "builds_total": delta_statistics([
                pair["town_growth_metrics"]["builds_total"]["policy_delta"]
                for pair in complete_pairs
            ]),
            "builds_by_year": {
                str(year): delta_statistics([
                    pair["town_growth_metrics"]["builds_by_year"][str(year)]["policy_delta"]
                    for pair in complete_pairs
                ]) for year in range(int(starting_year), int(starting_year) + int(years))
            },
        },
        "sign_pass": sign_pass,
        "ci_pass": ci_pass,
        "primary_mean_pass": primary_mean_pass,
        "primary_pass": primary_pass,
        "value_guard_pass": guard_pass,
        "verdict": verdict,
    }


def enforce_validation_outcome(failed_runs, policy_comparison=None):
    """Termine en erreur après écriture du rapport, sans masquer la cause de validation."""
    if failed_runs:
        raise SystemExit(f"Banc invalide : {len(failed_runs)} echec(s) de sante")
    if policy_comparison is not None and not policy_comparison["comparison_complete"]:
        raise SystemExit("Banc C66.4 incomplet : au moins une paire prévue est invalide ou absente")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument(
        "--decision-rule",
        choices=["signs20", "mean40"],
        default="signs20",
           help="Règle d'adoption C66.4 : 'signs20' (20 graines, test des signes bilatéral 15/20) "
               "ou 'mean40' (40 graines, IC95 Student-t > 0 et moyenne >= min_useful_primary_delta). "
               "Adoption uniquement sur graines distinctes, 10 ans et une répétition ; sinon diagnostic.",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=None,
        help="Graines de carte (défaut : SEEDS (20) sous signs20, SEEDS_40 (40) sous mean40)",
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--campaign", help="Identifiant C66.3 nouveau ; derive de --out ou horodate si omis")
    parser.add_argument("--policy-id", default="reference", help="Identifiant de la politique OpexAI testee")
    parser.add_argument("--reference", help="C66.4 : politique de reference explicite, ex. OpexAI[air_early_slot=1]")
    parser.add_argument("--variant", help="C66.4 : ex. OpexAI[c80_mode_regen=1]")
    parser.add_argument("--variant-policy-id", help="C66.4 : identifiant stable de la variante")
    parser.add_argument("--primary-metric", choices=list(SUCCESS_METRICS), default=PRIMARY_METRIC)
    parser.add_argument("--min-useful-primary-delta", type=float)
    parser.add_argument("--value-guard-max-loss-pct", type=float)
    parser.add_argument("--out", type=Path, default=None, help="JSON final ; C66.3 refuse tout ecrasement")
    parser.add_argument("--docker-image", default=os.environ.get("C66_DOCKER_IMAGE", "openttd-lab"))
    parser.add_argument("--docker-image-id", default=os.environ.get("C66_DOCKER_IMAGE_ID"))
    parser.add_argument("--selftest", action="store_true", help="Vérifie le décodage et le fail-closed sans lancer OpenTTD")
    parser.add_argument(
        "--line-telemetry", action="store_true",
        help="Diagnostic passif annuel: reconstruit les lignes depuis VEHS + ORDL/ORDR + STNN",
    )
    parser.add_argument(
        "--script-debug", action="store_true",
        help="Diagnostic uniquement: force OpenTTD -d script=4 pour conserver la stack NoAI complete",
    )
    parser.add_argument(
        "--engine-timeout", type=int, default=DEFAULT_ENGINE_TIMEOUT_SEC,
        help="Timeout subprocess OpenTTD par partie, en secondes (0 = aucun)",
    )
    args = parser.parse_args()
    if args.seeds is None:
        args.seeds = list(SEEDS_40) if args.decision_rule == "mean40" else list(SEEDS)

    if args.selftest:
        selftest()
        return

    if args.repeats < 1:
        parser.error("--repeats doit etre >= 1")
    reference_settings = ()
    if args.reference is not None:
        reference_settings = parse_opex_variant(args.reference)
        if reference_settings is None:
            parser.error("--reference doit utiliser le format OpexAI[cle=valeur]")
    policies = [{"id": args.policy_id, "role": "reference", "explicit_settings": tuple(reference_settings)}]
    intervention_settings = ()
    decision_rule = None
    if args.variant is not None:
        variant_settings = parse_opex_variant(args.variant)
        if variant_settings is None:
            parser.error("--variant doit utiliser le format OpexAI[cle=valeur]")
        if not args.variant_policy_id:
            parser.error("--variant-policy-id est requis avec --variant")
        if args.variant_policy_id == args.policy_id:
            parser.error("--variant-policy-id doit differer de --policy-id")
        if args.min_useful_primary_delta is None:
            parser.error("--min-useful-primary-delta doit etre fixe avant un banc C66.4")
        if args.value_guard_max_loss_pct is None:
            parser.error("--value-guard-max-loss-pct doit etre fixe avant un banc C66.4")
        if args.value_guard_max_loss_pct < 0:
            parser.error("--value-guard-max-loss-pct doit etre >= 0")
        ref_explicit = dict(reference_settings)
        var_explicit = dict(variant_settings)
        intervention_settings = tuple(
            sorted(
                key for key in (set(ref_explicit) | set(var_explicit))
                if ref_explicit.get(key) != var_explicit.get(key)
            )
        )
        if not intervention_settings:
            parser.error("reference et variante n'annoncent aucune difference de reglage")
        policies.append({
            "id": args.variant_policy_id,
            "role": "variant",
            "explicit_settings": tuple(variant_settings),
        })
        decision_rule = {
            "rule": args.decision_rule,
            "primary_metric": args.primary_metric,
            "min_useful_primary_delta": args.min_useful_primary_delta,
            "value_guard_metric": VALUE_GUARD_METRIC,
            "value_guard_max_loss_pct": args.value_guard_max_loss_pct,
            "all_planned_pairs_required_for_verdict": True,
        }
    elif any(value is not None for value in (
        args.variant_policy_id, args.min_useful_primary_delta, args.value_guard_max_loss_pct,
    )):
        parser.error("les options C66.4 de variante exigent --variant")

    campaign_id = args.campaign or (args.out.stem if args.out is not None else default_campaign_id())
    out = args.out or (ROOT / "results" / f"{campaign_id}.json")
    cfg = make_cfg(STARTING_YEAR)
    campaign = prepare_frozen_campaign(
        root=ROOT,
        out_path=out,
        campaign_id=campaign_id,
        policy_id=args.policy_id,
        seeds=args.seeds,
        years=args.years,
        repeats=args.repeats,
        starting_year=STARTING_YEAR,
        config_text=cfg,
        opex_explicit_settings=tuple(reference_settings),
        library_specs=LIBRARY_SPECS,
        harness_files=CAMPAIGN_HARNESS_FILES,
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        docker_image=args.docker_image,
        docker_image_id=args.docker_image_id,
        policy_definitions=policies,
        intervention_settings=intervention_settings,
        decision_rule=decision_rule,
        execution_options={key: str(value) if isinstance(value, Path) else value
                           for key, value in vars(args).items()},
    )
    returncode = launch_frozen_campaign(campaign)
    if returncode:
        raise SystemExit(returncode)


def frozen_execution_inputs(campaign):
    """Read hashed options/policies and reject inconsistent protocol metadata."""
    manifest = campaign.manifest
    args = argparse.Namespace(**manifest["execution"]["options"])
    config = manifest["configuration"]
    for key in ("seeds", "years", "repeats"):
        if getattr(args, key) != config[key]:
            raise ValueError(f"frozen execution option mismatch: {key}")
    if (config["starting_year"] != STARTING_YEAR
            or manifest["versions"]["openttd"] != OPENTTD_VERSION
            or manifest["versions"]["opengfx"] != OPENGFX_VERSION):
        raise ValueError("frozen runtime constants differ from manifest")
    if args.policy_id != manifest["policy"]["id"]:
        raise ValueError("frozen reference policy mismatch")
    comparison = manifest.get("comparison")
    if comparison:
        if args.variant_policy_id != comparison["variant_policy_id"]:
            raise ValueError("frozen variant policy mismatch")
        rule = comparison["decision_rule"]
        for option, field in (("decision_rule", "rule"), ("primary_metric", "primary_metric"),
                              ("min_useful_primary_delta", "min_useful_primary_delta"),
                              ("value_guard_max_loss_pct", "value_guard_max_loss_pct")):
            if getattr(args, option) != rule[field]:
                raise ValueError(f"frozen decision rule mismatch: {option}")
    elif args.variant_policy_id is not None:
        raise ValueError("frozen variant missing from manifest")
    policies = [
        {"id": policy["id"], "role": policy["role"],
         "explicit_settings": tuple(policy["settings"]["explicit"].items())}
        for policy in manifest["policies"]
    ]
    return args, policies


def execute_frozen_campaign(campaign):
    """Called only by the verified bundle's isolated bootstrap, not live main()."""
    import openttdlab
    from openttdlab import run_experiments
    from bench_v2 import enable_savegame_cleanup, write_json_atomically
    from frozen_harness import verify_manifest_bundle

    expected_source = campaign.bundle_dir / "harness" / "sweeps" / Path(__file__).name
    if Path(__file__).resolve() != expected_source.resolve():
        raise RuntimeError("campaign executor must originate from the frozen bundle")
    args, policies = frozen_execution_inputs(campaign)
    if args.script_debug:
        real_check_output = openttdlab.subprocess.check_output

        def check_output_with_script_debug(command, *rest, **kwargs):
            command = tuple(command)
            if any(str(part).startswith("-vnull") for part in command):
                command = command[:1] + ("-d", "script=4") + command[1:]
            return real_check_output(command, *rest, **kwargs)

        openttdlab.subprocess.check_output = check_output_with_script_debug

    global CHECKPOINT_PATH, ENGINE_LOG_DIR, LINE_TELEMETRY
    LINE_TELEMETRY = bool(args.line_telemetry)
    out = campaign.out_path
    CHECKPOINT_PATH = campaign.checkpoint_path
    ENGINE_LOG_DIR = campaign.engine_log_dir

    bench_v2.CHECKPOINT_PATH = CHECKPOINT_PATH
    enable_engine_failure_capture(timeout_sec=args.engine_timeout)
    enable_savegame_cleanup()

    exps = make_experiments_plan(
        args.seeds,
        args.years,
        repeats=args.repeats,
        campaign=campaign,
        policy_id=args.policy_id,
        policies=policies,
    )
    for experiment in exps:
        experiment["engine_log_path"] = str(engine_log_path_for(
            ENGINE_LOG_DIR,
            experiment["seed"],
            experiment.get("repeat", 0),
            policy_id=experiment.get("policy_id", args.policy_id),
        ))
    validate_paired_experiments(exps, [policy["id"] for policy in policies])
    protocol_label = "C66.4" if len(policies) == 2 else "C66.3"
    print(f"=== {protocol_label} campagne {campaign.campaign_id} ===")
    print(f"Bundle: {campaign.bundle_sha256} | Manifest: {campaign.manifest_sha256}")
    if not args.docker_image_id:
        print("NOTE C66.3: ID d'image Docker non injecte ; nom + empreinte runtime conserves dans le manifeste.")
    print(
        f"=== Lancement Banc 1v1 Duel OpexAI vs AAAHogEx : {len(exps)} parties "
        f"({len(args.seeds)} graines x {args.repeats} repetition(s) x {len(policies)} politique(s) x {args.years} ans) ==="
    )
    print(f"Workers: {args.max_workers} | Sortie: {out}")

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=exps,
        ai_libraries=campaign.ai_libraries,
    ))

    last_year = expected_last_year(STARTING_YEAR, args.years)
    last_checkpoint = expected_last_checkpoint(STARTING_YEAR, args.years)
    by_game = defaultdict(list)
    for row in rows:
        run = row.get("run") or []
        seed = run[1] if len(run) > 1 else row.get("seed")
        repeat = run[2] if len(run) > 2 else 0
        duel_policy_id = row.get("duel_policy_id") or args.policy_id
        game_id = row.get("game_id") or f"{campaign.campaign_id}:policy={duel_policy_id}:s{seed}:r{repeat}"
        by_game[game_id].append(row)

    planned_by_game = {experiment["game_id"]: experiment for experiment in exps}
    missing_game_ids = sorted(set(planned_by_game) - set(by_game))
    unexpected_game_ids = sorted(set(by_game) - set(planned_by_game))

    summary = []
    games = []
    for game_id, recs in sorted(by_game.items()):
        first_run = recs[0].get("run") or []
        seed = first_run[1] if len(first_run) > 1 else None
        repeat = first_run[2] if len(first_run) > 2 else 0
        policy_ids = {row.get("duel_policy_id") for row in recs}
        if len(policy_ids) != 1:
            raise ValueError(f"identité de politique instable dans {game_id}: {policy_ids}")
        duel_policy_id = next(iter(policy_ids))
        expected_experiment = planned_by_game.get(game_id)
        identity_error = None
        if expected_experiment is None:
            identity_error = f"unexpected_game:{game_id}"
        else:
            expected_identity = (
                expected_experiment.get("campaign_id"),
                expected_experiment.get("game_id"),
                expected_experiment.get("source_bundle_sha256"),
                expected_experiment.get("policy_id"),
            )
            observed_identities = {
                (
                    row.get("campaign_id"),
                    row.get("game_id"),
                    row.get("source_bundle_sha256"),
                    row.get("duel_policy_id"),
                )
                for row in recs
            }
            if observed_identities != {expected_identity}:
                identity_error = (
                    f"unstable_campaign_identity:{sorted(observed_identities, key=str)} "
                    f"expected={expected_identity}"
                )
        log_path = next((row.get("engine_log_path") for row in recs if row.get("engine_log_path")), None)
        assessment = assess_game(
            recs,
            starting_year=STARTING_YEAR,
            years=args.years,
            engine_log_path=log_path,
        )
        part = summarise(recs, expected_last_year=last_year, expected_savegames=args.years * 12)
        part = _stamp_structural_metrics(part, recs)
        part_annotated = annotate_summary(part, recs, assessment)
        for record in part_annotated:
            if record.get("status") == "bankrupt":
                for metric in SUCCESS_METRICS:
                    if record.get(metric) is None:
                        record[metric] = 0
            if identity_error:
                record["status"] = "missing_data"
                record["run_ok"] = False
                record["include_in_economic_stats"] = False
                record["failure_reason"] = identity_error
            record.update({
                "campaign_id": campaign.campaign_id,
                "policy_id": duel_policy_id if record["arm"] == "OpexAI" else "AAAHogEx",
                "duel_policy_id": duel_policy_id,
                "game_id": game_id,
                "company_slot": 0 if record["arm"] == "OpexAI" else 1,
                "source_bundle_sha256": campaign.bundle_sha256,
            })
        assessment = reconcile_assessment(assessment, part_annotated)
        summary.extend(part_annotated)
        games.append({
            "campaign_id": campaign.campaign_id,
            "policy_id": duel_policy_id,
            "game_id": game_id,
            "source_bundle_sha256": campaign.bundle_sha256,
            "seed": seed,
            "repeat": repeat,
            "game_ok": assessment["game_ok"],
            "game_status": assessment["game_status"],
            "engine_log_path": assessment["engine_log_path"],
            "expected_last_checkpoint": assessment["expected_last_checkpoint"],
            "unattributed_errors": assessment["unattributed_errors"],
            "companies": {
                name: {
                    "status": payload["status"],
                    "run_ok": payload["run_ok"],
                    "failure_reason": payload["failure_reason"],
                    "horizon_complete": payload["horizon_complete"],
                    "activity": payload["activity"]["signal"],
                }
                for name, payload in assessment["companies"].items()
            },
        })
    for record in summary:
        record.pop("openttd_output", None)
    failed = [record for record in summary if not record["run_ok"]]
    for game_id in missing_game_ids:
        experiment = planned_by_game[game_id]
        failure = {
            "arm": "duel",
            "seed": experiment["seed"],
            "repeat": experiment.get("repeat", 0),
            "duel_policy_id": experiment.get("policy_id"),
            "game_id": game_id,
            "status": "missing_data",
            "game_ok": False,
            "failure_reason": "missing_game:no_rows",
        }
        failed.append(failure)
        games.append({
            "campaign_id": campaign.campaign_id,
            "policy_id": experiment.get("policy_id"),
            "game_id": game_id,
            "source_bundle_sha256": campaign.bundle_sha256,
            "seed": experiment["seed"],
            "repeat": experiment.get("repeat", 0),
            "game_ok": False,
            "game_status": "missing_data",
            "engine_log_path": None,
            "expected_last_checkpoint": last_checkpoint,
            "unattributed_errors": [],
            "companies": {},
            "failure_reason": "missing_game:no_rows",
        })
    for game_id in unexpected_game_ids:
        if not any(record.get("game_id") == game_id for record in failed):
            failed.append({
                "arm": "duel",
                "seed": None,
                "repeat": 0,
                "duel_policy_id": None,
                "game_id": game_id,
                "status": "missing_data",
                "game_ok": False,
                "failure_reason": "unexpected_game",
            })

    policy_reports = {}
    for policy in policies:
        current_id = policy["id"]
        policy_summary = [record for record in summary if record.get("duel_policy_id") == current_id]
        policy_reports[current_id] = {
            "statistics": arm_statistics(policy_summary, list(ARMS)),
            "paired_comparisons": paired_comparisons(policy_summary, list(ARMS)),
        }

    policy_comparison = None
    if len(policies) == 2:
        policy_comparison = build_policy_comparison(
            summary,
            rows,
            seeds=args.seeds,
            repeats=args.repeats,
            reference_policy_id=args.policy_id,
            variant_policy_id=args.variant_policy_id,
            primary_metric=args.primary_metric,
            min_useful_primary_delta=args.min_useful_primary_delta,
            value_guard_max_loss_pct=args.value_guard_max_loss_pct,
            starting_year=STARTING_YEAR,
            years=args.years,
            decision_rule=args.decision_rule,
        )

    payload = {
        "campaign_id": campaign.campaign_id,
        "policy_id": args.policy_id,
        "source_bundle_sha256": campaign.bundle_sha256,
        "manifest_path": str(campaign.manifest_path),
        "manifest_sha256": campaign.manifest_sha256,
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "repeats": args.repeats,
        "policies": [
            {
                "id": policy["id"],
                "role": policy["role"],
                "explicit_settings": [list(item) for item in policy.get("explicit_settings", ())],
            }
            for policy in policies
        ],
        "arms": list(ARMS),
        "design": (
            "Deux duels partagés séparés, référence puis variante, chacun OpexAI slot 0 vs AAAHogEx slot 1"
            if len(policies) == 2 else
            "Duel partagé OpexAI (joueur 0) vs AAAHogEx (joueur 1)"
        ),
        "success_metrics": list(SUCCESS_METRICS),
        "expected_last_year": last_year,
        "expected_last_checkpoint": last_checkpoint,
        "engine_log_dir": str(ENGINE_LOG_DIR),
        "games": games,
        "summary": summary,
        "failed_runs": [
            {
                "arm": record["arm"],
                "seed": record["seed"],
                "repeat": record.get("repeat", 0),
                "duel_policy_id": record.get("duel_policy_id"),
                "game_id": record.get("game_id"),
                "status": record.get("status"),
                "game_ok": record.get("game_ok"),
                "failure_reason": record.get("failure_reason"),
            }
            for record in failed
        ],
        "statistics": policy_reports[args.policy_id]["statistics"],
        "paired_comparisons": policy_reports[args.policy_id]["paired_comparisons"],
        "policy_reports": policy_reports,
        "policy_comparison": policy_comparison,
        "line_telemetry": build_line_telemetry_report(rows) if LINE_TELEMETRY else None,
    }
    # A modified bundle cannot receive a final campaign report claiming its old hash.
    verify_manifest_bundle(campaign.manifest_path, campaign.manifest_sha256)
    write_json_atomically(out, payload)

    print("\n" + "=" * 115)
    print(f"BANC 1v1 OPEXAI vs AAAHOGEX (CARTE PARTAGÉE) — BILAN {args.years} ANS ({len(args.seeds)} GRAINES)")
    print("=" * 115)
    header = (f"{'Graine':<8} | {'Valeur Opex vs AAAHogEx':<32} | {'Profit An Opex vs AAA':<28} | "
              f"{'Score O/A':<14} | {'Véhicules O/A':<16} | {'Gares O/A':<12} | {'statut O/A':<28}")
    print(header)
    print("-" * len(header))

    # Tableau par graine/repetition
    runs_by_seed = {}
    for r in summary:
        runs_by_seed[(r.get("duel_policy_id"), r["arm"], r["seed"], r.get("repeat", 0))] = r

    for repeat in range(args.repeats):
      for s in args.seeds:
        op = runs_by_seed.get((args.policy_id, "OpexAI", s, repeat), {})
        aa = runs_by_seed.get((args.policy_id, "AAAHogEx", s, repeat), {})

        op_v, aa_v = op.get("company_value"), aa.get("company_value")
        op_p, aa_p = op.get("profit_year"), aa.get("profit_year")
        op_s, aa_s = op.get("performance_history"), aa.get("performance_history")
        op_veh, aa_veh = op.get("n_vehicles"), aa.get("n_vehicles")
        op_stn, aa_stn = op.get("n_stations"), aa.get("n_stations")

        v_str = (
            f"{op_v:>10,.0f} vs {aa_v:>10,.0f} ({(op_v / aa_v * 100) if aa_v else 0:>4.1f}%)"
            if (op_v is not None and aa_v is not None) else "FAIL"
        )
        p_str = f"{op_p:>8,.0f} vs {aa_p:>8,.0f}" if (op_p is not None and aa_p is not None) else "FAIL"
        s_str = f"{op_s:>4} vs {aa_s:<4}" if (op_s is not None and aa_s is not None) else "FAIL"
        veh_str = f"{op_veh:>3} vs {aa_veh:<3}" if (op_veh is not None and aa_veh is not None) else "FAIL"
        stn_str = f"{op_stn:>3} vs {aa_stn:<3}" if (op_stn is not None and aa_stn is not None) else "FAIL"

        st_op = op.get("status") or ("OK" if op.get("run_ok") else "FAIL")
        st_aa = aa.get("status") or ("OK" if aa.get("run_ok") else "FAIL")
        seed_label = f"{s}/r{repeat}" if args.repeats > 1 else str(s)
        print(f"{seed_label:<8} | {v_str:<32} | {p_str:<28} | {s_str:<14} | {veh_str:<16} | {stn_str:<12} | {st_op}/{st_aa}")

    print("-" * len(header))

    stats = payload["statistics"]
    for arm in ARMS:
        s = stats.get(arm, {})
        cv = s.get("company_value", {}).get("mean")
        py = s.get("profit_year", {}).get("mean")
        sc = s.get("performance_history", {}).get("mean")
        nv_list = [r["n_vehicles"] for r in summary if r.get("duel_policy_id") == args.policy_id and r["arm"] == arm and r.get("n_vehicles") is not None and r.get("run_ok", True)]
        ns_list = [r["n_stations"] for r in summary if r.get("duel_policy_id") == args.policy_id and r["arm"] == arm and r.get("n_stations") is not None and r.get("run_ok", True)]
        nv = statistics.mean(nv_list) if nv_list else None
        ns = statistics.mean(ns_list) if ns_list else None
        nv_str = f"{nv:>4.1f}" if nv is not None else " N/A"
        ns_str = f"{ns:>4.1f}" if ns is not None else " N/A"
        if cv is not None:
            print(f"MOYENNE [{arm:<8}] : CV: {cv:>10,.0f} £ | Profit/an: {py:>8,.0f} £ | Score: {sc:>4.0f} | Véhicules: {nv_str} | Gares: {ns_str}")

    print("\n=== COMPARAISON APPARIÉE OPEXAI vs AAAHOGEX ===")
    for comp in payload["paired_comparisons"]:
        a, b = comp["arm_a"], comp["arm_b"]
        if (a == "OpexAI" and b == "AAAHogEx") or (a == "AAAHogEx" and b == "OpexAI"):
            for metric in ("company_value", "profit_year", "performance_history", "median_station_rating"):
                m = comp["metrics"].get(metric, {})
                diff = m.get("mean_difference_percent")
                wins = m.get("arm_a_beats_arm_b")
                n = m.get("n")
                pval = m.get("wilcoxon_p") or m.get("sign_test_p")
                pval_str = f"p={pval:.4f}" if pval is not None else "p=N/A"
                if diff is not None:
                    print(f"  {metric:<24} : d% = {diff:+.2f}% | Victoires {a} = {wins}/{n} ({pval_str})")

    if policy_comparison is not None:
        primary = policy_comparison["aggregates"][args.primary_metric]["policy_delta"]
        guard = policy_comparison["aggregates"][VALUE_GUARD_METRIC]["policy_ratio"]
        print("\n=== C66.4 VARIANTE - RÉFÉRENCE ===")
        if args.decision_rule == "mean40":
            ci_t = primary.get("mean_student_t_95pct_ci")
            print(
                f"{args.primary_metric}: delta moyen={primary['mean']} median={primary['median']} "
                f"V/D/E={primary['wins']}/{primary['losses']}/{primary['ties']} "
                f"CI95_Student={ci_t} (borne basse > 0: {policy_comparison.get('ci_pass')})"
            )
        else:
            print(
                f"{args.primary_metric}: delta moyen={primary['mean']} median={primary['median']} "
                f"V/D/E={primary['wins']}/{primary['losses']}/{primary['ties']} "
                f"p_signes={primary['sign_test_p']} CI95={primary['mean_normal_95pct_ci']}"
            )
        print(
            f"company_value: ratio des moyennes={guard['ratio_of_means']} "
            f"({guard['ratio_of_means_percent_change']}%), moyenne des ratios={guard['mean_of_ratios']}"
        )
        print(
            f"paires={policy_comparison['complete_pairs']}/{policy_comparison['planned_pairs']} "
            f"verdict={policy_comparison['verdict']}"
        )

    enforce_validation_outcome(failed, policy_comparison)


def selftest():
    """Vérifie unitairement le comportement d'extract_company_record et de summarise en mode fail-closed."""
    global ENGINE_LOG_DIR
    # 1. Test sur fixture réelle
    fixture_path = ROOT / "sweeps" / "fixtures" / "c66_control_fixture_15_3.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            c66 = json.load(f)
        rec0 = extract_company_record(c66["chunks"], 0, ["OpexAI", 42, 0], "1970-12-01")
        assert rec0["vehs_chunk_valid"] is True, "Chunk VEHS valide attendu"
        assert rec0["stnn_chunk_valid"] is True, "Chunk STNN valide attendu"
        assert rec0["n_vehicles"] == 21, f"21 pilotables attendus, reçu {rec0['n_vehicles']}"
        assert rec0["primary_vehicles"] == 21, f"21 pilotables attendus, reçu {rec0['primary_vehicles']}"
        assert rec0["vehicle_pool_entries"] == 26, (
            f"26 entrées brutes attendues, reçu {rec0['vehicle_pool_entries']}"
        )
        assert rec0["n_stations"] == 24, f"24 gares attendues, reçu {rec0['n_stations']}"

    # 2. Test fail-closed sur chunks manquants / invalides
    corrupt_chunks = {"VEHS": None, "STNN": None, "PLYR": {0: {"old_economy": []}}}
    rec_bad = extract_company_record(corrupt_chunks, 0, ["OpexAI", 99, 0], "1970-12-01")
    assert rec_bad["vehs_chunk_valid"] is False, "VEHS None doit être invalide"
    assert rec_bad["stnn_chunk_valid"] is False, "STNN None doit être invalide"
    assert rec_bad["n_vehicles"] is None, "n_vehicles doit être None sur chunk invalide"
    assert rec_bad["primary_vehicles"] is None, "primary_vehicles doit être None sur chunk invalide"
    assert rec_bad["n_stations"] is None, "n_stations doit être None sur chunk invalide"
    assert rec_bad["fleet_status"] is None
    assert rec_bad["stations_by_facility"] is None

    # 3. Test summarise sur row corrompue
    summary = summarise([rec_bad])
    assert len(summary) == 1
    s0 = summary[0]
    assert s0["run_ok"] is False, "Le run doit être marqué en échec (run_ok=False)"
    assert s0["physical_ok"] is False, "physical_ok doit être False"
    assert "physical_decode_failure" in s0["failure_reason"], f"failure_reason attendu, reçu: {s0['failure_reason']}"
    assert s0["n_vehicles"] is None, "n_vehicles doit rester None dans summary"

    rec_bad["run"] = ["OpexAI", 99, 0]
    rec_ok = extract_company_record(
        {"PLYR": {1: {"old_economy": [{"company_value": 1}]}}, "VEHS": {}, "STNN": {}},
        1, ["AAAHogEx", 99, 0], "1974-12-01",
    )
    rec_ok["run"] = ["AAAHogEx", 99, 0]
    rec_ok["company_present"] = True
    rec_ok["primary_vehicles"] = 1
    rec_ok["n_stations"] = 1
    rec_ok["months_of_bankruptcy"] = 0
    rec_bad["company_present"] = True
    rec_bad["primary_vehicles"] = 0
    rec_bad["n_stations"] = 0
    rec_bad["months_of_bankruptcy"] = 0
    rec_bad["date"] = "1974-12-01"
    rec_ok["date"] = "1974-12-01"
    health = assess_game(
        [rec_bad, rec_ok], starting_year=1974, years=1,
        engine_log=(ROOT / "sweeps" / "fixtures" / "c66_health" / "clean.log").read_text(),
    )
    mixed = annotate_summary(summarise([rec_bad, rec_ok]), [rec_bad, rec_ok], health)
    opex_line = next(item for item in mixed if item["arm"] == "OpexAI")
    assert opex_line["run_ok"] is False
    assert "physical_decode_failure" in (opex_line["failure_reason"] or "")
    assert opex_line["status"] != "complete"
    assert opex_line["game_ok"] is False

    # 4. C66.2 : le journal est unique ; une erreur HogEx n'est pas imputée à Opex.
    import tempfile

    hogex_log = (ROOT / "sweeps" / "fixtures" / "c66_health" / "hogex_error.log").read_text()
    with tempfile.TemporaryDirectory() as tmp:
        ENGINE_LOG_DIR = Path(tmp)
        fake_log_path = engine_log_path_for(ENGINE_LOG_DIR, 7, 0, policy_id="reference")
        fake_row = {
            "chunks": corrupt_chunks,
            "date": "1974-12-01",
            "output": hogex_log,
            "experiment": {"seed": 7, "repeat": 0, "engine_log_path": str(fake_log_path)},
        }
        rec0, rec1 = keep(fake_row)
        assert rec0["engine_log_path"] == rec1["engine_log_path"]
        assert rec0["openttd_output"] is None and rec1["openttd_output"] is None
        assert Path(rec0["engine_log_path"]).read_text() == hogex_log
        rec0["run"] = ["OpexAI", 7, 0]
        rec1["run"] = ["AAAHogEx", 7, 0]
        rec0["company_present"] = True
        rec1["company_present"] = True
        rec0["primary_vehicles"] = 4
        rec1["primary_vehicles"] = 8
        rec0["n_stations"] = 2
        rec1["n_stations"] = 3
        rec0["months_of_bankruptcy"] = 0
        rec1["months_of_bankruptcy"] = 0
        rec0["company_value"] = 1000
        rec1["company_value"] = 2000
        game = assess_game(
            [rec0, rec1], starting_year=1974, years=1,
            engine_log_path=rec0["engine_log_path"],
        )
        assert game["companies"]["OpexAI"]["status"] != "noai_error"
        assert game["companies"]["AAAHogEx"]["status"] == "noai_error"
        assert game["game_ok"] is False
        annotated = annotate_summary(
            [
                {"arm": "OpexAI", "seed": 7, "repeat": 0, "run_ok": True, "failure_reason": None,
                 "openttd_output": hogex_log},
                {"arm": "AAAHogEx", "seed": 7, "repeat": 0, "run_ok": True, "failure_reason": None,
                 "openttd_output": ""},
            ],
            [rec0, rec1],
            game,
        )
        assert "openttd_output" not in annotated[0]
        assert annotated[0]["run_ok"] is False
        assert annotated[0]["status"] == "missing_data"
        assert annotated[1]["run_ok"] is False
        ENGINE_LOG_DIR = None

    rec_absent = extract_company_record({"PLYR": {}, "VEHS": {}, "STNN": {}}, 1, ["AAAHogEx", 1, 0], "1974-12-01")
    assert rec_absent["company_present"] is False

    # 4b. Early-slot : la ressource rare est comptee par TownID et facility airport,
    # independamment du nombre total de gares. Town 10 est partage 1-1, town 20 est
    # monopolise 2-0 par AAAHogEx ; une gare routiere ne doit pas compter.
    slot_fixture = {
        "STNN": {
            0: {"normal": {"base": {"owner": 0, "town": 10, "facilities": 8}}},
            1: {"normal": {"base": {"owner": 1, "town": 10, "facilities": 8}}},
            2: {"normal": {"base": {"owner": 1, "town": 20, "facilities": 8}}},
            3: {"normal": {"base": {"owner": 1, "town": 20, "facilities": 8}}},
            4: {"normal": {"base": {"owner": 0, "town": 30, "facilities": 4}}},
        },
        "SIGN": {
            0: {"name": "SK|70|10|20|50"},
            1: {"name": "SB|70|10|20|2"},
            2: {"name": "OE|A|771"},
        },
    }
    slots = airport_slot_metrics(slot_fixture)
    assert slots["airport_slots_opex"] == 1
    assert slots["airport_slots_aaahogex"] == 3
    assert slots["airport_towns_opex_present"] == 1
    assert slots["airport_towns_aaahogex_present"] == 2
    assert slots["airport_towns_shared_1_1"] == 1
    assert slots["airport_towns_aaahogex_2_opex_0"] == 1
    signs = early_slot_sign_metrics(slot_fixture)
    assert signs["early_slot_select_signs"] == 1
    assert signs["early_slot_build_signs"] == 1
    assert signs["early_slot_build_claims"] == 2
    assert signs["air_error_771_signs"] == 1

    # 4c. Telemetrie ligne : AAAHogEx partage un group_id et une liste ORDL entre
    # les vehicules d'une meme Route. TownID fournit la cle comparable entre parties.
    line_fixture = {
        "STNN": {
            0: {"normal": {"base": {"owner": 1, "town": 10, "facilities": 8, "xy": 1000},
                           "goods": [
                               {"status": 1, "time_since_pickup": 5, "rating": 120, "max_waiting_cargo": 40},
                               {"status": 0, "time_since_pickup": 255, "rating": 175, "max_waiting_cargo": 0},
                           ]}},
            1: {"normal": {"base": {"owner": 1, "town": 20, "facilities": 8, "xy": 2000},
                           "goods": [
                               {"status": 1, "time_since_pickup": 9, "rating": 90, "max_waiting_cargo": 80},
                               {"status": 0, "time_since_pickup": 255, "rating": 175, "max_waiting_cargo": 0},
                           ]}},
        },
        "ORDL": {
            "0": {"orders": [
                {"type": 1, "flags": 0, "dest": 0},
                {"type": 1, "flags": 0, "dest": 1},
            ]},
        },
        "VEHS": {
            0: {"type": 3, "aircraft": {"common": {
                "owner": 1, "unitnumber": 1, "subtype": 0, "group_id": 7,
                "orders": 1, "next": 0, "cargo_type": 0, "cargo_cap": 100,
                "profit_this_year": 25600, "profit_last_year": 12800, "value": 50000,
            }}},
            1: {"type": 3, "aircraft": {"common": {
                "owner": 1, "unitnumber": 2, "subtype": 0, "group_id": 7,
                "orders": 1, "next": 0, "cargo_type": 0, "cargo_cap": 80,
                "profit_this_year": 51200, "profit_last_year": 25600, "value": 45000,
            }}},
        },
    }
    line_diag = extract_line_telemetry(line_fixture, 1)
    assert line_diag["ok"] is True
    assert line_diag["unresolved_vehicles"] == []
    assert len(line_diag["lines"]) == 1
    line = line_diag["lines"][0]
    assert line["line_key_local"] == "group:7"
    assert line["market_key"] == "air|10,20"
    assert line["vehicles"] == 2
    assert line["capacity_by_cargo"] == {"0": 180}
    assert line["profit_this_year_gbp"] == 300.0
    assert line["ordered_station_tiles"] == [1000, 2000]
    assert line["endpoint_cargo_stats"] == [
        {
            "station_id": 0,
            "town_id": 10,
            "tile": 1000,
            "airport": {
                "tile": None, "width": None, "height": None,
                "type": None, "layout": None, "rotation": None,
            },
            "cargo": {
                "0": {
                    "rated": True,
                    "rating": 120,
                    "time_since_pickup": 5,
                    "max_waiting_cargo": 40,
                },
            },
        },
        {
            "station_id": 1,
            "town_id": 20,
            "tile": 2000,
            "airport": {
                "tile": None, "width": None, "height": None,
                "type": None, "layout": None, "rotation": None,
            },
            "cargo": {
                "0": {
                    "rated": True,
                    "rating": 90,
                    "time_since_pickup": 9,
                    "max_waiting_cargo": 80,
                },
            },
        },
    ]
    assert line["profit_last_year_gbp"] == 150.0

    import inspect
    import openttdlab
    from bench_v2 import enable_savegame_cleanup
    enable_engine_failure_capture(timeout_sec=30)
    enable_savegame_cleanup()
    missing = {"run_dir", "i", "final_screenshot_directory"} - set(
        inspect.signature(openttdlab._run_experiment).parameters
    )
    assert not missing, f"composition des wrappers a perdu {missing}"

    # 5. C66.3 : defaults effectifs, garde de comparaison et immutabilite du snapshot.
    defaults = parse_ai_settings(ROOT / "ai" / "OpexAI" / "info.nut")
    assert defaults["debug_signs"] == 1
    assert defaults["air_fleet_cadence_days"] == 7

    diff = validate_policy_settings(
        {"c80_mode_regen": 0, "road_mode": 0},
        {"c80_mode_regen": 1, "road_mode": 0},
        intervention_settings=("c80_mode_regen",),
    )
    assert set(diff) == {"c80_mode_regen"}
    try:
        validate_policy_settings(
            {"c80_mode_regen": 0, "road_mode": 0},
            {"c80_mode_regen": 1, "road_mode": 1},
            intervention_settings=("c80_mode_regen",),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("C66.3 doit refuser une difference de politique non annoncee")

    import shutil
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        live = tmp / "live"
        snap = tmp / "snap"
        live.mkdir()
        (live / "main.nut").write_text("version=1\n", encoding="utf-8")
        shutil.copytree(live, snap)
        frozen_hash = fingerprint_tree(snap)["sha256"]
        (live / "main.nut").write_text("version=2\n", encoding="utf-8")
        assert fingerprint_tree(snap)["sha256"] == frozen_hash

    # 6. C66.4 : comparaison de politiques appariée, ratios, signes et fail-closed.
    assert parse_opex_variant("OpexAI[c80_mode_regen=1]") == (("c80_mode_regen", 1),)
    try:
        parse_opex_variant("OpexAI[reglage_inconnu_c66=1]")
    except ValueError:
        pass
    else:
        raise AssertionError("C66.4 doit reutiliser la validation bench_v2 des reglages inconnus")

    synthetic_summary = []
    synthetic_rows = []
    values = {
        ("reference", 1): {"OpexAI": (100, 1000), "AAAHogEx": (90, 1100)},
        ("variant", 1): {"OpexAI": (120, 1050), "AAAHogEx": (95, 1120)},
        ("reference", 2): {"OpexAI": (200, 2000), "AAAHogEx": (210, 2200)},
        ("variant", 2): {"OpexAI": (190, 1900), "AAAHogEx": (205, 2150)},
    }
    for (policy, seed), arms in values.items():
        for arm, (profit_year_value, company_value) in arms.items():
            record = {
                "duel_policy_id": policy,
                "policy_id": policy if arm == "OpexAI" else "AAAHogEx",
                "arm": arm,
                "seed": seed,
                "repeat": 0,
                "run_ok": True,
                "game_ok": True,
                "status": "complete",
                "failure_reason": None,
                "profit_year": profit_year_value,
                "company_value": company_value,
                "profit": profit_year_value // 4,
                "performance_history": 100,
                "median_station_rating": 100,
            }
            synthetic_summary.append(record)
            synthetic_rows.append({
                **record,
                "run": [arm, seed, 0],
                "date": "1970-12-01",
            })

    comparison = build_policy_comparison(
        synthetic_summary,
        synthetic_rows,
        seeds=[1, 2],
        repeats=1,
        reference_policy_id="reference",
        variant_policy_id="variant",
        primary_metric="profit_year",
        min_useful_primary_delta=5,
        value_guard_max_loss_pct=5,
        starting_year=1970,
        years=1,
    )
    primary = comparison["aggregates"]["profit_year"]["policy_delta"]
    assert comparison["comparison_complete"] is True
    assert comparison["adoption_sample_complete"] is False
    assert comparison["verdict"] == "diagnostic_only"
    assert comparison["primary_pass"] is None
    assert primary["mean"] == 5.0 and primary["median"] == 5.0
    assert (primary["wins"], primary["losses"], primary["ties"]) == (1, 1, 0)
    assert primary["sign_test_n_excluding_ties"] == 2 and primary["sign_test_p"] == 1.0
    ratio = comparison["aggregates"]["company_value"]["policy_ratio"]
    assert ratio["n_positive_denominator"] == 2
    assert ratio["ratio_of_means"] != ratio["mean_of_ratios"]
    assert ratio_statistics([(10, 5), (20, 0), (30, -1)])["n_positive_denominator"] == 1

    # Test de la fonction de quantile Student-t (valeurs critiques 95% bilatéral)
    assert student_t_ci95_critical_value(1) == 12.706205
    assert student_t_ci95_critical_value(19) == 2.093024
    assert student_t_ci95_critical_value(39) == 2.022691
    assert student_t_ci95_critical_value(40) == 2.021075
    assert student_t_ci95_critical_value(100) == 1.983972
    try:
        student_t_ci95_critical_value(0)
    except ValueError:
        pass
    else:
        raise AssertionError("student_t_ci95_critical_value doit rejeter df < 1")

    def synthetic_policy_case(deltas, decision_rule="signs20", seeds=None):
        case_summary = []
        case_rows = []
        if seeds is None:
            seeds = list(range(1, len(deltas) + 1))
        for seed, delta in zip(seeds, deltas):
            for policy, opex_profit, opex_value in (
                ("reference", 100, 1000),
                ("variant", 100 + delta, 1001),
            ):
                for arm, profit_value, company_value in (
                    ("OpexAI", opex_profit, opex_value),
                    ("AAAHogEx", 90, 1100),
                ):
                    record = {
                        "duel_policy_id": policy,
                        "policy_id": policy if arm == "OpexAI" else "AAAHogEx",
                        "arm": arm,
                        "seed": seed,
                        "repeat": 0,
                        "run_ok": True,
                        "game_ok": True,
                        "status": "complete",
                        "failure_reason": None,
                        "profit_year": profit_value,
                        "company_value": company_value,
                        "profit": profit_value // 4,
                        "performance_history": 100,
                        "median_station_rating": 100,
                        "primary_vehicles": 10,
                    }
                    case_summary.append(record)
                    case_rows.append({
                        **record,
                        "run": [arm, seed, 0],
                        "date": "1979-12-01",
                    })
        return build_policy_comparison(
            case_summary,
            case_rows,
            seeds=seeds,
            repeats=1,
            reference_policy_id="reference",
            variant_policy_id="variant",
            primary_metric="profit_year",
            min_useful_primary_delta=5,
            value_guard_max_loss_pct=5,
            starting_year=1970,
            years=10,
            decision_rule=decision_rule,
        )

    # Non-régression signs20 : pass (15 victoires / 5 défaites, delta moyen >= 5)
    adopted = synthetic_policy_case([10] * 15 + [-1] * 5, decision_rule="signs20")
    assert adopted["comparison_complete"] is True
    assert adopted["adoption_sample_complete"] is True
    assert adopted["sign_pass"] is True
    assert adopted["primary_mean_pass"] is True
    assert adopted["primary_pass"] is True
    assert adopted["verdict"] == "pass"
    assert adopted["decision_rule"]["required_pairs"] == 20
    assert adopted["decision_rule"]["required_wins"] == 15

    # Non-régression signs20 : fail_primary (signes échouent 10/10 malgré moyenne positive)
    mean_positive_but_signs_fail = synthetic_policy_case([100] * 10 + [-1] * 10, decision_rule="signs20")
    assert mean_positive_but_signs_fail["primary_mean_pass"] is True
    assert mean_positive_but_signs_fail["sign_pass"] is False
    assert mean_positive_but_signs_fail["primary_pass"] is False
    assert mean_positive_but_signs_fail["verdict"] == "fail_primary"

    # mean40 : pass (40 paires, moyenne >= 5, borne basse IC95 Student > 0, garde OK)
    pass_mean40 = synthetic_policy_case([20] * 35 + [5] * 5, decision_rule="mean40")
    assert pass_mean40["comparison_complete"] is True
    assert pass_mean40["adoption_sample_complete"] is True
    assert pass_mean40["ci_pass"] is True
    assert pass_mean40["primary_mean_pass"] is True
    assert pass_mean40["primary_pass"] is True
    assert pass_mean40["value_guard_pass"] is True
    assert pass_mean40["verdict"] == "pass"
    assert pass_mean40["decision_rule"]["rule"] == "mean40"
    assert pass_mean40["decision_rule"]["required_pairs"] == 40
    p_delta_40 = pass_mean40["aggregates"]["profit_year"]["policy_delta"]
    assert p_delta_40["mean_student_t_95pct_ci"] is not None
    assert p_delta_40["mean_student_t_95pct_ci"][0] > 0

    # mean40 : fail_primary (cas A : moyenne < min_useful_primary_delta, ex: deltas 3.0 < 5.0)
    fail_mean_low = synthetic_policy_case([3] * 40, decision_rule="mean40")
    assert fail_mean_low["comparison_complete"] is True
    assert fail_mean_low["adoption_sample_complete"] is True
    assert fail_mean_low["ci_pass"] is True
    assert fail_mean_low["primary_mean_pass"] is False
    assert fail_mean_low["primary_pass"] is False
    assert fail_mean_low["verdict"] == "fail_primary"

    # mean40 : fail_primary (cas B : moyenne >= 5 mais forte variance -> borne basse IC95 <= 0)
    # 22 victoires (+100) et 18 pertes (-100) : moyenne = 10 >= 5, mais IC95 négatif en borne basse
    fail_ci_noise = synthetic_policy_case([100] * 22 + [-100] * 18, decision_rule="mean40")
    assert fail_ci_noise["comparison_complete"] is True
    assert fail_ci_noise["adoption_sample_complete"] is True
    assert fail_ci_noise["ci_pass"] is False
    assert fail_ci_noise["primary_mean_pass"] is True
    assert fail_ci_noise["primary_pass"] is False
    assert fail_ci_noise["verdict"] == "fail_primary"

    # mean40 : incomplet (39 paires fournies pour 40 planifiées)
    incomplete_mean40 = synthetic_policy_case([20] * 39, decision_rule="mean40", seeds=list(range(1, 41)))
    assert incomplete_mean40["comparison_complete"] is False
    assert incomplete_mean40["verdict"] == "incomplete"
    assert incomplete_mean40["primary_pass"] is None

    # mean40 : diagnostic_only (20 paires complètes sur 40 requises pour l'adoption)
    diag_mean40 = synthetic_policy_case([20] * 20, decision_rule="mean40", seeds=list(range(1, 21)))
    assert diag_mean40["comparison_complete"] is True
    assert diag_mean40["adoption_sample_complete"] is False
    assert diag_mean40["verdict"] == "diagnostic_only"
    assert diag_mean40["primary_pass"] is None

    incomplete = build_policy_comparison(
        synthetic_summary[:-1],
        synthetic_rows[:-1],
        seeds=[1, 2],
        repeats=1,
        reference_policy_id="reference",
        variant_policy_id="variant",
        primary_metric="profit_year",
        min_useful_primary_delta=5,
        value_guard_max_loss_pct=5,
        starting_year=1970,
        years=1,
    )
    assert incomplete["comparison_complete"] is False
    assert incomplete["verdict"] == "incomplete"
    assert incomplete["primary_pass"] is None
    assert engine_log_path_for("logs", 42, 0, "reference") != engine_log_path_for("logs", 42, 0, "variant")

    shared_adversary = object()
    paired_plan = [
        {"seed": 42, "repeat": 0, "days": 365, "openttd_config": "cfg", "bench_arm": "duel",
         "is_duel": True, "campaign_id": "c", "source_bundle_sha256": "bundle",
         "policy_id": "reference", "game_id": "g-ref", "ais": (object(), shared_adversary)},
        {"seed": 42, "repeat": 0, "days": 365, "openttd_config": "cfg", "bench_arm": "duel",
         "is_duel": True, "campaign_id": "c", "source_bundle_sha256": "bundle",
         "policy_id": "variant", "game_id": "g-var", "ais": (object(), shared_adversary)},
    ]
    validate_paired_experiments(paired_plan, ("reference", "variant"))
    try:
        validate_paired_experiments(
            [paired_plan[0], {**paired_plan[1], "days": 366}], ("reference", "variant")
        )
    except ValueError:
        pass
    else:
        raise AssertionError("C66.4 doit refuser une paire dont la durée diffère")

    # 7. C66.5 : un échec de validation survient après l'écriture atomique du rapport.
    from bench_v2 import write_json_atomically
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "validation.json"
        write_json_atomically(report_path, {"failed_runs": [{"arm": "OpexAI"}]})
        try:
            enforce_validation_outcome([{"arm": "OpexAI"}], None)
        except SystemExit:
            pass
        else:
            raise AssertionError("C66.5 doit interrompre un rapport contenant un échec de santé")
        assert report_path.exists()
        assert json.loads(report_path.read_text())["failed_runs"][0]["arm"] == "OpexAI"

    print("Selftest bench_1v1_5y_20seeds.py réussi avec succès !")


if __name__ == "__main__":
    main()
