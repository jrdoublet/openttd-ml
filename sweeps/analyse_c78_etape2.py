"""C78 etape 2 : Analyse diagnostique approfondie OpexAI contre AAAHogEx.

Identifie pourquoi les meilleures paires d'AAAHogEx ne sont jamais generees par OpexAI,
et pourquoi un candidat classe dans le top 5 et financable peut ne jamais etre construit.
Sondes passives C78_AIRPOOL, C78_AIRTOWN, C78_AIRPAIR, C78_BUILD et vivier C78_CAND.
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "results" / "diag_c78_lines_vs_aaa.json"
DEFAULT_OUT = ROOT / "results" / "analyse_c78_etape2.json"
TARGET_YEARS = (1973, 1975)
MAP_WIDTH = 256

# Ordre d'avancement des etapes pour les paires aeriennes (plus grand = plus avance)
STAGES_ORDER = [
    "hors_pool",
    "ville_ecartee",
    "paire_ecartee",
    "admitted",
    "dans_le_vivier",
    "classe",
    "tente",
    "construit",
]
STAGE_INDEX = {s: i for i, s in enumerate(STAGES_ORDER)}

# Ordre des rejets par ville
TOWN_OUTCOME_ORDER = {
    "origin_served": 0,
    "town_pop_small": 1,
    "no_site": 2,
    "site": 3,
}

# Ordre des rejets de paire dans C78_AIRPAIR (du plus precoce au plus tardif)
PAIR_OUTCOME_ORDER = {
    "distance_short": 0,
    "pax_band": 1,
    "distance_long": 2,
    "max_order_distance": 3,
    "abandoned": 4,
    "already_connected": 5,
    "economics_unavailable": 6,
    "profit_nonpositive": 7,
    "admitted": 8,
}


def get_line_pair(line):
    towns = line.get("towns") or []
    if len(towns) >= 2:
        return tuple(sorted(int(t) for t in towns[:2]))
    if len(towns) == 1:
        return (int(towns[0]), int(towns[0]))
    return ()


def get_candidate_pair(cand):
    town_a = cand.get("townA", -1)
    town_b = cand.get("townB", -1)
    if town_a >= 0 and town_b >= 0:
        return tuple(sorted([int(town_a), int(town_b)]))
    ind_a = cand.get("indA", -1)
    ind_b = cand.get("indB", -1)
    if ind_a >= 0 and ind_b >= 0:
        return tuple(sorted([int(ind_a), int(ind_b)]))
    return ()


def get_tile_manhattan_distance(t1, t2, map_width=MAP_WIDTH):
    if t1 is None or t2 is None or t1 < 0 or t2 < 0:
        return -1
    x1, y1 = t1 % map_width, t1 // map_width
    x2, y2 = t2 % map_width, t2 // map_width
    return abs(x1 - x2) + abs(y1 - y2)


def pair_band_info(years_dict, pair, year):
    """Distance de Manhattan entre les centres des deux villes (tuiles de C78_AIRPOOL) et bornes
    de distance de l'annee (airMin = bascule rail/avion). None si l'information manque."""
    tiles = {}
    mapx = None
    for y in sorted(years_dict.keys()):
        ap = years_dict[y].get("airpool") or {}
        if ap.get("mapx"):
            mapx = ap["mapx"]
        for tid in pair:
            info = get_town_pool_info(ap, tid)
            if info and len(info) >= 3 and info[2] is not None:
                tiles[tid] = info[2]
    bounds = ((years_dict.get(year) or {}).get("airpool") or {}).get("bounds") or {}
    if not bounds:
        for y in sorted(years_dict.keys()):
            b = (years_dict[y].get("airpool") or {}).get("bounds") or {}
            if b:
                bounds = b
    dist = None
    if len(tiles) == 2:
        dist = get_tile_manhattan_distance(tiles[pair[0]], tiles[pair[1]], mapx or MAP_WIDTH)
    air_min = bounds.get("airMin")
    below = (dist < air_min) if (dist is not None and air_min is not None) else None
    return {"dist_towns": dist, "airMin": air_min, "below_airmin": below}


def get_town_pool_info(airpool, town_id):
    if not airpool or "towns" not in airpool:
        return None
    towns = airpool["towns"]
    return towns.get(town_id) or towns.get(str(town_id))


def evaluate_air_pair_in_year(snapshot, pair):
    """Evalue le niveau atteint par la paire aerienne (townA, townB) au cours d'une annee donnee."""
    townA, townB = pair
    year = snapshot.get("year")
    airpool = snapshot.get("airpool") or {}
    airtowns = snapshot.get("airtowns") or []
    airpairs = snapshot.get("airpairs") or []
    candidates = snapshot.get("candidates") or []
    builds = snapshot.get("builds") or []
    opex_lines = (snapshot.get("companies", {}).get("0") or {}).get("lines", [])

    # 1. Construit ?
    for ol in opex_lines:
        if ol.get("mode") == "air" and get_line_pair(ol) == pair:
            return {
                "stage": "construit",
                "stage_idx": STAGE_INDEX["construit"],
                "reason": "built",
                "detail": f"line_profit={ol.get('profit_last_year', 0)}",
                "year": year,
            }

    # 2. Tente (C78_BUILD) ?
    matched_builds = []
    for b in builds:
        if b.get("mode") == "air":
            b_pair = tuple(sorted([b.get("townA", -1), b.get("townB", -1)]))
            if b_pair == pair:
                matched_builds.append(b)
    if matched_builds:
        last_b = matched_builds[-1]
        b_outcome = last_b.get("outcome", "-")
        b_reason = last_b.get("reason", "-")
        return {
            "stage": "tente",
            "stage_idx": STAGE_INDEX["tente"],
            "reason": b_reason if b_reason != "-" else b_outcome,
            "detail": f"rank={last_b.get('rank', -1)} outcome={b_outcome} reason={b_reason}",
            "year": year,
            "build_record": last_b,
        }

    # 3. Dans le vivier (C78_CAND) ?
    matched_cands = []
    for c in candidates:
        if c.get("mode") == "air" and get_candidate_pair(c) == pair:
            matched_cands.append(c)
    if matched_cands:
        best_cand = min(matched_cands, key=lambda c: c.get("rank", 9999) if c.get("rank", -1) >= 0 else 9999)
        rank = best_cand.get("rank", -1)
        if rank >= 0:
            return {
                "stage": "classe",
                "stage_idx": STAGE_INDEX["classe"],
                "reason": f"rank={rank}",
                "detail": f"rank={rank} P={best_cand.get('P', 0)} C={best_cand.get('C', 0)} aff={best_cand.get('affordable', 0)}",
                "year": year,
                "cand_record": best_cand,
            }
        else:
            return {
                "stage": "dans_le_vivier",
                "stage_idx": STAGE_INDEX["dans_le_vivier"],
                "reason": "unranked",
                "detail": f"P={best_cand.get('P', 0)} C={best_cand.get('C', 0)} aff={best_cand.get('affordable', 0)}",
                "year": year,
                "cand_record": best_cand,
            }

    # 4. Dans les paires examinees (C78_AIRPAIR) ?
    matched_pairs = []
    for ap in airpairs:
        ap_pair = tuple(sorted([ap.get("townA", -1), ap.get("townB", -1)]))
        if ap_pair == pair:
            matched_pairs.append(ap)
    if matched_pairs:
        # Meilleure issue sur combos et bras
        best_ap = max(matched_pairs, key=lambda ap: PAIR_OUTCOME_ORDER.get(ap.get("outcome", ""), -1))
        outcome = best_ap.get("outcome", "unknown")
        if outcome == "admitted":
            return {
                "stage": "admitted",
                "stage_idx": STAGE_INDEX["admitted"],
                "reason": "admitted",
                "detail": f"arm={best_ap.get('arm')} combo={best_ap.get('combo')} P={best_ap.get('P', -1)} C={best_ap.get('C', -1)}",
                "year": year,
            }
        else:
            return {
                "stage": "paire_ecartee",
                "stage_idx": STAGE_INDEX["paire_ecartee"],
                "reason": outcome,
                "detail": f"arm={best_ap.get('arm')} combo={best_ap.get('combo')} dist={best_ap.get('dist', -1)}",
                "year": year,
            }

    # 5. Hors pool de population ? (C78_AIRPOOL)
    pool = airpool.get("pool", 24)
    infoA = get_town_pool_info(airpool, townA)
    infoB = get_town_pool_info(airpool, townB)
    rankA = infoA[0] if infoA else None
    rankB = infoB[0] if infoB else None
    popA = infoA[1] if infoA else None
    popB = infoB[1] if infoB else None

    if rankA is None or rankA >= pool or rankB is None or rankB >= pool:
        faulty_town = None
        faulty_rank = None
        faulty_pop = None
        if rankA is None or rankA >= pool:
            faulty_town = townA
            faulty_rank = rankA
            faulty_pop = popA
        if rankB is None or rankB >= pool:
            if faulty_town is None or (rankB is not None and (faulty_rank is None or rankB > faulty_rank)):
                faulty_town = townB
                faulty_rank = rankB
                faulty_pop = popB

        detail_str = f"faulty_town={faulty_town} rank={faulty_rank} pop={faulty_pop} pool={pool}"
        return {
            "stage": "hors_pool",
            "stage_idx": STAGE_INDEX["hors_pool"],
            "reason": "hors_pool",
            "detail": detail_str,
            "faulty_town": faulty_town,
            "faulty_rank": faulty_rank,
            "faulty_pop": faulty_pop,
            "year": year,
        }

    # 6. Examine au niveau des villes (C78_AIRTOWN) : les deux villes sont dans le pool (rank < pool)
    outcomes_A = [at.get("outcome") for at in airtowns if at.get("town") == townA]
    outcomes_B = [at.get("outcome") for at in airtowns if at.get("town") == townB]
    best_A = max(outcomes_A, key=lambda o: TOWN_OUTCOME_ORDER.get(o, -1)) if outcomes_A else None
    best_B = max(outcomes_B, key=lambda o: TOWN_OUTCOME_ORDER.get(o, -1)) if outcomes_B else None

    order_A = TOWN_OUTCOME_ORDER.get(best_A, -1)
    order_B = TOWN_OUTCOME_ORDER.get(best_B, -1)
    if order_A <= order_B:
        faulty_town, faulty_reason = townA, (best_A or "no_site")
    else:
        faulty_town, faulty_reason = townB, (best_B or "no_site")

    return {
        "stage": "ville_ecartee",
        "stage_idx": STAGE_INDEX["ville_ecartee"],
        "reason": faulty_reason,
        "detail": f"town={faulty_town} reason={faulty_reason} (A:{best_A}, B:{best_B})",
        "faulty_town": faulty_town,
        "year": year,
    }


