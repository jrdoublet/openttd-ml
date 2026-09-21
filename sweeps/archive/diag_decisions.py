"""Deux questions en une passe.

1. C15 : la cadence d'agrandissement aerien MORD-elle ? Bras 365 (defaut historique) contre 90.
   Sous 365 le code doit etre litteralement celui d'avant ; sous 90 il doit produire strictement
   plus d'extensions de flotte, sinon le reglage est inerte et il n'y a rien a bancher (precedent
   portfolio_max_batch : 11 graines sur 20 en nuls exacts).

2. L'IA est-elle EMPECHEE ou INACTIVE ? Le goulot mesure est 61,2 % de transitions mensuelles
   sans construction avec >= 300 k en caisse, et la sonde de tension a montre que RIEN ne
   contraint dans 97 % des evaluations. On compte donc, par mois de jeu :
     - les mois sans AUCUNE trace de journal      -> l'IA ne tourne pas du tout ;
     - les mois sans aucune EVALUATION            -> elle ne regarde pas ;
     - les mois sans aucune ACTION de construction -> elle regarde et ne fait rien.
   La difference entre les trois tranche entre "empechee" et "inactive".
"""
import argparse, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg  # noqa: E402

_real = openttdlab.subprocess.check_output


def _hook(args, *rest, **kw):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real(args, *rest, **kw)


openttdlab.subprocess.check_output = _hook

OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
FAIL_RE = re.compile(r"Your script made an error|The script died unexpectedly")

# Ce qui compte comme une ACTION : de l'infrastructure ou des vehicules apparaissent reellement.
ACTIONS = {"RAIL_BUILD", "ROAD_BUILD", "AIR_BUILD", "WATER_BUILD", "FEEDER_BUILD", "RAIL_EXPAND"}
# Ce qui compte comme une EVALUATION : l'IA a classe ou examine des projets.
EVALS = {"PORTFOLIO_RANK", "PORTFOLIO_EMPTY", "TENSION", "PROJECT_CHOSEN", "PROJECT_DISCARD",
         "VIVIER", "VIVIER_GEN", "TASK"}


def keep(row):
    return ({"arm": row["experiment"]["dec_arm"], "seed": row["experiment"]["seed"],
             "date": str(row["date"]), "output": row.get("output")},)


def analyse(output):
    months_any, months_eval, months_action = set(), set(), set()
    kinds = Counter()
    grow_events = 0
    errors = []
    for line in (output or "").splitlines():
        if FAIL_RE.search(line):
            errors.append(line.strip()[:160])
            continue
        m = OPEX_RE.search(line)
        if not m:
            continue
        year, month, _d, kind, rest = m.groups()
        ym = (int(year), int(month))
        months_any.add(ym)
        kinds[kind] += 1
        if kind in EVALS:
            months_eval.add(ym)
        if kind in ACTIONS:
            months_action.add(ym)
        if kind == "AIR_FLEET" and "action=grow" in rest:
            grow_events += 1
            months_action.add(ym)
    return months_any, months_eval, months_action, kinds, grow_events, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 999, 7])
    parser.add_argument("--cadences", nargs="+", type=int, default=[365, 90])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_decisions.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    exps = []
    for cad in args.cadences:
        ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI",
                          (("decision_log", 1), ("air_fleet_cadence_days", cad)))
        for seed in args.seeds:
            exps.append({"seed": seed, "days": 365 * args.years,
                         "openttd_config": make_cfg(1970), "ais": (ai,), "dec_arm": cad})

    rows = list(run_experiments(
        openttd_version="15.3", opengfx_version="7.1", max_workers=args.workers,
        result_processor=keep, experiments=exps,
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail"))))

    total_months = args.years * 12
    out = {}
    print(f"\n{'cadence':>8} {'graine':>7} {'mois actifs':>12} {'mois evalues':>13} "
          f"{'mois action':>13} {'extensions air':>15}")
    for cad in args.cadences:
        for seed in args.seeds:
            output = ""
            for r in rows:
                if r["arm"] == cad and r["seed"] == seed and r.get("output"):
                    output = r["output"]
                    break
            any_, ev, act, kinds, grow, errors = analyse(output)
            if errors:
                print(f"🔴 cadence {cad} graine {seed} : {len(errors)} erreurs")
                for e in errors[:3]:
                    print("   ", e)
            out[f"{cad}|{seed}"] = {
                "months_any": len(any_), "months_eval": len(ev), "months_action": len(act),
                "grow_events": grow, "kinds": dict(kinds)}
            print(f"{cad:>8} {seed:>7} {len(any_):>5}/{total_months:<6} {len(ev):>6}/{total_months:<6} "
                  f"{len(act):>7}/{total_months:<6} {grow:>15}")

    print(f"\n--- lecture, sur {total_months} mois de jeu ---")
    for cad in args.cadences:
        ev = sum(out[f"{cad}|{s}"]["months_eval"] for s in args.seeds) / len(args.seeds)
        act = sum(out[f"{cad}|{s}"]["months_action"] for s in args.seeds) / len(args.seeds)
        grow = sum(out[f"{cad}|{s}"]["grow_events"] for s in args.seeds) / len(args.seeds)
        print(f"  cadence {cad:>3} : {100 * ev / total_months:.0f} % des mois evalues, "
              f"{100 * act / total_months:.0f} % avec une action, {grow:.1f} extensions air en moyenne")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"years": args.years, "seeds": args.seeds,
                                    "cadences": args.cadences, "per_run": out}, indent=1))
    print("\necrit", args.out)


if __name__ == "__main__":
    main()
