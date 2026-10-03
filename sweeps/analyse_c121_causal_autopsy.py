#!/usr/bin/env python3
"""Summarise passive C115/C121 AIR divergence from monthly save telemetry.

This reader never launches OpenTTD and never infers data unavailable in saves.
Line age is therefore measured from the first monthly checkpoint where the line
is visible, not from the exact in-game construction day.
"""

from __future__ import annotations

import argparse
import calendar
from collections import defaultdict
from datetime import date
import json
from pathlib import Path


def _month_add(text: str, months: int) -> str:
    year, month, day = map(int, text.split("-"))
    pos = year * 12 + (month - 1) + months
    out_year, out_month0 = divmod(pos, 12)
    out_month = out_month0 + 1
    out_day = min(day, calendar.monthrange(out_year, out_month)[1])
    return date(out_year, out_month, out_day).isoformat()


def _air_lines(row: dict) -> list[dict]:
    telemetry = row.get("line_telemetry") or {}
    return [line for line in telemetry.get("lines", []) if line.get("mode") == "air"]


def _mode_counts(row: dict) -> dict:
    counts = defaultdict(int)
    vehicles = defaultdict(int)
    for line in (row.get("line_telemetry") or {}).get("lines", []):
        mode = line.get("mode", "unknown")
        counts[mode] += 1
        vehicles[mode] += int(line.get("vehicles") or 0)
    return {"lines": dict(counts), "vehicles": dict(vehicles)}


def _line_signature(row: dict) -> tuple:
    return tuple(sorted(
        (line.get("market_key"), int(line.get("vehicles") or 0))
        for line in _air_lines(row)
    ))


def _endpoint_observation(line: dict) -> dict:
    waits = []
    ratings = []
    for endpoint in line.get("endpoint_cargo_stats") or []:
        pax = (endpoint.get("cargo") or {}).get("0") or {}
        wait = pax.get("max_waiting_cargo")
        rating = pax.get("rating")
        if isinstance(wait, (int, float)):
            waits.append(wait)
        if isinstance(rating, (int, float)):
            ratings.append(rating)
    return {
        "waiting_pax_max": max(waits) if waits else None,
        "waiting_pax_endpoints": waits,
        "rating_pax_mean": (sum(ratings) / len(ratings)) if ratings else None,
        "rating_pax_endpoints": ratings,
    }


def _line_snapshot(line: dict | None) -> dict | None:
    if line is None:
        return None
    out = {
        "market_key": line.get("market_key"),
        "town_ids": line.get("town_ids"),
        "vehicles": line.get("vehicles"),
        "capacity_by_cargo": line.get("capacity_by_cargo"),
        "profit_this_year_gbp": line.get("profit_this_year_gbp"),
        "profit_last_year_gbp": line.get("profit_last_year_gbp"),
        "vehicle_value": line.get("vehicle_value"),
    }
    out.update(_endpoint_observation(line))
    return out


def _cumulative_profit(records: list[tuple[str, dict]], start_date: str, end_date: str) -> float | None:
    """Approximate cumulative vehicle profit across calendar-year YTD resets."""
    selected = [(d, line) for d, line in records if start_date <= d <= end_date]
    if not selected:
        return None
    by_year = defaultdict(list)
    for d, line in selected:
        value = line.get("profit_this_year_gbp")
        if not isinstance(value, (int, float)):
            continue
        by_year[int(d[:4])].append((d, float(value)))
    if not by_year:
        return None
    start_year = int(start_date[:4])
    total = 0.0
    for year in sorted(by_year):
        values = sorted(by_year[year])
        last = values[-1][1]
        if year == start_year:
            first = values[0][1]
            total += last - first
        else:
            total += last
    return round(total, 3)


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _row_arm(row: dict) -> str | None:
    run = row.get("run") or []
    return run[0] if run else row.get("arm")


