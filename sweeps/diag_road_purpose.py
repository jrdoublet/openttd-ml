"""Estimateur de revenu ROUTIER, ventile par MOTIF.

S0 octotrigesies : la route encaisse ~50 % du revenu promis (mediane 0,47-0,54 apres controle),
avec une dispersion de 0,07 a 1,39 -- donc pas une erreur d'echelle mais un defaut de
DISCRIMINATION. Or la route melange quatre populations qui n'ont pas la meme raison d'etre :

  - town_growth : batie pour faire CROITRE une ville. Elle porte maintenant une prediction
                  economique DIRECTE issue de ses arrets reels ; son benefice INDIRECT de croissance
                  reste volontairement hors de ce diagnostic.
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
        for k in ("pred_rev", "real_rev", "pred_prof", "real_prof", "pred_run", "real_run",
                  "live_pred_rev", "live_pred_prof", "live_pred_run"):
            try:
                f[k] = float(f.get(k, 0))
            except ValueError:
                f[k] = 0.0
        try:
            f["age"] = int(f.get("age", -1))
        except ValueError:
            f["age"] = -1
        try:
            f["active_days"] = int(f.get("active_days", -1))
        except ValueError:
            f["active_days"] = -1
        for k in ("year_days", "live_pred_vehs", "live_pred_engine"):
            try:
                f[k] = int(f.get(k, -1))
            except ValueError:
                f[k] = -1
        out.append(f)
    return out


def bucket(r):
    """Motif x nature : les quatre populations routieres."""
    purpose = r.get("purpose", "profit")
    if purpose in ("town_growth", "feeder"):
        return purpose
    return "fret" if r.get("kind") == "freight" else "pax"


def full_year(r):
    if r.get("year_days", -1) > 0 and r.get("active_days", -1) >= 0:
        return r["active_days"] >= r["year_days"]
    return r.get("age", -1) >= 2


def operating_profit_ratio(rows, pred_rev_key, pred_run_key):
    vals = []
    for r in rows:
        pred = r.get(pred_rev_key, 0) - r.get(pred_run_key, 0)
        if pred > 0:
            vals.append(r["real_prof"] / pred)
    return vals


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
        print(f"{'motif':12} {'n tot':>6} {'n build':>8} {'build rev':>9} {'build prof':>10} "
              f"{'n live':>7} {'live rev':>8} {'live prof':>9}")
        for name, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            useful = [r for r in rs if r["pred_rev"] > 0 and full_year(r)]
            if not useful:
                print(f"{name:12} {len(rs):>6} {0:>8}   — aucune annee pleine avec prediction")
                payload[f"{mode}|{name}"] = {"n_total": len(rs), "n_useful": 0, "live_n_useful": 0}
                continue
            rev = sorted(r["real_rev"] / r["pred_rev"] for r in useful)
            prof = sorted(r["real_prof"] / r["pred_prof"] for r in useful if r["pred_prof"] > 0)
            agg = sum(r["real_rev"] for r in useful) / sum(r["pred_rev"] for r in useful)
            low = sum(1 for x in rev if x < 0.5)
            live = [r for r in rs if r.get("live_pred_rev", -1) > 0 and full_year(r)]
            live_rev = sorted(r["real_rev"] / r["live_pred_rev"] for r in live)
            live_prof = sorted(r["real_prof"] / r["live_pred_prof"] for r in live if r["live_pred_prof"] > 0)
            build_op = operating_profit_ratio(useful, "pred_rev", "pred_run")
            live_op = operating_profit_ratio(live, "live_pred_rev", "live_pred_run")
            real_losses = sum(1 for r in useful if r["real_prof"] < 0)
            build_op_losses = sum(1 for r in useful if (r["pred_rev"] - r["pred_run"]) < 0)
            live_op_losses = sum(1 for r in live if (r["live_pred_rev"] - r["live_pred_run"]) < 0)
            print(f"{name:12} {len(rs):>6} {len(useful):>8} {st.median(rev):>9.2f} "
                  f"{(st.median(prof) if prof else float('nan')):>10.2f} {len(live):>7} "
                  f"{(st.median(live_rev) if live_rev else float('nan')):>8.2f} "
                  f"{(st.median(live_prof) if live_prof else float('nan')):>9.2f}")
            print(f"{'':12} {'':>6} {'op':>8} "
                  f"{(st.median(build_op) if build_op else float('nan')):>9.2f} "
                  f"{'loss':>10} {real_losses:>3}/{len(useful):<3} "
                  f"{(st.median(live_op) if live_op else float('nan')):>8.2f} "
                  f"pred_loss={build_op_losses}/{live_op_losses}")
            payload[f"{mode}|{name}"] = {
                "n_total": len(rs), "n_useful": len(useful),
                "rev_median": st.median(rev), "rev_agg": agg,
                "prof_median": (st.median(prof) if prof else None),
                "rev_quartiles": st.quantiles(rev, n=4) if len(rev) >= 4 else None,
                "share_below_half": low / len(rev),
                "live_n_useful": len(live),
                "live_rev_median": (st.median(live_rev) if live_rev else None),
                "live_prof_median": (st.median(live_prof) if live_prof else None),
                "live_rev_agg": ((sum(r["real_rev"] for r in live) /
                                  sum(r["live_pred_rev"] for r in live)) if live else None),
                "build_operating_profit_ratio_median": (st.median(build_op) if build_op else None),
                "live_operating_profit_ratio_median": (st.median(live_op) if live_op else None),
                "real_loss_count": real_losses,
                "real_loss_share": real_losses / len(useful),
                "build_pred_operating_loss_count": build_op_losses,
                "live_pred_operating_loss_count": live_op_losses}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"years": args.years, "seeds": args.seeds,
                                    "groups": payload}, indent=1))
    print("\necrit", args.out)


if __name__ == "__main__":
    main()
