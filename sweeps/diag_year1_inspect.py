"""Chronologie fine et comparaison des lignes de l'Annee 1 (1970) sur la graine 42.

Lit les logs -d script=4 des deux IA pour reconstituer :
1. L'agenda mensuel d'AAAHogEx : quelles lignes, quels modes, quelles villes, combien de vehicules.
2. L'agenda mensuel d'OpexAI : quelles lignes, quels modes, quelles villes.
3. Le vivier d'OpexAI : pourquoi OpexAI n'a pas fait de rail ? Pourquoi une seule ligne air ?
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import make_cfg

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"

_real_check_output = openttdlab.subprocess.check_output

def _hook(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)

openttdlab.subprocess.check_output = _hook

def keep(row):
    return ({
        "arm": row["experiment"]["arm_name"],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "output": row.get("output", ""),
    },)

def main():
    cfg = make_cfg(1970)
    experiments = [
        {
            "arm_name": "AAAHogEx",
            "seed": 42,
            "days": 365,
            "openttd_config": cfg,
            "ais": (local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ()),),
        },
        {
            "arm_name": "OpexAI",
            "seed": 42,
            "days": 365,
            "openttd_config": cfg,
            "ais": (local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("decision_log", 1),)),),
        },
    ]

    print("Execution du diagnostic 1 an sur graine 42...")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=2,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    logs = {r["arm"]: r["output"] for r in rows if r.get("output")}

    # 1. Analyser AAAHogEx
    print("\n" + "=" * 100)
    print("CHRONOLOGIE DETAILLEE AAAHOGEX (1970)")
    print("=" * 100)
    hog_output = logs.get("AAAHogEx", "")
    hog_events = []
    for line in hog_output.splitlines():
        # Lignes avec date : YYYY-M-D ...
        m = re.search(r"(\d{4}-\d{1,2}-\d{1,2})\s+(.*)", line)
        if not m:
            continue
        dt, content = m.group(1), m.group(2)
        if any(kw in content for kw in [
            "RouteBuilder Start Build",
            "RouteBuilder Succeeded",
            "RouteBuilder Failed",
            "BuildFirstTrain",
            "BuildTrain",
            "BuildAircraft",
            "BuildRoadVehicle",
            "ChooseEngine",
            "TrainRoute railType",
            "AddPlace",
            "CommonRouteBuilder.Build succeeded",
        ]):
            if not any(ign in content for ign in ["EstimateCargoProductions", "Cannot ShareOrders"]):
                hog_events.append((dt, content))

    opex_output = logs.get("OpexAI", "")
    opex_events = []
    for line in opex_output.splitlines():
        if "OPEX " in line:
            m = re.search(r"OPEX (\d+-\d+-\d+) ([A-Z0-9_]+)\s*(.*)", line)
            if m:
                dt, kind, rest = m.group(1), m.group(2), m.group(3)
                opex_events.append({"date": dt, "kind": kind, "rest": rest})

    # Enregistrer dans un JSON pour analyse complete
    out_path = Path("/work/docs/diag_year1_inspect.json")
    with open(out_path, "w") as f:
        json.dump({
            "hog_events": hog_events,
            "opex_events": opex_events,
        }, f, indent=2)
    print(f"\n[diag_year1_inspect] Ecrit {len(hog_events)} hog_events et {len(opex_events)} opex_events dans {out_path}")

if __name__ == "__main__":
    main()

