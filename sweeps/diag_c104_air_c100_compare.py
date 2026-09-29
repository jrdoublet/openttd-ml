#!/usr/bin/env python3
"""C104 : compare legacy, premier C100 et C100.1 sur les memes contextes AIR."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg
from campaign_freeze import _frozen_library_descriptor

DEFAULT_SEEDS = (42, 100, 999)
SCRIPT_DEBUG_LEVEL = "3"
ENGINE_TIMEOUT_SEC = None
_SEEDS_WITH_PARSED_OUTPUT = set()
_real_check_output = openttdlab.subprocess.check_output
# raw_output est cumulatif a chaque checkpoint OpenTTDLab. Sans deduplication,
# keep() recopie tout l'historique C104_COMPARE dans chaque resultat : un simple
# seed42 x 4 ans a produit 191,6 Mo. Chaque worker garde donc les contextes deja
# vus et n'emet que les nouveaux evenements. La cle est celle de unique_events().
C104_KEEP_SEEN = set()


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", f"script={SCRIPT_DEBUG_LEVEL}") + args[1:]
        if ENGINE_TIMEOUT_SEC is not None and "timeout" not in kwargs:
            kwargs["timeout"] = ENGINE_TIMEOUT_SEC
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def parse_value(value: str):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_fields(text: str) -> dict:
    out = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        out[key] = parse_value(value)
    return out


def keep(row):
    seed = row.get("experiment", {}).get("seed")
    # OpenTTDLab appelle result_processor pour chaque sauvegarde mensuelle mais lui
    # repasse a chaque fois la meme sortie complete du processus OpenTTD. C104 ne
    # doit donc parser/retourner ce journal qu'une fois par experience/seed, sinon
    # le Pool transporte des dizaines de copies identiques et peut se bloquer.
    if seed in _SEEDS_WITH_PARSED_OUTPUT:
        return ()
    _SEEDS_WITH_PARSED_OUTPUT.add(seed)
    raw_output = row.get("output", "") or ""
    events = []
    for line in raw_output.splitlines():
        marker = "C104_COMPARE "
        if marker not in line:
            continue
        fields_s = line.split(marker, 1)[1]
        event = {}
        for token in fields_s.split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            try:
                parsed = int(value)
            except ValueError:
                try:
                    parsed = float(value)
                except ValueError:
                    parsed = value
            event[key] = parsed
        event["seed"] = seed
        event_key = (
            seed, event.get("year"), event.get("arm"), event.get("airport"),
            event.get("dist"), event.get("pax"), event.get("maxC"),
        )
        if event_key in C104_KEEP_SEEN:
            continue
        C104_KEEP_SEEN.add(event_key)
        events.append(event)
    if not events:
        return ()
    return ({
        "seed": seed,
        "date": str(row.get("date", "")),
        "events": events,
    },)


def stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 6),
        "median": round(statistics.median(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def pct(n, d):
    return round(100.0 * n / d, 3) if d else None


def ratio(a, b):
    return float(a) / float(b) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None


def unique_events(rows):
    unique = {}
    for row in rows:
        for event in row.get("events", []):
            key = (event.get("seed"), event.get("year"), event.get("arm"), event.get("airport"), event.get("dist"),
                   event.get("pax"), event.get("maxC"))
            unique[key] = event
    return list(unique.values())


def finance_capital(event, prefix):
    capital = event.get(prefix + "_C")
    imm = event.get(prefix + "_imm")
    if not isinstance(capital, (int, float)):
        return None
    new_airports = 2 if event.get("arm") == "newpair" else (1 if event.get("arm") == "hubsite" else 0)
    margin = 30000 if new_airports == 2 else (12000 if new_airports == 1 else 2000)
    return capital + (imm if isinstance(imm, (int, float)) else 0) + margin


def c69_score(event, prefix):
    profit = event.get(prefix + "_P")
    finance = finance_capital(event, prefix)
    kdec = event.get("kdec")
    if not isinstance(profit, (int, float)) or profit <= 0 or not isinstance(finance, (int, float)):
        return None
    denom = max(finance, kdec if isinstance(kdec, (int, float)) else 0)
    return 1000.0 * profit / denom if denom > 0 else None


def summarize_group(events):
    replay_switch = [e for e in events if e.get("replay_id") != e.get("legacy_id")]
    physical_switch = [e for e in events if e.get("physical_id") != e.get("legacy_id")]
    replay_score_ratio = [ratio(c69_score(e, "replay"), c69_score(e, "legacy")) for e in events]
    replay_legacy_score_ratio = [ratio(c69_score(e, "replay_legacy"), c69_score(e, "legacy")) for e in events]
    return {
        "events": len(events),
        "replay_switch": len(replay_switch),
        "replay_switch_pct": pct(len(replay_switch), len(events)),
        "physical_switch": len(physical_switch),
        "physical_switch_pct": pct(len(physical_switch), len(events)),
        "replay_transitions": dict(Counter(
            f"{e.get('legacy_id')}->{e.get('replay_id')}" for e in replay_switch).most_common()),
        "physical_transitions": dict(Counter(
            f"{e.get('legacy_id')}->{e.get('physical_id')}" for e in physical_switch).most_common()),
        "replay_vs_c69phys_disagree": sum(1 for e in events if e.get("replay_id") != e.get("c69phys_id")),
        "replay_vs_c69phys_disagree_pct": pct(
            sum(1 for e in events if e.get("replay_id") != e.get("c69phys_id")), len(events)),
        "physical_vs_c69phys_disagree_pct": pct(
            sum(1 for e in events if e.get("physical_id") != e.get("c69phys_id")), len(events)),
        "c69phys_transitions_from_legacy": dict(Counter(
            f"{e.get('legacy_id')}->{e.get('c69phys_id')}" for e in events
            if e.get("legacy_id") != e.get("c69phys_id")).most_common()),
        "replay_vs_marginal_disagree": sum(1 for e in events if e.get("replay_id") != e.get("marginal_id")),
        "replay_vs_marginal_disagree_pct": pct(
            sum(1 for e in events if e.get("replay_id") != e.get("marginal_id")), len(events)),
        "physical_vs_marginal_disagree_pct": pct(
            sum(1 for e in events if e.get("physical_id") != e.get("marginal_id")), len(events)),
        "marginal_transitions_from_legacy": dict(Counter(
            f"{e.get('legacy_id')}->{e.get('marginal_id')}" for e in events
            if e.get("legacy_id") != e.get("marginal_id")).most_common()),
        "replay_vs_onestep_disagree": sum(1 for e in events if e.get("replay_id") != e.get("onestep_id")),
        "replay_vs_onestep_disagree_pct": pct(
            sum(1 for e in events if e.get("replay_id") != e.get("onestep_id")), len(events)),
        "physical_vs_onestep_disagree_pct": pct(
            sum(1 for e in events if e.get("physical_id") != e.get("onestep_id")), len(events)),
        "onestep_transitions_from_legacy": dict(Counter(
            f"{e.get('legacy_id')}->{e.get('onestep_id')}" for e in events
            if e.get("legacy_id") != e.get("onestep_id")).most_common()),
        "power_alpha": {
            name: {
                "alpha": alpha,
                "replay_disagree": sum(1 for e in events if e.get("replay_id") != e.get(name + "_id")),
                "replay_disagree_pct": pct(sum(1 for e in events if e.get("replay_id") != e.get(name + "_id")), len(events)),
                "physical_disagree_pct": pct(sum(1 for e in events if e.get("physical_id") != e.get(name + "_id")), len(events)),
            }
            for name, alpha in (("p7", 0.4375), ("p8", 0.5), ("p9", 0.5625), ("p10", 0.625))
        },
        "speed_beta": {
            name: {
                "beta": beta,
                "replay_disagree": sum(1 for e in events if e.get("replay_id") != e.get(name + "_id")),
                "replay_disagree_pct": pct(sum(1 for e in events if e.get("replay_id") != e.get(name + "_id")), len(events)),
                "physical_disagree_pct": pct(sum(1 for e in events if e.get("physical_id") != e.get(name + "_id")), len(events)),
            }
            for name, beta in (("s1", 0.25), ("s2", 0.5), ("s3", 0.75), ("s4", 1.0))
        },
        "speed_elasticity": {
            name: {
                "threshold": threshold,
                "replay_disagree": sum(1 for e in events if e.get("replay_id") != e.get(name + "_id")),
                "replay_disagree_pct": pct(sum(1 for e in events if e.get("replay_id") != e.get(name + "_id")), len(events)),
                "physical_disagree_pct": pct(sum(1 for e in events if e.get("physical_id") != e.get(name + "_id")), len(events)),
            }
            for name, threshold in (("e25", 0.25), ("e50", 0.5), ("e75", 0.75), ("e100", 1.0))
        },
        "replay_price_over_legacy": stats(ratio(e.get("replay_price"), e.get("legacy_price")) for e in replay_switch),
        "replay_cap_over_legacy": stats(ratio(e.get("replay_cap"), e.get("legacy_cap")) for e in replay_switch),
        "replay_speed_over_legacy": stats(ratio(e.get("replay_speed"), e.get("legacy_speed")) for e in replay_switch),
        "replay_model_P_over_legacy_P": stats(ratio(e.get("replay_P"), e.get("legacy_P")) for e in replay_switch),
        "replay_engine_legacy_P_over_legacy_P": stats(
            ratio(e.get("replay_legacy_P"), e.get("legacy_P")) for e in replay_switch),
        "replay_engine_legacy_C_over_legacy_C": stats(
            ratio(e.get("replay_legacy_C"), e.get("legacy_C")) for e in replay_switch),
        "replay_days_over_legacy": stats(ratio(e.get("replay_days"), e.get("legacy_days")) for e in events),
        "physical_days_over_legacy": stats(ratio(e.get("physical_days"), e.get("legacy_days")) for e in events),
        "replay_score_over_legacy": stats(v for v in replay_score_ratio if v is not None),
        "replay_engine_legacy_score_over_legacy": stats(v for v in replay_legacy_score_ratio if v is not None),
        "kdec_over_legacy_finance": stats(
            ratio(e.get("kdec"), finance_capital(e, "legacy")) for e in events),
        "legacy_below_kdec_pct": pct(sum(
            1 for e in events if isinstance(e.get("kdec"), (int, float))
            and isinstance(finance_capital(e, "legacy"), (int, float))
            and finance_capital(e, "legacy") < e.get("kdec")), len(events)),
        "distance": stats(e.get("dist") for e in events),
        "pax": stats(e.get("pax") for e in events),
    }


def summarize(rows):
    events = unique_events(rows)
    by_arm = defaultdict(list)
    by_year = defaultdict(list)
    for event in events:
        by_arm[str(event.get("arm"))].append(event)
        by_year[str(event.get("year"))].append(event)
    return {
        "overall": summarize_group(events),
        "by_arm": {arm: summarize_group(group) for arm, group in sorted(by_arm.items())},
        "by_year": {year: summarize_group(group) for year, group in sorted(by_year.items())},
        "by_seed": {str(seed): summarize_group([e for e in events if e.get("seed") == seed])
                    for seed in sorted({e.get("seed") for e in events if isinstance(e.get("seed"), int)})},
    }


def main():
    global ENGINE_TIMEOUT_SEC
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=4)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument(
        "--engine-timeout",
        type=int,
        default=900,
        help="Timeout OpenTTD par partie, en secondes (0 = aucun)",
    )
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "diag_c104_air_c100_compare_3x4_20260927.json")
    parser.add_argument("--library-manifest", type=Path, default=None,
                        help="Manifest C66.4 avec bibliotheques AI gelees")
    parser.add_argument("--library-dir", type=Path, default=None,
                        help="Repertoire ai_libraries du bundle C66.4")
    args = parser.parse_args()
    if args.max_workers < 1 or args.max_workers > 10:
        parser.error("--max-workers doit etre entre 1 et 10")
    if args.engine_timeout < 0:
        parser.error("--engine-timeout doit etre >= 0")
    ENGINE_TIMEOUT_SEC = args.engine_timeout or None
    if args.out.exists():
        parser.error(f"sortie existante: {args.out}")

    enable_savegame_cleanup()
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("c104_air_c100_compare_probe", 1),))
    cfg = make_cfg(1970)
    if args.library_manifest is not None or args.library_dir is not None:
        if args.library_manifest is None or args.library_dir is None:
            parser.error("--library-manifest et --library-dir doivent etre fournis ensemble")
        manifest = json.loads(args.library_manifest.read_text(encoding="utf-8"))
        ai_libraries = tuple(
            _frozen_library_descriptor(group["requested_name"], group["resolved"], args.library_dir)
            for group in manifest["libraries"]
        )
    else:
        ai_libraries = (
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        )
    experiments = [{
        "bench_context": "solo",
        "bench_arm": "OpexAI[c104_air_c100_compare_probe=1]",
        "seed": seed,
        "days": 365 * args.years,
        "openttd_config": cfg,
        "ais": (opex,),
    } for seed in args.seeds]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.max_workers,
        result_processor=keep,
        ai_libraries=ai_libraries,
    ))
    summary = summarize(rows)
    payload = {
        "purpose": "C104 passive same-route legacy/replay/physical engine economics diagnostic; not adoption evidence",
        "years": args.years,
        "seeds": args.seeds,
        "settings": {"c104_air_c100_compare_probe": 1},
        "rows": rows,
        "summary": summary,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Sortie: {args.out}")


if __name__ == "__main__":
    main()
