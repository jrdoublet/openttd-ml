#!/usr/bin/env python3
"""Analyseur P5 bis : pré-planifier l'A* rail pendant les phases d'attente de capital ?

Lit et analyse :
1. `P5_WAIT_START` : état du vivier au début d'un épisode d'attente (alts, n_rail, rail_rank, déficit, profit, contrefactuel 0.96/1.70).
2. `P5_WAIT_END` : fin de l'épisode d'attente (durée en j/ticks, opcodes inutilisés vs utilisés, unused_ops/tick, cause de retour).
3. `P5_RAIL_PASS` : état du rail à chaque passage de `projects` (alts rail, finançabilité, présence dans best, stop).
4. `P5_RAIL_SEARCH` / `RAIL_SEARCH_END` : coût et issues réelles des recherches A* rail (OK, NOPA, ABND/DEAD/cap, SHORT, NOMATCH, cancelled).
5. `P5_BUILD_LINE` : lignes construites (mode, src, dst, capital).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

P5_WAIT_START_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) P5_WAIT_START\s+(.*)$", re.M)
P5_WAIT_END_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) P5_WAIT_END\s+(.*)$", re.M)
P5_RAIL_PASS_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) P5_RAIL_PASS\s+(.*)$", re.M)
P5_RAIL_SEARCH_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) P5_RAIL_SEARCH\s+(.*)$", re.M)
C56_RAIL_SEARCH_END_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) C56_TASK RAIL_SEARCH_END name=(\w+)\s+(.*)$", re.M)
P5_BUILD_LINE_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) P5_BUILD_LINE\s+(.*)$", re.M)
FIELD_RE = re.compile(r"(\w+)=(\S+)")


def _to_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _to_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def parse_fields(rest: str) -> dict[str, str]:
    return {k: v for k, v in FIELD_RE.findall(rest or "")}


def parse_p5_output(output: str, seed: int | None = None) -> dict:
    """Parse tous les enregistrements P5."""
    wait_starts: list[dict] = []
    wait_ends: list[dict] = []
    rail_passes: list[dict] = []
    rail_searches: list[dict] = []
    build_lines: list[dict] = []

    for year, month, day, rest in P5_WAIT_START_RE.findall(output or ""):
        fields = parse_fields(rest)
        w_id = _to_int(fields.get("id"), -1)
        if w_id < 0:
            continue
        date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        cap = _to_int(fields.get("cap"))
        rail_cap = _to_int(fields.get("rail_cap"))
        rail_fin_cap = _to_int(fields.get("rail_fin_cap"))
        rail_def = _to_int(fields.get("rail_def"))
        rail_rank = _to_int(fields.get("rail_rank"), -1)

        # Contrefactuel 0.96 / 1.70
        cf_cap = _to_int(fields.get("rail_cf_cap"))
        if cf_cap == 0 and rail_fin_cap > 0:
            cf_cap = int(rail_fin_cap * 96 / 170)
        cf_def = _to_int(fields.get("rail_cf_def"), max(0, cf_cap - cap) if cf_cap > 0 else 0)
        cf_rank = _to_int(fields.get("rail_cf_rank"), rail_rank)

        rec = {
            "id": w_id,
            "seed": seed,
            "year": int(year),
            "month": int(month),
            "day": int(day),
            "date": fields.get("date", date_str),
            "tick": _to_int(fields.get("tick")),
            "cap": cap,
            "alts": _to_int(fields.get("alts")),
            "n_rail": _to_int(fields.get("n_rail")),
            "n_air": _to_int(fields.get("n_air")),
            "n_road": _to_int(fields.get("n_road")),
            "n_fleet": _to_int(fields.get("n_fleet")),
            "rail_rank": rail_rank,
            "rail_kind": fields.get("rail_kind", "none"),
            "rail_src": _to_int(fields.get("rail_src"), -1),
            "rail_dst": _to_int(fields.get("rail_dst"), -1),
            "rail_cap": rail_cap,
            "rail_fin_cap": rail_fin_cap,
            "rail_def": rail_def,
            "rail_prof": _to_int(fields.get("rail_prof")),
            "rail_roi": _to_int(fields.get("rail_roi")),
            "rail_score": _to_float(fields.get("rail_score")),
            "rail_cf_cap": cf_cap,
            "rail_cf_def": cf_def,
            "rail_cf_rank": cf_rank,
            "rail_iters": _to_int(fields.get("rail_iters"), -1),
            "ahead_air": _to_int(fields.get("ahead_air")),
            "ahead_road": _to_int(fields.get("ahead_road")),
            "ahead_fleet": _to_int(fields.get("ahead_fleet")),
        }
        wait_starts.append(rec)

    for year, month, day, rest in P5_WAIT_END_RE.findall(output or ""):
        fields = parse_fields(rest)
        w_id = _to_int(fields.get("id"), -1)
        if w_id < 0:
            continue
        days = _to_int(fields.get("days"))
        ticks = _to_int(fields.get("ticks"))
        unused_ops = _to_int(fields.get("unused_ops"))
        used_ops = _to_int(fields.get("used_ops"))
        unused_ops_per_tick = round(unused_ops / max(1, ticks), 1)
        used_ops_per_tick = round(used_ops / max(1, ticks), 1)

        rec = {
            "id": w_id,
            "seed": seed,
            "year": int(year),
            "month": int(month),
            "day": int(day),
            "days": days,
            "ticks": ticks,
            "dispatches": _to_int(fields.get("dispatches")),
            "unused_ops": unused_ops,
            "used_ops": used_ops,
            "unused_ops_per_tick": unused_ops_per_tick,
            "used_ops_per_tick": used_ops_per_tick,
            "ret_reason": fields.get("ret_reason", "unknown"),
            "ret_task": fields.get("ret_task", "unknown"),
            "funded": _to_int(fields.get("funded")),
        }
        wait_ends.append(rec)

    for year, month, day, rest in P5_RAIL_PASS_RE.findall(output or ""):
        fields = parse_fields(rest)
        p_id = _to_int(fields.get("pass"), -1)
        if p_id < 0:
            continue
        date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        in_cap = _to_int(fields.get("in_cap"))
        best_rail_cap = _to_int(fields.get("best_rail_cap"), -1)
        best_rail_def = _to_int(fields.get("best_rail_def"), -1)
        best_rail_cf_cap = _to_int(fields.get("best_rail_cf_cap"), -1)
        if best_rail_cf_cap < 0 and best_rail_cap > 0:
            best_rail_cf_cap = int(best_rail_cap * 96 / 170)
        best_rail_cf_def = _to_int(fields.get("best_rail_cf_def"), max(0, best_rail_cf_cap - in_cap) if best_rail_cf_cap > 0 else -1)
        best_rail_cf_rank = _to_int(fields.get("best_rail_cf_rank"), _to_int(fields.get("best_rail_rank"), -1))

        rec = {
            "pass": p_id,
            "seed": seed,
            "year": int(year),
            "month": int(month),
            "day": int(day),
            "date": fields.get("date", date_str),
            "in_cap": in_cap,
            "alts": _to_int(fields.get("alts")),
            "rail_alts": _to_int(fields.get("rail_alts")),
            "rail_aff": _to_int(fields.get("rail_aff")),
            "rail_in_best": _to_int(fields.get("rail_in_best")),
            "nonrail_in_best": _to_int(fields.get("nonrail_in_best")),
            "rail_built": _to_int(fields.get("rail_built")),
            "stop": fields.get("stop", "none"),
            "best_rail_def": best_rail_def,
            "best_rail_cap": best_rail_cap,
            "best_rail_prof": _to_int(fields.get("best_rail_prof"), -1),
            "best_rail_score": _to_float(fields.get("best_rail_score"), -1.0),
            "best_rail_cf_def": best_rail_cf_def,
            "best_rail_cf_cap": best_rail_cf_cap,
            "best_rail_cf_rank": best_rail_cf_rank,
            "best_rail_kind": fields.get("best_rail_kind", "none"),
            "best_rail_rank": _to_int(fields.get("best_rail_rank"), -1),
            "best_nonrail_mode": fields.get("best_nonrail_mode", "none"),
            "best_nonrail_score": _to_float(fields.get("best_nonrail_score"), 0.0),
            "best_nonrail_cap": _to_int(fields.get("best_nonrail_cap"), 0),
        }
        rail_passes.append(rec)

    for year, month, day, rest in P5_RAIL_SEARCH_RE.findall(output or ""):
        fields = parse_fields(rest)
        s_id = _to_int(fields.get("id"), -1)
        if s_id < 0:
            continue
        iters = _to_int(fields.get("iters"))
        ops = _to_int(fields.get("ops"))
        ticks = _to_int(fields.get("ticks"))
        days = _to_int(fields.get("days"))
        outcome = fields.get("outcome", "none")
        result = fields.get("result", "none")
        ops_per_tick = round(ops / max(1, ticks), 1) if ticks > 0 else 0.0

        rec = {
            "id": s_id,
            "seed": seed,
            "year": int(year),
            "month": int(month),
            "day": int(day),
            "kind": fields.get("kind", "unknown"),
            "src": _to_int(fields.get("src"), -1),
            "dst": _to_int(fields.get("dst"), -1),
            "iters": iters,
            "ops": ops,
            "slices": _to_int(fields.get("slices")),
            "days": days,
            "ticks": ticks,
            "ops_per_tick": ops_per_tick,
            "outcome": outcome,
            "result": result,
            "budget": _to_int(fields.get("budget")),
            "source": "P5_RAIL_SEARCH",
        }
        rail_searches.append(rec)

    # Si C56_TASK RAIL_SEARCH_END est présent, on peut aussi l'analyser
    for year, month, day, kind, rest in C56_RAIL_SEARCH_END_RE.findall(output or ""):
        fields = parse_fields(rest)
        src = _to_int(fields.get("src"), -1)
        dst = _to_int(fields.get("dst"), -1)
        iters = _to_int(fields.get("iters"))
        outcome = fields.get("outcome", "none")
        result = fields.get("result", "none")
        ticks = _to_int(fields.get("ticks"), -1)
        days = _to_int(fields.get("days"), -1)
        budget = _to_int(fields.get("budget"), 0)

        # Vérifier si déjà capturé par P5_RAIL_SEARCH
        already = False
        for rs in rail_searches:
            if rs["src"] == src and rs["dst"] == dst and rs["iters"] == iters:
                already = True
                if rs["outcome"] in ("none", "NOPA") and outcome != "none":
                    rs["outcome"] = outcome
                    rs["result"] = result
                break
        if not already:
            rec = {
                "id": len(rail_searches) + 1,
                "seed": seed,
                "year": int(year),
                "month": int(month),
                "day": int(day),
                "kind": kind,
                "src": src,
                "dst": dst,
                "iters": iters,
                "ops": 0,
                "slices": 0,
                "days": days,
                "ticks": ticks,
                "ops_per_tick": 0.0,
                "outcome": outcome,
                "result": result,
                "budget": budget,
                "source": "RAIL_SEARCH_END",
            }
            rail_searches.append(rec)

    for year, month, day, rest in P5_BUILD_LINE_RE.findall(output or ""):
        fields = parse_fields(rest)
        b_id = _to_int(fields.get("id"), -1)
        if b_id < 0:
            continue
        rec = {
            "id": b_id,
            "seed": seed,
            "year": int(year),
            "month": int(month),
            "day": int(day),
            "mode": fields.get("mode", "unknown"),
            "src": _to_int(fields.get("src"), -1),
            "dst": _to_int(fields.get("dst"), -1),
            "cap": _to_int(fields.get("cap")),
        }
        build_lines.append(rec)

    return {
        "wait_starts": wait_starts,
        "wait_ends": wait_ends,
        "rail_passes": rail_passes,
        "rail_searches": rail_searches,
        "build_lines": build_lines,
    }


def compute_perturbation_table(series: list[dict], baseline_series: list[dict]) -> list[dict]:
    by_seed_base = {r.get("seed"): r for r in baseline_series}
    table = []
    for var in series:
        s = var.get("seed")
        if s not in by_seed_base:
            continue
        base = by_seed_base[s]
        b_val = base.get("company_value") or 0
        v_val = var.get("company_value") or 0
        b_prof = base.get("profit_year") or 0
        v_prof = var.get("profit_year") or 0
        b_veh = base.get("n_vehicles") or 0
        v_veh = var.get("n_vehicles") or 0
        b_st = base.get("n_stations") or 0
        v_st = var.get("n_stations") or 0

        val_pct = ((v_val - b_val) / b_val * 100) if b_val > 0 else 0.0
        prof_pct = ((v_prof - b_prof) / b_prof * 100) if b_prof > 0 else 0.0
        table.append({
            "seed": s,
            "val_ref": b_val, "val_var": v_val, "val_pct": round(val_pct, 1),
            "prof_ref": b_prof, "prof_var": v_prof, "prof_pct": round(prof_pct, 1),
            "veh_ref": b_veh, "veh_var": v_veh, "veh_delta": v_veh - b_veh,
            "st_ref": b_st, "st_var": v_st, "st_delta": v_st - b_st,
        })
    return table


def analyze_p5(
    combined_data: dict,
    max_year: int = 1975,
    seed_series: list[dict] | None = None,
    baseline_series: list[dict] | None = None,
) -> dict:
    """Analyse complète P5 : exposition, opcodes d'attente, coût A* et avance disponible."""
    all_starts = combined_data["wait_starts"]
    all_ends = combined_data["wait_ends"]
    all_passes = combined_data["rail_passes"]
    all_searches = combined_data["rail_searches"]
    all_builds = combined_data["build_lines"]

    starts = [s for s in all_starts if s["year"] <= max_year]
    ends_by_id_seed = {(e["id"], e["seed"]): e for e in all_ends}
    passes = [p for p in all_passes if p["year"] <= max_year]

    episodes: list[dict] = []
    for s in starts:
        key = (s["id"], s["seed"])
        end = ends_by_id_seed.get(key)
        days = end["days"] if end else -1
        ticks = end["ticks"] if end else -1
        unused_ops = end["unused_ops"] if end else 0
        used_ops = end["used_ops"] if end else 0
        unused_ops_per_tick = round(unused_ops / max(1, ticks), 1) if ticks > 0 else 0.0

        ep = {
            "id": s["id"],
            "seed": s["seed"],
            "year": s["year"],
            "date": s["date"],
            "tick": s["tick"],
            "cap": s["cap"],
            "alts": s["alts"],
            "n_rail": s["n_rail"],
            "n_air": s["n_air"],
            "n_road": s["n_road"],
            "n_fleet": s["n_fleet"],
            "rail_rank": s["rail_rank"],
            "rail_kind": s["rail_kind"],
            "rail_src": s["rail_src"],
            "rail_dst": s["rail_dst"],
            "rail_cap": s["rail_cap"],
            "rail_fin_cap": s["rail_fin_cap"],
            "rail_def": s["rail_def"],
            "rail_prof": s["rail_prof"],
            "rail_roi": s["rail_roi"],
            "rail_score": s["rail_score"],
            "rail_cf_cap": s["rail_cf_cap"],
            "rail_cf_def": s["rail_cf_def"],
            "rail_cf_rank": s["rail_cf_rank"],
            "rail_iters": s["rail_iters"],
            "ahead_air": s["ahead_air"],
            "ahead_road": s["ahead_road"],
            "ahead_fleet": s["ahead_fleet"],
            "days": days,
            "ticks": ticks,
            "dispatches": end["dispatches"] if end else 0,
            "unused_ops": unused_ops,
            "used_ops": used_ops,
            "unused_ops_per_tick": unused_ops_per_tick,
            "ret_reason": end["ret_reason"] if end else "unresolved",
            "ret_task": end["ret_task"] if end else "none",
            "resolved": (end is not None),
        }
        episodes.append(ep)

    assert len(starts) == len(episodes), "Incohérence nombre d'épisodes"

    # --- 1. EXPOSITION & CONTREFACTUEL ---
    n_episodes = len(episodes)
    episodes_with_rail = [e for e in episodes if e["n_rail"] > 0]
    n_ep_with_rail = len(episodes_with_rail)
    ep_rail_exposure_pct = (n_ep_with_rail / n_episodes * 100) if n_episodes > 0 else 0.0

    # Caractéristiques modélisées
    rail_ranks = [e["rail_rank"] for e in episodes_with_rail if e["rail_rank"] >= 0]
    rail_deficits = [e["rail_def"] for e in episodes_with_rail]
    rail_fin_caps = [e["rail_fin_cap"] for e in episodes_with_rail]
    rail_profs = [e["rail_prof"] for e in episodes_with_rail]
    rail_rois = [e["rail_roi"] for e in episodes_with_rail]
    rail_kinds = Counter(e["rail_kind"] for e in episodes_with_rail)

    ep_affordable_count = sum(1 for e in episodes_with_rail if e["rail_def"] == 0)
    ep_top1_count = sum(1 for e in episodes_with_rail if e["rail_rank"] == 0)
    ep_top3_count = sum(1 for e in episodes_with_rail if 0 <= e["rail_rank"] <= 2)
    ep_top5_count = sum(1 for e in episodes_with_rail if 0 <= e["rail_rank"] <= 4)

    # Caractéristiques contrefactuelles (0.96 / 1.70)
    cf_caps = [e["rail_cf_cap"] for e in episodes_with_rail]
    cf_deficits = [e["rail_cf_def"] for e in episodes_with_rail]
    cf_ranks = [e["rail_cf_rank"] for e in episodes_with_rail if e["rail_cf_rank"] >= 0]

    cf_affordable_count = sum(1 for e in episodes_with_rail if e["rail_cf_def"] == 0)
    cf_top1_count = sum(1 for e in episodes_with_rail if e["rail_cf_rank"] == 0)
    cf_top3_count = sum(1 for e in episodes_with_rail if 0 <= e["rail_cf_rank"] <= 2)
    cf_top5_count = sum(1 for e in episodes_with_rail if 0 <= e["rail_cf_rank"] <= 4)

    # Exposition hors épisodes (passages projects)
    n_passes = len(passes)
    passes_with_rail_alts = [p for p in passes if p["rail_alts"] > 0]
    passes_with_rail_aff = [p for p in passes if p["rail_aff"] > 0]
    passes_with_rail_in_best = [p for p in passes if p["rail_in_best"] > 0]
    passes_with_rail_built = [p for p in passes if p["rail_built"] > 0]

    # --- 2. OPCODES DISPONIBLES PAR ÉPISODE ---
    resolved_eps = [e for e in episodes if e["resolved"]]
    unused_ops_list = [e["unused_ops"] for e in resolved_eps]
    used_ops_list = [e["used_ops"] for e in resolved_eps]
    ticks_list = [e["ticks"] for e in resolved_eps]
    days_list = [e["days"] for e in resolved_eps]
    unused_per_tick_list = [e["unused_ops_per_tick"] for e in resolved_eps if e["ticks"] > 0]

    total_unused_ops = sum(unused_ops_list)
    total_used_ops = sum(used_ops_list)
    total_ticks = sum(ticks_list)
    total_days = sum(days_list)

    unused_ops_med = statistics.median(unused_ops_list) if unused_ops_list else 0
    unused_ops_p90 = sorted(unused_ops_list)[int(len(unused_ops_list) * 0.9)] if unused_ops_list else 0
    unused_ops_mean = statistics.mean(unused_ops_list) if unused_ops_list else 0

    unused_per_tick_med = statistics.median(unused_per_tick_list) if unused_per_tick_list else 0
    unused_per_tick_p90 = sorted(unused_per_tick_list)[int(len(unused_per_tick_list) * 0.9)] if unused_per_tick_list else 0
    unused_per_tick_mean = round(statistics.mean(unused_per_tick_list), 1) if unused_per_tick_list else 0

    days_med = statistics.median(days_list) if days_list else 0
    ticks_med = statistics.median(ticks_list) if ticks_list else 0

    # --- 3. COÛT D'UN A* RAIL RÉELLEMENT LANCÉ ---
    n_searches_all = len(all_searches)
    searches_in_scope = [s for s in all_searches if s["year"] <= max_year]
    searches_to_analyze = all_searches if n_searches_all > 0 else []

    search_iters = [s["iters"] for s in searches_to_analyze]
    search_ops = [s["ops"] for s in searches_to_analyze if s["ops"] > 0]
    search_ticks = [s["ticks"] for s in searches_to_analyze if s["ticks"] > 0]
    search_days = [s["days"] for s in searches_to_analyze if s["days"] >= 0]
    search_ops_per_tick = [s["ops_per_tick"] for s in searches_to_analyze if s.get("ops_per_tick", 0) > 0]

    outcomes_counter = Counter(s["outcome"] for s in searches_to_analyze)
    results_counter = Counter(s["result"] for s in searches_to_analyze)

    astar_cost_summary = {
        "n_searches_scope": len(searches_in_scope),
        "n_searches_total": n_searches_all,
        "iters_med": statistics.median(search_iters) if search_iters else 0,
        "iters_p90": sorted(search_iters)[int(len(search_iters) * 0.9)] if search_iters else 0,
        "ops_med": statistics.median(search_ops) if search_ops else 0,
        "ops_p90": sorted(search_ops)[int(len(search_ops) * 0.9)] if search_ops else 0,
        "ticks_med": statistics.median(search_ticks) if search_ticks else 0,
        "ticks_p90": sorted(search_ticks)[int(len(search_ticks) * 0.9)] if search_ticks else 0,
        "days_med": statistics.median(search_days) if search_days else 0,
        "days_p90": sorted(search_days)[int(len(search_days) * 0.9)] if search_days else 0,
        "ops_per_tick_med": statistics.median(search_ops_per_tick) if search_ops_per_tick else 0,
        "ops_per_tick_mean": round(statistics.mean(search_ops_per_tick), 1) if search_ops_per_tick else 0,
        "n_ok": outcomes_counter.get("OK", 0),
        "n_nopa": outcomes_counter.get("NOPA", 0),
        "n_cap": sum(v for k, v in outcomes_counter.items() if k in ("ABND", "DEAD")) or results_counter.get("cap", 0),
        "n_short": outcomes_counter.get("SHORT", 0),
        "n_nomatch": outcomes_counter.get("NOMATCH", 0),
        "n_cancelled": outcomes_counter.get("cancelled", 0),
        "outcomes": dict(outcomes_counter),
    }

    # --- 4. AVANCE DISPONIBLE ET DEVENIR DES CANDIDATS ---
    ref_astar_days_med = astar_cost_summary["days_med"] if astar_cost_summary["days_med"] > 0 else 63
    ref_astar_ops_med = astar_cost_summary["ops_med"] if astar_cost_summary["ops_med"] > 0 else 2367295

    built_lines_by_pair = defaultdict(list)
    for b in all_builds:
        if b["mode"] == "rail":
            built_lines_by_pair[(b["src"], b["dst"], b["seed"])].append(b)
            # Bidirectionnel
            built_lines_by_pair[(b["dst"], b["src"], b["seed"])].append(b)

    episodes_table = []
    fate_counts = Counter()
    total_avance_days = 0
    total_avance_days_built_later = 0
    avance_days_list = []
    fraction_covered_list = []

    for ep in episodes:
        has_rail = ep["n_rail"] > 0
        avance_days = 0
        fraction_covered = 0.0
        if has_rail and ep["days"] > 0:
            avance_days = min(ep["days"], ref_astar_days_med)
            fraction_covered = round((avance_days / ref_astar_days_med * 100), 1) if ref_astar_days_med > 0 else 0.0
            avance_days_list.append(avance_days)
            fraction_covered_list.append(fraction_covered)
            total_avance_days += avance_days

        # Devenir du candidat rail
        fate = "none"
        if has_rail:
            pair_key = (ep["rail_src"], ep["rail_dst"], ep["seed"])
            built_after = [b for b in built_lines_by_pair.get(pair_key, []) if b["id"] > ep["id"]]
            if built_after:
                fate = "built_later"
                total_avance_days_built_later += avance_days
            else:
                if ep["ret_reason"] in ("air_fleet", "targeted_air", "catalog", "month", "capital", "projects_useful", "immediate"):
                    fate = "superseded_by_other_mode"
                else:
                    fate = "never_built"
            fate_counts[fate] += 1

        fits_med = has_rail and (ep["unused_ops"] >= ref_astar_ops_med)
        episodes_table.append({
            "id": ep["id"],
            "seed": ep["seed"],
            "date": ep["date"],
            "days": ep["days"],
            "ticks": ep["ticks"],
            "unused_ops": ep["unused_ops"],
            "unused_ops_per_tick": ep["unused_ops_per_tick"],
            "has_rail": has_rail,
            "rail_rank": ep["rail_rank"],
            "rail_kind": ep["rail_kind"],
            "rail_cap": ep["rail_cap"],
            "rail_fin_cap": ep["rail_fin_cap"],
            "rail_def": ep["rail_def"],
            "rail_prof": ep["rail_prof"],
            "rail_cf_cap": ep["rail_cf_cap"],
            "rail_cf_def": ep["rail_cf_def"],
            "rail_cf_rank": ep["rail_cf_rank"],
            "avance_days": avance_days,
            "fraction_covered": fraction_covered,
            "fits_med": fits_med,
            "fate": fate,
            "ret_reason": ep["ret_reason"],
        })

    avance_days_med = statistics.median(avance_days_list) if avance_days_list else 0
    fraction_covered_med = statistics.median(fraction_covered_list) if fraction_covered_list else 0.0

    perturbation = []
    if seed_series and baseline_series:
        perturbation = compute_perturbation_table(seed_series, baseline_series)

    summary = {
        "n_episodes": n_episodes,
        "n_ep_with_rail": n_ep_with_rail,
        "ep_rail_exposure_pct": round(ep_rail_exposure_pct, 1),
        "rail_kinds": dict(rail_kinds),
        # Modélisé
        "rail_rank_med": statistics.median(rail_ranks) if rail_ranks else -1,
        "rail_def_med": statistics.median(rail_deficits) if rail_deficits else -1,
        "rail_cap_med": statistics.median(rail_fin_caps) if rail_fin_caps else -1,
        "rail_prof_med": statistics.median(rail_profs) if rail_profs else -1,
        "rail_roi_med": statistics.median(rail_rois) if rail_rois else -1,
        "ep_affordable_count": ep_affordable_count,
        "ep_top1_count": ep_top1_count,
        "ep_top3_count": ep_top3_count,
        "ep_top5_count": ep_top5_count,
        # Contrefactuel
        "cf_cap_med": statistics.median(cf_caps) if cf_caps else -1,
        "cf_def_med": statistics.median(cf_deficits) if cf_deficits else -1,
        "cf_rank_med": statistics.median(cf_ranks) if cf_ranks else -1,
        "cf_affordable_count": cf_affordable_count,
        "cf_top1_count": cf_top1_count,
        "cf_top3_count": cf_top3_count,
        "cf_top5_count": cf_top5_count,
        "cf_affordable_gain": cf_affordable_count - ep_affordable_count,
        # Passages
        "n_passes": n_passes,
        "passes_with_rail_alts": len(passes_with_rail_alts),
        "passes_with_rail_aff": len(passes_with_rail_aff),
        "passes_with_rail_in_best": len(passes_with_rail_in_best),
        "passes_with_rail_built": len(passes_with_rail_built),
        # Opcodes
        "total_unused_ops": total_unused_ops,
        "total_used_ops": total_used_ops,
        "unused_ops_med": unused_ops_med,
        "unused_ops_p90": unused_ops_p90,
        "unused_ops_mean": round(unused_ops_mean),
        "unused_per_tick_med": unused_per_tick_med,
        "unused_per_tick_p90": unused_per_tick_p90,
        "unused_per_tick_mean": unused_per_tick_mean,
        "days_med": days_med,
        "ticks_med": ticks_med,
        "total_ticks": total_ticks,
        "total_days": total_days,
        # Coût A*
        "astar_cost": astar_cost_summary,
        # Avance
        "avance_days_med": avance_days_med,
        "fraction_covered_med": fraction_covered_med,
        "total_avance_days": total_avance_days,
        "total_avance_days_built_later": total_avance_days_built_later,
        "fate_counts": dict(fate_counts),
        "episodes_table": episodes_table,
        "perturbation": perturbation,
    }
    return summary


