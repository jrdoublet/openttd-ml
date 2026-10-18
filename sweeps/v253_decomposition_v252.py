#!/usr/bin/env python3
"""
v253_decomposition_v252.py — Décomposition causale et quantitative du gain de V252.

Analyse les 855 remplacements de V252 mode 2 (campagne v252m2_airseul_20x10_20261018)
et départage les cinq hypothèses (a), (b), (c), (d), (e) avec les formules du code
OpenTTD 15.3 et la télémétrie de ligne appariée.
"""

import json
import glob
import os
import re
from collections import defaultdict, Counter

ENGINES_INFO = {
    215: {"name": "Sampson U52", "intro": 1928, "speed_disp": 473, "speed_noai": 118, "pax": 25, "mail": 4, "price": 28710, "running": 2390, "max_age_years": 20},
    216: {"name": "Coleman Count", "intro": 1947, "speed_disp": 473, "speed_noai": 118, "pax": 65, "mail": 8, "price": 30761, "running": 2812, "max_age_years": 20},
    217: {"name": "FFP Dart", "intro": 1954, "speed_disp": 947, "speed_noai": 236, "pax": 90, "mail": 10, "price": 32812, "running": 3656, "max_age_years": 18},
    218: {"name": "Yate Haugan", "intro": 1968, "speed_disp": 2316, "speed_noai": 579, "pax": 100, "mail": 20, "price": 153808, "running": 7031, "max_age_years": 25},
    219: {"name": "Bakewell Cotswald LB-3", "intro": 1933, "speed_disp": 473, "speed_noai": 118, "pax": 30, "mail": 6, "price": 30761, "running": 2756, "max_age_years": 20},
    220: {"name": "Bakewell Luckett LB-8", "intro": 1957, "speed_disp": 947, "speed_noai": 236, "pax": 200, "mail": 30, "price": 36914, "running": 6750, "max_age_years": 20},
    221: {"name": "Bakewell Luckett LB-9", "intro": 1964, "speed_disp": 947, "speed_noai": 236, "pax": 100, "mail": 15, "price": 34863, "running": 4218, "max_age_years": 20},
    222: {"name": "Bakewell Luckett LB80", "intro": 1978, "speed_disp": 947, "speed_noai": 236, "pax": 150, "mail": 30, "price": 36914, "running": 6890, "max_age_years": 20},
    223: {"name": "Bakewell Luckett LB-10", "intro": 1970, "speed_disp": 947, "speed_noai": 236, "pax": 220, "mail": 40, "price": 38964, "running": 5400, "max_age_years": 20},
    224: {"name": "Bakewell Luckett LB-11", "intro": 1989, "speed_disp": 947, "speed_noai": 236, "pax": 230, "mail": 25, "price": 41015, "running": 5343, "max_age_years": 20},
    225: {"name": "Yate Aerospace YAC 1-11", "intro": 1962, "speed_disp": 947, "speed_noai": 236, "pax": 95, "mail": 10, "price": 32812, "running": 3796, "max_age_years": 20},
    226: {"name": "Darwin 100", "intro": 1962, "speed_disp": 947, "speed_noai": 236, "pax": 170, "mail": 35, "price": 36914, "running": 6750, "max_age_years": 20},
    227: {"name": "Darwin 200", "intro": 1966, "speed_disp": 947, "speed_noai": 236, "pax": 110, "mail": 15, "price": 34863, "running": 4359, "max_age_years": 20},
    228: {"name": "Darwin 300", "intro": 1967, "speed_disp": 947, "speed_noai": 236, "pax": 300, "mail": 50, "price": 61523, "running": 7115, "max_age_years": 25},
    232: {"name": "Guru Galaxy", "intro": 1969, "speed_disp": 947, "speed_noai": 236, "pax": 240, "mail": 35, "price": 51269, "running": 6328, "max_age_years": 20},
    233: {"name": "Airtaxi A21", "intro": 1972, "speed_disp": 947, "speed_noai": 236, "pax": 260, "mail": 30, "price": 41015, "running": 6609, "max_age_years": 20},
}


