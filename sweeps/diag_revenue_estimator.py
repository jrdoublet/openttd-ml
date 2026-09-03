"""Diagnostic de l'estimateur de revenus et de profits (predit vs reel).

Compare les revenus et profits predits (revenueAnnual, profitAnnual) aux revenus et profits
reels mesures par _reportLines (via LINE_REVENUE), sur le banc standard 20 graines x 3 ans,
avec un focus particulier sur les lignes a faible ratio d'opcodes (low_ratio=1) autorisees
par vivier_ratio_filter=0.
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit  # noqa: E402

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
SCRIPT_DEBUG_LEVEL = "4"
CFG = make_cfg(1970)

DEFAULT_SEEDS = [
    42, 100, 7, 999, 2026, 1, 17, 73, 314, 512,
    1024, 1337, 4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309,
]

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", f"script={SCRIPT_DEBUG_LEVEL}") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

LINE_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[(\w)\] (.*)")
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_line_revenues(output):
    records = []
    for line in (output or "").splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        m2 = OPEX_RE.match(m.group(3).strip())
        if not m2:
            continue
        year, month, day, kind, rest = m2.groups()
        if kind != "LINE_REVENUE":
            continue
        fields = {}
        for token in rest.split():
            if "=" in token:
                k, _, v = token.partition("=")
                fields[k] = v
        try:
            records.append({
                "date": f"{int(year):04d}-{int(month):02d}-{int(day):02d}",
                "line": int(fields.get("line", -1)),
                "mode": fields.get("mode", "?"),
                "kind": fields.get("kind", "?"),
                "cargo": fields.get("cargo", "?"),
                "year": int(fields.get("year", 0)),
                "age": int(fields.get("age", 0)),
                "pred_rev": float(fields.get("pred_rev", 0)),
                "real_rev": float(fields.get("real_rev", 0)),
                "pred_prof": float(fields.get("pred_prof", 0)),
                "real_prof": float(fields.get("real_prof", 0)),
                "pred_run": float(fields.get("pred_run", 0)),
                "real_run": float(fields.get("real_run", 0)),
                "vehs": int(fields.get("vehs", 0)),
                "low_ratio": int(fields.get("low_ratio", 0)),
                "op_ratio": float(fields.get("op_ratio", -1)),
            })
        except Exception:
            continue
    return records


def keep(row):
    chunks = row["chunks"]
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    return ({
        "arm": row["experiment"]["diag_arm"],
        "seed": row["experiment"]["seed"],
        "profit": quarter_profit(last_closed),
        "profit_year": year_profit(closed),
        "company_value": last_closed.get("company_value", 0),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "output": row.get("output"),
    },)


def build_experiments(seeds, years):
    experiments = []
    opex_path = str(ROOT / "ai" / "OpexAI")
    arms = [
        ("baseline", (("decision_log", 1),)),
        ("no_filter", (("vivier_ratio_filter", 0), ("decision_log", 1))),
    ]
    for arm_name, settings in arms:
        ai = local_folder(opex_path, "OpexAI", settings)
        for seed in seeds:
            experiments.append({
                "seed": seed,
                "days": 365 * years,
                "openttd_config": CFG,
                "ais": (ai,),
                "diag_arm": arm_name,
            })
    return experiments


def summarize_ratios(records):
    if not records:
        return {"n_recs": 0}
    rev_ratios = [r["real_rev"] / r["pred_rev"] for r in records if r["pred_rev"] > 0]
    prof_ratios = [r["real_prof"] / r["pred_prof"] for r in records if r["pred_prof"] > 0]
    
    total_pred_rev = sum(r["pred_rev"] for r in records)
    total_real_rev = sum(r["real_rev"] for r in records)
    total_pred_prof = sum(r["pred_prof"] for r in records)
    total_real_prof = sum(r["real_prof"] for r in records)
    
    def median(lst):
        if not lst:
            return 0.0
        s = sorted(lst)
        n = len(s)
        return s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2.0

    return {
        "n_recs": len(records),
        "total_pred_rev": total_pred_rev,
        "total_real_rev": total_real_rev,
        "agg_rev_ratio": total_real_rev / total_pred_rev if total_pred_rev > 0 else 0.0,
        "med_rev_ratio": median(rev_ratios),
        "total_pred_prof": total_pred_prof,
        "total_real_prof": total_real_prof,
        "agg_prof_ratio": total_real_prof / total_pred_prof if total_pred_prof > 0 else 0.0,
        "med_prof_ratio": median(prof_ratios),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=str, default="docs/diag_revenue_estimator_3y_20seeds.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    print(f"=== Lancement Diagnostic Estimateur de Revenus : {len(args.seeds)} graines x {args.years} ans ===")
    experiments = build_experiments(args.seeds, args.years)

    results = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.max_workers,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    arm_data = defaultdict(dict)
    for r in results:
        arm_name = r["arm"]
        seed = r["seed"]
        out = r.get("output")
        if seed not in arm_data[arm_name]:
            arm_data[arm_name][seed] = {
                "arm": arm_name,
                "seed": seed,
                "profit": r["profit"],
                "profit_year": r["profit_year"],
                "company_value": r["company_value"],
                "n_vehicles": r["n_vehicles"],
                "n_stations": r["n_stations"],
                "line_revenues": [],
            }
        if r.get("company_value"):
            arm_data[arm_name][seed]["profit"] = r["profit"]
            arm_data[arm_name][seed]["profit_year"] = r["profit_year"]
            arm_data[arm_name][seed]["company_value"] = r["company_value"]
            arm_data[arm_name][seed]["n_vehicles"] = r["n_vehicles"]
            arm_data[arm_name][seed]["n_stations"] = r["n_stations"]
        if out:
            arm_data[arm_name][seed]["line_revenues"] = parse_line_revenues(out)

    analysis = {}
    for arm_name, seed_dict in arm_data.items():
        runs = list(seed_dict.values())
        all_recs = []
        for run in runs:
            all_recs.extend(run["line_revenues"])
        
        mature_recs = [r for r in all_recs if r["age"] >= 1]
        if not mature_recs:
            mature_recs = all_recs  # fallback to all recs if none age >= 1
        
        by_mode = {}
        for m in ("rail", "road", "air"):
            by_mode[m] = summarize_ratios([r for r in mature_recs if r["mode"] == m])
            
        low_ratio_recs = [r for r in mature_recs if r["low_ratio"] == 1]
        normal_ratio_recs = [r for r in mature_recs if r["low_ratio"] == 0]
        
        analysis[arm_name] = {
            "summary_overall": summarize_ratios(mature_recs),
            "by_mode": by_mode,
            "low_ratio": summarize_ratios(low_ratio_recs),
            "normal_ratio": summarize_ratios(normal_ratio_recs),
            "n_runs": len(runs),
            "company_values": {run["seed"]: run["company_value"] for run in runs},
            "profits_year": {run["seed"]: run["profit_year"] for run in runs},
        }

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"analysis": analysis, "runs": arm_data}, f, indent=2)

    print(f"\nRapport enregistre dans : {out_path}\n")

    print("=" * 80)
    print(f"{'ANALYSE ESTIMATEUR DE REVENUS & PROFITS (age >= 1)':^80}")
    print("=" * 80)
    for arm in ("baseline", "no_filter"):
        data = analysis.get(arm, {})
        overall = data.get("summary_overall", {})
        print(f"\n--- BRAS : {arm.upper()} ---")
        print(f"Lignes matures observees : {overall.get('n_recs', 0)}")
        print(f"Revenus: Pred={overall.get('total_pred_rev', 0):,.0f} £ | Reel={overall.get('total_real_rev', 0):,.0f} £ | Ratio Agrege={overall.get('agg_rev_ratio', 0):.2f} (Mediane={overall.get('med_rev_ratio', 0):.2f})")
        print(f"Profits: Pred={overall.get('total_pred_prof', 0):,.0f} £ | Reel={overall.get('total_real_prof', 0):,.0f} £ | Ratio Agrege={overall.get('agg_prof_ratio', 0):.2f} (Mediane={overall.get('med_prof_ratio', 0):.2f})")
        
        print("\n  Par mode de transport :")
        for m, stats in data.get("by_mode", {}).items():
            print(f"    - {m:<5} (n={stats.get('n_recs', 0):>3}) : Rev Real/Pred = {stats.get('agg_rev_ratio', 0):.2f} (med {stats.get('med_rev_ratio', 0):.2f}) | Prof Real/Pred = {stats.get('agg_prof_ratio', 0):.2f}")
            
        low = data.get("low_ratio", {})
        norm = data.get("normal_ratio", {})
        print("\n  Focus Low-Ratio vs Normal-Ratio :")
        print(f"    - Normal (n={norm.get('n_recs', 0):>3}) : Rev Real/Pred = {norm.get('agg_rev_ratio', 0):.2f} | Prof Real/Pred = {norm.get('agg_prof_ratio', 0):.2f}")
        print(f"    - Low-Ratio (n={low.get('n_recs', 0):>3}) : Rev Real/Pred = {low.get('agg_rev_ratio', 0):.2f} | Prof Real/Pred = {low.get('agg_prof_ratio', 0):.2f}")

    print("=" * 80)


if __name__ == "__main__":
    main()
