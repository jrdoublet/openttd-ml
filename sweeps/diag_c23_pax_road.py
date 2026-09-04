"""Diagnostic C23 : terme par terme pour le pax routier interurbain.

Mesure sur 5 graines x 10 ans (meme protocole que diag_road_purpose.py).
Filtre strict : mode="road", kind="pax", purpose="profit", age >= 2, pred_rev > 0.
Compare chaque terme predit au reel :
  - Cout de fonctionnement (pred_run vs real_run)
  - Flotte (pred_vehs vs vehs)
  - Note de gare (50 % suppose vs rating_a, rating_b reels)
  - Distance (dist Manhattan predite vs real_dist entre arrets)
  - Vitesse (pred_speed vs cat_speed vs real_speed)
  - Volume transporte annuel (pred_carried vs volume reel implicite)
  - Revenu annuel (pred_rev vs real_rev)
  - Profit annuel (pred_prof vs real_prof)
"""
import argparse, json, math, re, statistics as st, sys
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


def records(output, seed):
    out = []
    for line in (output or "").splitlines():
        if " LINE_REVENUE " not in line:
            continue
        tokens = line.split("LINE_REVENUE ", 1)[1].split()
        f = {"seed": seed}
        for t in tokens:
            if "=" in t:
                k, _, v = t.partition("=")
                f[k] = v
        # numeric casts
        float_fields = ("pred_rev", "real_rev", "pred_prof", "real_prof", "pred_run", "real_run",
                        "pred_carried", "op_ratio")
        int_fields = ("line", "year", "age", "vehs", "pred_vehs", "dist", "real_dist",
                      "pred_days", "pred_speed", "cat_speed", "real_speed",
                      "rating_a", "rating_b", "pop_a", "pop_b", "prod_a", "prod_b",
                      "wait_a", "wait_b", "cap", "low_ratio")
        for k in float_fields:
            try:
                f[k] = float(f.get(k, 0))
            except ValueError:
                f[k] = 0.0
        for k in int_fields:
            try:
                f[k] = int(f.get(k, -1))
            except ValueError:
                f[k] = -1
        out.append(f)
    return out