def find_first_year_aaa(snapshots_by_year, pair, mode):
    for y in sorted(snapshots_by_year.keys()):
        snap = snapshots_by_year[y]
        aaa_lines = (snap.get("companies", {}).get("1") or {}).get("lines", [])
        for l in aaa_lines:
            if l.get("mode") == mode and get_line_pair(l) == pair:
                return y
    return None


def analyse_air_lines(snapshots, target_years=TARGET_YEARS):
    # Indexer par (seed, year)
    by_seed_year = defaultdict(dict)
    for row in snapshots:
        seed = row.get("seed")
        year = row.get("year")
        if seed is not None and year is not None:
            by_seed_year[seed][year] = row

    air_analyses = []
    top5_unbuilt = []

    for seed, years_dict in sorted(by_seed_year.items()):
        for target_year in target_years:
            if target_year not in years_dict:
                continue
            snap_target = years_dict[target_year]
            aaa_data = (snap_target.get("companies", {}).get("1") or {})
            aaa_lines = list(aaa_data.get("lines", []))
            aaa_lines.sort(key=lambda l: float(l.get("profit_last_year", 0.0)), reverse=True)
            top20 = aaa_lines[:20]

            for line in top20:
                if line.get("mode") != "air":
                    continue
                pair = get_line_pair(line)
                if not pair:
                    continue
                first_year = find_first_year_aaa(years_dict, pair, "air") or target_year

                # Verifier si OpexAI a deja construit la paire a target_year
                opex_built_at_target = any(
                    ol.get("mode") == "air" and get_line_pair(ol) == pair
                    for ol in (snap_target.get("companies", {}).get("0") or {}).get("lines", [])
                )
                if opex_built_at_target:
                    continue

                # Etape dans l'annee de premiere exploitation
                snap_first = years_dict.get(first_year, snap_target)
                eval_first = evaluate_air_pair_in_year(snap_first, pair)

                # Etape la plus avancee sur toutes les annees <= target_year
                evals_all = []
                for y in sorted(years_dict.keys()):
                    if y <= target_year:
                        evals_all.append(evaluate_air_pair_in_year(years_dict[y], pair))

                best_eval = max(evals_all, key=lambda e: e["stage_idx"])

                # Classement de l'etape 1 pour cette paire
                # Vivier a target_year ?
                cand_target = any(
                    c.get("mode") == "air" and get_candidate_pair(c) == pair
                    for c in snap_target.get("candidates", [])
                )
                # Vivier dans une annee anterieure ?
                cand_prior = any(
                    c.get("mode") == "air" and get_candidate_pair(c) == pair
                    for y in years_dict if y < target_year
                    for c in years_dict[y].get("candidates", [])
                )

                if cand_target:
                    classe_etape1 = "dans_le_vivier_meme_annee"
                elif cand_prior:
                    classe_etape1 = "vivier_annee_anterieure_seulement"
                else:
                    classe_etape1 = "jamais_dans_le_vivier"

                band = pair_band_info(years_dict, pair, first_year)
                air_analyses.append({
                    "seed": seed,
                    "target_year": target_year,
                    "first_year_aaa": first_year,
                    "pair": list(pair),
                    "aaa_profit": float(line.get("profit_last_year", 0.0)),
                    "dist_towns": band["dist_towns"],
                    "airMin": band["airMin"],
                    "below_airmin": band["below_airmin"],
                    "classe_etape1": classe_etape1,
                    "best_stage_all_years": best_eval["stage"],
                    "best_stage_all_years_reason": best_eval["reason"],
                    "best_stage_all_years_detail": best_eval["detail"],
                    "best_stage_all_years_year": best_eval["year"],
                    "first_year_stage": eval_first["stage"],
                    "first_year_stage_reason": eval_first["reason"],
                    "first_year_stage_detail": eval_first["detail"],
                })

    # D.2 : Candidats OpexAI classes dans les 5 premiers au moins une annee, jamais construits
    for seed, years_dict in sorted(by_seed_year.items()):
        all_built_pairs = set()
        for y, snap in years_dict.items():
            for ol in (snap.get("companies", {}).get("0") or {}).get("lines", []):
                p = get_line_pair(ol)
                if p:
                    all_built_pairs.add((ol.get("mode"), p))

        # AAA top 20 lines sur les annees cibles
        aaa_top_pairs = set()
        for target_year in target_years:
            if target_year in years_dict:
                aaa_sorted = sorted((years_dict[target_year].get("companies", {}).get("1") or {}).get("lines", []),
                                    key=lambda l: float(l.get("profit_last_year", 0.0)), reverse=True)
                for l in aaa_sorted[:20]:
                    p = get_line_pair(l)
                    if p:
                        aaa_top_pairs.add((l.get("mode"), p))

        seen_top5 = set()
        for y in sorted(years_dict.keys()):
            snap = years_dict[y]
            for c in snap.get("candidates", []):
                mode = c.get("mode")
                pair = get_candidate_pair(c)
                rank = c.get("rank", -1)
                if 0 <= rank < 5 and (mode, pair) in aaa_top_pairs and (mode, pair) not in all_built_pairs:
                    key = (seed, mode, pair)
                    if key not in seen_top5:
                        seen_top5.add(key)
                        # Trouver tous les C78_BUILD pour cette paire
                        build_records = []
                        for by in sorted(years_dict.keys()):
                            for b in years_dict[by].get("builds", []):
                                if b.get("mode") == mode:
                                    bp = tuple(sorted([b.get("townA", -1), b.get("townB", -1)]))
                                    if bp == pair:
                                        build_records.append(b)

                        top5_unbuilt.append({
                            "seed": seed,
                            "mode": mode,
                            "pair": list(pair),
                            "best_rank_year": y,
                            "rank": rank,
                            "P": c.get("P", 0),
                            "C": c.get("C", 0),
                            "affordable": c.get("affordable", 0),
                            "build_attempts": build_records,
                            "status": "tenté" if build_records else "jamais_tenté",
                        })

    return air_analyses, top5_unbuilt


