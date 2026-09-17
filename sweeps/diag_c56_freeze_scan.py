"""Diagnostic C56 : combien de graines du banc GÈLENT, et dans quelle phase ?

Contexte : sur la graine 2026, OpexAI entre dans la phase EAU de `OpexBuildProjects` et n'en sort
jamais ; l'IA cesse alors toute activite pour le reste de la partie, sans erreur et avec
`run_ok = True`. Ce script repond a la seule question qui decide de la suite : est-ce UNE graine, ou
est-ce que nos bancs 20 graines trainent plusieurs parties amputees depuis des semaines ?

Detection, volontairement mecanique et sans interpretation :
  - `c56_task_trace=1` ecrit `TASK_ENTER`/`TASK_EXIT` et `STAGE_ENTER`/`STAGE_EXIT` IMMEDIATEMENT ;
  - une partie est declaree GELEE si son journal s'arrete AVANT l'annee de fin attendue ;
  - la phase nommee par le dernier `_ENTER` non apparie est le lieu du gel.

🔴 LE PIEGE, paye une fois : un `_ENTER` non apparie ne suffit PAS a declarer un gel. Une partie
saine se termine forcement au milieu d'une tache -- la partie s'arrete sur un nombre de ticks fixe,
pas sur une frontiere de tache -- donc sa derniere trace est presque toujours un `_ENTER` orphelin.
Le premier jet de ce script annoncait ainsi 19 gels sur 20 ; il y en a 3. **C'est l'annee de fin qui
tranche, l'appariement ne fait que nommer la phase.**

⚠️ PAS de `decision_log=1` : on veut le volume minimal. `-d script=4` reste necessaire pour que
AILog remonte, mais sans le journal de decision le fichier reste petit (~100 ko/partie contre ~1 Mo).
Ne jamais ajouter `decision_log=1` a un balayage 20 graines sans y repenser : une campagne de 13 Go
a deja rempli le disque de cette machine.

⚠️ Une partie NON gelee ne prouve pas que le code de l'eau est sain sur cette carte : elle peut
n'etre jamais passee par la phase eau. La colonne `water_entered` distingue les deux.
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
    OPENGFX_VERSION, OPENTTD_VERSION, SEEDS, build_arms, enable_savegame_cleanup,
    experiments, write_json_atomically,
)

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

# Le bras doit toujours porter c56_task_trace=1 : c'est lui qui ecrit les jalons dont depend
# toute la detection. --arm sert a ajouter un reglage a comparer (p. ex. water_lakes_ops_budget=1),
# pas a retirer la sonde.
DEFAULT_ARM = "OpexAI[c56_task_trace=1]"
TRACE_RE = re.compile(r"OPEX (\d+)-\d+-\d+ C56_TASK (TASK|STAGE)_(ENTER|EXIT) name=(\S+)")
YEAR_RE = re.compile(r"OPEX (\d+)-\d+-\d+ ")


def analyse(output, end_year=None):
    """Rend le verdict de gel d'une partie, sans interpretation.

    `end_year` est l'annee de fin attendue. Sans elle, `frozen` reste None : on refuse de
    rendre un verdict de gel, plutot que d'en rendre un faux."""
    traces = TRACE_RE.findall(output or "")
    years = [int(y) for y in YEAR_RE.findall(output or "")]
    open_stack = []
    water_entered = False
    water_exited = False
    for _year, kind, direction, name in traces:
        if name.endswith("water"):
            if direction == "ENTER":
                water_entered = True
            else:
                water_exited = True
        if direction == "ENTER":
            open_stack.append((kind, name))
        elif open_stack and open_stack[-1][1] == name:
            open_stack.pop()
        elif (kind, name) in open_stack:
            open_stack.remove((kind, name))
    last_logged = max(years) if years else None
    unmatched_enter = bool(traces) and traces[-1][2] == "ENTER"
    frozen = (None if end_year is None or last_logged is None
              else last_logged < end_year)
    return {
        "frozen": frozen,
        "unmatched_enter": unmatched_enter,
        "frozen_at": traces[-1][3] if (frozen and unmatched_enter) else None,
        "last_trace_year": int(traces[-1][0]) if traces else None,
        "last_logged_year": max(years) if years else None,
        "trace_count": len(traces),
        "water_entered": water_entered,
        "water_exited": water_exited,
        "unclosed": [name for _kind, name in open_stack],
    }


def keep_trace(row):
    arm, seed, _repeat = row["experiment"]["bench_run"]
    return ({
        "seed": seed, "arm": arm, "date": str(row["date"]),
        "output": row.get("output", ""),
        "n_stations": len(row.get("chunks", {}).get("STNN", {})),
        "n_vehicles": len(row.get("chunks", {}).get("VEHS", {})),
    },)


