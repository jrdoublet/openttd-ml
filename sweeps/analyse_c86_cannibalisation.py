#!/usr/bin/env python3
"""C86 Etape 1 : Analyse de cannibalisation des lignes aeriennes hub->hub.

Lit un jsonl brut produit par `sweeps/diag_c69_bottleneck_probe.py --grep " C56_TASK "`
(chaque ligne JSON contient `seed` et `grep` = ligne de log OPEX C56_TASK).

Pour chaque ligne construite par le bras `hubhub` (trace AIR_BUILT name=hubhub, champ line=) :
- Identifie ses deux gares stA et stB ;
- Trouve les AUTRES lignes aeriennes partageant l'une de ses deux gares (via stA/stB des traces LINE_PROFIT) ;
- Compare leur profit annuel total l'annee d'avant et l'annee d'apres l'ouverture (annee d'ouverture exclue) ;
- Met ce delta en regard du profit annuel de la nouvelle ligne elle-meme (a annee d'ouverture + 1).

Gere les donnees manquantes (ligne sans voisine, annees incompletes hors horizon, rapport manquant)
sans les convertir en zero.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


# Format de log emis par probes.nut::OpexC56TaskLog :
# OPEX AAAA-M-J C56_TASK <KIND> name=<...> cycle=- tick=<n> opsclk=<n> <champs k=v>
TASK_LOG_RE = re.compile(
    r"(?:OPEX\s+(\d+)-(\d+)-(\d+)\s+)?C56_TASK\s+(\w+)\s+(.*)"
)


def parse_kv_fields(rest_text):
    """Extrait un dictionnaire cle=valeur d'une chaine de log."""
    fields = {}
    for token in rest_text.split():
        if "=" in token:
            k, v = token.split("=", 1)
            fields[k] = v
    return fields


def parse_c56_log_line(text):
    """Parse une ligne de log C56_TASK brute.

    Retourne un dict avec kind, log_date, log_year, fields ou None si non reconnue.
    """
    m = TASK_LOG_RE.search(text)
    if not m:
        return None
    year_str, month_str, day_str, kind, rest = m.groups()
    log_year = int(year_str) if year_str is not None else None
    log_date = f"{year_str}-{month_str}-{day_str}" if year_str is not None else None
    fields = parse_kv_fields(rest)
    return {
        "kind": kind,
        "log_date": log_date,
        "log_year": log_year,
        "fields": fields,
    }


