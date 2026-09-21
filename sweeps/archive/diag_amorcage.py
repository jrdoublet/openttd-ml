"""L'AMORCAGE : pourquoi si peu de tentatives dans les 24 premiers mois ?

C'est la ou l'ecart se cree. A 3 ans nous sommes a 65 k de caisse et 300 000 d'emprunt -- le
PLAFOND -- quand AAAHogEx a 410 k et zero dette (S0 quaterquadragesies). Le modele de tension avait
conclu que rien ne contraint, mais il a ete mesure sur DIX ANS, donc domine par les annees riches :
la seule graine pauvre du lot montrait l'argent mordant 28 % du temps.

La question n'est pas "quel projet est le meilleur" mais "pourquoi si peu de TENTATIVES alors qu'on
est colle au plafond d'emprunt". Deux issues, qui menent ailleurs :
  - refus de TRESORERIE   -> le sujet est la vitesse d'amorcage, pas le classement ;
  - refus d'AUTRE CHOSE   -> on est bride par notre propre ordonnanceur en abondance relative,
                             et la question constructeur-contre-selecteur se pose frontalement.
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

BUILDS = {"RAIL_BUILD", "ROAD_BUILD", "AIR_BUILD", "WATER_BUILD", "FEEDER_BUILD"}
# Tout ce qui signale une tentative REFUSEE ou AVORTEE, quel que soit le chemin.
REFUS = {"PROJECT_DISCARD", "AIR_REFUSE", "FEEDER_REFUSE", "RAIL_BUILD_FAIL",
         "PORTFOLIO_EMPTY", "AIR_FLEET"}


def keep(row):
    return ({"seed": row["experiment"]["seed"], "date": str(row["date"]),
             "output": row.get("output"), "money": None},)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--months", type=int, default=24)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 999, 7, 1024, 314])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_amorcage.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("decision_log", 1),))
    rows = list(run_experiments(
        openttd_version="15.3", opengfx_version="7.1", max_workers=args.workers,
        result_processor=keep,
        experiments=[{"seed": s, "days": 31 * args.months + 40,
                      "openttd_config": make_cfg(1970), "ais": (ai,)} for s in args.seeds],
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail"))))

    builds, refus_kind, refus_reason = Counter(), Counter(), Counter()
    per_month = defaultdict(lambda: {"builds": 0, "refus": 0})
    loans = Counter()
    for seed in args.seeds:
        out = next((r["output"] for r in rows if r["seed"] == seed and r.get("output")), "")
        for line in out.splitlines():
            m = OPEX_RE.search(line)
            if not m:
                continue
            year, month, _d, kind, rest = m.groups()
            idx = (int(year) - 1970) * 12 + int(month)
            if idx > args.months:
                continue
            f = dict(t.split("=", 1) for t in rest.split() if "=" in t)
            if kind in BUILDS:
                builds[kind] += 1
                per_month[idx]["builds"] += 1
            elif kind in REFUS:
                if kind == "AIR_FLEET" and f.get("action") != "refuse":
                    continue
                refus_kind[kind] += 1
                refus_reason[f.get("reason", kind.lower())] += 1
                per_month[idx]["refus"] += 1
            elif kind == "LOAN":
                loans[f.get("action", "?")] += 1

    nb = sum(builds.values()); nr = sum(refus_kind.values())
    print(f"\n=== {args.months} premiers mois, {len(args.seeds)} graines ===")
    print(f"  constructions : {nb}  ({nb/len(args.seeds):.1f} par graine)")
    print(f"  refus         : {nr}  ({nr/len(args.seeds):.1f} par graine)")
    print(f"  ratio refus/construction : {nr/max(nb,1):.1f}")
    print("\n  constructions par mode :", dict(builds.most_common()))
    print("  emprunt :", dict(loans.most_common()))
    print(f"\n  {'MOTIF DE REFUS':32} {'n':>5}   part")
    for reason, n in refus_reason.most_common(12):
        print(f"  {reason:32} {n:>5}  ({100*n/max(nr,1):>4.0f} %)")
    cash = sum(n for r, n in refus_reason.items() if "cash" in r or "money" in r
               or r in ("M", "insufficient_cash"))
    print(f"\n  🔑 part des refus lies a la TRESORERIE : {100*cash/max(nr,1):.0f} %")
    print(f"\n  {'mois':>5} {'constr.':>8} {'refus':>7}")
    for idx in sorted(per_month):
        d_ = per_month[idx]
        print(f"  {idx:>5} {d_['builds']:>8} {d_['refus']:>7}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "months": args.months, "seeds": args.seeds, "builds": dict(builds),
        "refus_kind": dict(refus_kind), "refus_reason": dict(refus_reason),
        "loans": dict(loans),
        "per_month": {str(k): v for k, v in per_month.items()}}, indent=1))
    print("\necrit", args.out)


if __name__ == "__main__":
    main()
