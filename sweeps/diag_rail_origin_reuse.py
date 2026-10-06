#!/usr/bin/env python3
"""Diagnostic apparié du relâchement origin_served dans la génération rail.

Les deux bras activent rail_geometry_guard et decision_log. La seule différence est
rail_origin_reuse=0/1. Ce script est diagnostique : decision_log modifie le budget d'opcodes,
donc ses chiffres économiques ne valent pas qualification d'adoption.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import bench_v2  # noqa: E402
from bench_v2 import (  # noqa: E402
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    enable_savegame_cleanup,
    keep as bench_keep,
    make_cfg,
    script_failure_reason,
)


STARTING_YEAR = 1970
OPEX_EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def fields_from(rest):
    return dict(token.split("=", 1) for token in rest.split() if "=" in token)


def as_int(fields, key, default=0):
    try:
        return int(fields.get(key, default))
    except (TypeError, ValueError):
        return default


def parse_rail_events(output):
    vivier_kept = []
    vivier_produced = []
    prepairs = []
    last_rail_gen = None
    target_regen_shadows = []
    target_cargo_shadows = []
    target_cargo_skips = []
    origin_rejects = []
    rail_attempts = 0
    rail_builds = 0
    reuse_alt_attempts = 0
    reuse_alt_builds = 0
    rail_failures = Counter()
    chosen = Counter()
    air_priority_observations = 0
    air_priority_defers = 0
    for raw in (output or "").splitlines():
        if "RAIL_ORIGIN_REUSE_AIR_PRIORITY_DEFER" in raw:
            air_priority_defers += 1
        elif "RAIL_ORIGIN_REUSE_AIR_PRIORITY " in raw:
            air_priority_observations += 1
        match = OPEX_EVENT_RE.search(raw)
        if not match:
            continue
        _year, _month, _day, kind, rest = match.groups()
        fields = fields_from(rest)
        if kind == "VIVIER_GEN" and fields.get("mode") == "rail":
            kept = as_int(fields, "kept")
            produced = as_int(fields, "produced")
            vivier_kept.append(kept)
            vivier_produced.append(produced)
            last_rail_gen = {
                "date": f"{_year}-{_month}-{_day}",
                "produced": produced,
                "kept": kept,
            }
        elif kind == "RAIL_PREPAIR":
            record = dict(last_rail_gen or {})
            record.update({key: as_int(fields, key) if value.lstrip("-").isdigit() else value
                           for key, value in fields.items()})
            prepairs.append(record)
        elif kind == "RAIL_TARGET_REGEN_SHADOW":
            record = {"date": f"{_year}-{_month}-{_day}"}
            record.update({key: as_int(fields, key) if value.lstrip("-").isdigit() else value
                           for key, value in fields.items()})
            target_regen_shadows.append(record)
        elif kind == "RAIL_TARGET_CARGO_SHADOW":
            record = {"date": f"{_year}-{_month}-{_day}"}
            record.update({key: as_int(fields, key) if value.lstrip("-").isdigit() else value
                           for key, value in fields.items()})
            target_cargo_shadows.append(record)
        elif kind == "RAIL_TARGET_CARGO_SKIP":
            record = {"date": f"{_year}-{_month}-{_day}"}
            record.update({key: as_int(fields, key) if value.lstrip("-").isdigit() else value
                           for key, value in fields.items()})
            target_cargo_skips.append(record)
        elif kind == "VIVIER_REJECT" and fields.get("reason") == "origin_served":
            origin_rejects.append(as_int(fields, "n"))
        elif kind == "RAIL_ATTEMPT":
            rail_attempts += 1
            if as_int(fields, "reuse_alt") == 1:
                reuse_alt_attempts += 1
        elif kind == "RAIL_BUILD":
            rail_builds += 1
            if as_int(fields, "reuse_alt") == 1:
                reuse_alt_builds += 1
        elif kind == "RAIL_BUILD_FAIL":
            rail_failures[fields.get("reason", "?")] += 1
        elif kind == "PROJECT_CHOSEN":
            chosen[fields.get("mode", "?")] += 1
    return {
        "vivier_gen_events": len(vivier_kept),
        "vivier_kept_sum": sum(vivier_kept),
        "vivier_kept_mean": statistics.mean(vivier_kept) if vivier_kept else None,
        "vivier_produced_sum": sum(vivier_produced),
        "prepair_events": prepairs,
        "prepair_zero_produced": [event for event in prepairs if event.get("produced") == 0],
        "target_regen_shadows": target_regen_shadows,
        "target_regen_shadow_ops": sum(as_int(event, "ops") for event in target_regen_shadows),
        "target_regen_shadow_ticks": sum(as_int(event, "ticks") for event in target_regen_shadows),
        "target_cargo_shadows": target_cargo_shadows,
        "target_cargo_shadow_ops": sum(as_int(event, "opcodes") for event in target_cargo_shadows),
        "target_cargo_skips": target_cargo_skips,
        "origin_served_events": len(origin_rejects),
        "origin_served_sum": sum(origin_rejects),
        "origin_served_mean_nonzero": statistics.mean(origin_rejects) if origin_rejects else 0,
        "rail_attempts": rail_attempts,
        "rail_builds": rail_builds,
        "reuse_alt_attempts": reuse_alt_attempts,
        "reuse_alt_builds": reuse_alt_builds,
        "rail_build_failures": dict(sorted(rail_failures.items())),
        "trkfail": rail_failures.get("TRKFAIL", 0),
        "chosen_by_mode": dict(sorted(chosen.items())),
        "air_priority_observations": air_priority_observations,
        "air_priority_defers": air_priority_defers,
    }


def safe_delta(variant, reference):
    if variant is None or reference is None:
        return None
    return variant - reference


def final_summary(row):
    modes = row.get("primary_vehicles_by_mode") or {}
    stations = row.get("stations_by_facility") or {}
    return {
        "date": row.get("date"),
        "company_value": row.get("company_value"),
        "profit_year": row.get("profit_year"),
        "money": row.get("money"),
        "current_loan": row.get("current_loan"),
        "primary_vehicles": row.get("primary_vehicles"),
        "rail_vehicles": modes.get("rail"),
        "air_vehicles": modes.get("air"),
        "airports": row.get("air_airports"),
        "stations_total": row.get("n_stations"),
        "stations_by_facility": stations,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--seeds", nargs="+", type=int, default=[54321, 512, 123456, 4096])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--fallback", action="store_true",
        help="active rail_origin_reuse_fallback dans le bras variante",
    )
    parser.add_argument(
        "--pax-reuse", type=int, choices=(0, 1), default=1,
        help="sous-switch pax du bras variante (defaut 1 = candidat parent)",
    )
    parser.add_argument(
        "--freight-reuse", type=int, choices=(0, 1), default=1,
        help="sous-switch fret du bras variante (defaut 1 = candidat parent)",
    )
    parser.add_argument(
        "--air-priority-guard", action="store_true",
        help="compare le parent origin-reuse+shadow au meme bras avec garde AIR causale",
    )
    parser.add_argument(
        "--multiline-match", action="store_true",
        help="compare le parent origin-reuse au meme bras avec resolution de service multi-ligne",
    )
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "results" / "rail_origin_reuse_smoke_4x5_20261005.json",
    )
    args = parser.parse_args()
    if args.years > 5:
        raise SystemExit("ce diagnostic ciblé est volontairement limité à 5 ans")
    if not 1 <= args.workers <= 10:
        raise SystemExit("workers doit rester entre 1 et 10")

    if args.air_priority_guard and args.multiline_match:
        raise SystemExit("--air-priority-guard et --multiline-match sont deux interventions distinctes")
    if (args.air_priority_guard or args.multiline_match) and not args.fallback:
        raise SystemExit("les diagnostics isoles air-priority/multiline exigent --fallback")
    shared_origin_settings = None
    if args.air_priority_guard:
        base = "OpexAI[decision_log=1,rail_geometry_guard=1,rail_origin_reuse=1,rail_origin_reuse_fallback=1"
        base += f",rail_origin_reuse_pax={args.pax_reuse}"
        base += f",rail_origin_reuse_freight={args.freight_reuse}"
        reference = base + ",rail_origin_reuse_air_priority_shadow=1,rail_origin_reuse_air_priority=0]"
        variant = base + ",rail_origin_reuse_air_priority_shadow=1,rail_origin_reuse_air_priority=1]"
        shared_origin_settings = (
            ("decision_log", 1), ("rail_geometry_guard", 1), ("rail_origin_reuse", 1),
            ("rail_origin_reuse_fallback", 1), ("rail_origin_reuse_pax", args.pax_reuse),
            ("rail_origin_reuse_freight", args.freight_reuse),
            ("rail_origin_reuse_air_priority_shadow", 1),
        )
    elif args.multiline_match:
        base = "OpexAI[decision_log=1,rail_geometry_guard=1,rail_origin_reuse=1,rail_origin_reuse_fallback=1"
        base += f",rail_origin_reuse_pax={args.pax_reuse}"
        base += f",rail_origin_reuse_freight={args.freight_reuse}"
        reference = base + ",rail_origin_reuse_multiline_match=0]"
        variant = base + ",rail_origin_reuse_multiline_match=1]"
        shared_origin_settings = (
            ("decision_log", 1), ("rail_geometry_guard", 1), ("rail_origin_reuse", 1),
            ("rail_origin_reuse_fallback", 1), ("rail_origin_reuse_pax", args.pax_reuse),
            ("rail_origin_reuse_freight", args.freight_reuse),
        )
    else:
        reference = "OpexAI[decision_log=1,rail_geometry_guard=1,rail_origin_exposure_shadow=1,rail_origin_reuse=0]"
        variant = "OpexAI[decision_log=1,rail_geometry_guard=1,rail_origin_exposure_shadow=1,rail_target_cargo_prefilter=1,rail_origin_reuse=0]"
    arms = {
        reference: local_folder(
            str(ROOT / "ai" / "OpexAI"), "OpexAI",
            shared_origin_settings + (("rail_origin_reuse_air_priority", 0),)
            if args.air_priority_guard else
            shared_origin_settings + (("rail_origin_reuse_multiline_match", 0),)
            if args.multiline_match else
            (("decision_log", 1), ("rail_geometry_guard", 1),
             ("rail_origin_exposure_shadow", 1), ("rail_origin_reuse", 0)),
        ),
        variant: local_folder(
            str(ROOT / "ai" / "OpexAI"), "OpexAI",
            shared_origin_settings + (("rail_origin_reuse_air_priority", 1),)
            if args.air_priority_guard else
            shared_origin_settings + (("rail_origin_reuse_multiline_match", 1),)
            if args.multiline_match else
            (("decision_log", 1), ("rail_geometry_guard", 1),
             ("rail_origin_exposure_shadow", 1), ("rail_target_cargo_prefilter", 1),
             ("rail_origin_reuse", 0)),
        ),
    }
    arm_names = (reference, variant)
    cfg = make_cfg(STARTING_YEAR)
    experiments = [
        {
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (arms[arm],),
            "bench_run": [arm, seed, 0],
        }
        for arm in arm_names
        for seed in args.seeds
    ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.workers,
        result_processor=bench_keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row["run"])].append(row)

    per_run = {}
    for arm in arm_names:
        for seed in args.seeds:
            key = (arm, seed, 0)
            series = grouped.get(key, [])
            if not series:
                per_run[key] = {"ok": False, "error": "missing_run"}
                continue
            final = max(series, key=lambda row: row["date"])
            failure = script_failure_reason(final.get("openttd_output"))
            per_run[key] = {
                "ok": failure is None,
                "error": failure,
                "final": final_summary(final),
                "events": parse_rail_events(final.get("openttd_output")),
            }

    pairs = []
    for seed in args.seeds:
        ref = per_run[(reference, seed, 0)]
        var = per_run[(variant, seed, 0)]
        pair = {"seed": seed, "reference": ref, "variant": var, "deltas": {}}
        if ref.get("ok") and var.get("ok"):
            for metric in (
                "company_value", "profit_year", "money", "current_loan",
                "primary_vehicles", "rail_vehicles", "air_vehicles", "airports", "stations_total",
            ):
                pair["deltas"][metric] = safe_delta(
                    var["final"].get(metric), ref["final"].get(metric)
                )
            for metric in (
                "vivier_kept_sum", "vivier_produced_sum", "origin_served_sum",
                "rail_attempts", "rail_builds", "trkfail",
                "reuse_alt_attempts", "reuse_alt_builds",
                "air_priority_observations", "air_priority_defers",
            ):
                pair["deltas"][metric] = safe_delta(
                    var["events"].get(metric), ref["events"].get(metric)
                )
            pair["deltas"]["air_projects_chosen"] = (
                var["events"]["chosen_by_mode"].get("air", 0)
                - ref["events"]["chosen_by_mode"].get("air", 0)
            )
            pair["deltas"]["rail_projects_chosen"] = (
                var["events"]["chosen_by_mode"].get("rail", 0)
                - ref["events"]["chosen_by_mode"].get("rail", 0)
            )
        pairs.append(pair)

    aggregate = {}
    metric_names = sorted({key for pair in pairs for key in pair["deltas"]})
    for metric in metric_names:
        vals = [pair["deltas"].get(metric) for pair in pairs]
        vals = [value for value in vals if value is not None]
        aggregate[metric] = {
            "count": len(vals),
            "mean": statistics.mean(vals) if vals else None,
            "median": statistics.median(vals) if vals else None,
            "positive": sum(value > 0 for value in vals),
            "negative": sum(value < 0 for value in vals),
            "zero": sum(value == 0 for value in vals),
        }

    intervention = {
        "rail_origin_reuse": [0, 1],
        "rail_origin_reuse_fallback_variant": 1 if args.fallback else 0,
        "rail_origin_reuse_pax_variant": args.pax_reuse,
        "rail_origin_reuse_freight_variant": args.freight_reuse,
        "rail_origin_reuse_air_priority_guard": 0,
    }
    shared_nondefault = {"decision_log": 1, "rail_geometry_guard": 1}
    if args.air_priority_guard:
        intervention = {
            "rail_origin_reuse": [1, 1],
            "rail_origin_reuse_fallback": [1, 1],
            "rail_origin_reuse_pax": [args.pax_reuse, args.pax_reuse],
            "rail_origin_reuse_freight": [args.freight_reuse, args.freight_reuse],
            "rail_origin_reuse_air_priority_shadow": [1, 1],
            "rail_origin_reuse_air_priority": [0, 1],
        }
        shared_nondefault.update({
            "rail_origin_reuse": 1,
            "rail_origin_reuse_fallback": 1,
            "rail_origin_reuse_pax": args.pax_reuse,
            "rail_origin_reuse_freight": args.freight_reuse,
            "rail_origin_reuse_air_priority_shadow": 1,
        })
    elif args.multiline_match:
        intervention = {
            "rail_origin_reuse": [1, 1],
            "rail_origin_reuse_fallback": [1, 1],
            "rail_origin_reuse_pax": [args.pax_reuse, args.pax_reuse],
            "rail_origin_reuse_freight": [args.freight_reuse, args.freight_reuse],
            "rail_origin_reuse_multiline_match": [0, 1],
        }
        shared_nondefault.update({
            "rail_origin_reuse": 1,
            "rail_origin_reuse_fallback": 1,
            "rail_origin_reuse_pax": args.pax_reuse,
            "rail_origin_reuse_freight": args.freight_reuse,
        })

    payload = {
        "purpose": "paired causal smoke for rail origin reuse; diagnostic only",
        "years": args.years,
        "seeds": args.seeds,
        "workers": args.workers,
        "reference": reference,
        "variant": variant,
        "shared_nondefault": shared_nondefault,
        "intervention": intervention,
        "pairs": pairs,
        "aggregate_deltas_variant_minus_reference": aggregate,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, sort_keys=True))
    print(f"ecrit {args.out}")


if __name__ == "__main__":
    main()
