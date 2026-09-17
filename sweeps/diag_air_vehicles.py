"""Diagnostic PAR AVION : profit, revenu implicite et chargement de chaque appareil d'une meme
paire de villes, un an apres sa construction.

Demande le 2026-09-03 : le vivier aerien empile des lignes redondantes entre les deux memes villes
(voir docs/journal correspondant), et l'hypothese a verifier est que chaque avion supplementaire
gagne moins que le precedent (ROI decroissant, la demande de la paire etant fixe).

Deux sources, deux niveaux de confiance :
  - profit_last_year et revenu implicite (profit + cout de fonctionnement) viennent de
    AIVehicle.GetProfitLastYear / GetRunningCost, EXACTEMENT la formule que main.nut:_reportLines
    utilise deja pour line.lastProfit / line.lastRevenue (verifiee, deja en prod). On les lit ici
    via les panneaux OZ|line|year|profit et OO|line|year|revenu qu'OpexSign pose deja (defaut
    debug_signs=1, philosophie "armes egales").
  - load_unload_ticks vient du chunk VEHS brut (champ NON VERIFIE par ce projet avant ce script :
    present dans le dump results/phase2_vehs_explore.json mais jamais lu jusqu'ici). A traiter comme
    une piste, pas un fait etabli -- imprime brut, jamais transforme en conclusion silencieuse.

report ne tourne qu'UNE FOIS PAR AN (_lastReportYear), donc l'annee N+1 ne voit que le profit
PARTIEL de N (vehicules construits en cours d'annee). Pour comparer les avions a armes egales il
faut une annee CIVILE COMPLETE pour chacun : on tourne donc 3 ans et on lit le rapport de l'annee
1972 (couvre 1971 en entier pour tous les avions construits en 1970).
"""
import argparse
import json
import re
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
SCRIPT_DEBUG_LEVEL = "4"

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", f"script={SCRIPT_DEBUG_LEVEL}") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

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

LINE_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[(\w)\] (.*)")
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def _first(value):
    return value[0] if isinstance(value, list) and value else value


def parse_opex_decisions(output):
    events = []
    for line in (output or "").splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        _company, _level, text = m.groups()
        m2 = OPEX_RE.match(text.strip())
        if not m2:
            continue
        year, month, day, kind, rest = m2.groups()
        fields = {}
        for token in rest.split():
            if "=" in token:
                key, _, value = token.partition("=")
                fields[key] = value
        events.append({"date": f"{int(year):04d}-{int(month):02d}-{int(day):02d}",
                        "kind": kind, "fields": fields})
    return events


def parse_signs(chunks):
    """OZ|line|year|profit, OU|line|year|vehCount|runCost, OO|line|year|revenu, OY|line|year|rA|rB."""
    out = {"OZ": [], "OU": [], "OO": [], "OY": []}
    for sign in (chunks.get("SIGN") or {}).values():
        name = sign.get("name") if isinstance(sign, dict) else None
        if not name:
            continue
        parts = name.split("|")
        if parts[0] in out:
            out[parts[0]].append(parts[1:])
    return out


def parse_aircraft(chunks, owner=0):
    """VEHS brut, type=3 (avion), champs de results/phase2_vehs_explore.json. load_unload_ticks NON
    VERIFIE semantiquement par ce projet -- lu ici pour la premiere fois."""
    result = []
    for key, vehicle in (chunks.get("VEHS") or {}).items():
        if not isinstance(vehicle, dict) or str(vehicle.get("type")) != "3":
            continue
        body = _first(vehicle.get("aircraft"))
        common = _first((body or {}).get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != owner:
            continue
        result.append({
            "veh_key": key, "unitnumber": common.get("unitnumber"),
            "build_year": common.get("build_year"), "age_days": common.get("age"),
            "profit_this_year": common.get("profit_this_year"),
            "profit_last_year": common.get("profit_last_year"),
            "value": common.get("value"), "cargo_cap": common.get("cargo_cap"),
            "load_unload_ticks": common.get("load_unload_ticks"),
            "current_order_time": common.get("current_order_time"),
            "last_station_visited": common.get("last_station_visited"),
        })
    return result


def keep(row):
    chunks = row["chunks"]
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "signs": parse_signs(chunks),
        "aircraft": parse_aircraft(chunks),
        "output": row.get("output"),
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_air_vehicles.json")
    args = parser.parse_args()

    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI",
                       (("probe_events", 1), ("decision_log", 1)))
    experiments = [
        {"seed": seed, "days": 365 * args.years, "openttd_config": CFG,
         "ais": (ai,), "diag_arm": "OpexAI"}
        for seed in args.seeds
    ]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=experiments, max_workers=1, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    # Le journal complet (AIR_BUILD, pour dater/nommer les avions) : une seule fois par graine.
    decisions_by_seed = {}
    for r in rows:
        seed = r["seed"]
        if seed not in decisions_by_seed and r.get("output"):
            decisions_by_seed[seed] = parse_opex_decisions(r["output"])
    for r in rows:
        r.pop("output", None)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "years": args.years, "seeds": args.seeds,
        "rows": rows, "decisions_by_seed": decisions_by_seed,
    }, indent=1))
    print("ecrit", args.out, "-", len(rows), "lignes,",
          sum(len(v) for v in decisions_by_seed.values()), "decisions")


if __name__ == "__main__":
    main()