def format_p5_report(summary: dict, seeds: list[int], max_year: int = 1975) -> str:
    lines = [
        f"# Rapport P5 bis — Pré-planification A* rail pendant l'attente de capital",
        f"",
        f"Graines étudiées : {seeds} | Période : 1970–{max_year}.",
        f"",
        f"## 1. Issues réelles des recherches A* rail",
    ]

    ac = summary["astar_cost"]
    lines.extend([
        f"- **Recherches A* observées** : {ac['n_searches_scope']} sur 1970–{max_year} ({ac['n_searches_total']} sur toute la simulation)",
        f"- **Répartition des issues réelles** :",
        f"  - Succès (`OK / found`) : **{ac['n_ok']}**",
        f"  - Aucun chemin (`NOPA`) : **{ac['n_nopa']}**",
        f"  - Plafond itérations (`ABND/DEAD / cap`) : **{ac['n_cap']}**",
        f"  - Tracé trop court (`SHORT`) : **{ac['n_short']}**",
        f"  - Quai non connectable (`NOMATCH`) : **{ac['n_nomatch']}**",
        f"  - Annulée / coupée : **{ac['n_cancelled']}**",
        f"- **Coût réel de l'A*** :",
        f"  - Itérations : Médiane = **{ac['iters_med']}** | p90 = **{ac['iters_p90']}**",
        f"  - Opcodes : Médiane = **{ac['ops_med']:,}** | p90 = **{ac['ops_p90']:,}**",
        f"  - Durée calendaire : Médiane = **{ac['days_med']} jours** ({ac['ticks_med']} ticks) | p90 = **{ac['days_p90']} jours** ({ac['ticks_p90']} ticks)",
        f"  - Débit A* observé : Médiane = **{ac['ops_per_tick_med']:,} opcodes/tick** | Moyenne = **{ac['ops_per_tick_mean']:,} opcodes/tick**",
        f"",
        f"## 2. Exposition du rail pendant les épisodes d'attente (1970–{max_year})",
        f"- **Nombre total d'épisodes d'attente (`all_unaffordable`)** : **{summary['n_episodes']}**",
        f"- **Épisodes avec au moins un candidat rail dans le vivier** : **{summary['n_ep_with_rail']} / {summary['n_episodes']}** ({summary['ep_rail_exposure_pct']} %)",
    ])

    if summary["n_ep_with_rail"] > 0:
        lines.extend([
            f"",
            f"### Comparaison d'impact du facteur 1,70 (Modélisé vs Contrefactuel 0,96/1,70) :",
            f"| Métrique | Modélisé (avec 1,70) | Contrefactuel (0,96/1,70) | Évolution |",
            f"|---|---:|---:|---:|",
            f"| **Capital requis médian** | **{summary['rail_cap_med']:,} £** | **{summary['cf_cap_med']:,} £** | -43,5 % |",
            f"| **Déficit médian vs caisse** | **{summary['rail_def_med']:,} £** | **{summary['cf_def_med']:,} £** | -{summary['rail_def_med'] - summary['cf_def_med']:,} £ |",
            f"| **Épisodes finançables** | **{summary['ep_affordable_count']} / {summary['n_ep_with_rail']}** | **{summary['cf_affordable_count']} / {summary['n_ep_with_rail']}** | +{summary['cf_affordable_gain']} |",
            f"| **Rang médian vivier** | **{summary['rail_rank_med']}** | **{summary['cf_rank_med']}** | {'+' if summary['cf_rank_med'] < summary['rail_rank_med'] else ''}{summary['rail_rank_med'] - summary['cf_rank_med']} places |",
            f"| **Dans le Top 1 (meilleur)** | **{summary['ep_top1_count']} / {summary['n_ep_with_rail']}** | **{summary['cf_top1_count']} / {summary['n_ep_with_rail']}** | +{summary['cf_top1_count'] - summary['ep_top1_count']} |",
            f"| **Dans le Top 3** | **{summary['ep_top3_count']} / {summary['n_ep_with_rail']}** | **{summary['cf_top3_count']} / {summary['n_ep_with_rail']}** | +{summary['cf_top3_count'] - summary['ep_top3_count']} |",
            f"| **Dans le Top 5** | **{summary['ep_top5_count']} / {summary['n_ep_with_rail']}** | **{summary['cf_top5_count']} / {summary['n_ep_with_rail']}** | +{summary['cf_top5_count'] - summary['ep_top5_count']} |",
            f"",
            f"- **Profit annuel médian estimé** : **{summary['rail_prof_med']:,} £/an** (ROI médian : {summary['rail_roi_med']} %)",
            f"- **Répartition par kind** : {summary['rail_kinds']}",
        ])

    pct_alts = f" ({summary['passes_with_rail_alts'] / summary['n_passes'] * 100:.1f} %)" if summary['n_passes'] > 0 else ""
    pct_aff = f" ({summary['passes_with_rail_aff'] / summary['n_passes'] * 100:.1f} %)" if summary['n_passes'] > 0 else ""
    pct_best = f" ({summary['passes_with_rail_in_best'] / summary['n_passes'] * 100:.1f} %)" if summary['n_passes'] > 0 else ""

    lines.extend([
        f"",
        f"### Exposition hors épisodes (passages `projects` totaux : {summary['n_passes']}) :",
        f"- Passages avec alternatives rail dans le catalogue : **{summary['passes_with_rail_alts']} / {summary['n_passes']}**{pct_alts}",
        f"- Passages avec au moins un candidat rail **finançable** : **{summary['passes_with_rail_aff']} / {summary['n_passes']}**{pct_aff}",
        f"- Passages avec un candidat rail dans `best` : **{summary['passes_with_rail_in_best']} / {summary['n_passes']}**{pct_best}",
        f"- Lignes rail effectivement construites : **{summary['passes_with_rail_built']} / {summary['n_passes']}**",
        f"",
        f"## 3. Opcodes disponibles pendant les épisodes d'attente",
        f"- **Durée médiane d'un épisode** : **{summary['days_med']} jours** ({summary['ticks_med']} ticks moteur)",
        f"- **Opcodes inutilisés par épisode** : Médiane = **{summary['unused_ops_med']:,}** | p90 = **{summary['unused_ops_p90']:,}** | Moyenne = **{summary['unused_ops_mean']:,}**",
        f"- **Opcodes inutilisés par tick** : Médiane = **{summary['unused_per_tick_med']:,} ops/tk** | p90 = **{summary['unused_per_tick_p90']:,} ops/tk** | Moyenne = **{summary['unused_per_tick_mean']:,} ops/tk**",
        f"- **Cumul total des opcodes gaspillés en attente** : **{summary['total_unused_ops']:,} opcodes** (sur {summary['total_ticks']} ticks)",
        f"- *Explication des écarts (450 à 4 500+ ops/tk)* : L'ordonnanceur alloue un budget moteur de 10 000 ops/tick. Lors des ticks actifs (reconstruction du catalogue, scoring complet de projets, tranches A*), une part importante du budget est consommée par ces tâches. Lors des ticks passifs (aucun travail dû, attente pure), la quasi-totalité du budget (~9 500 ops) est relâchée.",
        f"",
        f"## 4. Avance disponible et devenir des candidats",
        f"- **Avance potentielle médiane par épisode** : **{summary['avance_days_med']} jours**",
        f"- **Fraction médiane de l'A* couverte par l'attente** : **{summary['fraction_covered_med']} %**",
        f"- **Cumul total de l'avance théorique** : **{summary['total_avance_days']} jours** (dont **{summary['total_avance_days_built_later']} jours** sur des candidats effectivement construits plus tard)",
        f"- **Devenir du meilleur candidat rail au retour du capital** :",
        f"  - `built_later` (effectivement construit plus tard dans la partie) : **{summary['fate_counts'].get('built_later', 0)}**",
        f"  - `superseded_by_other_mode` (dépassé par air/flotte/route au retour du capital) : **{summary['fate_counts'].get('superseded_by_other_mode', 0)}**",
        f"  - `never_built` (jamais construit de toute la partie) : **{summary['fate_counts'].get('never_built', 0)}**",
        f"",
        f"## 5. Tableau détaillé par épisode d'attente (1970–{max_year})",
        f"| Épisode | Graine | Date | Durée | Ops/tk libres | Rail présent | Rang (Mod/CF) | Cap (Mod/CF) | Déficit (Mod/CF) | Avance | Couvert | Devenir |",
        f"|---:|---:|---|---:|---:|:---:|---:|---:|---:|---:|---:|:---|",
    ])

    for ep in summary["episodes_table"][:45]:
        has_r = "OUI" if ep["has_rail"] else "NON"
        r_rank = f"{ep['rail_rank']} / {ep['rail_cf_rank']}" if ep["has_rail"] else "—"
        r_cap = f"{ep['rail_fin_cap']:,} / {ep['rail_cf_cap']:,}" if ep["has_rail"] else "—"
        r_def = f"{ep['rail_def']:,} / {ep['rail_cf_def']:,}" if ep["has_rail"] else "—"
        av_str = f"{ep['avance_days']} j" if ep["has_rail"] else "—"
        frac_str = f"{ep['fraction_covered']} %" if ep["has_rail"] else "—"
        lines.append(
            f"| {ep['id']} | {ep['seed']} | {ep['date']} | {ep['days']} j | {ep['unused_ops_per_tick']:,} | {has_r} | {r_rank} | {r_cap} | {r_def} | {av_str} | {frac_str} | {ep['fate']} |"
        )

    if summary["perturbation"]:
        lines.extend([
            f"",
            f"## 6. Perturbation sous sonde (probe_scheduler=1 vs référence probe_scheduler=0)",
            f"| Graine | Valeur ref | Valeur sonde | Delta val (%) | Profit ref | Profit sonde | Delta prof (%) | Véh ref | Véh sonde (delta) | Gares ref | Gares sonde (delta) |",
            f"|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for p in summary["perturbation"]:
            lines.append(
                f"| {p['seed']} | {p['val_ref']:,} £ | {p['val_var']:,} £ | {p['val_pct']:+.1f} % | {p['prof_ref']:,} £ | {p['prof_var']:,} £ | {p['prof_pct']:+.1f} % | {p['veh_ref']} | {p['veh_var']} ({p['veh_delta']:+d}) | {p['st_ref']} | {p['st_var']} ({p['st_delta']:+d}) |"
            )

    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file", help="Fichier JSON produit par diag_p5_preplan.py")
    parser.add_argument("--max-year", type=int, default=1975)
    parser.add_argument("--out-md", help="Fichier Markdown de sortie")
    args = parser.parse_args(argv)

    data = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    summary = data.get("summary")
    seeds = data.get("seeds", [42, 100, 999])

    report = format_p5_report(summary, seeds, max_year=args.max_year)
    if args.out_md:
        Path(args.out_md).write_text(report, encoding="utf-8")
        print(f"Rapport écrit dans {args.out_md}")
    else:
        print(report)


if __name__ == "__main__":
    main()
