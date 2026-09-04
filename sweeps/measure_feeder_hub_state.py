"""Mesure fine de l'etat du hub au moment de la decision de construire chaque feeder (An 1)."""
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import make_cfg

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"

_real_check_output = openttdlab.subprocess.check_output

def _hook(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)

openttdlab.subprocess.check_output = _hook

def keep(row):
    return ({"output": row.get("output", "")},)

def main():
    cfg = make_cfg(1970)
    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("decision_log", 1),))
    print("Execution du diagnostic feeders Annee 1 (graine 42)...")
    res = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=[{
            "seed": 42,
            "days": 365,
            "openttd_config": cfg,
            "ais": (ai,),
        }],
        max_workers=1,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    out = res[-1]["output"]
    print("\n" + "=" * 90)
    print("DECISIONS FEEDER ET ETAT DU HUB AU MOMENT DE LA DECISION (1970, Graine 42)")
    print("=" * 90)
    for line in out.splitlines():
        if "FEEDER_BUILD" in line or "FEEDER_MAIL_BUILD" in line or "AIR_BUILD" in line:
            m = re.search(r"OPEX (\d+-\d+-\d+) ([A-Z0-9_]+)\s*(.*)", line)
            if m:
                dt, kind, rest = m.group(1), m.group(2), m.group(3)
                print(f"[{dt}] {kind:<18} {rest}")

if __name__ == "__main__":
    main()
