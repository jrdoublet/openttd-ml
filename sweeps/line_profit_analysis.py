"""Analyse du profit des lignes par mode (rail, air, route, eau) pour OpexAI et AAAHogEx.

Ce module extrait et analyse la télémétrie par ligne (snapshots annuels VEHS)
et les panneaux de diagnostic (SIGN) pour mesurer le profit réalisé en montée en charge
et en régime, et comparer aux estimations à l'élection quand disponibles.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import statistics as stats
from typing import Any, Dict, List, Optional, Tuple


# Conversion d'échelle documentée dans AGENTS.md et bench_1v1_5y_20seeds.py
PROFIT_RAW_UNITS_PER_GBP = 256.0


def parse_sign(name: str) -> Optional[Dict[str, Any]]:
    """Parse un panneau diagnostic OpexAI en dictionnaire typé."""
    if not name or not isinstance(name, str):
        return None
    parts = name.split("|")
    prefix = parts[0]

    try:
        # AIR: AF|<lineId>|<vehs>|<profitAnnual>
        if prefix == "AF" and len(parts) >= 4:
            return {
                "kind": "air_plan",
                "line_id": int(parts[1]),
                "vehs": int(parts[2]),
                "pred_profit": int(parts[3]),
            }
        # AIR: AH|<lineId>|<reuseA>|<capital>|<hubRoutes>
        if prefix == "AH" and len(parts) >= 4:
            return {
                "kind": "air_capital",
                "line_id": int(parts[1]),
                "reuse_a": int(parts[2]),
                "pred_capital": int(parts[3]),
                "hub_routes": int(parts[4]) if len(parts) > 4 else None,
            }
        # AIR: AC|<lineId>|<plannedCapital>|<actualCost>|<planes>|<vehicles> (probe_cost=1)
        if prefix == "AC" and len(parts) >= 4:
            return {
                "kind": "air_cost",
                "line_id": int(parts[1]),
                "planned_capital": int(parts[2]),
                "actual_cost": int(parts[3]),
                "planes": int(parts[4]) if len(parts) > 4 else None,
            }
        # RAIL/ROAD: OF|<lineId>|<revenueAnnual>
        if prefix == "OF" and len(parts) >= 3:
            return {
                "kind": "pred_revenue",
                "line_id": int(parts[1]),
                "pred_revenue": int(parts[2]),
            }
        # RAIL/ROAD: OJ|<lineId>|<runningAnnual>
        if prefix == "OJ" and len(parts) >= 3:
            return {
                "kind": "pred_running",
                "line_id": int(parts[1]),
                "pred_running": int(parts[2]),
            }
        # RAIL/ROAD: OK|<lineId>|<amortAnnual>
        if prefix == "OK" and len(parts) >= 3:
            return {
                "kind": "pred_amort",
                "line_id": int(parts[1]),
                "pred_amort": int(parts[2]),
            }
        # RAIL: DC|<lineId>|<capital>|<actualCost>|... (probe_cost=1)
        if prefix == "DC" and len(parts) >= 4:
            return {
                "kind": "rail_cost",
                "line_id": int(parts[1]),
                "planned_capital": int(parts[2]),
                "actual_cost": int(parts[3]),
            }
        # ROAD: RC|<yy>|<lineId>|1|<cost>|<vehs>
        if prefix == "RC" and len(parts) >= 6:
            return {
                "kind": "road_cost",
                "yy": int(parts[1]),
                "line_id": int(parts[2]),
                "actual_cost": int(parts[4]),
                "vehs": int(parts[5]),
            }
        # ALL: OZ|<lineId>|<year>|<profit>
        if prefix == "OZ" and len(parts) >= 4:
            return {
                "kind": "real_profit",
                "line_id": int(parts[1]),
                "year": int(parts[2]),
                "real_profit": int(parts[3]),
            }
        # ALL: OO|<lineId>|<year>|<revenue>
        if prefix == "OO" and len(parts) >= 4:
            return {
                "kind": "real_revenue",
                "line_id": int(parts[1]),
                "year": int(parts[2]),
                "real_revenue": int(parts[3]),
            }
        # ALL: OU|<lineId>|<year>|<vehCount>|<runCost>
        if prefix == "OU" and len(parts) >= 5:
            return {
                "kind": "real_running",
                "line_id": int(parts[1]),
                "year": int(parts[2]),
                "vehs": int(parts[3]),
                "real_run_cost": int(parts[4]),
            }
        # ALL: OY|<lineId>|<year>|<ratingA>|<ratingB>
        if prefix == "OY" and len(parts) >= 5:
            return {
                "kind": "ratings",
                "line_id": int(parts[1]),
                "year": int(parts[2]),
                "rating_a": int(parts[3]),
                "rating_b": int(parts[4]),
            }
    except (ValueError, IndexError):
        return None

    return None


def extract_estimates_from_signs(signs: List[str]) -> Dict[int, Dict[str, Any]]:
    """Agrège les prédictions et réalisations par line_id à partir d'une liste de panneaux."""
    lines: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
        "pred_revenue": None,
        "pred_running": None,
        "pred_amort": None,
        "pred_profit": None,
        "pred_capital": None,
        "actual_capital": None,
        "annual_real_profit": {},
        "annual_real_revenue": {},
        "annual_real_run_cost": {},
    })

    for sign_name in signs:
        p = parse_sign(sign_name)
        if not p:
            continue
        lid = p.get("line_id")
        if lid is None:
            continue
        line = lines[lid]
        k = p["kind"]
        if k == "air_plan":
            line["pred_profit"] = p["pred_profit"]
        elif k == "air_capital":
            line["pred_capital"] = p["pred_capital"]
        elif k == "air_cost":
            line["pred_capital"] = p["planned_capital"]
            line["actual_capital"] = p["actual_cost"]
        elif k == "pred_revenue":
            line["pred_revenue"] = p["pred_revenue"]
        elif k == "pred_running":
            line["pred_running"] = p["pred_running"]
        elif k == "pred_amort":
            line["pred_amort"] = p["pred_amort"]
        elif k == "rail_cost":
            line["pred_capital"] = p["planned_capital"]
            line["actual_capital"] = p["actual_cost"]
        elif k == "road_cost":
            line["actual_capital"] = p["actual_cost"]
        elif k == "real_profit":
            line["annual_real_profit"][p["year"]] = p["real_profit"]
        elif k == "real_revenue":
            line["annual_real_revenue"][p["year"]] = p["real_revenue"]
        elif k == "real_running":
            line["annual_real_run_cost"][p["year"]] = p["real_run_cost"]

    # Calcul profit prédit pour rail/road si OF/OJ/OK présents
    for lid, line in lines.items():
        if line["pred_profit"] is None:
            r = line["pred_revenue"]
            run = line["pred_running"]
            a = line["pred_amort"]
            if r is not None and run is not None and a is not None:
                line["pred_profit"] = r - run - a

    return dict(lines)


