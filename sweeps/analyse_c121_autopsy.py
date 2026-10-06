"""Analyse causale C115 <-> C121 a partir des traces passives/autopsie.

Ce script ne lance aucun jeu. Il relie :
- le premier snapshot post-build instrumente (decision deja irreversible),
- les C121_BUILD existants,
- la telemetrie mensuelle reconstruite hors NoAI depuis les sauvegardes.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path


AUTOPSY_RE = re.compile(r"C121_AUTOPSY kind=(\S+) (.*)$")
C121_BUILD_RE = re.compile(r"C121_BUILD (.*)$")
KV_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s]+)")


def kv_fields(text):
    out = {}
    for key, value in KV_RE.findall(text):
        if value in ("true", "false"):
            out[key] = value == "true"
            continue
        try:
            out[key] = int(value)
            continue
        except ValueError:
            pass
        try:
            out[key] = float(value)
            continue
        except ValueError:
            out[key] = value
    return out


def parse_autopsy_log(path):
    snap = None
    cands = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        match = AUTOPSY_RE.search(line)
        if not match:
            continue
        kind, tail = match.groups()
        row = kv_fields(tail)
        row["kind"] = kind
        if kind == "BUILD_SNAPSHOT" and snap is None:
            snap = row
        elif kind == "POST_CAND" and snap is not None and row.get("seq") == snap.get("seq"):
            cands.append(row)
    cands.sort(key=lambda row: row.get("rank", 999))
    return {"snapshot": snap, "candidates": cands}


def parse_c121_builds(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        match = C121_BUILD_RE.search(line)
        if not match:
            continue
        rows.append(kv_fields(match.group(1)))
    return rows


def ym(date):
    year, month = map(int, str(date)[:7].split("-"))
    return year * 12 + month


def month_text(index):
    year, month0 = divmod(index - 1, 12)
    return f"{year:04d}-{month0 + 1:02d}"


def median(values):
    vals = [value for value in values if value is not None and math.isfinite(value)]
    return statistics.median(vals) if vals else None


def safe_ratio(realized, predicted):
    if realized is None or predicted in (None, 0):
        return None
    return realized / float(predicted)


def air_lines(snapshot):
    return [line for line in snapshot.get("lines", []) if line.get("mode") == "air"]


def line_id_key(line):
    return tuple(sorted(int(value) for value in line.get("station_ids", [])))


def town_key(line):
    return tuple(sorted(int(value) for value in line.get("town_ids", []) if value is not None))


def build_snapshot_index(result):
    by_run = defaultdict(list)
    for snap in (result.get("line_telemetry") or {}).get("snapshots", []):
        by_run[(snap.get("duel_policy_id"), snap.get("arm"), snap.get("seed"))].append(snap)
    for rows in by_run.values():
        rows.sort(key=lambda row: ym(row["date"]))
    return by_run


def load_monthly_rows(path):
    out = defaultdict(list)
    with Path(path).open(encoding="utf-8") as handle:
        for raw in handle:
            row = json.loads(raw)
            run = row.get("run") or []
            if not run:
                continue
            out[(row.get("duel_policy_id"), run[0], run[1])].append(row)
    for rows in out.values():
        rows.sort(key=lambda row: ym(row["date"]))
    return out


def find_line_series(snapshots, station_ids=None, town_ids=None):
    station_key = tuple(sorted(station_ids)) if station_ids else None
    town_candidates = []
    if town_ids:
        base = tuple(sorted(town_ids))
        town_candidates = [base, tuple(value + 1 for value in base), tuple(value - 1 for value in base)]
    matches = []
    chosen_key = None
    chosen_basis = None
    for snap in snapshots:
        for line in air_lines(snap):
            if station_key and line_id_key(line) == station_key:
                chosen_key = line.get("line_key_local")
                chosen_basis = "station_ids"
                break
            if town_candidates and town_key(line) in town_candidates:
                chosen_key = line.get("line_key_local")
                chosen_basis = "town_ids"
                break
        if chosen_key is not None:
            break
    if chosen_key is None:
        return [], None
    for snap in snapshots:
        for line in air_lines(snap):
            if line.get("line_key_local") == chosen_key:
                matches.append((snap, line))
                break
    return matches, chosen_basis


def monthly_profit_increments(series):
    increments = {}
    previous = None
    for snap, line in series:
        index = ym(snap["date"])
        current = float(line.get("profit_this_year_gbp") or 0.0)
        year = int(str(snap["date"])[:4])
        if previous is None or previous[0] != year:
            inc = current
        else:
            inc = current - previous[1]
        increments[index] = inc
        previous = (year, current)
    return increments


def endpoint_metrics(line):
    waits = []
    ratings = []
    pickups = []
    for endpoint in line.get("endpoint_cargo_stats", []):
        pax = (endpoint.get("cargo") or {}).get("0") or {}
        if pax.get("max_waiting_cargo") is not None:
            waits.append(float(pax["max_waiting_cargo"]))
        if pax.get("rating") is not None:
            ratings.append(float(pax["rating"]))
        if pax.get("time_since_pickup") is not None:
            pickups.append(float(pax["time_since_pickup"]))
    return {
        "waiting_max_sum": sum(waits) if waits else None,
        "rating_mean": sum(ratings) / len(ratings) if ratings else None,
        "time_since_pickup_max": max(pickups) if pickups else None,
    }


def aaa_overlap_at(snapshot_index, policy, seed, target_month, towns):
    aaa = snapshot_index.get((policy, "AAAHogEx", seed), [])
    if not aaa:
        return None
    snap = min(aaa, key=lambda row: abs(ym(row["date"]) - target_month))
    wanted = set(towns or [])
    if not wanted:
        return None
    aaa_towns = set()
    for line in air_lines(snap):
        aaa_towns.update(line.get("town_ids") or [])
    return len(wanted & aaa_towns)


def outcome_at(series, snapshot_index, policy, seed, months_after):
    if not series:
        return None
    increments = monthly_profit_increments(series)
    build_month = ym(series[0][0]["date"])
    target = build_month + months_after
    by_month = {ym(item[0]["date"]): item for item in series}
    if target not in by_month:
        return None
    row = by_month[target]
    snap, line = row
    target_actual = ym(snap["date"])
    window = 6 if months_after == 6 else 12
    start = target_actual - window + 1
    rolling = sum(value for month, value in increments.items() if start <= month <= target_actual)
    observed_months = sum(1 for month in increments if start <= month <= target_actual)
    annualized = rolling * (12.0 / observed_months) if observed_months else None
    endpoint = endpoint_metrics(line)
    towns = line.get("town_ids") or []
    return {
        "date": snap["date"],
        "months_after_nominal": months_after,
        "profit_ytd": line.get("profit_this_year_gbp"),
        "profit_trailing_window": rolling,
        "profit_trailing_window_months": observed_months,
        "profit_annualized_from_window": annualized,
        "vehicles": line.get("vehicles"),
        "town_ids": towns,
        "capacity_by_cargo": line.get("capacity_by_cargo"),
        "aaa_endpoint_overlap": aaa_overlap_at(snapshot_index, policy, seed, target_actual, towns),
        **endpoint,
    }


def price_band(row):
    price = row.get("plane_price")
    if price is None:
        return "unknown"
    if price < 40000:
        return "<40k"
    if price < 55000:
        return "40-55k"
    return ">=55k"


def build_period(row):
    text = str(row.get("first_observed_month") or "")
    if len(text) < 4 or not text[:4].isdigit():
        return "unknown"
    year = int(text[:4])
    if year <= 1971:
        return "1970-71"
    if year <= 1973:
        return "1972-73"
    return "1974+"


def first_physical_divergence(monthly, seed):
    ref = {row["date"]: row for row in monthly[("c115_reference", "OpexAI", seed)]}
    var = {row["date"]: row for row in monthly[("c121_base", "OpexAI", seed)]}
    for date in sorted(set(ref) & set(var)):
        a, b = ref[date], var[date]
        fields = ("air_primary_vehicles", "airport_slots_opex", "airport_towns_opex_present")
        if any(a.get(field) != b.get(field) for field in fields):
            return {
                "date": date,
                "c115": {field: a.get(field) for field in fields} | {"money": a.get("money")},
                "c121": {field: b.get(field) for field in fields} | {"money": b.get("money")},
            }
    return None


def summarize_group(rows, key_fn):
    groups = defaultdict(list)
    for row in rows:
        groups[str(key_fn(row))].append(row)
    out = {}
    for key, values in sorted(groups.items()):
        ratios12 = [row.get("ratio_12m") for row in values if row.get("ratio_12m") is not None]
        ratios24 = [row.get("ratio_24m") for row in values if row.get("ratio_24m") is not None]
        out[key] = {
            "n": len(values),
            "n_12m": len(ratios12),
            "ratio_12m_median": median(ratios12),
            "n_24m": len(ratios24),
            "ratio_24m_median": median(ratios24),
        }
    return out


def distance_band(row):
    distance = row.get("payment_distance") or row.get("distance")
    if distance is None:
        return "unknown"
    if distance <= 175:
        return "<=175"
    if distance <= 250:
        return "176-250"
    return ">250"


def demand_band(row):
    vals = [row.get("pax_a"), row.get("pax_b")]
    if any(value is None for value in vals):
        return "unknown"
    demand = min(vals)
    if demand < 100:
        return "<100"
    if demand < 200:
        return "100-199"
    return ">=200"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--jsonl", required=True)
    parser.add_argument("--engine-dir", required=True)
    parser.add_argument("--probe-42-dir", required=True)
    parser.add_argument("--probe-rest-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    snapshots = build_snapshot_index(result)
    monthly = load_monthly_rows(args.jsonl)
    seeds = [42, 100, 999]
    per_seed = {}
    calibration = []

    for seed in seeds:
        probe_dir = Path(args.probe_42_dir if seed == 42 else args.probe_rest_dir)
        seed_report = {"first_physical_divergence": first_physical_divergence(monthly, seed)}
        for policy in ("c115_reference", "c121_base"):
            probe = parse_autopsy_log(probe_dir / f"{policy}_seed{seed}_r0.log")
            chosen = probe["candidates"][0] if probe["candidates"] else None
            info = {"probe_snapshot": probe["snapshot"], "selected": chosen,
                    "top_candidates": probe["candidates"][:8]}
            series = []
            basis = None
            if chosen:
                series, basis = find_line_series(
                    snapshots.get((policy, "OpexAI", seed), []),
                    town_ids=[chosen.get("town_a"), chosen.get("town_b")],
                )
            info["match_basis"] = basis
            info["first_observed_month"] = series[0][0]["date"] if series else None
            info["first_line_key"] = series[0][1]["line_key_local"] if series else None
            info["outcomes"] = {str(month): outcome_at(series, snapshots, policy, seed, month)
                                for month in (6, 12, 24)}
            seed_report[policy] = info
        per_seed[str(seed)] = seed_report

        c121_builds = parse_c121_builds(Path(args.engine_dir) / f"c121_base_seed{seed}_r0.log")
        for build in c121_builds:
            station_ids = [build.get("station_id_a"), build.get("station_id_b")]
            if any(value is None for value in station_ids):
                continue
            series, basis = find_line_series(
                snapshots.get(("c121_base", "OpexAI", seed), []), station_ids=station_ids
            )
            if not series:
                continue
            out6 = outcome_at(series, snapshots, "c121_base", seed, 6)
            out12 = outcome_at(series, snapshots, "c121_base", seed, 12)
            out24 = outcome_at(series, snapshots, "c121_base", seed, 24)
            first_month = ym(series[0][0]["date"])
            first_towns = series[0][1].get("town_ids") or []
            realized12 = out12 and out12.get("profit_annualized_from_window")
            realized24 = out24 and out24.get("profit_annualized_from_window")
            predicted = build.get("actual_profit")
            calibration.append({
                "seed": seed,
                "line": build.get("line"),
                "arm": build.get("arm"),
                "first_observed_month": series[0][0]["date"],
                "match_basis": basis,
                "station_ids": station_ids,
                "town_ids": first_towns,
                "aaa_overlap_at_first_observation": aaa_overlap_at(
                    snapshots, "c121_base", seed, first_month, first_towns
                ),
                "actual_n": build.get("actual_n"),
                "decision_n": build.get("decision_n"),
                "target_n": build.get("target_n"),
                "predicted_actual_profit": predicted,
                "predicted_decision_profit": build.get("decision_profit"),
                "predicted_target_profit": build.get("target_profit"),
                "actual_capital": build.get("actual_capital", build.get("decision_capital")),
                "decision_capital": build.get("decision_capital"),
                "airport_capital": build.get("airport_capital"),
                "new_airports": build.get("new_airports"),
                "plane_price": build.get("plane_price"),
                "payment_distance": build.get("payment_distance"),
                "pax_a": build.get("pax_a"),
                "pax_b": build.get("pax_b"),
                "mail_a": build.get("mail_a"),
                "mail_b": build.get("mail_b"),
                "outcome_6m": out6,
                "outcome_12m": out12,
                "outcome_24m": out24,
                "ratio_12m": safe_ratio(realized12, predicted),
                "ratio_24m": safe_ratio(realized24, predicted),
            })

    calib_summary = {
        "n": len(calibration),
        "n_12m": sum(row.get("ratio_12m") is not None for row in calibration),
        "ratio_12m_median": median([row.get("ratio_12m") for row in calibration]),
        "n_24m": sum(row.get("ratio_24m") is not None for row in calibration),
        "ratio_24m_median": median([row.get("ratio_24m") for row in calibration]),
        "by_seed": summarize_group(calibration, lambda row: row["seed"]),
        "by_actual_n": summarize_group(calibration, lambda row: row.get("actual_n")),
        "by_decision_n": summarize_group(calibration, lambda row: row.get("decision_n")),
        "by_new_airports": summarize_group(calibration, lambda row: row.get("new_airports")),
        "by_plane_price": summarize_group(calibration, price_band),
        "by_distance": summarize_group(calibration, distance_band),
        "by_demand": summarize_group(calibration, demand_band),
        "by_arm": summarize_group(calibration, lambda row: row.get("arm")),
        "by_build_period": summarize_group(calibration, build_period),
        "by_aaa_overlap": summarize_group(
            calibration, lambda row: row.get("aaa_overlap_at_first_observation")
        ),
    }

    payload = {
        "source_result": args.result,
        "seeds": seeds,
        "per_seed": per_seed,
        "calibration_summary": calib_summary,
        "calibration_rows": calibration,
        "limitations": [
            "Town population is not serialized in the current savegame parser; no population-band calibration is inferred.",
            "Waiting is max_waiting_cargo since rating recalculation, not instantaneous queue.",
            "Line profit windows are reconstructed from monthly cumulative vehicle profit snapshots; month of construction is bounded by first monthly appearance.",
        ],
    }
    Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "per_seed": {seed: {
            "first_div": per_seed[str(seed)]["first_physical_divergence"],
            "c115_first": per_seed[str(seed)]["c115_reference"]["first_observed_month"],
            "c121_first": per_seed[str(seed)]["c121_base"]["first_observed_month"],
            "c115_12m": per_seed[str(seed)]["c115_reference"]["outcomes"]["12"],
            "c121_12m": per_seed[str(seed)]["c121_base"]["outcomes"]["12"],
        } for seed in seeds},
        "calibration_summary": calib_summary,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