def analyse_rail_lines(snapshots, target_years=TARGET_YEARS):
    by_seed_year = defaultdict(dict)
    for row in snapshots:
        seed = row.get("seed")
        year = row.get("year")
        if seed is not None and year is not None:
            by_seed_year[seed][year] = row

    rail_analyses = []

    for seed, years_dict in sorted(by_seed_year.items()):
        for target_year in target_years:
            if target_year not in years_dict:
                continue
            snap = years_dict[target_year]
            aaa_lines = list((snap.get("companies", {}).get("1") or {}).get("lines", []))
            aaa_lines.sort(key=lambda l: float(l.get("profit_last_year", 0.0)), reverse=True)
            top20 = aaa_lines[:20]

            for line in top20:
                if line.get("mode") != "rail":
                    continue
                pair = get_line_pair(line)
                tiles = line.get("tiles") or []
                dist = get_tile_manhattan_distance(tiles[0], tiles[1]) if len(tiles) >= 2 else -1

                # Recherche dans les candidats C78_CAND sur toutes les annees <= target_year
                exact_cands = []
                shared_cands = []
                for y in sorted(years_dict.keys()):
                    if y <= target_year:
                        for c in years_dict[y].get("candidates", []):
                            if c.get("mode") == "rail":
                                cp = get_candidate_pair(c)
                                if cp == pair:
                                    exact_cands.append(c)
                                elif pair and cp and (pair[0] in cp or pair[1] in cp):
                                    shared_cands.append(c)

                best_exact = max(exact_cands, key=lambda c: c.get("P", 0)) if exact_cands else None
                best_shared = max(shared_cands, key=lambda c: c.get("P", 0)) if shared_cands else None

                rail_analyses.append({
                    "seed": seed,
                    "year": target_year,
                    "pair": list(pair),
                    "cargo": line.get("cargo", []),
                    "distance": dist,
                    "vehicles": line.get("vehicles", 0),
                    "profit": float(line.get("profit_last_year", 0.0)),
                    "has_exact_cand": best_exact is not None,
                    "exact_cand": best_exact,
                    "shared_cands_count": len(shared_cands),
                    "best_shared_cand": best_shared,
                })

    return rail_analyses


