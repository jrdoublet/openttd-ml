"""Diagnostic C52 #1 : le remappage d'ID apres renouvellement automatique s'execute-t-il ?

⚠️ RAISON D'ETRE, a lire avant de changer la fenetre. L'evenement `ET_VEHICLE_AUTOREPLACED` ne
peut PAS se produire dans le banc officiel 1970-1980 : le renouvellement se declenche six mois
avant l'age maximal, un camion vit ~12 ans (`ai/OpexAI/main.nut:8280-8286`, campagne 20 ans), et
OpexAI ne possede aucune flotte au 1er janvier 1970. Le premier remplacement tombe vers 1981-1982.

Ce diagnostic est donc le SEUL endroit ou le code du handler est reellement execute. Un smoke ou un
banc 10 ans ne le traverse jamais : ils valident que l'enum `AIEvent.ET_VEHICLE_AUTOREPLACED`
existe (le test est evalue a chaque tour de boucle), mais jamais le `Convert` ni les accesseurs.
**Ne pas raccourcir la fenetre sous 14 ans : le diagnostic deviendrait silencieusement vide.**

Un resultat `events = 0` ne prouve pas que la correction est inutile : il prouve que la fenetre est
trop courte. C'est `events > 0` qui valide le nom de classe et des accesseurs.
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

ARM = "OpexAI[probe_events=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C52_AUTOREPLACE\s*(.*)")
# rail/road/air/water/unknown : type du VEHICULE renouvele (AIVehicle.GetVehicleType du nouvel ID).
# line_* : mode de la LIGNE ou l'ancien ID a ete retrouve -- nul quand l'evenement est untracked.
FIELDS = ("events", "remap_line_vehicles", "remap_line_vehicle", "remap_scrap_vehicles",
          "remap_scrap_index", "untracked", "rail", "road", "air", "water", "unknown",
          "line_rail", "line_road", "line_air", "line_water")


def parse_fields(fields):
    return dict(token.split("=", 1) for token in fields.split() if "=" in token)


def parse_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def numeric(event):
    return {field: int(event.get(field, 0)) for field in FIELDS}


def build_metrics(events):
    annual = {}
    summaries = []
    for event in events:
        if "year" not in event:
            continue
        if event.get("phase") == "annual":
            year = int(event["year"])
            entry = annual.setdefault(year, {field: 0 for field in FIELDS})
            for field, value in numeric(event).items():
                entry[field] += value
        elif event.get("phase") == "summary":
            summaries.append((int(event["year"]), numeric(event)))
    by_year = [{"year": year, **annual[year]} for year in sorted(annual)]
    cumulative = {field: 0 for field in FIELDS}
    for row in by_year:
        for field in FIELDS:
            cumulative[field] += row[field]
    return {"by_year": by_year, "cumulative": cumulative,
            "last_summary": ({"year": summaries[-1][0], **summaries[-1][1]}
                             if summaries else None)}


def run_selftest():
    output = "\n".join((
        "OPEX 1982-1-1 C52_AUTOREPLACE phase=annual year=1982 events=3 remap_line_vehicles=2 "
        "remap_line_vehicle=1 remap_scrap_vehicles=0 remap_scrap_index=0 untracked=1 rail=1 "
        "road=1 air=1 water=0 unknown=0 line_rail=1 line_road=1 line_air=0 line_water=0",
        "OPEX 1983-1-1 C52_AUTOREPLACE phase=annual year=1983 events=2 remap_line_vehicles=2 "
        "remap_line_vehicle=0 remap_scrap_vehicles=1 remap_scrap_index=1 untracked=0 rail=2 "
        "road=0 air=0 water=0 unknown=0 line_rail=2 line_road=0 line_air=0 line_water=0",
    ))
    metrics = build_metrics(parse_events(output))
    assert metrics["cumulative"]["events"] == 5, metrics
    assert metrics["cumulative"]["remap_line_vehicles"] == 4, metrics
    assert metrics["cumulative"]["untracked"] == 1, metrics
    assert metrics["cumulative"]["line_rail"] == 3, metrics
    assert len(metrics["by_year"]) == 2, metrics
    print("selftest ok")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=14,
                        help="14 minimum : sous ce seuil l'evenement ne peut pas se produire")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years < 14:
        parser.error("--years < 14 : la fenetre serait trop courte pour que l'evenement existe")

    out = args.out or ROOT / "results" / f"diag_c52_autoreplace_{args.years}y_{len(args.seeds)}seeds.json"
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
        "failed_run_count": len(failed),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    print("cumule:", json.dumps(total))
    if total["events"] == 0:
        print("⚠️ events=0 : la fenetre est trop courte OU le handler n'est jamais atteint.")
    if failed:
        raise SystemExit(f"diagnostic invalide: {len(failed)} echec(s) NoAI")


if __name__ == "__main__":
    main()
