#!/usr/bin/env python3
"""C121 : shadow descriptif AIR unifie, sans effet de decision."""

from __future__ import annotations

import argparse
import contextlib
from datetime import date, timedelta
import functools
import importlib
import json
from pathlib import Path
import re
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg
from diag_c117_air_throughput import analyse
from diag_airport_delay_engine import extract_measurements as extract_air_timing

DEFAULT_SEEDS = (42, 100, 999, 1234, 5678)
C117_RE = re.compile(r"C117_AIR_THROUGHPUT\s+(.*)")
C121_RE = re.compile(r"C121_BUILD\s+(.*)")
C121_HUB_RE = re.compile(r"C121_HUB_DELAY\s+(.*)")
AIR_PLAN_PERF_RE = re.compile(r"AIR_PLAN_PERF:\s+(.*)")
LINE_TELEMETRY = False

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


if not getattr(openttdlab.subprocess.check_output, "_c121_script_debug", False):
    _check_output_with_script_debug._c121_script_debug = True
    openttdlab.subprocess.check_output = _check_output_with_script_debug


def cached_bananas_ai_library(unique_id: str, name: str):
    """Utilise le cache OpenTTDLab complet avant de consulter BaNaNaS.

    ``download_from_bananas`` interroge l'API avant de regarder son propre cache.
    Pour un banc reproductible deja chauffe, cela rend inutilement le lancement
    dependant d'une panne HTTP. Le format relu ici est exactement le fichier
    ``*_dependencies`` ecrit par OpenTTDLab lui-meme ; si une piece manque on
    retombe sur le comportement upstream normal.
    """
    version = getattr(openttdlab, "__version__", "")
    cache = Path.home() / ".cache" / "OpenTTDLab" / version / "bananas"
    dependency_files = sorted(cache.glob(f"{unique_id}-{name}-*.tar_dependencies"))
    if not dependency_files:
        return bananas_ai_library(unique_id, name)
    dependency_file = dependency_files[-1]
    rows = []
    for line in dependency_file.read_text(encoding="utf-8").splitlines():
        parts = line.split(",")
        if len(parts) != 4:
            return bananas_ai_library(unique_id, name)
        content_id, filename, license_name, md5 = parts
        path = cache / filename
        if not path.is_file():
            return bananas_ai_library(unique_id, name)
        rows.append((content_id, filename, license_name, md5, path))

    @contextlib.contextmanager
    def copy_cached(get_http_client, get_cache_dir):
        yield [
            (content_id, filename, license_name, md5,
             functools.partial(openttdlab._file_contents, str(path)))
            for content_id, filename, license_name, md5, path in rows
        ]

    return name, copy_cached


@contextlib.contextmanager
def opex_source_for_shadow():
    """Source C121 normale : aucun catalogue PASS/MAIL externe n'est injecte."""
    yield ROOT / "ai" / "OpexAI"


def parse_value(value: str):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_fields(text: str):
    fields = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        fields[key] = parse_value(value)
    return fields


