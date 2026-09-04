"""Banc apparie Year 1 (1970) : OpexAI AVEC feeders vs OpexAI SANS feeders sur 5 graines."""
import json
import statistics
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import make_cfg, year_profit, quarter_profit, station_ratings

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
DEFAULT_SEEDS = (42, 100, 7, 999, 2026)
TYPE_TO_MODE = {"0": "train", "1": "roadveh", "2": "ship", "3": "aircraft"}
VEHICLE_MODES = ("train", "roadveh", "ship", "aircraft")

def _first(value):
    return value[0] if isinstance(value, list) and value else value

def vehicle_breakdown(chunks, owner=0):
    counts = {mode: 0 for mode in VEHICLE_MODES}
    for vehicle in (chunks.get("VEHS") or {}).values():
        if not isinstance(vehicle, dict): continue
        vtype = str(vehicle.get("type"))
        if vtype not in TYPE_TO_MODE: continue
        mode = TYPE_TO_MODE[vtype]
        body = _first(vehicle.get(mode))
        common = _first((body or {}).get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != owner: continue
        if not common.get("unitnumber"): continue
        counts[mode] += 1
    return counts

def keep(row):
    chunks = row["chunks"]
    player = (chunks.get("PLYR") or {}).get(0) or (chunks.get("PLYR") or {}).get("0") or {}
    closed = player.get("old_economy") or []
    last = closed[0] if closed else {}
    ratings = station_ratings(chunks)
    counts = vehicle_breakdown(chunks)

    return ({
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row.get("date", "")),
        "company_value": last.get("company_value", 0),
        "profit_year": year_profit(closed) or 0,
        "performance_history": last.get("performance_history", 0),
        "delivered_cargo": last.get("delivered_cargo", 0),
        "money": player.get("money", 0),
        "current_loan": player.get("current_loan", 0),
        "n_vehicles": sum(counts.values()),
        "by_mode": counts,
        "n_stations": len(chunks.get("STNN") or {}),
    },)

def main():
    cfg = make_cfg(1970)
    seeds = [42, 100, 7, 999, 2026]
    experiments = []

    ai_with = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("feeder_enabled", 1),))
    ai_without = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("feeder_enabled", 0),))

    for s in seeds:
        experiments.append({
            "bench_arm": "Avec_Feeders",
            "seed": s,
            "days": 365,
            "openttd_config": cfg,
            "ais": (ai_with,),
        })
        experiments.append({
            "bench_arm": "Sans_Feeders",
            "seed": s,
            "days": 365,
            "openttd_config": cfg,
            "ais": (ai_without,),
        })

    print(f"Lancement banc apparie Annee 1 (5 graines, Avec vs Sans feeders)...")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=8,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    by_run = {}
    for r in rows:
        if r["date"].startswith("1970-12") or r["date"].startswith("1971-01"):
            by_run[(r["arm"], r["seed"])] = r

    print("\n" + "=" * 105)
    print("BANC APPARIE ANNEE 1 (1970) : AVEC FEEDERS vs SANS FEEDERS (5 GRAINES)")
    print("=" * 105)
    header = f"{'Graine':<7} | {'Valeur Avec vs Sans':<28} | {'Profit Avec vs Sans':<26} | {'Score A vs S':<16} | {'Avions A vs S':<16} | {'Cash A vs S':<20}"
    print(header)
    print("-" * len(header))

    with_vals, without_vals = [], []
    with_profs, without_profs = [], []
    with_scs, without_scs = [], []
    with_planes, without_planes = [], []
    with_cash, without_cash = [], []

    for s in seeds:
        w = by_run.get(("Avec_Feeders", s), {})
        wo = by_run.get(("Sans_Feeders", s), {})

        wv, wov = w.get("company_value", 0), wo.get("company_value", 0)
        wp, wop = w.get("profit_year", 0), wo.get("profit_year", 0)
        ws, wos = w.get("performance_history", 0), wo.get("performance_history", 0)
        w_pl, wo_pl = w.get("by_mode", {}).get("aircraft", 0), wo.get("by_mode", {}).get("aircraft", 0)
        wc, woc = w.get("money", 0), wo.get("money", 0)

        with_vals.append(wv)
        without_vals.append(wov)
        with_profs.append(wp)
        without_profs.append(wop)
        with_scs.append(ws)
        without_scs.append(wos)
        with_planes.append(w_pl)
        without_planes.append(wo_pl)
        with_cash.append(wc)
        without_cash.append(woc)

        diff_v = ((wv - wov) / wov * 100) if wov > 0 else 0
        diff_p = ((wp - wop) / wop * 100) if wop > 0 else 0

        v_str = f"{wv:>8,.0f} vs {wov:>8,.0f} ({diff_v:>+5.1f}%)"
        p_str = f"{wp:>7,.0f} vs {wop:>7,.0f} ({diff_p:>+5.1f}%)"
        s_str = f"{ws:>3} vs {wos:>3}"
        pl_str = f"{w_pl:>2} vs {wo_pl:>2}"
        c_str = f"{wc:>7,.0f} vs {woc:>7,.0f}"

        print(f"{s:<7} | {v_str:<28} | {p_str:<26} | {s_str:<16} | {pl_str:<16} | {c_str:<20}")

    print("-" * len(header))
    mv_w, mv_wo = statistics.mean(with_vals), statistics.mean(without_vals)
    mp_w, mp_wo = statistics.mean(with_profs), statistics.mean(without_profs)
    ms_w, ms_wo = statistics.mean(with_scs), statistics.mean(without_scs)
    mpl_w, mpl_wo = statistics.mean(with_planes), statistics.mean(without_planes)
    mc_w, mc_wo = statistics.mean(with_cash), statistics.mean(without_cash)

    diff_mv = ((mv_w - mv_wo) / mv_wo * 100) if mv_wo > 0 else 0
    diff_mp = ((mp_w - mp_wo) / mp_wo * 100) if mp_wo > 0 else 0

    print(f"MOYENNE | {mv_w:>8,.0f} vs {mv_wo:>8,.0f} ({diff_mv:>+5.1f}%) | {mp_w:>7,.0f} vs {mp_wo:>7,.0f} ({diff_mp:>+5.1f}%) | {ms_w:>3.0f} vs {ms_wo:>3.0f}       | {mpl_w:>2.1f} vs {mpl_wo:>2.1f}       | {mc_w:>7,.0f} vs {mc_wo:>7,.0f}")
    med_v_w, med_v_wo = statistics.median(with_vals), statistics.median(without_vals)
    med_p_w, med_p_wo = statistics.median(with_profs), statistics.median(without_profs)
    diff_med_v = ((med_v_w - med_v_wo) / med_v_wo * 100) if med_v_wo > 0 else 0
    diff_med_p = ((med_p_w - med_p_wo) / med_p_wo * 100) if med_p_wo > 0 else 0
    print(f"MEDIANE | {med_v_w:>8,.0f} vs {med_v_wo:>8,.0f} ({diff_med_v:>+5.1f}%) | {med_p_w:>7,.0f} vs {med_p_wo:>7,.0f} ({diff_med_p:>+5.1f}%) | {statistics.median(with_scs):>3.0f} vs {statistics.median(without_scs):>3.0f}       | {statistics.median(with_planes):>2.0f} vs {statistics.median(without_planes):>2.0f}       | {statistics.median(with_cash):>7,.0f} vs {statistics.median(without_cash):>7,.0f}")

if __name__ == "__main__":
    main()
