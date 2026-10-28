#!/usr/bin/env python3
"""Offline EB-2 / EB-6 arbitrage and causal diagnostic from C66 engine logs.

Usage:
    python3 sweeps/diag_eb2_arbitrage.py --manifest PATH/CAMPAIGN.manifest.json [--out ANALYSIS.json]

Provides rigorous causal answers to:
1. Actual cost vs selection quote (overrun & ROI re-evaluation).
2. Complete outcome of every fallback event & distinct OD (built, refused cash, A* cap/fail).
3. Line economic performance at comparable age (age=1, age=2) vs non-fallback lines.
4. Competing projects, immediate cash blocking, and concurrent substitution in Reference.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from statistics import mean, median
from typing import Any, Dict, List, Optional, Tuple


def to_days(d_str: str) -> int:
    parts = [int(x) for x in d_str.split("-")]
    return parts[0] * 365 + parts[1] * 30 + parts[2]


def parse_engine_logs(manifest_path: Path) -> Tuple[Dict[str, Any], List[Path], List[Path]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    options = manifest.get("execution", {}).get("options", {})
    seeds = options.get("seeds", [])

    engine_dir = manifest_path.parent / (manifest_path.stem.replace(".manifest", "") + "_engine")
    if not engine_dir.exists():
        engine_dir = manifest_path.with_name(manifest_path.name.replace(".manifest.json", "_engine"))

    if not engine_dir.exists():
        raise FileNotFoundError(f"Engine log directory not found: {engine_dir}")

    var_paths = []
    ref_paths = []
    for s in seeds:
        vp = engine_dir / f"eb2_new_station_seed{s}_r0.log"
        rp = engine_dir / f"reference_seed{s}_r0.log"
        if vp.exists():
            var_paths.append(vp)
        if rp.exists():
            ref_paths.append(rp)

    return manifest, var_paths, ref_paths


def analyze_arbitrage(manifest_path: Path) -> Dict[str, Any]:
    manifest, var_paths, ref_paths = parse_engine_logs(manifest_path)
    campaign_id = manifest.get("campaign_id", "unknown")

    # Map reference logs by seed
    ref_by_seed = {}
    for rp in ref_paths:
        m = re.search(r"seed(\d+)_", rp.name)
        if m:
            ref_by_seed[m.group(1)] = rp.read_text(encoding="utf-8", errors="replace").splitlines()

    total_fallbacks = 0
    distinct_ods: Dict[Tuple[str, int, int], List[Dict[str, Any]]] = defaultdict(list)
    var_builds: Dict[Tuple[str, int], Dict[str, Any]] = {}
    var_builds_by_od: Dict[Tuple[str, int, int], List[Dict[str, Any]]] = defaultdict(list)
    line_is_fallback: Dict[Tuple[str, int], bool] = {}
    line_delays: Dict[Tuple[str, int], Dict[str, Any]] = {}
    line_rev_age1: Dict[Tuple[str, int], Dict[str, Any]] = {}
    line_rev_age2: Dict[Tuple[str, int], Dict[str, Any]] = {}

    cases = []
    unbuilt_cases = []

    # Process all variant logs
    for vp in var_paths:
        seed = re.search(r"seed(\d+)_", vp.name).group(1)
        lines = vp.read_text(encoding="utf-8", errors="replace").splitlines()

        # Index reference builds for this seed: (days, date_str, (src, dst), cost, cargo)
        ref_lines = ref_by_seed.get(seed, [])
        ref_builds = []
        for l in ref_lines:
            if "RAIL_BUILD" in l:
                m = re.search(r"OPEX (\d+-\d+-\d+).*src=(\d+) dst=(\d+) cargo=(\w+).*cost=(\d+)", l)
                if m:
                    ref_builds.append((
                        to_days(m.group(1)),
                        m.group(1),
                        (int(m.group(2)), int(m.group(3))),
                        int(m.group(5)),
                        m.group(4)
                    ))

        # 1. Index all builds in variant
        for idx, l in enumerate(lines):
            if "RAIL_BUILD " in l:
                m = re.search(r"OPEX (\d+-\d+-\d+).*line=(\d+) src=(\d+) dst=(\d+) cargo=(\w+).*cost=(\d+)", l)
                if m:
                    lid = int(m.group(2))
                    src = int(m.group(3))
                    dst = int(m.group(4))
                    binfo = {
                        "seed": seed,
                        "line": lid,
                        "date": m.group(1),
                        "days": to_days(m.group(1)),
                        "src": src,
                        "dst": dst,
                        "cargo": m.group(5),
                        "cost": int(m.group(6)),
                        "idx": idx,
                    }
                    var_builds[(seed, lid)] = binfo
                    var_builds_by_od[(seed, src, dst)].append(binfo)
            elif "RAIL_COMMISSION" in l:
                m = re.search(r"line=(\d+).*delay_days=(\d+).*search_to_service_days=(\d+)", l)
                if m:
                    line_delays[(seed, int(m.group(1)))] = {
                        "delay_days": int(m.group(2)),
                        "search_to_service_days": int(m.group(3))
                    }
            elif "LINE_REVENUE" in l:
                m = re.search(r"line=(\d+).*age=(\d+).*real_rev=(\d+).*real_prof=(-?\d+)", l)
                if m:
                    lid = int(m.group(1))
                    age = int(m.group(2))
                    item = {
                        "seed": seed,
                        "line": lid,
                        "real_rev": int(m.group(3)),
                        "real_prof": int(m.group(4))
                    }
                    if age == 1:
                        line_rev_age1[(seed, lid)] = item
                    elif age == 2:
                        line_rev_age2[(seed, lid)] = item

        # 2. Track quotes and fallbacks
        chosen_map = {}
        for idx, l in enumerate(lines):
            if "PROJECT_CHOSEN" in l:
                m = re.search(r"src=(\d+) dst=(\d+).*cost=(\d+) profit=(\d+) roi=(\d+)", l)
                if m:
                    chosen_map[(int(m.group(1)), int(m.group(2)))] = {
                        "quote": int(m.group(3)),
                        "profit": int(m.group(4)),
                        "roi": int(m.group(5)),
                        "idx": idx,
                    }
            elif "EB2_FALLBACK" in l:
                m = re.search(r"OPEX (\d+-\d+-\d+).*src=(\d+) dst=(\d+)", l)
                if m:
                    total_fallbacks += 1
                    date_str = m.group(1)
                    src = int(m.group(2))
                    dst = int(m.group(3))
                    key = (seed, src, dst)
                    distinct_ods[key].append({
                        "date": date_str,
                        "days": to_days(date_str),
                        "idx": idx
                    })

    # Mark lines that correspond to fallback ODs
    for (seed, src, dst), fb_list in distinct_ods.items():
        if (seed, src, dst) in var_builds_by_od:
            for b in var_builds_by_od[(seed, src, dst)]:
                line_is_fallback[(seed, b["line"])] = True

    # 3. Analyze each built fallback (Case analysis)
    for (seed, src, dst), fb_list in distinct_ods.items():
        first_fb = fb_list[0]
        fb_idx = first_fb["idx"]
        date_str = first_fb["date"]
        v_days = first_fb["days"]

        # Was it built?
        built_matches = var_builds_by_od.get((seed, src, dst), [])
        if built_matches:
            b = built_matches[0]
            lid = b["line"]
            actual_cost = b["cost"]
            cargo = b["cargo"]

            # Look backwards for quote
            quote = None
            pred_prof = None
            pred_roi = None
            lines = [l for l in (var_paths[0].parent / f"eb2_new_station_seed{seed}_r0.log").read_text(encoding="utf-8", errors="replace").splitlines()]
            for b_idx in range(max(0, fb_idx - 50), fb_idx):
                if f"PROJECT_CHOSEN" in lines[b_idx] and f"src={src} dst={dst}" in lines[b_idx]:
                    mq = re.search(r"cost=(\d+).*profit=(\d+).*roi=(\d+)", lines[b_idx])
                    if mq:
                        quote = int(mq.group(1))
                        pred_prof = int(mq.group(2))
                        pred_roi = int(mq.group(3))
                        break

            # Check next cash block
            cap_after = None
            blocked_next = None
            blocked_mode = None
            for j in range(b["idx"] + 1, min(b["idx"] + 40, len(lines))):
                la = lines[j]
                if "capital_after=" in la and cap_after is None:
                    mc = re.search(r"capital_after=(\d+)", la)
                    if mc:
                        cap_after = int(mc.group(1))
                if "reason=cash" in la and "finance=" in la:
                    mb = re.search(r"next_mode=(\w+).*finance=(\d+)", la)
                    if mb:
                        blocked_mode = mb.group(1)
                        blocked_next = int(mb.group(2))
                    break

            # Check reference concurrent build within 60 days
            ref_lines = ref_by_seed.get(seed, [])
            ref_builds = []
            for l in ref_lines:
                if "RAIL_BUILD" in l:
                    m = re.search(r"OPEX (\d+-\d+-\d+).*src=(\d+) dst=(\d+) cargo=(\w+).*cost=(\d+)", l)
                    if m:
                        ref_builds.append((
                            to_days(m.group(1)),
                            m.group(1),
                            (int(m.group(2)), int(m.group(3))),
                            int(m.group(5)),
                            m.group(4)
                        ))
            next_ref = [rb for rb in ref_builds if 0 <= (rb[0] - v_days) <= 60 and rb[2] != (src, dst)]
            ref_match = None
            if next_ref:
                rb = next_ref[0]
                ref_match = {
                    "date": rb[1],
                    "od": list(rb[2]),
                    "cost": rb[3],
                    "cargo": rb[4],
                    "delay_days": rb[0] - v_days,
                }

            overrun = (actual_cost - quote) if quote is not None else None
            overrun_pct = ((actual_cost - quote) / quote * 100.0) if quote else None
            actual_roi = int(pred_prof / actual_cost * 1000) if (pred_prof and actual_cost) else None

            cases.append({
                "seed": seed,
                "line": lid,
                "date": date_str,
                "src": src,
                "dst": dst,
                "cargo": cargo,
                "quote": quote,
                "actual_cost": actual_cost,
                "overrun": overrun,
                "overrun_pct": overrun_pct,
                "predicted_profit": pred_prof,
                "predicted_roi": pred_roi,
                "actual_roi": actual_roi,
                "capital_after": cap_after,
                "blocked_next_finance": blocked_next,
                "blocked_next_mode": blocked_mode,
                "reference_concurrent_build": ref_match,
            })
        else:
            # Unbuilt fallback analysis
            last_fb = fb_list[-1]
            last_idx = last_fb["idx"]
            lines = [l for l in (var_paths[0].parent / f"eb2_new_station_seed{seed}_r0.log").read_text(encoding="utf-8", errors="replace").splitlines()]

            search_res = "in_progress_at_end"
            search_iters = 0
            discard_reason = None
            refused_cash = False
            abandoned = False

            for j in range(last_idx + 1, min(len(lines), last_idx + 6000)):
                l = lines[j]
                if f"src={src} dst={dst}" in l:
                    if "RAIL_SEARCH_END" in l:
                        m_res = re.search(r"outcome=(\w+).*result=(\w+).*iters=(\d+)", l)
                        if m_res:
                            search_res = f"{m_res.group(1)}_{m_res.group(2)}"
                            search_iters = int(m_res.group(3))
                    elif "phase=refused_cash" in l or "reason=cash_at_build" in l or "insufficient_cash" in l:
                        refused_cash = True
                    elif "PROJECT_DISCARD" in l:
                        m_dis = re.search(r"reason=([\w_]+)", l)
                        if m_dis:
                            r = m_dis.group(1)
                            if "cash" in r:
                                refused_cash = True
                            elif "search_in_progress" not in r:
                                discard_reason = r
                    elif "ABANDON_PAIR" in l:
                        abandoned = True
                elif "C50_CHRONO phase=refused_cash" in l and search_res.startswith("OK"):
                    refused_cash = True
                    break
                elif "C56_TASK TASK_ENTER name=projects" in l and search_res != "in_progress_at_end" and (refused_cash or abandoned or discard_reason):
                    break

            cat = "other"
            if refused_cash:
                cat = "refused_cash"
            elif "ABND" in search_res or abandoned:
                cat = "astar_abandon_cap"
            elif discard_reason in ["TRKFAIL", "STNFAIL", "SITEB", "SITEA", "NOPA"]:
                cat = f"astar_{discard_reason}"
            elif search_res == "in_progress_at_end" or "1974-1" in last_fb["date"]:
                cat = "horizon_cutoff"
            else:
                cat = f"search_{search_res}"

            unbuilt_cases.append({
                "seed": seed,
                "src": src,
                "dst": dst,
                "attempts_count": len(fb_list),
                "last_date": last_fb["date"],
                "category": cat,
                "search_result": search_res,
                "search_iters": search_iters,
                "refused_cash": refused_cash,
                "discard_reason": discard_reason
            })

    # 4. Summary statistics on Quote vs Actual Overrun
    valid_quotes = [c for c in cases if c["quote"] is not None]
    overruns = [c["overrun"] for c in valid_quotes]
    overrun_pcts = [c["overrun_pct"] for c in valid_quotes]
    actuals = [c["actual_cost"] for c in cases]
    quotes = [c["quote"] for c in valid_quotes]
    pred_rois = [c["predicted_roi"] for c in valid_quotes if c["predicted_roi"] is not None]
    act_rois = [c["actual_roi"] for c in valid_quotes if c["actual_roi"] is not None]
    cash_blocks = [c for c in cases if c["blocked_next_finance"] is not None]
    ref_substs = [c for c in cases if c["reference_concurrent_build"] is not None]

    # 5. Comparable Age Performance (Age 1 & Age 2)
    fb_age1 = []
    non_fb_age1 = []
    for (seed, lid), rev in line_rev_age1.items():
        cost = var_builds.get((seed, lid), {}).get("cost")
        if cost and cost > 0:
            item = {
                "seed": seed,
                "line": lid,
                "cost": cost,
                "prof": rev["real_prof"],
                "rev": rev["real_rev"],
                "roi_pct": rev["real_prof"] / cost * 100.0
            }
            if line_is_fallback.get((seed, lid), False):
                fb_age1.append(item)
            else:
                non_fb_age1.append(item)

    fb_age2 = []
    non_fb_age2 = []
    for (seed, lid), rev in line_rev_age2.items():
        cost = var_builds.get((seed, lid), {}).get("cost")
        if cost and cost > 0:
            item = {
                "seed": seed,
                "line": lid,
                "cost": cost,
                "prof": rev["real_prof"],
                "rev": rev["real_rev"],
                "roi_pct": rev["real_prof"] / cost * 100.0
            }
            if line_is_fallback.get((seed, lid), False):
                fb_age2.append(item)
            else:
                non_fb_age2.append(item)

    # Delays
    fb_del = [line_delays[k] for k in line_delays if line_is_fallback.get(k, False)]
    non_fb_del = [line_delays[k] for k in line_delays if not line_is_fallback.get(k, False)]

    # Build year distribution of fallback lines
    fb_years = Counter(int(c["date"].split("-")[0]) for c in cases)

    unbuilt_cat_counts = Counter(u["category"] for u in unbuilt_cases)

    summary = {
        "campaign_id": campaign_id,
        "seeds_count": len(var_paths),
        "total_fallbacks_triggered": total_fallbacks,
        "total_fallback_events": total_fallbacks,
        "total_fallbacks_built": len(cases),
        "distinct_fallback_ods": len(distinct_ods),
        "distinct_fallback_built": len(cases),
        "distinct_fallback_built_pct": (len(cases) / len(distinct_ods) * 100.0) if distinct_ods else 0.0,
        "distinct_fallback_unbuilt": len(unbuilt_cases),
        "distinct_fallback_unbuilt_pct": (len(unbuilt_cases) / len(distinct_ods) * 100.0) if distinct_ods else 0.0,
        "unbuilt_breakdown": dict(unbuilt_cat_counts),
        "build_year_distribution": dict(fb_years),
        "quote_selection_mean": mean(quotes) if quotes else 0.0,
        "quote_selection_median": median(quotes) if quotes else 0.0,
        "actual_cost_mean": mean(actuals) if actuals else 0.0,
        "actual_cost_median": median(actuals) if actuals else 0.0,
        "overrun_mean": mean(overruns) if overruns else 0.0,
        "overrun_median": median(overruns) if overruns else 0.0,
        "overrun_pct_mean": mean(overrun_pcts) if overrun_pcts else 0.0,
        "overrun_count_positive": sum(1 for d in overruns if d > 0),
        "overrun_rate_pct": (sum(1 for d in overruns if d > 0) / len(valid_quotes) * 100.0) if valid_quotes else 0.0,
        "predicted_roi_mean": mean(pred_rois) if pred_rois else 0.0,
        "actual_roi_mean": mean(act_rois) if act_rois else 0.0,
        "immediate_cash_block_count": len(cash_blocks),
        "immediate_cash_block_pct": (len(cash_blocks) / len(cases) * 100.0) if cases else 0.0,
        "reference_concurrent_build_count": len(ref_substs),
        "reference_concurrent_build_pct": (len(ref_substs) / len(cases) * 100.0) if cases else 0.0,
        "reference_concurrent_delay_mean_days": mean(c["reference_concurrent_build"]["delay_days"] for c in ref_substs) if ref_substs else 0.0,
        "reference_concurrent_cost_mean": mean(c["reference_concurrent_build"]["cost"] for c in ref_substs) if ref_substs else 0.0,
        "performance_age1": {
            "fallback": {
                "count": len(fb_age1),
                "cost_mean": mean(x["cost"] for x in fb_age1) if fb_age1 else 0.0,
                "cost_median": median(x["cost"] for x in fb_age1) if fb_age1 else 0.0,
                "profit_mean": mean(x["prof"] for x in fb_age1) if fb_age1 else 0.0,
                "profit_median": median(x["prof"] for x in fb_age1) if fb_age1 else 0.0,
                "return_mean_pct": mean(x["roi_pct"] for x in fb_age1) if fb_age1 else 0.0,
                "return_median_pct": median(x["roi_pct"] for x in fb_age1) if fb_age1 else 0.0,
            },
            "non_fallback": {
                "count": len(non_fb_age1),
                "cost_mean": mean(x["cost"] for x in non_fb_age1) if non_fb_age1 else 0.0,
                "cost_median": median(x["cost"] for x in non_fb_age1) if non_fb_age1 else 0.0,
                "profit_mean": mean(x["prof"] for x in non_fb_age1) if non_fb_age1 else 0.0,
                "profit_median": median(x["prof"] for x in non_fb_age1) if non_fb_age1 else 0.0,
                "return_mean_pct": mean(x["roi_pct"] for x in non_fb_age1) if non_fb_age1 else 0.0,
                "return_median_pct": median(x["roi_pct"] for x in non_fb_age1) if non_fb_age1 else 0.0,
            }
        },
        "performance_age2": {
            "fallback": {
                "count": len(fb_age2),
                "cost_mean": mean(x["cost"] for x in fb_age2) if fb_age2 else 0.0,
                "cost_median": median(x["cost"] for x in fb_age2) if fb_age2 else 0.0,
                "profit_mean": mean(x["prof"] for x in fb_age2) if fb_age2 else 0.0,
                "profit_median": median(x["prof"] for x in fb_age2) if fb_age2 else 0.0,
                "return_mean_pct": mean(x["roi_pct"] for x in fb_age2) if fb_age2 else 0.0,
                "return_median_pct": median(x["roi_pct"] for x in fb_age2) if fb_age2 else 0.0,
            },
            "non_fallback": {
                "count": len(non_fb_age2),
                "cost_mean": mean(x["cost"] for x in non_fb_age2) if non_fb_age2 else 0.0,
                "cost_median": median(x["cost"] for x in non_fb_age2) if non_fb_age2 else 0.0,
                "profit_mean": mean(x["prof"] for x in non_fb_age2) if non_fb_age2 else 0.0,
                "profit_median": median(x["prof"] for x in non_fb_age2) if non_fb_age2 else 0.0,
                "return_mean_pct": mean(x["roi_pct"] for x in non_fb_age2) if non_fb_age2 else 0.0,
                "return_median_pct": median(x["roi_pct"] for x in non_fb_age2) if non_fb_age2 else 0.0,
            }
        },
        "commission_delays": {
            "fallback": {
                "count": len(fb_del),
                "delay_days_mean": mean(x["delay_days"] for x in fb_del) if fb_del else 0.0,
                "delay_days_median": median(x["delay_days"] for x in fb_del) if fb_del else 0.0,
                "search_to_service_mean": mean(x["search_to_service_days"] for x in fb_del) if fb_del else 0.0,
                "search_to_service_median": median(x["search_to_service_days"] for x in fb_del) if fb_del else 0.0,
            },
            "non_fallback": {
                "count": len(non_fb_del),
                "delay_days_mean": mean(x["delay_days"] for x in non_fb_del) if non_fb_del else 0.0,
                "delay_days_median": median(x["delay_days"] for x in non_fb_del) if non_fb_del else 0.0,
                "search_to_service_mean": mean(x["search_to_service_days"] for x in non_fb_del) if non_fb_del else 0.0,
                "search_to_service_median": median(x["search_to_service_days"] for x in non_fb_del) if non_fb_del else 0.0,
            }
        }
    }

    return {
        "summary": summary,
        "built_cases": cases,
        "unbuilt_cases": unbuilt_cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="Path to campaign manifest JSON")
    parser.add_argument("--out", type=Path, help="Output path for JSON report")
    args = parser.parse_args()

    result = analyze_arbitrage(args.manifest)
    s = result["summary"]

    print("=== EB-2 / EB-6 DIAGNOSTIC DE L'ARBITRAGE ET DES SURCOÛTS ===")
    print(f"Campagne : {s['campaign_id']} ({s['seeds_count']} graines)")
    print(f"\n1. DÉCOMPTE ET ISSUE DES REPLIS :")
    print(f"  Occurrences totales d'EB2_FALLBACK : {s['total_fallback_events']}")
    print(f"  Paires OD distinctes concernées :    {s['distinct_fallback_ods']}")
    print(f"  - Paires construites :               {s['distinct_fallback_built']} ({s['distinct_fallback_built_pct']:.1f}%)")
    print(f"  - Paires jamais construites :        {s['distinct_fallback_unbuilt']} ({s['distinct_fallback_unbuilt_pct']:.1f}%)")
    print(f"  Détail des {s['distinct_fallback_unbuilt']} paires non construites :")
    for cat, cnt in sorted(s["unbuilt_breakdown"].items(), key=lambda x: -x[1]):
        print(f"    * {cat:20s}: {cnt}")
    print(f"  Répartition par année de construction des replis :")
    for yr, cnt in sorted(s["build_year_distribution"].items()):
        print(f"    * {yr} : {cnt} lignes")

    print(f"\n2. BIAIS DU DEVIS DE SÉLECTION (QUOTING OVERRUN) :")
    print(f"  Devis initial moyen de sélection :  {s['quote_selection_mean']:.0f} £ (médiane {s['quote_selection_median']:.0f} £)")
    print(f"  Coût réel débité moyen :            {s['actual_cost_mean']:.0f} £ (médiane {s['actual_cost_median']:.0f} £)")
    print(f"  Surcoût moyen (réel - devis) :       {s['overrun_mean']:+.0f} £ ({s['overrun_pct_mean']:+.1f}%)")
    print(f"  Taux de replis en dépassement :     {s['overrun_count_positive']} / {s['distinct_fallback_built']} ({s['overrun_rate_pct']:.1f}%)")
    print(f"  ROI projeté vs ROI réel moyen :     {s['predicted_roi_mean']:.0f} -> {s['actual_roi_mean']:.0f} (chute de {((s['actual_roi_mean']-s['predicted_roi_mean'])/s['predicted_roi_mean']*100):+.1f}%)")

    a1 = s["performance_age1"]
    print(f"\n3. PERFORMANCE ÉCONOMIQUE À ÂGE COMPARABLE :")
    print(f"  -- À ÂGE = 1 (première année civile pleine d'exploitation) :")
    print(f"     Lignes replis ({a1['fallback']['count']} lignes) :")
    print(f"       Capital engagé moyen : {a1['fallback']['cost_mean']:.0f} £ (médiane {a1['fallback']['cost_median']:.0f} £)")
    print(f"       Profit annuel moyen :  {a1['fallback']['profit_mean']:.0f} £ (médiane {a1['fallback']['profit_median']:.0f} £)")
    print(f"       Rendement moyen :      {a1['fallback']['return_mean_pct']:.1f}% (médiane {a1['fallback']['return_median_pct']:.1f}%)")
    print(f"     Lignes ordinaires ({a1['non_fallback']['count']} lignes) :")
    print(f"       Capital engagé moyen : {a1['non_fallback']['cost_mean']:.0f} £ (médiane {a1['non_fallback']['cost_median']:.0f} £)")
    print(f"       Profit annuel moyen :  {a1['non_fallback']['profit_mean']:.0f} £ (médiane {a1['non_fallback']['profit_median']:.0f} £)")
    print(f"       Rendement moyen :      {a1['non_fallback']['return_mean_pct']:.1f}% (médiane {a1['non_fallback']['return_median_pct']:.1f}%)")

    a2 = s["performance_age2"]
    print(f"  -- À ÂGE = 2 (deuxième année civile pleine d'exploitation) :")
    print(f"     Lignes replis ({a2['fallback']['count']} lignes) :")
    print(f"       Capital engagé moyen : {a2['fallback']['cost_mean']:.0f} £ (médiane {a2['fallback']['cost_median']:.0f} £)")
    print(f"       Profit annuel moyen :  {a2['fallback']['profit_mean']:.0f} £ (médiane {a2['fallback']['profit_median']:.0f} £)")
    print(f"       Rendement moyen :      {a2['fallback']['return_mean_pct']:.1f}% (médiane {a2['fallback']['return_median_pct']:.1f}%)")
    print(f"     Lignes ordinaires ({a2['non_fallback']['count']} lignes) :")
    print(f"       Capital engagé moyen : {a2['non_fallback']['cost_mean']:.0f} £ (médiane {a2['non_fallback']['cost_median']:.0f} £)")
    print(f"       Profit annuel moyen :  {a2['non_fallback']['profit_mean']:.0f} £ (médiane {a2['non_fallback']['profit_median']:.0f} £)")
    print(f"       Rendement moyen :      {a2['non_fallback']['return_mean_pct']:.1f}% (médiane {a2['non_fallback']['return_median_pct']:.1f}%)")

    delays = s["commission_delays"]
    print(f"  -- DÉLAIS DE MISE EN SERVICE :")
    print(f"     Lignes replis :    délai total moyen {delays['fallback']['delay_days_mean']:.1f} j (recherche->service: {delays['fallback']['search_to_service_mean']:.1f} j)")
    print(f"     Lignes ordinaires : délai total moyen {delays['non_fallback']['delay_days_mean']:.1f} j (recherche->service: {delays['non_fallback']['search_to_service_mean']:.1f} j)")

    print(f"\n4. ÉVICTION ET SUBSTITUTION CAUSALE :")
    print(f"  Arrêts de caisse immédiats (projet suivant bloqué) : {s['immediate_cash_block_count']} ({s['immediate_cash_block_pct']:.1f}%)")
    print(f"  Constructions concurrentes en Référence (<60j) :     {s['reference_concurrent_build_count']} ({s['reference_concurrent_build_pct']:.1f}%)")
    if s["reference_concurrent_build_count"]:
        print(f"  - Délai moyen du projet concurrent en Référence :   {s['reference_concurrent_delay_mean_days']:.1f} jours")
        print(f"  - Coût moyen du projet concurrent en Référence :    {s['reference_concurrent_cost_mean']:.0f} £")

    if args.out:
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nRapport détaillé écrit dans : {args.out}")


if __name__ == "__main__":
    main()