def analyse(result_path: Path) -> dict:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    rows = load_rows(result_path.with_suffix(".jsonl"))
    policies = [p["id"] for p in result.get("policies", [])]
    if len(policies) != 2:
        raise ValueError("expected exactly two policies")
    reference, variant = policies

    index = {}
    for row in rows:
        run = row.get("run") or []
        seed = int(run[1]) if len(run) > 1 else None
        key = (row.get("duel_policy_id"), _row_arm(row), seed, row.get("date"))
        index[key] = row

    per_seed = []
    for seed in result.get("seeds", []):
        dates = sorted({
            row.get("date") for row in rows
            if (row.get("run") or [None, None])[1] == seed and _row_arm(row) == "OpexAI"
            and row.get("date")
        })
        first = None
        for d in dates:
            ref = index.get((reference, "OpexAI", seed, d))
            var = index.get((variant, "OpexAI", seed, d))
            if not ref or not var:
                continue
            if _line_signature(ref) != _line_signature(var):
                first = (d, ref, var)
                break

        first_payload = None
        if first:
            d, ref, var = first
            ref_air = {line.get("market_key"): line for line in _air_lines(ref)}
            var_air = {line.get("market_key"): line for line in _air_lines(var)}
            aaa_ref = index.get((reference, "AAAHogEx", seed, d)) or {}
            aaa_var = index.get((variant, "AAAHogEx", seed, d)) or {}
            first_payload = {
                "date": d,
                "reference": {
                    "money": ref.get("money"), "loan": ref.get("current_loan"),
                    "airports": ref.get("air_airports"), "mode_counts": _mode_counts(ref),
                    "air_markets": sorted(ref_air),
                    "only_markets": sorted(set(ref_air) - set(var_air)),
                },
                "variant": {
                    "money": var.get("money"), "loan": var.get("current_loan"),
                    "airports": var.get("air_airports"), "mode_counts": _mode_counts(var),
                    "air_markets": sorted(var_air),
                    "only_markets": sorted(set(var_air) - set(ref_air)),
                },
                "aaa_reference": {
                    "airports": aaa_ref.get("air_airports"),
                    "air_lines": len(_air_lines(aaa_ref)),
                    "air_vehicles": sum(int(x.get("vehicles") or 0) for x in _air_lines(aaa_ref)),
                },
                "aaa_variant": {
                    "airports": aaa_var.get("air_airports"),
                    "air_lines": len(_air_lines(aaa_var)),
                    "air_vehicles": sum(int(x.get("vehicles") or 0) for x in _air_lines(aaa_var)),
                },
            }

        line_outcomes = {}
        for policy in policies:
            policy_rows = [
                row for row in rows
                if row.get("duel_policy_id") == policy and _row_arm(row) == "OpexAI"
                and (row.get("run") or [None, None])[1] == seed
            ]
            histories = defaultdict(list)
            for row in sorted(policy_rows, key=lambda x: x.get("date") or ""):
                d = row.get("date")
                for line in _air_lines(row):
                    histories[line.get("market_key")].append((d, line))
            policy_lines = []
            for market, history in sorted(histories.items(), key=lambda item: item[1][0][0]):
                first_seen = history[0][0]
                entry = {"market_key": market, "first_seen": first_seen, "horizons": {}}
                for months in (6, 12, 24):
                    target = _month_add(first_seen, months)
                    line = next((line for d, line in history if d == target), None)
                    entry["horizons"][str(months)] = {
                        "target_date": target,
                        "present": line is not None,
                        "snapshot": _line_snapshot(line),
                        "cum_profit_since_first_seen_gbp": _cumulative_profit(history, first_seen, target),
                    }
                entry["last_seen"] = history[-1][0]
                entry["final_present"] = history[-1][0] == max(r.get("date") for r in policy_rows if r.get("date"))
                policy_lines.append(entry)
            line_outcomes[policy] = policy_lines

        pair = next((p for p in (result.get("policy_comparison") or {}).get("per_pair", [])
                     if int(p.get("seed")) == int(seed)), None)
        final = None
        if pair:
            final = {
                "profit_year_delta": (pair.get("metrics") or {}).get("profit_year", {}).get("policy_delta"),
                "duel_gap_evolution": (pair.get("metrics") or {}).get("profit_year", {}).get("duel_gap_evolution"),
                "primary_vehicles_delta": (pair.get("metrics") or {}).get("primary_vehicles", {}).get("policy_delta"),
                "slots_delta": (pair.get("air_structural_metrics") or {}).get("airport_slots_opex", {}).get("policy_delta"),
                "towns_delta": (pair.get("air_structural_metrics") or {}).get("airport_towns_opex_present", {}).get("policy_delta"),
            }
        first_year_timeline = []
        for d in dates[:13]:
            item = {"date": d}
            for label, policy in (("reference", reference), ("variant", variant)):
                own = index.get((policy, "OpexAI", seed, d)) or {}
                aaa = index.get((policy, "AAAHogEx", seed, d)) or {}
                modes = _mode_counts(own)
                item[label] = {
                    "money": own.get("money"),
                    "airports": own.get("air_airports"),
                    "air_lines": len(_air_lines(own)),
                    "air_vehicles": modes.get("vehicles", {}).get("air", 0),
                    "rail_lines": modes.get("lines", {}).get("rail", 0),
                    "road_lines": modes.get("lines", {}).get("road", 0),
                    "aaa_airports": aaa.get("air_airports"),
                    "aaa_air_lines": len(_air_lines(aaa)),
                    "aaa_air_vehicles": sum(int(x.get("vehicles") or 0) for x in _air_lines(aaa)),
                }
            first_year_timeline.append(item)
        per_seed.append({
            "seed": seed,
            "first_physical_air_divergence": first_payload,
            "first_year_timeline": first_year_timeline,
            "first_air_lines": {policy: line_outcomes[policy][:6] for policy in policies},
            "final": final,
        })

    return {
        "source_result": str(result_path),
        "reference": reference,
        "variant": variant,
        "telemetry_scope": (result.get("line_telemetry") or {}).get("scope"),
        "per_seed": per_seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = analyse(args.result)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    if args.compact:
        for seed in report["per_seed"]:
            first = seed["first_physical_air_divergence"] or {}
            ref = first.get("reference") or {}
            var = first.get("variant") or {}
            print(
                "SEED", seed["seed"], "FIRST", first.get("date"),
                "REF_AIR", (ref.get("mode_counts") or {}).get("vehicles", {}).get("air", 0),
                "VAR_AIR", (var.get("mode_counts") or {}).get("vehicles", {}).get("air", 0),
                "REF_CASH", ref.get("money"), "VAR_CASH", var.get("money"),
                "FINAL", seed.get("final"),
            )
            for policy in (report["reference"], report["variant"]):
                print(" POLICY", policy)
                for line in seed["first_air_lines"][policy][:4]:
                    fields = []
                    for months in ("6", "12", "24"):
                        horizon = line["horizons"][months]
                        snap = horizon.get("snapshot") or {}
                        fields.append(
                            f"m{months}:p={horizon.get('cum_profit_since_first_seen_gbp')}"
                            f",v={snap.get('vehicles')},w={snap.get('waiting_pax_max')}"
                        )
                    print("  ", line["market_key"], "seen", line["first_seen"], *fields)
            for point in seed["first_year_timeline"]:
                ref = point["reference"]
                var = point["variant"]
                print(
                    " TL", point["date"],
                    f"ref=A{ref['air_vehicles']}/R{ref['rail_lines']}/cash{ref['money']}/AAA{ref['aaa_air_vehicles']}",
                    f"var=A{var['air_vehicles']}/R{var['rail_lines']}/cash{var['money']}/AAA{var['aaa_air_vehicles']}",
                )
    else:
        print(text)


if __name__ == "__main__":
    main()