def analyze_pax_road(records_list):
    # Filter for C23: mode == "road", kind == "pax", purpose == "profit", age >= 2, pred_rev > 0
    c23 = [r for r in records_list if r.get("mode") == "road" and r.get("kind") == "pax"
           and r.get("purpose", "profit") == "profit" and r.get("age", 0) >= 2
           and r.get("pred_rev", 0) > 0]

    print(f"\n=======================================================")
    print(f"C23 : DIAGNOSTIC TERME PAR TERME (n = {len(c23)} annees pleines)")
    print(f"=======================================================\n")

    if not c23:
        print("Aucun enregistrement pax routier interurbain trouve !")
        return {}

    # Ratios
    rev_ratios = [r["real_rev"] / r["pred_rev"] for r in c23]
    prof_ratios = [r["real_prof"] / r["pred_prof"] for r in c23 if r["pred_prof"] > 0]
    run_ratios = [r["real_run"] / r["pred_run"] for r in c23 if r["pred_run"] > 0]
    vehs_ratios = [r["vehs"] / r["pred_vehs"] for r in c23 if r["pred_vehs"] > 0]

    # Distances
    dist_preds = [r["dist"] for r in c23 if r["dist"] > 0]
    dist_reals = [r["real_dist"] for r in c23 if r["real_dist"] > 0]
    dist_ratios = [r["real_dist"] / r["dist"] for r in c23 if r["dist"] > 0 and r["real_dist"] > 0]

    # Ratings
    ratings_a = [r["rating_a"] for r in c23 if r["rating_a"] >= 0]
    ratings_b = [r["rating_b"] for r in c23 if r["rating_b"] >= 0]
    ratings_all = ratings_a + ratings_b

    # Speeds
    speed_preds = [r["pred_speed"] for r in c23 if r["pred_speed"] > 0]
    speed_cats = [r["cat_speed"] for r in c23 if r["cat_speed"] > 0]
    speed_reals = [r["real_speed"] for r in c23 if r["real_speed"] > 0]
    speed_ratios = [r["real_speed"] / r["pred_speed"] for r in c23 if r["real_speed"] > 0 and r["pred_speed"] > 0]

    # Carried
    carried_preds = [r["pred_carried"] for r in c23 if r["pred_carried"] > 0]
    # Implied carried: in OpenTTD, real_rev = carried_real * price_per_unit
    # price_per_unit = pred_rev / pred_carried
    implied_carried = []
    carried_ratios = []
    for r in c23:
        if r["pred_carried"] > 0 and r["pred_rev"] > 0 and r["real_rev"] >= 0:
            price_per_unit = r["pred_rev"] / r["pred_carried"]
            c_real = r["real_rev"] / price_per_unit if price_per_unit > 0 else 0
            implied_carried.append(c_real)
            carried_ratios.append(c_real / r["pred_carried"])

    # Populations and monthly town production
    pops = [r["pop_a"] for r in c23 if r["pop_a"] > 0] + [r["pop_b"] for r in c23 if r["pop_b"] > 0]
    prods = [r["prod_a"] for r in c23 if r["prod_a"] > 0] + [r["prod_b"] for r in c23 if r["prod_b"] > 0]
    waits = [r["wait_a"] for r in c23 if r["wait_a"] >= 0] + [r["wait_b"] for r in c23 if r["wait_b"] >= 0]

    def fmt_stat(vals):
        if not vals:
            return "N/A"
        med = st.median(vals)
        mean = st.mean(vals)
        q = st.quantiles(vals, n=4) if len(vals) >= 4 else [min(vals), med, max(vals)]
        return f"med={med:.2f} (moy={mean:.2f}, Q1={q[0]:.2f}, Q3={q[2]:.2f}, min={min(vals):.2f}, max={max(vals):.2f})"

    print("--- 1. BILAN FINANCIER GLOBAL ---")
    print(f"Revenu reel / predit     : {fmt_stat(rev_ratios)}")
    print(f"  Agrégé somme(reel)/somme(pred) : {sum(r['real_rev'] for r in c23) / sum(r['pred_rev'] for r in c23):.3f}")
    print(f"  Part sous 0.50                 : {100 * sum(1 for x in rev_ratios if x < 0.5) / len(rev_ratios):.1f} %")
    print(f"Profit reel / predit     : {fmt_stat(prof_ratios)}")
    print(f"Cout fonct reel / predit : {fmt_stat(run_ratios)}")
    print(f"Flotte reelle / predite  : {fmt_stat(vehs_ratios)}")

    print("\n--- 2. TERME PAR TERME ---")
    print(f"[COUT FONCT] pred={st.median([r['pred_run'] for r in c23]):.0f}  reel={st.median([r['real_run'] for r in c23]):.0f}  ratio={fmt_stat(run_ratios)}")
    print(f"[FLOTTE]     pred={st.median([r['pred_vehs'] for r in c23]):.1f}  reel={st.median([r['vehs'] for r in c23]):.1f}  ratio={fmt_stat(vehs_ratios)}")
    print(f"[DISTANCE]   pred={st.median(dist_preds):.1f}  reel={st.median(dist_reals):.1f}  ratio={fmt_stat(dist_ratios)}")
    print(f"[VITESSE]    pred={st.median(speed_preds) if speed_preds else 0:.1f}  cat={st.median(speed_cats) if speed_cats else 0:.1f}  reel={st.median(speed_reals) if speed_reals else 0:.1f}  ratio reel/pred={fmt_stat(speed_ratios)}")
    print(f"[NOTE GARE]  pred=50.0 % (STATION_RATING_PCT)  reel={fmt_stat(ratings_all)} %  ratio={st.median(ratings_all)/50.0:.2f}")
    print(f"[VOLUME/AN]  pred={st.median(carried_preds):.0f}  implied_reel={st.median(implied_carried):.0f}  ratio={fmt_stat(carried_ratios)}")
    if pops:
        print(f"[VILLE POP]  med={st.median(pops):.0f} (min={min(pops)}, max={max(pops)})")
    if prods:
        print(f"[VILLE PROD] med={st.median(prods):.0f} (min={min(prods)}, max={max(prods)})")
    if waits:
        print(f"[ATTENTE]    med={st.median(waits):.0f} (min={min(waits)}, max={max(waits)})")

    # Detail line by line
    print("\n--- 3. DETAIL LIGNE PAR LIGNE (identifiant unique graine:line) ---")
    print(f"{'ligne':>10} {'an':>4} {'age':>3} {'rev_p':>7} {'rev_r':>7} {'r/p':>6} "
          f"{'prof_p':>7} {'prof_r':>7} {'run_p':>6} {'run_r':>6} {'v_p':>3} {'v_r':>3} "
          f"{'d_p':>3} {'d_r':>3} {'sp_r':>4} {'notA':>4} {'notB':>4} {'car_p':>5} {'car_r':>5}")
    for r in sorted(c23, key=lambda x: (x["seed"], x["line"], x["year"])):
        lid = f"{r['seed']}:{r['line']}"
        c_real = (r["real_rev"] / (r["pred_rev"] / r["pred_carried"])) if (r["pred_carried"] > 0 and r["pred_rev"] > 0) else 0
        print(f"{lid:>10} {r['year']:>4} {r['age']:>3} {r['pred_rev']:>7.0f} {r['real_rev']:>7.0f} "
              f"{r['real_rev']/r['pred_rev']:>6.2f} {r['pred_prof']:>7.0f} {r['real_prof']:>7.0f} "
              f"{r['pred_run']:>6.0f} {r['real_run']:>6.0f} {r['pred_vehs']:>3} {r['vehs']:>3} "
              f"{r['dist']:>3} {r['real_dist']:>3} {r['real_speed']:>4} {r['rating_a']:>4} {r['rating_b']:>4} "
              f"{r['pred_carried']:>5.0f} {c_real:>5.0f}")

    summary = {
        "n_useful": len(c23),
        "rev_ratio_median": st.median(rev_ratios),
        "rev_ratio_agg": sum(r["real_rev"] for r in c23) / sum(r["pred_rev"] for r in c23),
        "rev_ratio_q1": st.quantiles(rev_ratios, n=4)[0] if len(rev_ratios) >= 4 else min(rev_ratios),
        "rev_ratio_q3": st.quantiles(rev_ratios, n=4)[2] if len(rev_ratios) >= 4 else max(rev_ratios),
        "rev_ratio_min": min(rev_ratios),
        "rev_ratio_max": max(rev_ratios),
        "share_below_half": sum(1 for x in rev_ratios if x < 0.5) / len(rev_ratios),
        "prof_ratio_median": st.median(prof_ratios) if prof_ratios else None,
        "run_ratio_median": st.median(run_ratios) if run_ratios else None,
        "vehs_ratio_median": st.median(vehs_ratios) if vehs_ratios else None,
        "dist_ratio_median": st.median(dist_ratios) if dist_ratios else None,
        "rating_median": st.median(ratings_all) if ratings_all else None,
        "speed_ratio_median": st.median(speed_ratios) if speed_ratios else None,
        "carried_ratio_median": st.median(carried_ratios) if carried_ratios else None,
        "records": c23
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 999, 7, 1024, 314])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "diag_c23_pax_road.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("decision_log", 1), ("road_fleet_fix", 1)))
    print(f"Lancement de la simulation {len(args.seeds)} graines x {args.years} ans (road_fleet_fix=1)...")
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
        allrecs += records(out, seed)

    print(f"\n{len(allrecs)} enregistrements LINE_REVENUE extraits.")
    summary = analyze_pax_road(allrecs)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "years": args.years,
        "seeds": args.seeds,
        "summary": summary
    }, indent=2))
    print(f"\nResultats ecrits dans {args.out}")


if __name__ == "__main__":
    main()