def to_int(val, default=None):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def to_float(val, default=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def load_task_records(lines_or_stream):
    """Charge les enregistrements AIR_BUILT et LINE_PROFIT depuis un iterable de lignes.

    Chaque ligne peut etre du JSON (format diag_c69_bottleneck_probe --grep) ou du texte brut.
    Groupe par seed.
    """
    seeds_data = defaultdict(lambda: {"air_builts": [], "line_profits": []})

    for line in lines_or_stream:
        line = line.strip()
        if not line:
            continue
        seed = None
        raw_text = line
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                seed = data.get("seed")
                raw_text = data.get("grep", data.get("raw", data.get("log", data.get("text", ""))))
            except json.JSONDecodeError:
                pass

        if seed is None:
            seed = "default"

        parsed = parse_c56_log_line(raw_text)
        if not parsed:
            continue

        kind = parsed["kind"]
        fields = parsed["fields"]
        log_year = parsed["log_year"]

        if kind == "AIR_BUILT":
            arm = fields.get("name", fields.get("arm", "unknown"))
            line_id = to_int(fields.get("line"))
            profit_mod = to_float(fields.get("profit"))
            cost_mod = to_float(fields.get("cost"))
            st_a = to_int(fields.get("stA"))
            st_b = to_int(fields.get("stB"))
            seeds_data[seed]["air_builts"].append({
                "arm": arm,
                "line_id": line_id,
                "profit_modelled": profit_mod,
                "cost_modelled": cost_mod,
                "stA": st_a,
                "stB": st_b,
                "open_year": log_year,
                "log_date": parsed["log_date"],
            })

        elif kind == "LINE_PROFIT":
            line_id = to_int(fields.get("line", fields.get("name")))
            # `year` est l'annee du RAPPORT (debut d'annee, GetProfitLastYear) : le profit
            # porte sur l'annee precedente. On indexe par annee de profit.
            rep_year = to_int(fields.get("year"))
            if rep_year is not None:
                rep_year -= 1
            profit = to_float(fields.get("profit"))
            veh = to_int(fields.get("veh"))
            st_a = to_int(fields.get("stA"))
            st_b = to_int(fields.get("stB"))
            wait_a = to_int(fields.get("waitA"))
            wait_b = to_int(fields.get("waitB"))
            rate_a = to_int(fields.get("rateA"))
            rate_b = to_int(fields.get("rateB"))
            seeds_data[seed]["line_profits"].append({
                "line_id": line_id,
                "year": rep_year,
                "profit": profit,
                "veh": veh,
                "stA": st_a,
                "stB": st_b,
                "waitA": wait_a,
                "waitB": wait_b,
                "rateA": rate_a,
                "rateB": rate_b,
            })

    return seeds_data


def analyse_seed_cannibalisation(seed, data):
    """Analyse les effets de cannibalisation pour une graine donnee.

    Ne convertit jamais les donnees manquantes en zero.
    """
    air_builts = data["air_builts"]
    line_profits = data["line_profits"]

    # 1. Indexer les traces LINE_PROFIT
    # line_reports: line_id -> year -> record
    line_reports = defaultdict(dict)
    # line_stations: line_id -> set(stA, stB)
    line_stations = defaultdict(set)

    for lp in line_profits:
        lid = lp["line_id"]
        yr = lp["year"]
        if lid is not None and yr is not None:
            line_reports[lid][yr] = lp
            if lp["stA"] is not None and lp["stA"] >= 0:
                line_stations[lid].add(lp["stA"])
            if lp["stB"] is not None and lp["stB"] >= 0:
                line_stations[lid].add(lp["stB"])

    # Completer line_stations avec les traces AIR_BUILT si dispo
    for ab in air_builts:
        lid = ab["line_id"]
        if lid is not None:
            if ab["stA"] is not None and ab["stA"] >= 0:
                line_stations[lid].add(ab["stA"])
            if ab["stB"] is not None and ab["stB"] >= 0:
                line_stations[lid].add(ab["stB"])

    # Ensemble de toutes les annees rapportees dans cette graine
    all_reported_years = set()
    for lid, rep_by_yr in line_reports.items():
        all_reported_years.update(rep_by_yr.keys())

    # 2. Filtrer les lignes construites par hubhub
    # Dedupliquer par line_id au cas ou
    seen_hubhub = set()
    hubhub_builds = []
    for ab in air_builts:
        if ab["arm"] == "hubhub" and ab["line_id"] is not None:
            if ab["line_id"] not in seen_hubhub:
                seen_hubhub.add(ab["line_id"])
                hubhub_builds.append(ab)

    # 3. Analyser chaque ligne hubhub
    evaluated_cases = []
    no_neighbor_cases = []
    incomplete_year_cases = []
    incomplete_other_cases = []

    for hb in hubhub_builds:
        lid = hb["line_id"]
        open_year = hb["open_year"]
        st_set = line_stations.get(lid, set())

        case_info = {
            "seed": seed,
            "line_id": lid,
            "open_year": open_year,
            "stations": sorted(list(st_set)),
        }

        if open_year is None:
            case_info["reason"] = "missing_open_year"
            incomplete_other_cases.append(case_info)
            continue

        year_before = open_year - 1
        year_after = open_year + 1

        # Verifier si les annees d'avant et d'apres sont couvertes par le run
        if year_before not in all_reported_years or year_after not in all_reported_years:
            case_info["reason"] = "years_outside_horizon"
            case_info["year_before"] = year_before
            case_info["year_after"] = year_after
            incomplete_year_cases.append(case_info)
            continue

        # Profit de la nouvelle ligne a year_after
        new_line_rep = line_reports.get(lid, {}).get(year_after)
        if new_line_rep is None or new_line_rep.get("profit") is None:
            case_info["reason"] = "new_line_missing_after_report"
            incomplete_other_cases.append(case_info)
            continue
        new_line_profit = new_line_rep["profit"]

        if len(st_set) < 2:
            case_info["reason"] = "missing_station_ids"
            incomplete_other_cases.append(case_info)
            continue

        # Trouver les autres lignes aeriennes partageant l'une des deux gares
        # Voisines actives l'annee d'avant l'ouverture
        neighbors_before = []
        for other_lid, other_stations in line_stations.items():
            if other_lid == lid:
                continue
            if other_stations & st_set:
                # Cette ligne partage au moins une gare
                if year_before in line_reports.get(other_lid, {}):
                    neighbors_before.append(other_lid)

        if not neighbors_before:
            case_info["reason"] = "no_preexisting_neighbors"
            case_info["new_line_profit"] = new_line_profit
            no_neighbor_cases.append(case_info)
            continue

        # Verifier si toutes les voisines de l'annee d'avant ont un rapport a year_after
        missing_neighbors = [
            nlid for nlid in neighbors_before
            if year_after not in line_reports.get(nlid, {})
        ]
        if missing_neighbors:
            case_info["reason"] = "neighbor_missing_after_report"
            case_info["missing_neighbors"] = missing_neighbors
            incomplete_other_cases.append(case_info)
            continue

        # Cas completement evaluable
        profit_before = sum(line_reports[nlid][year_before]["profit"] for nlid in neighbors_before)
        profit_after = sum(line_reports[nlid][year_after]["profit"] for nlid in neighbors_before)
        delta_neighbors = profit_after - profit_before

        case_record = {
            "seed": seed,
            "line_id": lid,
            "open_year": open_year,
            "year_before": year_before,
            "year_after": year_after,
            "stations": sorted(list(st_set)),
            "neighbors": sorted(neighbors_before),
            "neighbors_count": len(neighbors_before),
            "profit_neighbors_before": profit_before,
            "profit_neighbors_after": profit_after,
            "delta_neighbors": delta_neighbors,
            "new_line_profit": new_line_profit,
            "neighbors_decreased": (delta_neighbors < 0),
            "net_gain": new_line_profit + delta_neighbors,
        }
        evaluated_cases.append(case_record)

    # Agregation pour cette graine
    eval_count = len(evaluated_cases)
    sum_delta = sum(c["delta_neighbors"] for c in evaluated_cases) if eval_count > 0 else None
    sum_new_profit = sum(c["new_line_profit"] for c in evaluated_cases) if eval_count > 0 else None
    dec_count = sum(1 for c in evaluated_cases if c["neighbors_decreased"]) if eval_count > 0 else 0
    dec_share = (dec_count / eval_count) if eval_count > 0 else None

    return {
        "seed": seed,
        "hubhub_built_count": len(hubhub_builds),
        "evaluated_count": eval_count,
        "no_neighbor_count": len(no_neighbor_cases),
        "incomplete_years_count": len(incomplete_year_cases),
        "incomplete_other_count": len(incomplete_other_cases),
        "delta_neighbors_sum": sum_delta,
        "new_line_profit_sum": sum_new_profit,
        "decreased_count": dec_count,
        "decreased_share": dec_share,
        "evaluated_cases": evaluated_cases,
        "no_neighbor_cases": no_neighbor_cases,
        "incomplete_year_cases": incomplete_year_cases,
        "incomplete_other_cases": incomplete_other_cases,
    }


def analyse_cannibalisation(lines_or_stream):
    """Analyse l'ensemble des donnees chargees par graine et produit le bilan global."""
    seeds_data = load_task_records(lines_or_stream)
    per_seed = {}
    all_evaluated = []

    for seed, data in sorted(seeds_data.items(), key=lambda x: str(x[0])):
        res = analyse_seed_cannibalisation(seed, data)
        per_seed[seed] = res
        all_evaluated.extend(res["evaluated_cases"])

    total_hubhub = sum(r["hubhub_built_count"] for r in per_seed.values())
    total_eval = len(all_evaluated)
    total_no_neighbor = sum(r["no_neighbor_count"] for r in per_seed.values())
    total_incomplete_years = sum(r["incomplete_years_count"] for r in per_seed.values())
    total_incomplete_other = sum(r["incomplete_other_count"] for r in per_seed.values())

    if total_eval > 0:
        total_delta = sum(c["delta_neighbors"] for c in all_evaluated)
        total_new_profit = sum(c["new_line_profit"] for c in all_evaluated)
        total_decreased = sum(1 for c in all_evaluated if c["neighbors_decreased"])
        overall_dec_share = total_decreased / total_eval
        net_impact = total_new_profit + total_delta
    else:
        total_delta = None
        total_new_profit = None
        total_decreased = 0
        overall_dec_share = None
        net_impact = None

    summary = {
        "total_hubhub_built": total_hubhub,
        "total_evaluated": total_eval,
        "total_no_neighbor": total_no_neighbor,
        "total_incomplete_years": total_incomplete_years,
        "total_incomplete_other": total_incomplete_other,
        "total_delta_neighbors": total_delta,
        "total_new_line_profit": total_new_profit,
        "total_decreased_count": total_decreased,
        "overall_decreased_share": overall_dec_share,
        "net_impact": net_impact,
        "per_seed": per_seed,
    }
    return summary


def format_currency(val):
    if val is None:
        return "N/A"
    return f"{val:+,.0f} £" if val < 0 or "+" in str(val) else f"{val:,.0f} £"


def print_report(summary):
    """Affiche le rapport formateur sur stdout."""
    print("=" * 80)
    print(" C86 : ANALYSE DE CANNIBALISATION AIR HUB->HUB")
    print("=" * 80)
    print(f"Lignes hub->hub construites : {summary['total_hubhub_built']}")
    print(f"Cas evaluables              : {summary['total_evaluated']}")
    print(f"Lignes sans voisine         : {summary['total_no_neighbor']} (non converties en 0)")
    print(f"Annees incompletes (horizon): {summary['total_incomplete_years']} (non converties en 0)")
    if summary["total_incomplete_other"] > 0:
        print(f"Autres donnees manquantes   : {summary['total_incomplete_other']}")
    print("-" * 80)

    per_seed = summary["per_seed"]
    print(f"{'Graine':<10} | {'HubHub':<6} | {'Eval':<5} | {'NoNeigh':<7} | {'IncYr':<5} | {'Delta Voisines':<15} | {'Profit Nv Ligne':<15} | {'Voisines < 0'}")
    print("-" * 80)
    for seed, r in sorted(per_seed.items(), key=lambda x: str(x[0])):
        s_eval = r["evaluated_count"]
        d_vois = f"{r['delta_neighbors_sum']:+,.0f} £" if r["delta_neighbors_sum"] is not None else "N/A"
        p_nv = f"{r['new_line_profit_sum']:,.0f} £" if r["new_line_profit_sum"] is not None else "N/A"
        dec_str = f"{r['decreased_count']}/{s_eval} ({r['decreased_share']*100:.1f}%)" if r["decreased_share"] is not None else "N/A"
        print(f"{str(seed):<10} | {r['hubhub_built_count']:<6} | {s_eval:<5} | {r['no_neighbor_count']:<7} | {r['incomplete_years_count']:<5} | {d_vois:<15} | {p_nv:<15} | {dec_str}")

    print("-" * 80)
    print("TOTAL AGREGÉ :")
    d_total = f"{summary['total_delta_neighbors']:+,.0f} £" if summary["total_delta_neighbors"] is not None else "N/A"
    p_total = f"{summary['total_new_line_profit']:,.0f} £" if summary["total_new_line_profit"] is not None else "N/A"
    dec_total = f"{summary['total_decreased_count']}/{summary['total_evaluated']} ({summary['overall_decreased_share']*100:.1f}%)" if summary["overall_decreased_share"] is not None else "N/A"
    net_str = f"{summary['net_impact']:+,.0f} £" if summary["net_impact"] is not None else "N/A"
    print(f"  Somme des variations des voisines : {d_total}")
    print(f"  Somme des profits nv lignes       : {p_total}")
    print(f"  Impact net total (profit + delta) : {net_str}")
    print(f"  Part de cas ou les voisines baissent: {dec_total}")
    print("=" * 80)


def run_selftest():
    """Selftest pur Python utilisant un jeu de donnees synthetique."""
    synthetic_logs = [
        # Graine 42
        # Annee 1970 : Ligne 1 reliant stA=10 stB=20
        json.dumps({"seed": 42, "grep": "OPEX 1971-1-1 C56_TASK LINE_PROFIT name=1 cycle=- tick=10 opsclk=10 year=1971 profit=50000 veh=2 stA=10 stB=20 waitA=100 waitB=100 rateA=70 rateB=70"}),
        # Annee 1971 : Ligne 1 fait 50000. Ligne 3 reliant stA=30 stB=40 fait 40000.
        json.dumps({"seed": 42, "grep": "OPEX 1972-1-1 C56_TASK LINE_PROFIT name=1 cycle=- tick=20 opsclk=20 year=1972 profit=50000 veh=2 stA=10 stB=20 waitA=100 waitB=100 rateA=70 rateB=70"}),
        json.dumps({"seed": 42, "grep": "OPEX 1972-1-1 C56_TASK LINE_PROFIT name=3 cycle=- tick=25 opsclk=25 year=1972 profit=40000 veh=2 stA=30 stB=40 waitA=80 waitB=80 rateA=75 rateB=75"}),

        # En 1972 : Construction de la ligne 2 par hubhub reliant stA=20 stB=25 (partage la gare 20 avec la ligne 1 !)
        json.dumps({"seed": 42, "grep": "OPEX 1972-6-15 C56_TASK AIR_BUILT name=hubhub cycle=- tick=30 opsclk=30 line=2 profit=22000 cost=30000 stA=20 stB=25"}),
        # En 1972 : Construction de la ligne 4 par hubhub reliant stA=40 stB=45 (partage la gare 40 avec la ligne 3 !)
        json.dumps({"seed": 42, "grep": "OPEX 1972-7-20 C56_TASK AIR_BUILT name=hubhub cycle=- tick=35 opsclk=35 line=4 profit=21000 cost=31000 stA=40 stB=45"}),
        # En 1972 : Construction de la ligne 5 par hubhub reliant stA=50 stB=60 (aucun voisin preexistant)
        json.dumps({"seed": 42, "grep": "OPEX 1972-8-01 C56_TASK AIR_BUILT name=hubhub cycle=- tick=40 opsclk=40 line=5 profit=18000 cost=28000 stA=50 stB=60"}),

        # Annee 1972 (annee d'ouverture, exclue de la comparaison)
        json.dumps({"seed": 42, "grep": "OPEX 1973-1-1 C56_TASK LINE_PROFIT name=1 cycle=- tick=50 opsclk=50 year=1973 profit=42000 veh=2 stA=10 stB=20 waitA=90 waitB=90 rateA=68 rateB=68"}),
        json.dumps({"seed": 42, "grep": "OPEX 1973-1-1 C56_TASK LINE_PROFIT name=2 cycle=- tick=52 opsclk=52 year=1973 profit=12000 veh=2 stA=20 stB=25 waitA=40 waitB=40 rateA=70 rateB=70"}),
        json.dumps({"seed": 42, "grep": "OPEX 1973-1-1 C56_TASK LINE_PROFIT name=3 cycle=- tick=54 opsclk=54 year=1973 profit=41000 veh=2 stA=30 stB=40 waitA=85 waitB=85 rateA=75 rateB=75"}),
        json.dumps({"seed": 42, "grep": "OPEX 1973-1-1 C56_TASK LINE_PROFIT name=4 cycle=- tick=56 opsclk=56 year=1973 profit=11000 veh=2 stA=40 stB=45 waitA=45 waitB=45 rateA=72 rateB=72"}),
        json.dumps({"seed": 42, "grep": "OPEX 1973-1-1 C56_TASK LINE_PROFIT name=5 cycle=- tick=58 opsclk=58 year=1973 profit=10000 veh=2 stA=50 stB=60 waitA=50 waitB=50 rateA=70 rateB=70"}),

        # Annee 1973 (annee apres ouverture = year_after) :
        # - Ligne 1 : profit passe de 50000 a 30000 (baisse de -20000 -> cannibalisation !)
        # - Ligne 2 (nouvelle ligne) : profit = 25000
        json.dumps({"seed": 42, "grep": "OPEX 1974-1-1 C56_TASK LINE_PROFIT name=1 cycle=- tick=70 opsclk=70 year=1974 profit=30000 veh=2 stA=10 stB=20 waitA=60 waitB=60 rateA=65 rateB=65"}),
        json.dumps({"seed": 42, "grep": "OPEX 1974-1-1 C56_TASK LINE_PROFIT name=2 cycle=- tick=72 opsclk=72 year=1974 profit=25000 veh=2 stA=20 stB=25 waitA=60 waitB=60 rateA=72 rateB=72"}),
        # - Ligne 3 : profit passe de 40000 a 45000 (hausse de +5000 -> pas de cannibalisation)
        # - Ligne 4 (nouvelle ligne) : profit = 20000
        json.dumps({"seed": 42, "grep": "OPEX 1974-1-1 C56_TASK LINE_PROFIT name=3 cycle=- tick=74 opsclk=74 year=1974 profit=45000 veh=2 stA=30 stB=40 waitA=90 waitB=90 rateA=78 rateB=78"}),
        json.dumps({"seed": 42, "grep": "OPEX 1974-1-1 C56_TASK LINE_PROFIT name=4 cycle=- tick=76 opsclk=76 year=1974 profit=20000 veh=2 stA=40 stB=45 waitA=55 waitB=55 rateA=73 rateB=73"}),
        # - Ligne 5 (sans voisine preexistante) : profit = 22000
        json.dumps({"seed": 42, "grep": "OPEX 1974-1-1 C56_TASK LINE_PROFIT name=5 cycle=- tick=78 opsclk=78 year=1974 profit=22000 veh=2 stA=50 stB=60 waitA=60 waitB=60 rateA=71 rateB=71"}),

        # Cas annees incompletes :
        # Ligne 6 construite en 1970 (year_before = 1969 hors run)
        json.dumps({"seed": 42, "grep": "OPEX 1970-5-01 C56_TASK AIR_BUILT name=hubhub cycle=- tick=2 opsclk=2 line=6 profit=20000 cost=30000 stA=10 stB=70"}),
        # Ligne 7 construite en 1973 (year_after = 1974 hors run)
        json.dumps({"seed": 42, "grep": "OPEX 1973-5-01 C56_TASK AIR_BUILT name=hubhub cycle=- tick=80 opsclk=80 line=7 profit=20000 cost=30000 stA=10 stB=80"}),
    ]

    summary = analyse_cannibalisation(synthetic_logs)

    # Verifications rigoureuses
    assert summary["total_hubhub_built"] == 5, f"attendu 5, obtenu {summary['total_hubhub_built']}"
    assert summary["total_evaluated"] == 2, f"attendu 2, obtenu {summary['total_evaluated']}"
    assert summary["total_no_neighbor"] == 1, f"attendu 1, obtenu {summary['total_no_neighbor']}"
    assert summary["total_incomplete_years"] == 2, f"attendu 2, obtenu {summary['total_incomplete_years']}"

    # Delta voisines = (-20000) + (+5000) = -15000
    assert summary["total_delta_neighbors"] == -15000.0, f"attendu -15000, obtenu {summary['total_delta_neighbors']}"
    # Profit nv lignes = 25000 + 20000 = 45000
    assert summary["total_new_line_profit"] == 45000.0, f"attendu 45000, obtenu {summary['total_new_line_profit']}"
    # Impact net = 45000 - 15000 = 30000
    assert summary["net_impact"] == 30000.0, f"attendu 30000, obtenu {summary['net_impact']}"
    # Baisse : 1 cas sur 2 (50%)
    assert summary["total_decreased_count"] == 1, f"attendu 1, obtenu {summary['total_decreased_count']}"
    assert summary["overall_decreased_share"] == 0.5, f"attendu 0.5, obtenu {summary['overall_decreased_share']}"

    # Verifier les details des cas
    eval_cases = summary["per_seed"][42]["evaluated_cases"]
    c1 = next(c for c in eval_cases if c["line_id"] == 2)
    assert c1["delta_neighbors"] == -20000.0
    assert c1["new_line_profit"] == 25000.0
    assert c1["neighbors_decreased"] is True

    c2 = next(c for c in eval_cases if c["line_id"] == 4)
    assert c2["delta_neighbors"] == 5000.0
    assert c2["new_line_profit"] == 20000.0
    assert c2["neighbors_decreased"] is False

    print("Selftest analyse_c86_cannibalisation : PASS (assertions verifiees avec succes).")
    return True


def main():
    parser = argparse.ArgumentParser(description="Analyse de cannibalisation AIR hub->hub (C86)")
    parser.add_argument("input_file", nargs="?", help="Fichier jsonl brut produit par sweeps/diag_c69_bottleneck_probe.py --grep ' C56_TASK '")
    parser.add_argument("--json", action="store_true", help="Sortie structuree en JSON")
    parser.add_argument("--selftest", action="store_true", help="Execute le test interne pur Python")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        sys.exit(0)

    if not args.input_file:
        parser.print_help()
        sys.exit(1)

    in_path = Path(args.input_file)
    if not in_path.is_file():
        print(f"Erreur : fichier introuvable {in_path}", file=sys.stderr)
        sys.exit(1)

    with open(in_path, "r", encoding="utf-8") as fh:
        summary = analyse_cannibalisation(fh)

    if args.json:
        # Serialiser sans les cles non serialisables
        print(json.dumps(summary, indent=2))
    else:
        print_report(summary)


if __name__ == "__main__":
    main()