def track_lines_from_snapshots(
    snapshots: List[Dict[str, Any]],
    arm: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Suit les lignes sur l'ensemble des snapshots annuels (décembre)."""
    # Clé unique par ligne et par partie : (arm, seed, line_key)
    tracked: Dict[Tuple[str, int, str], Dict[str, Any]] = {}

    sorted_snaps = sorted(snapshots, key=lambda s: s.get("year", 0))

    for s in sorted_snaps:
        s_arm = s.get("arm")
        if arm and s_arm != arm:
            continue
        seed = s.get("seed")
        year = s.get("year")
        if seed is None or year is None:
            continue

        for l in s.get("lines", []):
            mode = l.get("mode")
            local_key = l.get("line_key_local", "")
            # Pour AAAHogEx, group_id est stable si présent
            line_id_key = local_key
            if s_arm == "AAAHogEx" and l.get("group_id") is not None:
                line_id_key = f"group:{l['group_id']}"

            unique_key = (s_arm, seed, line_id_key)
            if unique_key not in tracked:
                tracked[unique_key] = {
                    "arm": s_arm,
                    "seed": seed,
                    "line_key": line_id_key,
                    "market_key": l.get("market_key"),
                    "mode": mode,
                    "first_year": year,
                    "town_ids": l.get("town_ids", []),
                    "station_ids": l.get("station_ids", []),
                    "cargo_types": l.get("cargo_types", []),
                    "capacity_by_cargo": l.get("capacity_by_cargo", {}),
                    "history_profit_last": {},
                    "history_profit_this": {},
                    "history_vehs": {},
                }
            item = tracked[unique_key]
            item["history_profit_last"][year] = l.get("profit_last_year_gbp", 0.0)
            item["history_profit_this"][year] = l.get("profit_this_year_gbp", 0.0)
            item["history_vehs"][year] = l.get("vehicles", 1)

    # Post-traitement : classification montée en charge vs régime
    results = []
    for (s_arm, seed, lkey), item in tracked.items():
        y0 = item["first_year"]
        # Année de montée en charge :
        # - En y0, profit_this est l'exploitation partielle (quelques mois)
        # - En y0 + 1, profit_last représente l'année civile y0 complète (ou partielle)
        ramp_up_val = item["history_profit_last"].get(y0 + 1)
        partial_y0_this = item["history_profit_this"].get(y0)

        # Régime : années pleines suivant la mise en service
        # profit_last à y0 + 2 correspond à l'année pleine y0 + 1, etc.
        regime_years = [y for y in range(y0 + 2, 1976) if y in item["history_profit_last"]]
        regime_vals = [item["history_profit_last"][y] for y in regime_years]

        mean_regime = stats.mean(regime_vals) if regime_vals else None
        median_regime = stats.median(regime_vals) if regime_vals else None
        latest_vehs = item["history_vehs"].get(max(item["history_vehs"].keys())) if item["history_vehs"] else 1

        results.append({
            "arm": s_arm,
            "seed": seed,
            "line_key": lkey,
            "mode": item["mode"],
            "first_year": y0,
            "town_ids": item["town_ids"],
            "station_ids": item["station_ids"],
            "cargo_types": item["cargo_types"],
            "capacity_by_cargo": item["capacity_by_cargo"],
            "vehs": latest_vehs,
            "partial_y0_this": partial_y0_this,
            "ramp_up": ramp_up_val,
            "n_regime_years": len(regime_vals),
            "regime_years": regime_years,
            "regime_profits": regime_vals,
            "mean_regime": mean_regime,
            "median_regime": median_regime,
            "min_regime": min(regime_vals) if regime_vals else None,
            "max_regime": max(regime_vals) if regime_vals else None,
        })

    return results


def summarize_by_mode(lines: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Produit les métriques agrégées par mode pour un ensemble de lignes analysées."""
    by_mode = defaultdict(list)
    for l in lines:
        by_mode[l["mode"]].append(l)

    summary = {}
    for mode in ["rail", "air", "road", "water"]:
        m_lines = by_mode.get(mode, [])
        if not m_lines:
            continue

        reg_lines = [l for l in m_lines if l["mean_regime"] is not None]
        ramp_lines = [l for l in m_lines if l["ramp_up"] is not None]

        reg_means = [l["mean_regime"] for l in reg_lines]
        ramp_vals = [l["ramp_up"] for l in ramp_lines]
        vehs = [l["vehs"] for l in m_lines]

        seeds = set(l["seed"] for l in m_lines)
        n_seeds = len(seeds) if seeds else 1

        # Déciles régime
        sorted_reg = sorted(reg_means)
        deciles = {}
        if sorted_reg:
            for q in [10, 25, 50, 75, 90, 95]:
                idx = min(len(sorted_reg) - 1, int(len(sorted_reg) * q / 100))
                deciles[f"p{q}"] = sorted_reg[idx]

        summary[mode] = {
            "total_lines": len(m_lines),
            "lines_per_seed": len(m_lines) / n_seeds,
            "regime_lines": len(reg_lines),
            "regime_lines_per_seed": len(reg_lines) / n_seeds,
            "total_vehs": sum(vehs),
            "mean_vehs_per_line": stats.mean(vehs) if vehs else 0.0,
            "ramp_up": {
                "count": len(ramp_vals),
                "mean": stats.mean(ramp_vals) if ramp_vals else None,
                "median": stats.median(ramp_vals) if ramp_vals else None,
                "stdev": stats.stdev(ramp_vals) if len(ramp_vals) > 1 else 0.0,
                "min": min(ramp_vals) if ramp_vals else None,
                "max": max(ramp_vals) if ramp_vals else None,
            },
            "regime": {
                "count": len(reg_means),
                "mean": stats.mean(reg_means) if reg_means else None,
                "median": stats.median(reg_means) if reg_means else None,
                "stdev": stats.stdev(reg_means) if len(reg_means) > 1 else 0.0,
                "min": min(reg_means) if reg_means else None,
                "max": max(reg_means) if reg_means else None,
                "deciles": deciles,
                "total_profit_annual": sum(reg_means),
                "avg_annual_profit_per_seed": sum(reg_means) / n_seeds,
                "negative_count": sum(x < 0 for x in reg_means),
                "negative_pct": (sum(x < 0 for x in reg_means) / len(reg_means) * 100) if reg_means else 0.0,
            }
        }

    return summary


def summarize_by_seed(lines: List[Dict[str, Any]]) -> Dict[int, Dict[str, Dict[str, Any]]]:
    """Produit les totaux par graine et par mode."""
    by_seed: Dict[int, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for l in lines:
        by_seed[l["seed"]][l["mode"]].append(l)

    result = {}
    for seed, modes in sorted(by_seed.items()):
        result[seed] = {}
        for mode, m_lines in modes.items():
            reg_lines = [l for l in m_lines if l["mean_regime"] is not None]
            reg_means = [l["mean_regime"] for l in reg_lines]
            ramp_vals = [l["ramp_up"] for l in m_lines if l["ramp_up"] is not None]
            result[seed][mode] = {
                "total_lines": len(m_lines),
                "regime_lines": len(reg_lines),
                "mean_ramp": stats.mean(ramp_vals) if ramp_vals else 0.0,
                "mean_regime": stats.mean(reg_means) if reg_means else 0.0,
                "median_regime": stats.median(reg_means) if reg_means else 0.0,
                "total_regime_profit": sum(reg_means),
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", "-i", type=Path, required=True, help="Chemin du JSON de résultats")
    parser.add_argument("--arm", choices=["OpexAI", "AAAHogEx"], help="Filtrer par bras")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    snapshots = data.get("line_telemetry", {}).get("snapshots", [])
    if not snapshots:
        print("Aucun snapshot de télémétrie par ligne trouvé.")
        return

    arms = [args.arm] if args.arm else ["OpexAI", "AAAHogEx"]

    for arm in arms:
        print(f"\n{'='*30} {arm} {'='*30}")
        tracked = track_lines_from_snapshots(snapshots, arm=arm)
        mode_summary = summarize_by_mode(tracked)
        seed_summary = summarize_by_seed(tracked)

        for mode, s in mode_summary.items():
            print(f"\nMODE: {mode.upper()}")
            print(f"  Lignes créées : {s['total_lines']} ({s['lines_per_seed']:.1f}/graine) | Véhicules : {s['total_vehs']}")
            print(f"  Lignes en régime (>=1 an plein) : {s['regime_lines']} ({s['regime_lines_per_seed']:.1f}/graine)")
            if s["ramp_up"]["count"]:
                r = s["ramp_up"]
                print(f"  Montée en charge : moyenne = {r['mean']:.1f} £, médiane = {r['median']:.1f} £")
            if s["regime"]["count"]:
                reg = s["regime"]
                print(f"  Régime : moyenne = {reg['mean']:.1f} £/an, médiane = {reg['median']:.1f} £/an (écart-type = {reg['stdev']:.1f} £)")
                print(f"  Plage : [{reg['min']:.1f} £, {reg['max']:.1f} £] | Négatives : {reg['negative_count']} ({reg['negative_pct']:.1f}%)")
                print(f"  Profit total régime par graine : {reg['avg_annual_profit_per_seed']:.1f} £/an")


if __name__ == "__main__":
    main()
