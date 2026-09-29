#!/usr/bin/env python3
"""C116.3: sonde passive legere du prix d'ombre du capital sous le vrai C115."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg
from campaign_freeze import _frozen_library_descriptor

DEFAULT_SEEDS = (42, 100, 999)
C114_LOSS_SEEDS = {100, 7, 17, 314, 1024, 12345, 424242, 8675309}
SCRIPT_DEBUG_LEVEL = "3"
ENGINE_TIMEOUT_SEC = None
_SEEDS_WITH_PARSED_OUTPUT = set()
_KEEP_SEEN = set()
_real_check_output = openttdlab.subprocess.check_output


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


def keep(row):
    seed = row.get("experiment", {}).get("seed")
    if seed in _SEEDS_WITH_PARSED_OUTPUT:
        return ()
    _SEEDS_WITH_PARSED_OUTPUT.add(seed)
    events = []
    for line in (row.get("output", "") or "").splitlines():
        marker = "C116_PROJECT "
        if marker not in line:
            continue
        event = {}
        for token in line.split(marker, 1)[1].split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            event[key] = parse_value(value)
        event["seed"] = seed
        event_key = (
            seed, event.get("year"), event.get("arm"), event.get("airport"),
            event.get("dist"), event.get("pax"), event.get("maxC"),
        )
        if event_key in _KEEP_SEEN:
            continue
        _KEEP_SEEN.add(event_key)
        events.append(event)
    return ({"seed": seed, "date": str(row.get("date", "")), "events": events},) if events else ()


def stats(values):
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(vals), "mean": statistics.mean(vals), "median": statistics.median(vals),
        "min": min(vals), "max": max(vals),
    }


def ratio(a, b):
    return float(a) / float(b) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None


def predicted_id(event, switch):
    runner = event.get("runner_id")
    legacy = event.get("legacy_id")
    return runner if switch and isinstance(runner, int) and runner >= 0 else legacy


def rule_summary(events, name, switch_fn):
    usable = [e for e in events if isinstance(e.get("legacy_id"), int) and isinstance(e.get("c115_id"), int)]
    switched = []
    agreements = 0
    c115_switches = 0
    c115_switch_agreements = 0
    both_switch = 0
    extra = 0
    missed = 0
    for event in usable:
        switch = bool(switch_fn(event)) and event.get("runner_id") != event.get("legacy_id")
        if switch:
            switched.append(event)
        pred = predicted_id(event, switch)
        actual = event.get("c115_id")
        if pred == actual:
            agreements += 1
        actual_switch = actual != event.get("legacy_id")
        if actual_switch:
            c115_switches += 1
            if switch:
                both_switch += 1
            if pred == actual:
                c115_switch_agreements += 1
            if not switch:
                missed += 1
        elif switch:
            extra += 1
    return {
        "name": name,
        "usable": len(usable),
        "switches": len(switched),
        "switch_pct": 100.0 * len(switched) / len(usable) if usable else None,
        "c115_agreement_pct": 100.0 * agreements / len(usable) if usable else None,
        "c115_switch_agreement_pct": 100.0 * c115_switch_agreements / c115_switches if c115_switches else None,
        "capital_saving_recall_pct": 100.0 * both_switch / c115_switches if c115_switches else None,
        "capital_saving_precision_pct": 100.0 * both_switch / len(switched) if switched else None,
        "missed_c115_switches": missed,
        "extra_switches": extra,
        "capital_ratio_on_switch": stats(ratio(e.get("runner_C"), e.get("legacy_C")) for e in switched),
        "profit_ratio_on_switch": stats(ratio(e.get("runner_P"), e.get("legacy_P")) for e in switched),
    }


def summarise(events):
    c115_switched = [e for e in events if e.get("c115_id") != e.get("legacy_id")]
    runner_available = [e for e in events if isinstance(e.get("runner_id"), int) and e.get("runner_id") >= 0
                        and e.get("runner_id") != e.get("legacy_id")]
    rules = {
        "self_unlock": rule_summary(events, "self_unlock", lambda e: e.get("self_unlock") == 1),
        "air_unlock_roi": rule_summary(
            events, "air_unlock_roi",
            lambda e: isinstance(e.get("c116u_hurdle"), (int, float)) and e.get("c116u_hurdle") > 0
            and isinstance(e.get("mroi"), (int, float)) and e.get("mroi") < e.get("c116u_hurdle")),
        "global_unlock_roi": rule_summary(
            events, "global_unlock_roi",
            lambda e: isinstance(e.get("c116g_hurdle"), (int, float)) and e.get("c116g_hurdle") > 0
            and isinstance(e.get("mroi"), (int, float)) and e.get("mroi") < e.get("c116g_hurdle")),
        "top_raw_shadow": rule_summary(
            events, "top_raw_shadow",
            lambda e: isinstance(e.get("c116t_hurdle"), (int, float)) and e.get("c116t_hurdle") > 0
            and isinstance(e.get("mroi"), (int, float)) and e.get("mroi") < e.get("c116t_hurdle")),
        "top_portfolio_score": rule_summary(
            events, "top_portfolio_score",
            lambda e: isinstance(e.get("c116t_score"), (int, float)) and e.get("c116t_score") > 0
            and isinstance(e.get("mroi"), (int, float)) and e.get("mroi") < e.get("c116t_score")),
        "top_raw_shadow_kdec": rule_summary(
            events, "top_raw_shadow_kdec",
            lambda e: isinstance(e.get("kdec"), (int, float))
            and isinstance(e.get("legacy_C"), (int, float)) and e.get("legacy_C") > e.get("kdec")
            and isinstance(e.get("c116t_hurdle"), (int, float)) and e.get("c116t_hurdle") > 0
            and isinstance(e.get("mroi"), (int, float)) and e.get("mroi") < e.get("c116t_hurdle")),
        "top_portfolio_score_kdec": rule_summary(
            events, "top_portfolio_score_kdec",
            lambda e: isinstance(e.get("kdec"), (int, float))
            and isinstance(e.get("legacy_C"), (int, float)) and e.get("legacy_C") > e.get("kdec")
            and isinstance(e.get("c116t_score"), (int, float)) and e.get("c116t_score") > 0
            and isinstance(e.get("mroi"), (int, float)) and e.get("mroi") < e.get("c116t_score")),
    }
    return {
        "events": len(events),
        "runner_available_pct": 100.0 * len(runner_available) / len(events) if events else None,
        "c115_switches": len(c115_switched),
        "c115_switch_pct": 100.0 * len(c115_switched) / len(events) if events else None,
        "c115_transitions": dict(Counter(
            f"{e.get('legacy_id')}->{e.get('c115_id')}" for e in c115_switched).most_common()),
        "replay_used_pct": 100.0 * sum(e.get("replay_used") == 1 for e in events) / len(events) if events else None,
        "snapshot_age_days": stats(e.get("c116p_age") for e in events if isinstance(e.get("c116p_age"), (int, float)) and e.get("c116p_age") >= 0),
        "top_mode": dict(Counter(str(e.get("c116t_mode")) for e in events).most_common()),
        "mroi_over_top_raw": stats(
            ratio(e.get("mroi"), e.get("c116t_hurdle")) for e in events
            if isinstance(e.get("c116t_hurdle"), (int, float)) and e.get("c116t_hurdle") > 0),
        "mroi_over_top_score": stats(
            ratio(e.get("mroi"), e.get("c116t_score")) for e in events
            if isinstance(e.get("c116t_score"), (int, float)) and e.get("c116t_score") > 0),
        "rules": rules,
    }


def unique_events(rows):
    return [event for row in rows for event in row.get("events", [])]


def build_summary(rows):
    events = unique_events(rows)
    by_year = defaultdict(list)
    by_arm = defaultdict(list)
    by_seed = defaultdict(list)
    for event in events:
        by_year[str(event.get("year"))].append(event)
        by_arm[str(event.get("arm"))].append(event)
        by_seed[str(event.get("seed"))].append(event)
    losses = [e for e in events if e.get("seed") in C114_LOSS_SEEDS]
    winners = [e for e in events if isinstance(e.get("seed"), int) and e.get("seed") not in C114_LOSS_SEEDS]
    return {
        "overall": summarise(events),
        "by_year": {k: summarise(v) for k, v in sorted(by_year.items())},
        "by_arm": {k: summarise(v) for k, v in sorted(by_arm.items())},
        "c114_cohorts": {"old_losers": summarise(losses), "old_winners": summarise(winners)},
        "by_seed": {k: summarise(v) for k, v in sorted(by_seed.items(), key=lambda kv: int(kv[0]))},
    }


def main():
    global ENGINE_TIMEOUT_SEC
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=4)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--engine-timeout", type=int, default=900)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c116_project_probe_3x4.json")
    parser.add_argument("--library-manifest", type=Path, default=None)
    parser.add_argument("--library-dir", type=Path, default=None)
    args = parser.parse_args()
    if not 1 <= args.max_workers <= 10:
        parser.error("--max-workers doit etre entre 1 et 10")
    ENGINE_TIMEOUT_SEC = args.engine_timeout or None
    if args.out.exists():
        parser.error(f"sortie existante: {args.out}")

    enable_savegame_cleanup()
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("c116_air_project_probe", 1),))
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
        "bench_arm": "OpexAI[c116_air_project_probe=1]",
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
    summary = build_summary(rows)
    payload = {
        "purpose": "C116.3 lightweight passive shadow-price diagnostic on the real C115 trajectory",
        "years": args.years,
        "seeds": args.seeds,
        "settings": {"c116_air_project_probe": 1, "c115_air_c100_capital_replay": 1},
        "rows": rows,
        "summary": summary,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Sortie: {args.out}")


if __name__ == "__main__":
    main()