def parse_v252_replace_line(line, seed=0):
    """Parse une ligne V252_REPLACE de journal OpexDecide."""
    if "V252_REPLACE" not in line:
        return None
    m = re.search(
        r"OPEX (\d{4})-(\d+)-(\d+).*?line=(\d+).*?old_engine=(\d+).*?new_engine=(\d+).*?old_veh=(\d+).*?new_veh=(\d+).*?price=(\d+).*?age=(\d+).*?profit=([0-9\.\-]+)",
        line,
    )
    if not m:
        return None
    return {
        "seed": seed,
        "year": int(m.group(1)),
        "month": int(m.group(2)),
        "day": int(m.group(3)),
        "line_id": int(m.group(4)),
        "old_engine": int(m.group(5)),
        "new_engine": int(m.group(6)),
        "old_veh": int(m.group(7)),
        "new_veh": int(m.group(8)),
        "price": int(m.group(9)),
        "age": int(m.group(10)),
        "profit_logged": float(m.group(11)),
    }


def parse_all_v252_replaces(log_dir):
    """Charge et parse tous les V252_REPLACE des journaux d'un dossier."""
    replaces = []
    log_files = sorted(glob.glob(os.path.join(log_dir, "v252m2_seed*_r0.log")))
    for lf in log_files:
        seed_match = re.search(r"seed(\d+)", lf)
        seed = int(seed_match.group(1)) if seed_match else 0
        with open(lf, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                r = parse_v252_replace_line(line, seed=seed)
                if r:
                    replaces.append(r)
    return replaces


def categorize_replacements(replaces):
    """Ventile les événements de remplacement par catégorie de transition."""
    categories = {
        "to_217_from_223": [],
        "to_217_from_228": [],
        "to_217_from_other": [],
        "to_218": [],
        "to_228": [],
        "other": [],
    }
    for r in replaces:
        oe, ne = r["old_engine"], r["new_engine"]
        if ne == 217:
            if oe == 223:
                categories["to_217_from_223"].append(r)
            elif oe == 228:
                categories["to_217_from_228"].append(r)
            else:
                categories["to_217_from_other"].append(r)
        elif ne == 218:
            categories["to_218"].append(r)
        elif ne == 228:
            categories["to_228"].append(r)
        else:
            categories["other"].append(r)
    return categories


def build_telemetry_indices(snapshots):
    """Construit les index de recherche pour les lignes et véhicules dans les snapshots."""
    veh_index = {}
    market_index = {}
    for s in snapshots:
        seed = s["seed"]
        pol = s["duel_policy_id"]
        yr = s["year"]
        for l in s.get("lines", []):
            mkey = l.get("market_key")
            market_index[(seed, pol, yr, mkey)] = l
            vfins = {vf["vehicle_id"]: vf for vf in l.get("vehicle_financials", [])}
            for vid in l.get("vehicle_ids", []):
                veh_index[(seed, pol, yr, vid)] = (l, vfins.get(vid), mkey)
    return veh_index, market_index


def compute_group_financials(replaces_subset, veh_index, market_index):
    """Calcule les métriques financières avant/après sur un sous-ensemble de remplacements."""
    old_veh_profits = []
    new_veh_profits = []
    line_prof_before = []
    line_prof_after = []
    ref_line_prof_before = []
    ref_line_prof_after = []
    rating_before = []
    rating_after = []
    waiting_before = []
    waiting_after = []

    for r in replaces_subset:
        s = r["seed"]
        y = r["year"]
        ov = r["old_veh"]
        nv = r["new_veh"]

        if y - 1 >= 1970 and y + 1 <= 1979:
            old_data = veh_index.get((s, "v252m2", y - 1, ov))
            new_data = veh_index.get((s, "v252m2", y + 1, nv))
            if old_data and new_data:
                old_line, old_vf, mkey = old_data
                new_line, new_vf, _ = new_data
                if old_vf and new_vf:
                    vp_b = old_vf.get("profit_last_year_gbp", 0.0)
                    vp_a = new_vf.get("profit_last_year_gbp", 0.0)
                    if vp_b > 0 and vp_a > 0:
                        old_veh_profits.append(vp_b)
                        new_veh_profits.append(vp_a)

                lp_b = old_line.get("profit_this_year_gbp", 0.0)
                lp_a = new_line.get("profit_this_year_gbp", 0.0)
                line_prof_before.append(lp_b)
                line_prof_after.append(lp_a)

                ref_b = market_index.get((s, "reference", y - 1, mkey))
                ref_a = market_index.get((s, "reference", y + 1, mkey))
                if ref_b and ref_a:
                    ref_line_prof_before.append(ref_b.get("profit_this_year_gbp", 0.0))
                    ref_line_prof_after.append(ref_a.get("profit_this_year_gbp", 0.0))

                r_b = [st["cargo"]["0"]["rating"] for st in old_line.get("endpoint_cargo_stats", []) if "0" in st.get("cargo", {}) and st["cargo"]["0"].get("rated")]
                r_a = [st["cargo"]["0"]["rating"] for st in new_line.get("endpoint_cargo_stats", []) if "0" in st.get("cargo", {}) and st["cargo"]["0"].get("rated")]
                if r_b and r_a:
                    rating_before.append(sum(r_b) / len(r_b))
                    rating_after.append(sum(r_a) / len(r_a))

                w_b = [st["cargo"]["0"]["max_waiting_cargo"] for st in old_line.get("endpoint_cargo_stats", []) if "0" in st.get("cargo", {})]
                w_a = [st["cargo"]["0"]["max_waiting_cargo"] for st in new_line.get("endpoint_cargo_stats", []) if "0" in st.get("cargo", {})]
                if w_b and w_a:
                    waiting_before.append(max(w_b))
                    waiting_after.append(max(w_a))

    n_lines = len(line_prof_before)
    avg_line_before = sum(line_prof_before) / n_lines if n_lines > 0 else 0.0
    avg_line_after = sum(line_prof_after) / n_lines if n_lines > 0 else 0.0
    delta_line = avg_line_after - avg_line_before

    n_ref = len(ref_line_prof_before)
    avg_ref_before = sum(ref_line_prof_before) / n_ref if n_ref > 0 else 0.0
    avg_ref_after = sum(ref_line_prof_after) / n_ref if n_ref > 0 else 0.0
    delta_ref = avg_ref_after - avg_ref_before

    surperformance = delta_line - delta_ref if n_ref > 0 else delta_line

    n_rat = len(rating_before)
    avg_rat_before = sum(rating_before) / n_rat if n_rat > 0 else 0.0
    avg_rat_after = sum(rating_after) / n_rat if n_rat > 0 else 0.0

    n_wait = len(waiting_before)
    avg_wait_before = sum(waiting_before) / n_wait if n_wait > 0 else 0.0
    avg_wait_after = sum(waiting_after) / n_wait if n_wait > 0 else 0.0

    return {
        "n_events": len(replaces_subset),
        "n_matched_lines": n_lines,
        "line_profit_before": avg_line_before,
        "line_profit_after": avg_line_after,
        "delta_line_profit": delta_line,
        "ref_line_profit_before": avg_ref_before,
        "ref_line_profit_after": avg_ref_after,
        "delta_ref_line_profit": delta_ref,
        "surperformance_vs_ref": surperformance,
        "rating_before": avg_rat_before,
        "rating_after": avg_rat_after,
        "delta_rating": avg_rat_after - avg_rat_before,
        "waiting_before": avg_wait_before,
        "waiting_after": avg_wait_after,
        "delta_waiting": avg_wait_after - avg_wait_before,
    }


def synthesize_decomposition(categories, veh_index, market_index, n_seeds=20):
    """Synthétise la décomposition des gains par groupe et compare au gain total."""
    results = {}
    for cat_name, rlist in categories.items():
        results[cat_name] = compute_group_financials(rlist, veh_index, market_index)

    contributions_k_gbp = {}
    for cat_name, res in results.items():
        events_per_seed = res["n_events"] / float(n_seeds)
        contrib = events_per_seed * res["surperformance_vs_ref"] / 1000.0
        contributions_k_gbp[cat_name] = contrib

    return results, contributions_k_gbp
