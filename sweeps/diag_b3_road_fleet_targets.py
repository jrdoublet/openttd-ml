"""B3 : diagnostic apparié du plafond temporel de flotte routière.

Compare road_time_scaled_cap=0 et =1 sur les mêmes graines, avec decision_log=1 dans
les deux bras. Diagnostic seulement : aucun verdict d'adoption n'est rendu ici.
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
    summarise as bench_summarise,
)
from game_health import assess_game, annotate_summary  # noqa: E402

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


def as_int(fields, key, default=None):
    try:
        return int(fields[key])
    except (KeyError, TypeError, ValueError):
        return default


def parse_fleet_events(output):
    ranking, chosen, lines = [], [], []
    errors = []
    for raw_line in (output or "").splitlines():
        match = OPEX_EVENT_RE.search(raw_line)
        if not match:
            continue
        year, month, day, event_kind, rest = match.groups()
        fields = fields_from(rest)
        if fields.get("mode") != "road" and event_kind != "LINE_REVENUE":
            continue
        if event_kind == "LINE_REVENUE" and fields.get("mode") != "road":
            continue

        base = {
            "date": f"{year}-{int(month):02d}-{int(day):02d}",
            "kind": fields.get("kind", "unknown"),
            "purpose": fields.get("purpose", "unknown"),
        }
        if event_kind in ("PORTFOLIO_RANK", "PROJECT_CHOSEN"):
            required = ("raw_vehs", "berth_cap", "fleet_cap", "capped_vehs")
            missing = [key for key in required if key not in fields]
            if missing:
                errors.append(
                    f"{event_kind} missing={','.join(missing)} line={raw_line.strip()[:240]}"
                )
                continue
            event = dict(base)
            event.update({key: as_int(fields, key) for key in required})
            event["rank"] = as_int(fields, "rank", -1)
            event["src"] = as_int(fields, "src", -1)
            event["dst"] = as_int(fields, "dst", -1)
            (ranking if event_kind == "PORTFOLIO_RANK" else chosen).append(event)

        elif event_kind == "LINE_REVENUE":
            required = (
                "raw_vehs",
                "pred_berth_cap",
                "pred_vehicle_cap",
                "berth_cap",
                "vehicle_cap",
                "pred_vehs",
                "vehs",
                "n_stops_a",
                "n_stops_b",
                "extra_stops",
            )
            missing = [key for key in required if key not in fields]
            if missing:
                errors.append(
                    f"LINE_REVENUE missing={','.join(missing)} line={raw_line.strip()[:240]}"
                )
                continue
            event = dict(base)
            event.update({key: as_int(fields, key) for key in required})
            event["line"] = as_int(fields, "line", -1)
            event["age"] = as_int(fields, "age", -1)
            lines.append(event)

    return {"ranking": ranking, "chosen": chosen, "lines": lines, "errors": errors}


def target_summary(items, selected_key, vehicle_cap_key="fleet_cap", berth_key="berth_cap"):
    if not items:
        return {
            "count": 0,
            "raw_gt_berth": 0,
            "raw_gt_vehicle_cap": 0,
            "raw_gt_selected": 0,
            "vehicle_cap_gt_berth": 0,
            "selected_gt_vehicle_cap": 0,
            "raw_max": None,
            "berth_max": None,
            "vehicle_cap_max": None,
            "selected_max": None,
        }
    return {
        "count": len(items),
        "raw_gt_berth": sum(item["raw_vehs"] > item[berth_key] for item in items),
        "raw_gt_vehicle_cap": sum(
            item["raw_vehs"] > item[vehicle_cap_key] for item in items
        ),
        "raw_gt_selected": sum(item["raw_vehs"] > item[selected_key] for item in items),
        "vehicle_cap_gt_berth": sum(
            item[vehicle_cap_key] > item[berth_key] for item in items
        ),
        "selected_gt_vehicle_cap": sum(
            item[selected_key] > item[vehicle_cap_key] for item in items
        ),
        "raw_max": max(item["raw_vehs"] for item in items),
        "berth_max": max(item[berth_key] for item in items),
        "vehicle_cap_max": max(item[vehicle_cap_key] for item in items),
        "selected_max": max(item[selected_key] for item in items),
    }


def line_summary(items):
    summary = target_summary(
        items,
        selected_key="pred_vehs",
        vehicle_cap_key="vehicle_cap",
        berth_key="berth_cap",
    )
    summary.update(
        {
            "actual_below_raw": sum(item["vehs"] < item["raw_vehs"] for item in items),
            "actual_gt_vehicle_cap": sum(
                item["vehs"] > item["vehicle_cap"] for item in items
            ),
            "actual_at_or_above_berth": sum(
                item["vehs"] >= item["berth_cap"] for item in items
            ),
            "with_extra_stops": sum(item["extra_stops"] > 0 for item in items),
            "extra_stops_but_base_stop_counts": sum(
                item["extra_stops"] > 0
                and item["n_stops_a"] == 1
                and item["n_stops_b"] == 1
                for item in items
            ),
        }
    )
    return summary


def summarise_events(events):
    by_kind = {}
    kinds = sorted(
        {
            event["kind"]
            for group in ("ranking", "chosen", "lines")
            for event in events[group]
        }
    )
    for kind in kinds:
        ranks = [e for e in events["ranking"] if e["kind"] == kind]
        chosen = [e for e in events["chosen"] if e["kind"] == kind]
        lines = [e for e in events["lines"] if e["kind"] == kind]
        by_kind[kind] = {
            "ranking": target_summary(ranks, "capped_vehs"),
            "chosen": target_summary(chosen, "capped_vehs"),
            "lines": line_summary(lines),
        }

    violations = []
    for label in ("ranking", "chosen"):
        for event in events[label]:
            if event["capped_vehs"] > event["fleet_cap"]:
                violations.append(
                    {"scope": label, "reason": "selected_gt_vehicle_cap", **event}
                )
    for event in events["lines"]:
        if event["vehs"] > event["vehicle_cap"]:
            violations.append({"scope": "lines", "reason": "actual_gt_vehicle_cap", **event})

    return {
        "ranking": target_summary(events["ranking"], "capped_vehs"),
        "chosen": target_summary(events["chosen"], "capped_vehs"),
        "lines": line_summary(events["lines"]),
        "road_line_kinds": dict(Counter(event["kind"] for event in events["lines"])),
        "road_line_purposes": dict(Counter(event["purpose"] for event in events["lines"])),
        "by_kind": by_kind,
        "errors": list(events["errors"]),
        "violations": violations[:20],
    }


def health_summary(rows, arm_name, years):
    series = sorted(rows, key=lambda row: row["date"])
    final_output = series[-1].get("openttd_output") or ""
    assessment = assess_game(
        series,
        starting_year=STARTING_YEAR,
        years=years,
        expected_companies=(arm_name,),
        slot_map={0: {"company_id": 0, "name": arm_name}},
        engine_log=final_output,
    )
    part = bench_summarise(
        series,
        expected_last_year=STARTING_YEAR + years - 1,
        expected_savegames=years * 12,
    )
    annotated = annotate_summary(part, series, assessment)
    if len(annotated) != 1:
        raise AssertionError(f"résumé inattendu pour {arm_name}: {len(annotated)}")
    return annotated[0], assessment


def safe_delta(variant, reference):
    if variant is None or reference is None:
        return None
    return variant - reference


def selftest():
    sample = "\n".join(
        (
            "OPEX 1970-01-01 PORTFOLIO_RANK rank=0 mode=road kind=pax "
            "raw_vehs=7 berth_cap=2 fleet_cap=5 capped_vehs=5",
            "OPEX 1970-01-02 PROJECT_CHOSEN rank=0 mode=road kind=freight src=10 dst=20 "
            "raw_vehs=6 berth_cap=2 fleet_cap=2 capped_vehs=2",
            "OPEX 1971-01-01 LINE_REVENUE line=3 mode=road kind=pax age=1 purpose=profit "
            "raw_vehs=6 pred_berth_cap=2 pred_vehicle_cap=5 berth_cap=2 vehicle_cap=5 "
            "pred_vehs=5 vehs=4 n_stops_a=1 n_stops_b=1 extra_stops=1",
        )
    )
    events = parse_fleet_events(sample)
    assert not events["errors"], events["errors"]
    summary = summarise_events(events)
    assert summary["ranking"]["vehicle_cap_gt_berth"] == 1
    assert summary["chosen"]["vehicle_cap_gt_berth"] == 0
    assert summary["by_kind"]["freight"]["chosen"]["vehicle_cap_max"] == 2
    assert summary["lines"]["actual_gt_vehicle_cap"] == 0
    assert summary["lines"]["extra_stops_but_base_stop_counts"] == 1
    print("selftest OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "review_b3_time_scaled_cap_paired_5x6.json",
    )
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return

    reference = "OpexAI[decision_log=1,road_time_scaled_cap=0]"
    variant = "OpexAI[decision_log=1,road_time_scaled_cap=1]"
    arm_names = (reference, variant)
    arms = {
        reference: local_folder(
            str(ROOT / "ai" / "OpexAI"), "OpexAI",
            (("decision_log", 1), ("road_time_scaled_cap", 0)),
        ),
        variant: local_folder(
            str(ROOT / "ai" / "OpexAI"), "OpexAI",
            (("decision_log", 1), ("road_time_scaled_cap", 1)),
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()

    cfg = make_cfg(STARTING_YEAR)
    experiments = [
        {
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (arms[arm_name],),
            "bench_run": [arm_name, seed, 0],
        }
        for arm_name in arm_names
        for seed in args.seeds
    ]

    enable_savegame_cleanup()
    rows = list(
        run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            experiments=experiments,
            max_workers=args.workers,
            result_processor=bench_keep,
            ai_libraries=(
                bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                bananas_ai_library("5046524c", "Pathfinder.Rail"),
            ),
        )
    )

    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row["run"])].append(row)

    finals = {}
    fleet = {}
    health = {}
    for arm_name in arm_names:
        for seed in args.seeds:
            key = (arm_name, seed, 0)
            series = grouped.get(key, [])
            if not series:
                health[key] = {
                    "run_ok": False,
                    "failure_reason": "missing_run",
                    "horizon_complete": False,
                    "status": "missing_data",
                }
                fleet[key] = summarise_events(
                    {"ranking": [], "chosen": [], "lines": [], "errors": ["missing_run"]}
                )
                continue
            final = max(series, key=lambda row: row["date"])
            final_summary, assessment = health_summary(series, arm_name, args.years)
            finals[key] = final_summary
            health[key] = {
                "run_ok": final_summary.get("run_ok"),
                "status": final_summary.get("status"),
                "failure_reason": final_summary.get("failure_reason"),
                "last_date": final_summary.get("last_date"),
                "horizon_complete": final_summary.get("horizon_complete"),
                "n_savegames": final_summary.get("n_savegames"),
                "game_ok": assessment.get("game_ok"),
                "game_status": assessment.get("game_status"),
            }
            events = parse_fleet_events(final.get("openttd_output"))
            fleet[key] = summarise_events(events)

    pairs = []
    for seed in args.seeds:
        ref_key = (reference, seed, 0)
        var_key = (variant, seed, 0)
        ref = finals.get(ref_key, {})
        var = finals.get(var_key, {})
        ref_fleet = fleet[ref_key]
        var_fleet = fleet[var_key]
        pair = {
            "seed": seed,
            "health": {
                "reference": health[ref_key],
                "variant": health[var_key],
            },
            "economics": {},
            "fleet": {
                "reference": ref_fleet,
                "variant": var_fleet,
            },
        }
        for metric in (
            "company_value",
            "profit_year",
            "performance_history",
            "primary_vehicles",
        ):
            pair["economics"][metric] = {
                "reference": ref.get(metric),
                "variant": var.get(metric),
                "delta": safe_delta(var.get(metric), ref.get(metric)),
            }
        ref_road = (ref.get("primary_vehicles_by_mode") or {}).get("road")
        var_road = (var.get("primary_vehicles_by_mode") or {}).get("road")
        pair["economics"]["road_primary_vehicles"] = {
            "reference": ref_road,
            "variant": var_road,
            "delta": safe_delta(var_road, ref_road),
        }
        pairs.append(pair)

    deltas = {}
    for metric in (
        "company_value",
        "profit_year",
        "performance_history",
        "primary_vehicles",
        "road_primary_vehicles",
    ):
        vals = [
            pair["economics"][metric]["delta"]
            for pair in pairs
            if pair["economics"][metric]["delta"] is not None
        ]
        deltas[metric] = {
            "count": len(vals),
            "mean": statistics.mean(vals) if vals else None,
            "median": statistics.median(vals) if vals else None,
            "wins": sum(value > 0 for value in vals),
            "losses": sum(value < 0 for value in vals),
            "ties": sum(value == 0 for value in vals),
        }

    all_health_ok = all(
        pair["health"][arm]["run_ok"]
        and pair["health"][arm]["horizon_complete"]
        and pair["health"][arm]["game_ok"]
        for pair in pairs
        for arm in ("reference", "variant")
    )
    fields_complete = all(
        not pair["fleet"][arm]["errors"]
        for pair in pairs
        for arm in ("reference", "variant")
    )

    def kind_blocks(arm, kind):
        return [
            pair["fleet"][arm]["by_kind"][kind]
            for pair in pairs
            if kind in pair["fleet"][arm]["by_kind"]
        ]

    def caps_equal_berth(block):
        return (
            block["ranking"]["vehicle_cap_gt_berth"] == 0
            and block["chosen"]["vehicle_cap_gt_berth"] == 0
            and block["lines"]["vehicle_cap_gt_berth"] == 0
        )

    reference_pax = kind_blocks("reference", "pax")
    reference_freight = kind_blocks("reference", "freight")
    variant_pax = kind_blocks("variant", "pax")
    variant_freight = kind_blocks("variant", "freight")

    invariants = {
        "all_runs_healthy_complete_horizon": all_health_ok,
        "fields_complete": fields_complete,
        "reference_pax_cap_equals_berth": bool(reference_pax)
        and all(caps_equal_berth(block) for block in reference_pax),
        "reference_freight_cap_equals_berth": bool(reference_freight)
        and all(caps_equal_berth(block) for block in reference_freight),
        "variant_freight_cap_equals_berth": bool(variant_freight)
        and all(caps_equal_berth(block) for block in variant_freight),
        "variant_pax_temporal_cap_exercised": bool(variant_pax)
        and any(
            block[scope]["vehicle_cap_gt_berth"] > 0
            for block in variant_pax
            for scope in ("ranking", "chosen", "lines")
        ),
        "variant_pax_cap_bounded_by_max_road_vehicles": bool(variant_pax)
        and all(
            (block[scope]["vehicle_cap_max"] is None or block[scope]["vehicle_cap_max"] <= 8)
            for block in variant_pax
            for scope in ("ranking", "chosen", "lines")
        ),
        "no_logged_selected_or_actual_above_vehicle_cap": all(
            not pair["fleet"][arm]["violations"]
            for pair in pairs
            for arm in ("reference", "variant")
        ),
    }

    payload = {
        "purpose": (
            "B3 paired diagnostic: raw demand target vs simultaneous berth capacity vs "
            "time-scaled vehicle cap vs actual road fleet; no adoption verdict"
        ),
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "workers": args.workers,
        "arms": {"reference": reference, "variant": variant},
        "explicit_settings": {
            "reference": {"decision_log": 1, "road_time_scaled_cap": 0},
            "variant": {"decision_log": 1, "road_time_scaled_cap": 1},
        },
        "pairs": pairs,
        "paired_deltas": deltas,
        "invariants": invariants,
        "complete_pairs": sum(
            pair["health"]["reference"]["run_ok"] and pair["health"]["variant"]["run_ok"]
            for pair in pairs
        ),
        "planned_pairs": len(args.seeds),
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"paired_deltas": deltas, "invariants": invariants}, sort_keys=True))
    print(f"ecrit {args.out}")


if __name__ == "__main__":
    main()
