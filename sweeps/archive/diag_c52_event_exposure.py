"""Diagnostic C52 : frequence REELLE de chaque evenement dans la fenetre du banc.

⚠️ RAISON D'ETRE. Le tableau des neuf taches de la fiche C52 est classe "par valeur/risque
decroissant" -- mais ce classement est une INTUITION. Deux resultats du 2026-09-11 l'ont mise en
defaut : C55 a rendu un verdict nul au banc apres un diagnostic prometteur, et la tache C52 #1,
classee premiere, s'est revelee ne rien reparer (33 renouvellements en 16 ans, tous routiers, tous
hors inventaire). Ce diagnostic remplace l'intuition par un comptage.

Lecture : un evenement a frequence NULLE dans la fenetre ne peut pas porter de gain mesurable, quel
que soit son rang dans la fiche. Un evenement frequent merite d'etre regarde meme s'il est mal
classe. Le comptage se fait AVANT toute branche de _processEvents, donc aucun `continue` existant
ne peut rendre un evenement invisible.

`vehicle_unprofitable_distinct` compte les VEHICULES distincts de l'annee, pas les signalements :
un meme vehicule signale douze fois n'est pas douze problemes.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, keep, summarise, write_json_atomically,
)
import bench_v2

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

ARM = "OpexAI[c52_event_exposure_probe=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C52_EVENT_EXPOSURE\s*(.*)")
FIELDS = (
    "vehicle_crashed", "crashed_train", "crashed_other", "vehicle_waiting_in_depot",
    "industry_open", "industry_close", "town_founded", "engine_available", "vehicle_lost",
    "subsidy_offer", "subsidy_offer_expired", "subsidy_awarded", "subsidy_expired",
    "vehicle_autoreplaced", "vehicle_unprofitable", "vehicle_unprofitable_distinct",
    "aircraft_dest_too_far", "station_first_vehicle", "road_reconstruction", "engine_preview",
    "exclusive_transport_rights", "other",
)
# Les evenements que la fiche C52 designe comme jamais ecoutes : ce sont eux que le diagnostic
# doit trancher. Les autres ne servent que de base de comparaison.
TASK_FIELDS = (
    "crashed_other", "vehicle_unprofitable_distinct", "aircraft_dest_too_far",
    "station_first_vehicle", "road_reconstruction", "vehicle_autoreplaced",
    "engine_preview", "exclusive_transport_rights",
)


def parse_fields(fields):
    return dict(token.split("=", 1) for token in fields.split() if "=" in token)


def parse_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def numeric(event):
    return {field: int(event.get(field, 0)) for field in FIELDS}


def build_metrics(events):
    annual = {}
    for event in events:
        if "year" not in event or event.get("phase") != "annual":
            continue
        year = int(event["year"])
        entry = annual.setdefault(year, {field: 0 for field in FIELDS})
        for field, value in numeric(event).items():
            entry[field] += value
    by_year = [{"year": year, **annual[year]} for year in sorted(annual)]
    cumulative = {field: 0 for field in FIELDS}
    for row in by_year:
        for field in FIELDS:
            cumulative[field] += row[field]
    return {"by_year": by_year, "cumulative": cumulative}


def run_selftest():
    line = ("OPEX 1975-1-1 C52_EVENT_EXPOSURE phase=annual year=1975 "
            + " ".join(f"{field}=1" for field in FIELDS))
    other = ("OPEX 1976-1-1 C52_EVENT_EXPOSURE phase=summary year=1976 "
             + " ".join(f"{field}=99" for field in FIELDS))
    metrics = build_metrics(parse_events(line + "\n" + other))
    assert len(metrics["by_year"]) == 1, metrics
    assert metrics["cumulative"]["vehicle_crashed"] == 1, metrics
    # La ligne summary est cumulative : elle ne doit jamais entrer dans le total annuel.
    assert metrics["cumulative"]["other"] == 1, metrics
    print("selftest ok")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 2026])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return

    out = args.out or ROOT / "results" / f"diag_c52_event_exposure_{args.years}y_{len(args.seeds)}seeds.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    built = build_arms([ARM])
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(built, args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    per_seed = []
    for record in summary:
        output = record.pop("openttd_output", "")
        per_seed.append({
            "seed": record["seed"],
            "run_ok": record["run_ok"],
            "failure_reason": record.get("failure_reason"),
            "metrics": build_metrics(parse_events(output)),
        })
    total = {field: 0 for field in FIELDS}
    for entry in per_seed:
        for field in FIELDS:
            total[field] += entry["metrics"]["cumulative"][field]
    failed = [entry for entry in per_seed if not entry["run_ok"]]
    payload = {
        "arm": ARM, "years": args.years, "seeds": args.seeds,
        "per_seed": per_seed, "cumulative": total,
        "task_fields": list(TASK_FIELDS),
        "failed_run_count": len(failed),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    print("--- evenements PORTEURS DE TACHE (jamais ecoutes aujourd'hui) ---")
    for field in TASK_FIELDS:
        print(f"  {field:34s} {total[field]:6d}")
    print("--- base de comparaison (deja ecoutes) ---")
    for field in FIELDS:
        if field not in TASK_FIELDS:
            print(f"  {field:34s} {total[field]:6d}")
    if failed:
        raise SystemExit(f"diagnostic invalide: {len(failed)} echec(s) NoAI")


if __name__ == "__main__":
    main()
