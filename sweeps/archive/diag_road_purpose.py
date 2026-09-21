"""Estimateur de revenu ROUTIER, ventile par MOTIF.

S0 octotrigesies : la route encaisse ~50 % du revenu promis (mediane 0,47-0,54 apres controle),
avec une dispersion de 0,07 a 1,39 -- donc pas une erreur d'echelle mais un defaut de
DISCRIMINATION. Or la route melange quatre populations qui n'ont pas la meme raison d'etre :

  - town_growth : batie pour faire CROITRE une ville, candidat a revenueAnnual = 0 explicite.
                  La comparer a une prediction n'a aucun sens -- a exclure, pas a corriger.
  - feeder      : DECHARGE dans un hub, son revenu propre n'est pas sa finalite.
  - fret        : paire industrie -> accepteur.
  - pax normal  : liaison interurbaine ordinaire, la seule que l'estimateur pretende predire.

Deux controles imposes par S0 octotrigesies : ecarter les predictions nulles, et ne garder que
age >= 2 (65 % des enregistrements sont a age = 1, une PREMIERE ANNEE PARTIELLE qui sous-estime
mecaniquement le reel).
"""
import argparse, json, re, statistics as st, sys
from collections import defaultdict
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


def keep(row):
    return ({"seed": row["experiment"]["seed"], "date": str(row["date"]),
             "output": row.get("output")},)


def records(output):
    out = []
    for line in (output or "").splitlines():
        if " LINE_REVENUE " not in line:
            continue
        f = dict(t.split("=", 1) for t in line.split("LINE_REVENUE ", 1)[1].split() if "=" in t)
        for k in ("pred_rev", "real_rev", "pred_prof", "real_prof", "pred_run", "real_run"):
            try:
                f[k] = float(f.get(k, 0))
            except ValueError:
                f[k] = 0.0
        try:
            f["age"] = int(f.get("age", -1))
        except ValueError:
            f["age"] = -1
        out.append(f)
    return out


def bucket(r):
    """Motif x nature : les quatre populations routieres."""
    purpose = r.get("purpose", "profit")
    if purpose in ("town_growth", "feeder"):
        return purpose
    return "fret" if r.get("kind") == "freight" else "pax"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 999, 7, 1024, 314])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_road_purpose.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("decision_log", 1),))
    rows = list(run_experiments(
        openttd_version="15.3", opengfx_version="7.1", max_workers=args.workers,
        result_processor=keep,
        experiments=[{"seed": s, "days": 365 * args.years,
                      "openttd_config": make_cfg(1970), "ais": (ai,)} for s in args.seeds],
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail"))))

    allrecs = []
    for seed in args.seeds:
        out = next((r["output"] for r in rows if r["seed"] == seed and r.get("output")), "")
        allrecs += records(out)
    print(f"\n{len(allrecs)} enregistrements, dont {sum(1 for r in allrecs if r['mode']=='road')} routiers")

    payload = {}
    for mode in ("road", "rail", "air"):
        rec = [r for r in allrecs if r.get("mode") == mode]
        if not rec:
            continue
        print(f"\n########## {mode.upper()} — {len(rec)} enregistrements ##########")
        groups = defaultdict(list)
        for r in rec:
            groups[bucket(r)].append(r)
        print(f"{'motif':12} {'n tot':>6} {'n utiles':>9} {'rev med':>8} {'prof med':>9} "
              f"{'rev agrege':>11} {'sous 0,5':>9}")
        for name, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            useful = [r for r in rs if r["pred_rev"] > 0 and r["age"] >= 2]
            if not useful:
                print(f"{name:12} {len(rs):>6} {0:>9}   — aucune annee pleine avec prediction")
                payload[f"{mode}|{name}"] = {"n_total": len(rs), "n_useful": 0}
                continue
            rev = sorted(r["real_rev"] / r["pred_rev"] for r in useful)
            prof = sorted(r["real_prof"] / r["pred_prof"] for r in useful if r["pred_prof"] > 0)
            agg = sum(r["real_rev"] for r in useful) / sum(r["pred_rev"] for r in useful)
            low = sum(1 for x in rev if x < 0.5)
            print(f"{name:12} {len(rs):>6} {len(useful):>9} {st.median(rev):>8.2f} "
                  f"{(st.median(prof) if prof else float('nan')):>9.2f} {agg:>11.2f} "
                  f"{100*low/len(rev):>8.0f} %")
            payload[f"{mode}|{name}"] = {
                "n_total": len(rs), "n_useful": len(useful),
                "rev_median": st.median(rev), "rev_agg": agg,
                "prof_median": (st.median(prof) if prof else None),
                "rev_quartiles": st.quantiles(rev, n=4) if len(rev) >= 4 else None,
                "share_below_half": low / len(rev)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"years": args.years, "seeds": args.seeds,
                                    "groups": payload}, indent=1))
    print("\necrit", args.out)


if __name__ == "__main__":
    main()
