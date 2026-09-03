"""Sonde : est-ce que AILog des deux IA remonte sur stdout avec -d script=N ?

openttdlab n'expose aucun crochet pour les arguments de ligne de commande d'OpenTTD. Mais il
lance le binaire par subprocess.check_output et parallelise par multiprocessing.Pool ; sous
Linux le demarrage est `fork`, donc un patch pose AVANT l'appel est herite par les workers.
On patche donc check_output DANS le module openttdlab, sans toucher au paquet installe.
"""
import json
import subprocess
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
LEVEL = sys.argv[1] if len(sys.argv) > 1 else "3"

_real_check_output = openttdlab.subprocess.check_output


def _patched(args, *rest, **kwargs):
    args = tuple(args)
    # Seul le lancement de partie porte -vnull ; le screenshot eventuel ne doit pas etre touche.
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", f"script={LEVEL}") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _patched

CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""

rows = run_experiments(
    openttd_version="15.3",
    opengfx_version="7.1",
    experiments=[{
        "seed": 42,
        "days": 365,
        "openttd_config": CFG,
        "ais": [
            local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("debug_signs", 1),)),
            local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ()),
        ],
    }],
    ai_libraries=(
        bananas_ai_library("51554648", "Queue.FibonacciHeap"),
        bananas_ai_library("5046524c", "Pathfinder.Rail"),
    ),
    max_workers=1,
    result_processor=lambda row: (row,),
)

rows = list(rows)
out = rows[-1].get("output") or ""
print(f"lignes de sortie : {len(out.splitlines())}, octets : {len(out)}")
Path("/work/docs/probe_ailog_raw.txt").write_text(out)
for line in out.splitlines()[:40]:
    print(line[:200])