def build_summary(air_analyses, top5_unbuilt, rail_analyses):
    # Tableau de synthese des etapes bloquantes pour les lignes aeriennes
    def make_table(analyses, key_stage, key_reason):
        counts = {
            "jamais_dans_le_vivier": defaultdict(int),
            "vivier_annee_anterieure_seulement": defaultdict(int),
            "dans_le_vivier_meme_annee": defaultdict(int),
        }
        for a in analyses:
            cls = a["classe_etape1"]
            stage = a[key_stage]
            reason = a[key_reason]
            counts[cls][(stage, reason)] += 1
        return {
            cls: [{"stage": s, "reason": r, "count": cnt} for (s, r), cnt in sorted(c_dict.items(), key=lambda x: (STAGE_INDEX.get(x[0][0], -1), x[0][1]))]
            for cls, c_dict in counts.items()
        }

    table_all_years = make_table(air_analyses, "best_stage_all_years", "best_stage_all_years_reason")
    table_first_year = make_table(air_analyses, "first_year_stage", "first_year_stage_reason")

    # Bandes de distance : paires d'AAAHogEx plus courtes que la bascule rail/avion (airMin)
    band_table = defaultdict(lambda: {"below_airmin": 0, "above_airmin": 0, "unknown": 0})
    for a in air_analyses:
        key = "below_airmin" if a.get("below_airmin") is True else (
            "above_airmin" if a.get("below_airmin") is False else "unknown")
        band_table[a["classe_etape1"]][key] += 1
    dists = sorted(a["dist_towns"] for a in air_analyses if a.get("dist_towns") is not None)
    air_mins = sorted({a["airMin"] for a in air_analyses if a.get("airMin") is not None})

    return {
        "air_band_vs_airmin": {k: dict(v) for k, v in band_table.items()},
        "air_pair_distances": dists,
        "air_min_values": air_mins,
        "air_non_built_count": len(air_analyses),
        "air_stages_all_years": table_all_years,
        "air_stages_first_year": table_first_year,
        "air_details": air_analyses,
        "top5_unbuilt_candidates": top5_unbuilt,
        "rail_lines": rail_analyses,
    }