def run_selftest():
    """Les trois cas que le premier jet de ce script confondait."""
    # 1. GEL REEL : le journal s'arrete en 1972 alors qu'on attend 1979, sur une entree eau ouverte.
    frozen_log = "\n".join((
        "OPEX 1972-9-3 C56_TASK TASK_ENTER name=catalog cycle=74",
        "OPEX 1972-9-5 C56_TASK STAGE_ENTER name=c56_stage_air cycle=-",
        "OPEX 1972-9-8 C56_TASK STAGE_EXIT name=c56_stage_air cycle=-",
        "OPEX 1972-9-11 C56_TASK STAGE_ENTER name=c56_stage_water cycle=-",
    ))
    verdict = analyse(frozen_log, end_year=1979)
    assert verdict["frozen"] is True, verdict
    assert verdict["frozen_at"] == "c56_stage_water", verdict
    assert verdict["water_entered"] and not verdict["water_exited"], verdict

    # 2. 🔴 LE CAS QUI A FAIT SUR-DECLARER 19 GELS SUR 20 : une partie SAINE atteint 1979 mais
    #    s'arrete au milieu d'une tache, donc sur un `_ENTER` orphelin. Ce n'est PAS un gel.
    healthy_cut = "\n".join((
        "OPEX 1979-9-3 C56_TASK TASK_ENTER name=catalog cycle=74",
        "OPEX 1979-9-5 C56_TASK STAGE_ENTER name=c56_stage_water cycle=-",
        "OPEX 1979-9-8 C56_TASK STAGE_EXIT name=c56_stage_water cycle=-",
        "OPEX 1979-9-9 C56_TASK TASK_ENTER name=projects cycle=75",
    ))
    verdict = analyse(healthy_cut, end_year=1979)
    assert verdict["frozen"] is False, verdict
    assert verdict["unmatched_enter"] is True, verdict
    assert verdict["frozen_at"] is None, verdict
    assert verdict["water_exited"] is True, verdict

    # 3. Sans annee de fin, on REFUSE de trancher plutot que de trancher faux.
    assert analyse(frozen_log)["frozen"] is None, "sans end_year, pas de verdict"
    print("selftest ok")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--arm", default=DEFAULT_ARM)
    args = parser.parse_args()
    if not args.selftest and "c56_task_trace=1" not in args.arm:
        parser.error("--arm doit contenir c56_task_trace=1 : sans la sonde, aucun gel n'est detectable")
    if args.selftest:
        run_selftest()
        return

    out = args.out or ROOT / "results" / f"diag_c56_freeze_scan_{args.years}y_{len(args.seeds)}seeds.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    enable_savegame_cleanup()
    built = build_arms([args.arm])
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep_trace,
        experiments=experiments(built, args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    latest = {}
    for row in rows:
        if row["seed"] not in latest or row["date"] > latest[row["seed"]]["date"]:
            latest[row["seed"]] = row
    per_seed = []
    for seed in sorted(latest):
        row = latest[seed]
        verdict = analyse(row["output"], end_year=1970 + args.years - 1)
        verdict.update({"seed": seed, "n_stations": row["n_stations"],
                        "n_vehicles": row["n_vehicles"]})
        per_seed.append(verdict)
    measurable = [entry for entry in per_seed if entry["frozen"] is not None]
    inconclusive = [entry for entry in per_seed if entry["frozen"] is None]
    frozen = [entry for entry in measurable if entry["frozen"]]
    water_seeds = [entry for entry in per_seed if entry["water_entered"]]
    payload = {
        "arm": args.arm, "years": args.years, "seeds": args.seeds,
        "per_seed": per_seed,
        # Fail closed : sans trace datee, "0 gel" serait une conclusion faussement rassurante.
        "frozen_count": len(frozen) if measurable else None,
        "measurable_count": len(measurable),
        "inconclusive_count": len(inconclusive),
        "water_entered_count": len(water_seeds),
    }
    write_json_atomically(out, payload)
    print(f"out {out}")
    if inconclusive:
        print(
            f"INCONCLUSIVES : {len(inconclusive)} / {len(per_seed)}  |  "
            f"mesurables : {len(measurable)}  |  passees par la phase eau : {len(water_seeds)}"
        )
    else:
        print(f"GELEES : {len(frozen)} / {len(per_seed)}  |  passees par la phase eau : {len(water_seeds)}")
    print(f"{'graine':>8} {'gelee':>6} {'phase':>20} {'an.fin':>7} {'eau in/out':>11} {'gares':>6}")
    for entry in per_seed:
        print(f"{entry['seed']:>8} {str(entry['frozen']):>6} {str(entry['frozen_at']):>20} "
              f"{str(entry['last_logged_year']):>7} "
              f"{str(entry['water_entered'])[:1]}/{str(entry['water_exited'])[:1]:>9} "
              f"{entry['n_stations']:>6}")


if __name__ == "__main__":
    main()
