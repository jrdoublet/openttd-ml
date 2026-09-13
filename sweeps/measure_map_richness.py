"""Mesure la richesse exogene des cartes utilisees par un banc apparie.

Une IA-sonde passive photographie la carte des son demarrage, avant toute construction : nombre
de villes, population totale et maximale, nombre d'industries et dimensions. Les valeurs passent
par SIGN, canal relu dans les sauvegardes par OpenTTDLab.
"""
import argparse
import atexit
import json
from pathlib import Path
import re
import shutil
import sys

from openttdlab import local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, SEEDS, enable_savegame_cleanup, make_cfg,
    write_json_atomically,
)

PROBE_DIR = Path("/tmp/openttd-ml-map-richness-probe")
PROBE_NAME = "MapRichnessProbe"
URBAN_RE = re.compile(r"^MRU\|(\d+)\|(\d+)\|(\d+)$")
MAP_RE = re.compile(r"^MRM\|(\d+)\|(\d+)\|(\d+)$")


def make_probe():
    if PROBE_DIR.exists():
        raise RuntimeError(f"sonde temporaire deja presente : {PROBE_DIR}")
    PROBE_DIR.mkdir()
    (PROBE_DIR / "info.nut").write_text(f'''class {PROBE_NAME}Info extends AIInfo {{
  function GetAuthor()      {{ return "openttd-ml"; }}
  function GetName()        {{ return "{PROBE_NAME}"; }}
  function GetDescription() {{ return "Passive initial map richness probe"; }}
  function GetVersion()     {{ return 1; }}
  function GetDate()        {{ return "2026-09-12"; }}
  function CreateInstance() {{ return "{PROBE_NAME}"; }}
  function GetShortName()   {{ return "MRCH"; }}
  function GetAPIVersion()  {{ return "15"; }}
}}
RegisterAI({PROBE_NAME}Info());
''')
    (PROBE_DIR / "main.nut").write_text(f'''class {PROBE_NAME} extends AIController {{}}

function {PROBE_NAME}::Start()
{{
  local nTowns = 0;
  local totalPopulation = 0;
  local maxPopulation = 0;
  local towns = AITownList();
  for (local town = towns.Begin(); !towns.IsEnd(); town = towns.Next()) {{
    local population = AITown.GetPopulation(town);
    nTowns++;
    totalPopulation += population;
    if (population > maxPopulation) maxPopulation = population;
  }}

  local industries = AIIndustryList();
  local nIndustries = 0;
  for (local industry = industries.Begin(); !industries.IsEnd(); industry = industries.Next()) {{
    if (AIIndustry.IsValidIndustry(industry)) nIndustries++;
  }}

  local anchor = AIMap.GetTileIndex(1, 1);
  AISign.BuildSign(anchor, "MRU|" + nTowns + "|" + totalPopulation + "|" + maxPopulation);
  AISign.BuildSign(anchor, "MRM|" + nIndustries + "|" + AIMap.GetMapSizeX() + "|" + AIMap.GetMapSizeY());
  while (true) this.Sleep(1000);
}}
''')


def keep(row):
    signs = row.get("chunks", {}).get("SIGN", {})
    values = signs.values() if isinstance(signs, dict) else signs
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "signs": [sign.get("name", "") for sign in values if isinstance(sign, dict)],
    },)


def parse_record(row):
    urban = [URBAN_RE.match(sign) for sign in row["signs"]]
    urban = [match for match in urban if match]
    map_data = [MAP_RE.match(sign) for sign in row["signs"]]
    map_data = [match for match in map_data if match]
    if len(urban) != 1 or len(map_data) != 1:
        raise RuntimeError(f"panneaux incomplets seed={row['seed']}: {row['signs']}")
    n_towns, total_population, max_population = map(int, urban[0].groups())
    n_industries, map_x, map_y = map(int, map_data[0].groups())
    return {
        "seed": row["seed"],
        "capture_date": row["date"],
        "map_x": map_x,
        "map_y": map_y,
        "n_towns": n_towns,
        "total_population": total_population,
        "mean_town_population": round(total_population / n_towns, 6) if n_towns else 0,
        "max_town_population": max_population,
        "n_industries": n_industries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--starting-year", type=int, default=1970)
    parser.add_argument("--map-size", type=int, default=8)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args()
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    make_probe()
    atexit.register(shutil.rmtree, PROBE_DIR, ignore_errors=True)
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=tuple({
            "seed": seed,
            "days": 365,
            "openttd_config": make_cfg(args.starting_year, args.map_size),
            "ais": (local_folder(str(PROBE_DIR), PROBE_NAME),),
        } for seed in args.seeds),
    ))
    latest = {}
    for row in rows:
        if row["seed"] not in latest or row["date"] > latest[row["seed"]]["date"]:
            latest[row["seed"]] = row
    missing = sorted(set(args.seeds) - set(latest))
    if missing:
        raise RuntimeError(f"graines sans sauvegarde : {missing}")

    records = [parse_record(latest[seed]) for seed in args.seeds]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "starting_year": args.starting_year,
        "openttd_config": make_cfg(args.starting_year, args.map_size),
        "method": "passive NoAI SIGN snapshot at startup, before construction",
        "seeds": args.seeds,
        "records": records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomically(args.out, payload)
    print("ecrit", args.out)
    for record in records:
        print(
            f"seed={record['seed']:<8} towns={record['n_towns']:<3} "
            f"population={record['total_population']:<7} max={record['max_town_population']:<5} "
            f"industries={record['n_industries']}"
        )


if __name__ == "__main__":
    main()