def print_report(summary):
    print("=" * 78)
    print(" C78 ETAPE 2 : POURQUOI LES MEILLEURES LIGNES D'AAAHOGEX NE SONT PAS CONSTRUITES")
    print("=" * 78)
    print()

    print("1. LIGNES AERIENNES NON CONSTRUITES PAR OPEXAI (TOP 20 AAAHOGEX, 1973 & 1975)")
    print(f"Total des lignes analysees : {summary['air_non_built_count']}")
    print()

    for title, table_key in [
        ("Meilleure etape atteinte (sur toutes les annees <= Y)", "air_stages_all_years"),
        ("Etape atteinte l'annee de premiere apparition chez AAAHogEx", "air_stages_first_year"),
    ]:
        print(f"--- {title} ---")
        for cls_name in ("jamais_dans_le_vivier", "vivier_annee_anterieure_seulement"):
            rows = summary[table_key].get(cls_name, [])
            tot = sum(r["count"] for r in rows)
            print(f"  Classe : {cls_name} ({tot} lignes)")
            if not rows:
                print("    (aucune ligne)")
            else:
                for r in rows:
                    print(f"    - {r['stage']:<18} | {r['reason']:<24} : {r['count']:>3} ligne(s)")
        print()

    print("--- Bandes de distance : paire d'AAAHogEx plus courte que airMin (bascule rail/avion) ? ---")
    print(f"  Valeurs de airMin observees : {summary.get('air_min_values')}")
    for cls_name, counts in sorted(summary.get("air_band_vs_airmin", {}).items()):
        print(f"  {cls_name:<36} : sous airMin {counts.get('below_airmin', 0):>3} | au-dessus {counts.get('above_airmin', 0):>3} | inconnu {counts.get('unknown', 0):>3}")
    d = summary.get("air_pair_distances") or []
    if d:
        print(f"  Distances des paires (centres de villes) : min {d[0]}, mediane {d[len(d) // 2]}, max {d[-1]}")
    print()

    # Echantillon de details pour hors_pool et villes ecartees
    print("--- Details des rejets de generation (annee de premiere apparition) ---")
    for d in summary["air_details"][:20]:
        print(f"  Graine {d['seed']} {d['first_year_aaa']} Paire {d['pair']} [AAA: £{int(d['aaa_profit'])}] :")
        print(f"    Etape: {d['first_year_stage']} | Raison: {d['first_year_stage_reason']} | Detail: {d['first_year_stage_detail']}")
    if len(summary["air_details"]) > 20:
        print(f"  ... ({len(summary['air_details']) - 20} lignes supplementaires)")
    print()

    print("2. CANDIDATS D'OPEXAI DANS LE TOP 5 NON CONSTRUITS")
    print(f"Total : {len(summary['top5_unbuilt_candidates'])}")
    for c in summary["top5_unbuilt_candidates"]:
        b_att = c["build_attempts"]
        print(f"  Graine {c['seed']} {c['mode']} {c['pair']} : Rang={c['rank']} en {c['best_rank_year']}, P={c['P']}, C={c['C']}, Fin={c['affordable']}, Statut={c['status']}")
        if b_att:
            for b in b_att:
                print(f"    -> Tentative C78_BUILD : annee={b.get('year')} rang={b.get('rank')} outcome={b.get('outcome')} reason={b.get('reason')}")
        else:
            print("    -> JAMAIS TENTÉ dans C78_BUILD (jamais passe au constructeur)")
    print()

    print("3. RAIL : TOP 20 AAAHOGEX ET CANDIDATS OPEXAI CORRESPONDANTS")
    print(f"Total lignes rail analysees : {len(summary['rail_lines'])}")
    for r in summary["rail_lines"]:
        cargos = ",".join(str(c) for c in r["cargo"]) if r["cargo"] else "-"
        print(f"  Graine {r['seed']} {r['year']} Paire {r['pair']} : Cargo=[{cargos}] Dist={r['distance']} Vehi={r['vehicles']} Profit=£{int(r['profit'])}")
        if r["has_exact_cand"]:
            ec = r["exact_cand"]
            print(f"    -> Candidat exact dans C78_CAND : P={ec.get('P')} C={ec.get('C')} Rang={ec.get('rank')}")
        else:
            print(f"    -> Aucun candidat exact dans C78_CAND (candidats avec ville commune : {r['shared_cands_count']})")
            if r["best_shared_cand"]:
                sc = r["best_shared_cand"]
                print(f"       Meilleur candidat commun : ({sc.get('townA')},{sc.get('townB')}) P={sc.get('P')} C={sc.get('C')} Rang={sc.get('rank')}")
    print("=" * 78)