def keep(row):
    experiment = row.get("experiment", {})
    seed = experiment.get("seed")
    date_s = str(row.get("date", ""))
    days = int(experiment.get("days", 0) or 0)
    final_date = date(1970, 1, 1) + timedelta(days=days)
    try:
        row_date = date.fromisoformat(date_s[:10])
    except ValueError:
        return ()
    if row_date < final_date - timedelta(days=31) or row_date > final_date:
        return ()
    output = row.get("output", "") or ""
    output_lower = output.lower()
    events = [parse_fields(fields) for fields in C117_RE.findall(output)]
    builds = [parse_fields(fields) for fields in C121_RE.findall(output)]
    hub_delays = [parse_fields(fields) for fields in C121_HUB_RE.findall(output)]
    plan_perf = [parse_fields(fields) for fields in AIR_PLAN_PERF_RE.findall(output)]
    timing = extract_air_timing(row.get("chunks") or {}, seed, date_s)
    line_telemetry = None
    if LINE_TELEMETRY:
        # Post-traitement du savegame uniquement : aucun opcode NoAI ni effet
        # causal. Reutilise le decodeur deja valide du banc 1v1 pour obtenir
        # rating/time_since_pickup/max_waiting_cargo par endpoint et cargo.
        from bench_1v1_5y_20seeds import extract_line_telemetry
        line_telemetry = extract_line_telemetry(row.get("chunks") or {}, 0)
    return ({
        "seed": seed,
        "date": date_s,
        "events": events,
        "c121_builds": builds,
        "hub_delay_updates": hub_delays,
        "air_plan_perf": plan_perf,
        "timing_measurements": timing,
        "line_telemetry": line_telemetry,
        "event_count": len(events),
        "c121_build_count": len(builds),
        "hub_delay_update_count": len(hub_delays),
        "air_plan_perf_count": len(plan_perf),
        "had_script_error": "script died unexpectedly" in output_lower or "script error" in output_lower,
        "output_tail": output[-16000:],
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--engine-replay", action="store_true",
        help="Active le replay passif moteur/flotte C121 sur les capacites PASS/MAIL deja observees",
    )
    parser.add_argument(
        "--line-telemetry", action="store_true",
        help="Diagnostic host-only du savegame final: lignes + station.goods par cargo",
    )
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "results" / "c121_air_economics_shadow_5x6_20260928.json",
    )
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers doit etre entre 1 et 6")
    global LINE_TELEMETRY
    LINE_TELEMETRY = bool(args.line_telemetry)
    enable_savegame_cleanup()
    settings = (
        ("save_full_state", 0),
        ("c115_air_c100_capital_replay", 1),
        ("c117_air_throughput_probe", 1),
        ("c121_air_economics_shadow", 1),
        ("c121_air_economics", 0),
        ("c121_air_engine_replay_shadow", 1 if args.engine_replay else 0),
        ("b9_air_demand_shadow", 0),
    )
    with opex_source_for_shadow() as opex_source:
        opex = local_folder(str(opex_source), "OpexAI", settings)
        cfg = make_cfg(1970)
        experiments = [
            {
                "bench_context": "solo",
                "bench_arm": "OpexAI[C115=1,C117=1,C121-shadow=1,engine-replay="
                             + ("1" if args.engine_replay else "0") + "]",
                "seed": seed,
                "days": 365 * args.years,
                "openttd_config": cfg,
                "ais": (opex,),
            }
            for seed in args.seeds
        ]
        processor_module = importlib.import_module("run_c121_air_economics_shadow")
        # result_processor est le module reimporte, distinct de __main__ :
        # propager explicitement le flag host-only sinon keep() conserve False.
        processor_module.LINE_TELEMETRY = LINE_TELEMETRY
        rows = list(run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            experiments=experiments,
            max_workers=args.workers,
            result_processor=processor_module.keep,
            ai_libraries=(
                cached_bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                cached_bananas_ai_library("5046524c", "Pathfinder.Rail"),
            ),
        ))
    checkpoint_rows = list(rows)
    latest_by_seed = {}
    for row in checkpoint_rows:
        seed = row.get("seed")
        if seed is None:
            continue
        previous = latest_by_seed.get(seed)
        if previous is None or row.get("date", "") > previous.get("date", ""):
            latest_by_seed[seed] = row
    rows = [latest_by_seed[seed] for seed in args.seeds if seed in latest_by_seed]
    analysis = analyse(rows)
    failed = []
    for seed in args.seeds:
        seed_rows = [row for row in rows if row.get("seed") == seed]
        if not seed_rows:
            failed.append({"seed": seed, "reason": "missing"})
        elif any(row.get("had_script_error") for row in seed_rows):
            failed.append({"seed": seed, "reason": "script_error"})
        elif not any(row.get("event_count", 0) > 0 for row in seed_rows):
            failed.append({"seed": seed, "reason": "no_c117_events"})
        elif not any(row.get("c121_build_count", 0) > 0 for row in seed_rows):
            failed.append({"seed": seed, "reason": "no_c121_builds"})

    payload = {
        "campaign_id": args.out.stem,
        "purpose": "C121 passive unified AIR economics shadow; no decision change",
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "workers": args.workers,
        "settings": dict(settings),
        "health": {
            "expected_runs": len(args.seeds),
            "observed_runs": len(rows),
            "checkpoint_rows": len(checkpoint_rows),
            "failed_runs": failed,
            "all_runs_healthy": len(rows) == len(args.seeds) and not failed,
        },
        "rows": rows,
        "analysis": analysis,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "health": payload["health"],
        "c117_event_count": analysis["event_count"],
        "line_count": analysis["line_count"],
        "c121_build_count": sum(row.get("c121_build_count", 0) for row in rows),
        "hub_delay_update_count": sum(row.get("hub_delay_update_count", 0) for row in rows),
        "overall": analysis["overall"],
    }, indent=2))
    print(f"Sortie: {args.out}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
