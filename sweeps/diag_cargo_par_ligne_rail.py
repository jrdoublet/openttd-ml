#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_cargo_par_ligne_rail.py -- Diagnostic chiffre : cargo par ligne rail (OpexAI vs AAAHogEx).

Ce script lit en lecture seule les donnees d'exposition 3x10 de wt-v270 :
- JSONL mensuel (delivered_cargo_last_quarter, capacities_by_cargo, primary_vehicles_by_mode, profit_year)
- line_telemetry (snapshots annuels au 1er decembre : lignes rail, vehicules, capacites, gares, attente, note, delais)
- journaux moteur (*_engine/reference_seed<N>_r0.log.gz : LINE_REVENUE pour Opex, TrainRoute/BuildTrain pour AAAHogEx)

Auteur : agy (diagnostic demande le 20/10/2026)
"""

import os
import sys
import gzip
import json
import re
import argparse
import unittest
from typing import Dict, List, Any, Tuple

DEFAULT_BASE = "/home/deploy/projects/openttd-ml/results/worktrees_archives_20261020/wt-v270/results"

CARGO_NAMES = {
    0: "Passengers",
    1: "Coal",
    2: "Mail",
    3: "Oil",
    4: "Livestock",
    5: "Goods",
    6: "Grain",
    7: "Wood",
    8: "Iron Ore",
    9: "Steel",
    10: "Valuables",
}

RAW_CARGO_IDS = [1, 3, 4, 6, 7, 8]
TRANSFORMED_CARGO_IDS = [5, 9]
FREIGHT_CARGO_IDS = RAW_CARGO_IDS + TRANSFORMED_CARGO_IDS


def load_jsonl_summary(jsonl_path: str, target_dates: List[str] = ["1975-12-01", "1979-12-01"], policy: str = "reference") -> Dict[Tuple[str, int, str], Dict[str, Any]]:
    """Lit les enregistrements mensuels du JSONL pour les dates cibles."""
    res = {}
    with gzip.open(jsonl_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            d = json.loads(line)
            if d.get("duel_policy_id") == policy:
                date = d.get("date")
                if date in target_dates:
                    ai, seed, _ = d.get("run")
                    res[(ai, seed, date)] = d
    return res


def load_telemetry_snapshots(json_gz_path: str, policy: str = "reference") -> List[Dict[str, Any]]:
    """Charge line_telemetry['snapshots'] du fichier JSON compresse."""
    with gzip.open(json_gz_path, "rt", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    snaps = data.get("line_telemetry", {}).get("snapshots", [])
    return [s for s in snaps if s.get("duel_policy_id") == policy]


def analyze_lines_telemetry(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse les lignes rail fret d'un snapshot."""
    lines = [l for l in snapshot.get("lines", []) if l.get("mode") == "rail"]
    freight_lines = []
    for l in lines:
        cargos = l.get("cargo_types", [])
        if any(c not in ("0", "2") for c in cargos):
            freight_lines.append(l)

    n_lines = len(freight_lines)
    total_trains = sum(l.get("vehicles", 0) for l in freight_lines)
    trains_per_line = total_trains / n_lines if n_lines > 0 else 0.0

    total_cap = sum(sum(l.get("capacity_by_cargo", {}).values()) for l in freight_lines)
    places_per_train = total_cap / total_trains if total_trains > 0 else 0.0

    total_profit_gbp = sum(l.get("profit_last_year_gbp", 0.0) for l in freight_lines)

    # Distances
    dists = []
    for l in freight_lines:
        tiles = l.get("ordered_station_tiles", [])
        if len(tiles) >= 2:
            t1, t2 = tiles[0], tiles[1]
            x1, y1 = t1 % 256, t1 // 256
            x2, y2 = t2 % 256, t2 // 256
            dists.append(abs(x1 - x2) + abs(y1 - y2))

    mean_dist = sum(dists) / len(dists) if dists else 0.0
    dists_sorted = sorted(dists)
    median_dist = dists_sorted[len(dists_sorted) // 2] if dists_sorted else 0.0

    # Stations partagees
    src_stations = {}
    dst_stations = {}
    for l in freight_lines:
        stats = l.get("endpoint_cargo_stats", [])
        src_id, dst_id = None, None
        for ep in stats:
            stn = ep.get("station_id")
            for cid, cinfo in ep.get("cargo", {}).items():
                if cid not in ("0", "2"):
                    if cinfo.get("rated") or not cinfo.get("accepts"):
                        src_id = stn
                    if cinfo.get("accepts"):
                        dst_id = stn
        stn_ids = l.get("ordered_station_ids", l.get("station_ids", []))
        if src_id is None and len(stn_ids) >= 1:
            src_id = stn_ids[0]
        if dst_id is None and len(stn_ids) >= 2:
            dst_id = stn_ids[1]

        src_stations.setdefault(src_id, []).append(l)
        dst_stations.setdefault(dst_id, []).append(l)

    shared_dst_count = sum(len(llist) for stn, llist in dst_stations.items() if len(llist) > 1)
    shared_src_count = sum(len(llist) for stn, llist in src_stations.items() if len(llist) > 1)

    pct_shared_dst = (shared_dst_count / n_lines * 100.0) if n_lines > 0 else 0.0
    pct_shared_src = (shared_src_count / n_lines * 100.0) if n_lines > 0 else 0.0

    # Cargo transforme
    trans_lines = sum(1 for l in freight_lines if any(c in ("5", "9") for c in l.get("cargo_types", [])))
    pct_trans_lines = (trans_lines / n_lines * 100.0) if n_lines > 0 else 0.0

    # Attente, notes, time_since_pickup et borne capacite vs offre
    waits = []
    ratings = []
    tsps = []
    cap_bounded = 0
    supply_bounded = 0

    for l in freight_lines:
        l_vehs = l.get("vehicles", 1)
        l_cap = sum(l.get("capacity_by_cargo", {}).values())
        rame_cap = l_cap / l_vehs if l_vehs > 0 else l_cap

        ep_stats = l.get("endpoint_cargo_stats", [])
        max_w = 0.0
        r_found = None
        tsp_found = None
        for ep in ep_stats:
            for cid, cinfo in ep.get("cargo", {}).items():
                if cid not in ("0", "2"):
                    w = float(cinfo.get("max_waiting_cargo", 0))
                    if w > max_w:
                        max_w = w
                    if cinfo.get("rated"):
                        r_found = cinfo.get("rating")
                        tsp_found = cinfo.get("time_since_pickup")

        waits.append(max_w)
        if r_found is not None:
            ratings.append(float(r_found))
        if tsp_found is not None:
            tsps.append(float(tsp_found))

        if max_w > rame_cap:
            cap_bounded += 1
        else:
            supply_bounded += 1

    return {
        "n_lines": n_lines,
        "total_trains": total_trains,
        "trains_per_line": trains_per_line,
        "total_cap": total_cap,
        "places_per_train": places_per_train,
        "total_profit_gbp": total_profit_gbp,
        "mean_dist": mean_dist,
        "median_dist": median_dist,
        "min_dist": min(dists) if dists else 0,
        "max_dist": max(dists) if dists else 0,
        "shared_dst_lines": shared_dst_count,
        "pct_shared_dst": pct_shared_dst,
        "shared_src_lines": shared_src_count,
        "pct_shared_src": pct_shared_src,
        "trans_lines": trans_lines,
        "pct_trans_lines": pct_trans_lines,
        "mean_wait": sum(waits) / len(waits) if waits else 0.0,
        "median_wait": sorted(waits)[len(waits) // 2] if waits else 0.0,
        "mean_rating": sum(ratings) / len(ratings) if ratings else 0.0,
        "mean_tsp": sum(tsps) / len(tsps) if tsps else 0.0,
        "cap_bounded": cap_bounded,
        "supply_bounded": supply_bounded,
        "pct_cap_bounded": (cap_bounded / n_lines * 100.0) if n_lines > 0 else 0.0,
        "pct_supply_bounded": (supply_bounded / n_lines * 100.0) if n_lines > 0 else 0.0,
    }


def parse_opex_line_revenue(log_path: str, target_year: int) -> List[Dict[str, Any]]:
    """Parse la sonde LINE_REVENUE rail pour OpexAI."""
    lines = []
    with gzip.open(log_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "[script:4] [0]" in line and "LINE_REVENUE" in line and "mode=rail" in line:
                tokens = line.strip().split()
                kv = dict(t.split("=", 1) for t in tokens if "=" in t)
                if kv.get("kind") == "freight" and int(kv.get("year", 0)) == target_year:
                    lines.append(kv)
    return lines


def parse_aaa_train_routes(log_path: str, max_year: int) -> List[Dict[str, Any]]:
    """Parse les TrainRoute dans les journaux AAAHogEx."""
    routes = []
    with gzip.open(log_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "[script:4] [1]" in line and "TrainRoute pathDistance" in line:
                m = re.search(r"(\d{4}-\d+-\d+) TrainRoute pathDistance:(\d+) distance:(\d+) (T:)?([^<]+)<-([^\[]+)\[([^\]]+)\]Rail", line)
                if m:
                    date, pd, d, t, dest, src, cargo = m.groups()
                    year = int(date.split("-")[0])
                    if year <= max_year:
                        routes.append({
                            "date": date,
                            "year": year,
                            "path_distance": int(pd),
                            "distance": int(d),
                            "is_transfer": bool(t),
                            "dest": dest.strip(),
                            "src": src.strip(),
                            "cargo": cargo.strip(),
                        })
    return routes


def check_return_routes(log_path: str) -> Dict[str, int]:
    """Compte les tentatives et succes de fret retour dans les journaux AAAHogEx."""
    checks = 0
    tries = 0
    succeeded = 0
    with gzip.open(log_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "[script:4] [1]" in line:
                if "CheckBuildReturnRoute" in line:
                    checks += 1
                elif "Try BuildReturnRoute" in line:
                    tries += 1
                elif "build return route succeeded" in line:
                    succeeded += 1
    return {"checks": checks, "tries": tries, "succeeded": succeeded}


class TestDiagRail(unittest.TestCase):
    """Auto-tests unitaires."""

    def test_cargo_constants(self):
        self.assertEqual(CARGO_NAMES[1], "Coal")
        self.assertEqual(CARGO_NAMES[5], "Goods")
        self.assertEqual(CARGO_NAMES[8], "Iron Ore")
        self.assertEqual(CARGO_NAMES[9], "Steel")

    def test_cap_vs_supply_bounding(self):
        stats = analyze_lines_telemetry({
            "lines": [
                {
                    "mode": "rail",
                    "cargo_types": ["1"],
                    "vehicles": 1,
                    "capacity_by_cargo": {"1": 60},
                    "ordered_station_tiles": [100, 200],
                    "endpoint_cargo_stats": [
                        {"station_id": 1, "cargo": {"1": {"max_waiting_cargo": 80, "rated": True, "rating": 180}}}
                    ]
                },
                {
                    "mode": "rail",
                    "cargo_types": ["1"],
                    "vehicles": 1,
                    "capacity_by_cargo": {"1": 60},
                    "ordered_station_tiles": [100, 200],
                    "endpoint_cargo_stats": [
                        {"station_id": 2, "cargo": {"1": {"max_waiting_cargo": 20, "rated": True, "rating": 180}}}
                    ]
                }
            ]
        })
        self.assertEqual(stats["n_lines"], 2)
        self.assertEqual(stats["cap_bounded"], 1)
        self.assertEqual(stats["supply_bounded"], 1)
        self.assertEqual(stats["pct_cap_bounded"], 50.0)


def main():
    parser = argparse.ArgumentParser(description="Diagnostic cargo par ligne rail (OpexAI vs AAAHogEx)")
    parser.add_argument("--base-dir", default=DEFAULT_BASE, help="Dossier des resultats wt-v270")
    parser.add_argument("--detail", action="store_true", help="Affiche le detail des lignes bornees par la capacite")
    parser.add_argument("--selftest", action="store_true", help="Execute les tests unitaires")
    args = parser.parse_args()

    if args.selftest:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDiagRail)
        runner = unittest.TextTestRunner(verbosity=2)
        res = runner.run(suite)
        sys.exit(0 if res.wasSuccessful() else 1)

    base_dir = args.base_dir
    jsonl_path = os.path.join(base_dir, "v270_expo_3x10_20261019.jsonl.gz")
    json_gz_path = os.path.join(base_dir, "v270_expo_3x10_20261019.json.gz")
    engine_dir = os.path.join(base_dir, "v270_expo_3x10_20261019_engine")

    print(f"Chargement des donnees depuis : {base_dir}")
    jsonl_data = load_jsonl_summary(jsonl_path)
    snapshots = load_telemetry_snapshots(json_gz_path)

    seeds = [42, 7, 1234]
    years = [1975, 1979]

    print("\n" + "=" * 90)
    print("TABLEAU 1 : METRIQUES RESEAU RAIL FRET (1975 et 1979)")
    print("=" * 90)

    header = (
        f"{'Annee':5s} | {'Graine':6s} | {'Cie':8s} | {'Lignes':6s} | {'Trains/L':8s} | {'Places/Tr':9s} | "
        f"{'Dist Moy':8s} | {'Fret/Mois':9s} | {'%Transf':7s} | {'%DestPart':9s} | {'%SrcPart':8s} | {'%Retour':7s}"
    )
    print(header)
    print("-" * len(header))

    agg = {}

    for year in years:
        date_str = f"{year}-12-01"
        for seed in seeds:
            for ai in ["OpexAI", "AAAHogEx"]:
                snap = [s for s in snapshots if s.get("year") == year and s.get("seed") == seed and s.get("arm") == ai][0]
                t_stats = analyze_lines_telemetry(snap)

                jd = jsonl_data.get((ai, seed, date_str), {})
                deliv = jd.get("delivered_cargo_last_quarter", [])
                raw_deliv = sum(deliv[i] for i in RAW_CARGO_IDS if i < len(deliv))
                trans_deliv = sum(deliv[i] for i in TRANSFORMED_CARGO_IDS if i < len(deliv))
                total_freight_deliv = raw_deliv + trans_deliv
                freight_per_month = total_freight_deliv / 3.0
                pct_trans_deliv = (trans_deliv / total_freight_deliv * 100.0) if total_freight_deliv > 0 else 0.0

                fret_retour_pct = 0.0

                row_str = (
                    f"{year:5d} | {seed:6d} | {ai:8s} | {t_stats['n_lines']:6d} | {t_stats['trains_per_line']:8.2f} | "
                    f"{t_stats['places_per_train']:9.1f} | {t_stats['mean_dist']:8.1f} | {freight_per_month:9.1f} | "
                    f"{pct_trans_deliv:6.1f}% | {t_stats['pct_shared_dst']:8.1f}% | {t_stats['pct_shared_src']:7.1f}% | {fret_retour_pct:6.1f}%"
                )
                print(row_str)

                key = (year, ai)
                if key not in agg:
                    agg[key] = {
                        "n_lines": [], "trains_per_line": [], "places_per_train": [],
                        "dist": [], "freight_per_month": [], "pct_trans_deliv": [],
                        "pct_shared_dst": [], "pct_shared_src": [], "profit": [],
                        "rating": [], "tsp": [], "wait": [], "cap_bounded": 0, "total_lines": 0
                    }
                agg[key]["n_lines"].append(t_stats["n_lines"])
                agg[key]["trains_per_line"].append(t_stats["trains_per_line"])
                agg[key]["places_per_train"].append(t_stats["places_per_train"])
                agg[key]["dist"].append(t_stats["mean_dist"])
                agg[key]["freight_per_month"].append(freight_per_month)
                agg[key]["pct_trans_deliv"].append(pct_trans_deliv)
                agg[key]["pct_shared_dst"].append(t_stats["pct_shared_dst"])
                agg[key]["pct_shared_src"].append(t_stats["pct_shared_src"])
                agg[key]["profit"].append(t_stats["total_profit_gbp"])
                agg[key]["rating"].append(t_stats["mean_rating"])
                agg[key]["tsp"].append(t_stats["mean_tsp"])
                agg[key]["wait"].append(t_stats["mean_wait"])
                agg[key]["cap_bounded"] += t_stats["cap_bounded"]
                agg[key]["total_lines"] += t_stats["n_lines"]

    print("\n" + "=" * 90)
    print("MOYENNES PAR COMPAGNIE ET PAR ANNEE")
    print("=" * 90)
    for (year, ai), vals in agg.items():
        m_lines = sum(vals["n_lines"]) / len(vals["n_lines"])
        m_tpl = sum(vals["trains_per_line"]) / len(vals["trains_per_line"])
        m_ppt = sum(vals["places_per_train"]) / len(vals["places_per_train"])
        m_dist = sum(vals["dist"]) / len(vals["dist"])
        m_fpm = sum(vals["freight_per_month"]) / len(vals["freight_per_month"])
        m_ptd = sum(vals["pct_trans_deliv"]) / len(vals["pct_trans_deliv"])
        m_psd = sum(vals["pct_shared_dst"]) / len(vals["pct_shared_dst"])
        m_pss = sum(vals["pct_shared_src"]) / len(vals["pct_shared_src"])
        m_prof = sum(vals["profit"]) / len(vals["profit"]) / 1000.0
        m_rate = sum(vals["rating"]) / len(vals["rating"]) / 255.0 * 100.0
        m_tsp = sum(vals["tsp"]) / len(vals["tsp"])
        pct_cap = vals["cap_bounded"] / vals["total_lines"] * 100.0

        print(f"{year} {ai:8s} : Lignes={m_lines:4.1f} | Trains/L={m_tpl:.2f} | Places/Tr={m_ppt:5.1f} | Dist={m_dist:5.1f} | Fret/mois={m_fpm:6.1f} u | Cargo/Ligne={m_fpm/m_lines:5.1f} u/m")
        print(f"            Profit rail fret={m_prof:6.1f} k£ | %Transf={m_ptd:4.1f}% | %DestPart={m_psd:4.1f}% | %SrcPart={m_pss:4.1f}%")
        print(f"            Note source={m_rate:4.1f}% | Temps ramassage={m_tsp:4.1f} per (≈{m_tsp*2.5:4.1f} j) | Bornes capacite={pct_cap:4.1f}% ({vals['cap_bounded']}/{vals['total_lines']})")

    print("\n" + "=" * 90)
    print("TABLEAU 2 : SONDE LINE_REVENUE OPEXAI (OFFRE VS CAPACITE)")
    print("=" * 90)

    for year in years:
        all_lr = []
        for seed in seeds:
            log_path = os.path.join(engine_dir, f"reference_seed{seed}_r0.log.gz")
            lr = parse_opex_line_revenue(log_path, year)
            all_lr.extend(lr)

        n_lr = len(all_lr)
        prods = [float(r["src_prod"]) for r in all_lr if float(r.get("src_prod", -1)) >= 0]
        pcts = [float(r["src_pct"]) for r in all_lr if float(r.get("src_pct", -1)) >= 0]
        waits = [float(r["wait_a"]) for r in all_lr]
        rame_caps = [float(r["cap"]) / float(r["vehs"]) if float(r["vehs"]) > 0 else float(r["cap"]) for r in all_lr]

        cap_b = sum(1 for w, c in zip(waits, rame_caps) if w > c)
        sup_b = n_lr - cap_b

        m_prod = sum(prods) / len(prods) if prods else 0.0
        m_pct = sum(pcts) / len(pcts) if pcts else 0.0
        m_wait = sum(waits) / len(waits) if waits else 0.0
        m_rcap = sum(rame_caps) / len(rame_caps) if rame_caps else 0.0

        ratios = sorted([w / c if c > 0 else 0.0 for w, c in zip(waits, rame_caps)])
        p10 = ratios[int(0.1 * n_lr)] if n_lr else 0
        p25 = ratios[int(0.25 * n_lr)] if n_lr else 0
        p50 = ratios[int(0.50 * n_lr)] if n_lr else 0
        p75 = ratios[int(0.75 * n_lr)] if n_lr else 0
        p90 = ratios[int(0.90 * n_lr)] if n_lr else 0

        print(f"Annee {year} (OpexAI, {n_lr} lignes analysees au total sur 3 graines) :")
        print(f"  Production source moyenne : {m_prod:5.1f} unites/mois | Part transportee moyenne : {m_pct:4.1f}%")
        print(f"  Attente quai moyenne      : {m_wait:5.1f} unites      | Capacite par rame moyenne : {m_rcap:5.1f} places")
        print(f"  Ratio attente / rame_cap  : p10={p10:.2f}, p25={p25:.2f}, mediane(p50)={p50:.2f}, p75={p75:.2f}, p90={p90:.2f}")
        print(f"  Classification            : Bornees par la capacite (wait > cap) = {cap_b:2d} ({cap_b/n_lr*100:4.1f}%) | Bornees par l'offre = {sup_b:2d} ({sup_b/n_lr*100:4.1f}%)")

        if args.detail:
            print("  Detail des lignes bornees par la capacite :")
            for r, w, c in zip(all_lr, waits, rame_caps):
                if w > c:
                    print(f"    Ligne {r.get('line'):2s} cargo={r.get('cargo'):5s} wait={w:5.0f} cap={c:5.0f} dist={r.get('dist'):3s} vehs={r.get('vehs')} prof={float(r.get('real_prof',0))/1000:5.1f}k£")


if __name__ == "__main__":
    main()