def run_selftest():
    mock_snapshots = [
        {
            "seed": 7,
            "year": 1971,
            "date": "1971-12-31",
            "airpool": {
                "pool": 24,
                "towns": {
                    10: [0, 2500],
                    12: [1, 2000],
                    15: [2, 1800],
                    18: [25, 500],  # rank 25 >= pool 24 -> hors_pool
                    20: [3, 1600],
                    28: [4, 1500],
                },
            },
            "airtowns": [
                {"combo": "0:12", "town": 10, "rank": 0, "outcome": "site"},
                {"combo": "0:12", "town": 12, "rank": 1, "outcome": "site"},
                {"combo": "0:12", "town": 15, "rank": 2, "outcome": "origin_served"},
                {"combo": "0:12", "town": 20, "rank": 3, "outcome": "site"},
                {"combo": "0:12", "town": 28, "rank": 4, "outcome": "site"},
            ],
            "airpairs": [
                {"arm": "newpair", "combo": "0:12", "townA": 10, "townB": 20, "dist": 15, "outcome": "distance_short", "P": -1, "C": -1},
                {"arm": "newpair", "combo": "0:12", "townA": 12, "townB": 28, "dist": 40, "outcome": "admitted", "P": 80000, "C": 30000},
            ],
            "candidates": [
                {"mode": "air", "townA": 12, "townB": 28, "indA": -1, "indB": -1, "P": 80000, "C": 30000, "rank": 2, "affordable": 1},
                {"mode": "rail", "townA": 50, "townB": 60, "indA": 1, "indB": 2, "P": 45000, "C": 60000, "rank": -1, "affordable": 0},
            ],
            "builds": [
                {"mode": "air", "townA": 12, "townB": 28, "indA": -1, "indB": -1, "P": 80000, "C": 30000, "rank": 2, "outcome": "rejected", "reason": "AFAIL"},
            ],
            "companies": {
                "0": {"lines": []},
                "1": {
                    "lines": [
                        # Ligne 1 : (10, 15) -> ville_ecartee (origin_served sur 15)
                        {"mode": "air", "towns": [10, 15], "vehicles": 2, "profit_last_year": 120000.0, "airports": [], "airport_types": []},
                        # Ligne 2 : (10, 20) -> paire_ecartee (distance_short)
                        {"mode": "air", "towns": [10, 20], "vehicles": 2, "profit_last_year": 110000.0, "airports": [], "airport_types": []},
                        # Ligne 3 : (12, 18) -> hors_pool (18 a un rang 25 >= pool 24)
                        {"mode": "air", "towns": [12, 18], "vehicles": 3, "profit_last_year": 200000.0, "airports": [], "airport_types": []},
                        # Ligne 4 : (12, 28) -> tente (AFAIL)
                        {"mode": "air", "towns": [12, 28], "vehicles": 2, "profit_last_year": 95000.0, "airports": [], "airport_types": []},
                        # Ligne 5 Rail : (50, 60) -> candidat exact
                        {"mode": "rail", "towns": [50, 60], "vehicles": 4, "profit_last_year": 180000.0, "tiles": [1000, 1256], "cargo": [0]},
                    ]
                },
            },
        },
        {
            "seed": 7,
            "year": 1973,
            "date": "1973-12-31",
            "airpool": {
                "pool": 24,
                "towns": {
                    10: [0, 2500],
                    12: [1, 2000],
                    15: [2, 1800],
                    18: [25, 500],
                    20: [3, 1600],
                    28: [4, 1500],
                },
            },
            "airtowns": [],
            "airpairs": [],
            "candidates": [
                # Paire 12-18 au rang 0 en 1973
                {"mode": "air", "townA": 12, "townB": 18, "indA": -1, "indB": -1, "P": 79000, "C": 25000, "rank": 0, "affordable": 1},
            ],
            "builds": [],  # Jamais tente pour 12-18
            "companies": {
                "0": {"lines": []},
                "1": {
                    "lines": [
                        {"mode": "air", "towns": [10, 15], "vehicles": 2, "profit_last_year": 140000.0, "airports": [], "airport_types": []},
                        {"mode": "air", "towns": [10, 20], "vehicles": 2, "profit_last_year": 130000.0, "airports": [], "airport_types": []},
                        {"mode": "air", "towns": [12, 18], "vehicles": 4, "profit_last_year": 236000.0, "airports": [], "airport_types": []},
                        {"mode": "air", "towns": [12, 28], "vehicles": 3, "profit_last_year": 115000.0, "airports": [], "airport_types": []},
                        {"mode": "rail", "towns": [50, 60], "vehicles": 5, "profit_last_year": 210000.0, "tiles": [1000, 1256], "cargo": [0]},
                    ]
                },
            },
        },
    ]

    air_analyses, top5_unbuilt = analyse_air_lines(mock_snapshots, target_years=(1973,))
    assert len(air_analyses) == 4, f"Expected 4 air lines, got {len(air_analyses)}"

    by_pair = {tuple(a["pair"]): a for a in air_analyses}

    # Paire 10-15 en 1971 : ville_ecartee (origin_served)
    assert by_pair[(10, 15)]["first_year_stage"] == "ville_ecartee"
    assert by_pair[(10, 15)]["first_year_stage_reason"] == "origin_served"

    # Paire 10-20 en 1971 : paire_ecartee (distance_short)
    assert by_pair[(10, 20)]["first_year_stage"] == "paire_ecartee"
    assert by_pair[(10, 20)]["first_year_stage_reason"] == "distance_short"

    # Paire 12-18 : classe au rang 0 sur all_years (dans vivier en 1973), mais hors_pool en 1971
    assert by_pair[(12, 18)]["first_year_stage"] == "hors_pool"
    assert by_pair[(12, 18)]["best_stage_all_years"] == "classe"

    # Paire 12-28 : tente (AFAIL)
    assert by_pair[(12, 28)]["best_stage_all_years"] == "tente"
    assert by_pair[(12, 28)]["best_stage_all_years_reason"] == "AFAIL"

    # Top 5 non construits : paire 12-18 doit apparaitre comme jamais tente
    assert len(top5_unbuilt) >= 1, "Expected at least 1 top5 unbuilt candidate"
    p12_18 = next(c for c in top5_unbuilt if c["pair"] == [12, 18])
    assert p12_18["rank"] == 0
    assert p12_18["status"] == "jamais_tenté"

    # Rail analysis
    rail_analyses = analyse_rail_lines(mock_snapshots, target_years=(1973,))
    assert len(rail_analyses) == 1
    r = rail_analyses[0]
    assert r["pair"] == [50, 60]
    assert r["has_exact_cand"] is True
    assert r["cargo"] == [0]
    # Manhattan dist entre 1000 et 1256 : (1000 % 256 = 232, 1000 // 256 = 3), (1256 % 256 = 232, 1256 // 256 = 4) -> abs(232-232)+abs(3-4)=1
    assert r["distance"] == 1

    summary = build_summary(air_analyses, top5_unbuilt, rail_analyses)
    assert summary["air_non_built_count"] == 4
    print("analyse_c78_etape2 selftest passed: stages, reasons, top5 candidates and rail analysis verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input_file", type=Path, default=DEFAULT_IN,
                        help=f"Fichier d'entree produit par diag_c78_lines_vs_aaa.py (defaut: {DEFAULT_IN})")
    parser.add_argument("--years", nargs="+", type=int, default=list(TARGET_YEARS),
                        help=f"Annees a analyser (defaut: {list(TARGET_YEARS)})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Fichier JSON de sortie du resume (defaut: {DEFAULT_OUT})")
    parser.add_argument("--selftest", action="store_true",
                        help="Execute les tests internes")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if not args.input_file.exists():
        sys.exit(f"Erreur : fichier introuvable {args.input_file}. Executez d'abord diag_c78_lines_vs_aaa.py.")

    data = json.loads(args.input_file.read_text(encoding="utf-8"))
    air_analyses, top5_unbuilt = analyse_air_lines(data, target_years=tuple(args.years))
    rail_analyses = analyse_rail_lines(data, target_years=tuple(args.years))
    summary = build_summary(air_analyses, top5_unbuilt, rail_analyses)

    print_report(summary)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Rapport JSON enregistre : {args.out}")


if __name__ == "__main__":
    main()
