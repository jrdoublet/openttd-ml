"""Duels contre AAAHogEx : % du profit AAAHogEx atteint par OpexAI, annee par annee.

Metrique primaire (decision utilisateur 2026-09-30) : pour chaque annee civile
close ``y``, ``ratio_y = profit_opex(y) / profit_aaahogex(y)`` dans la meme
partie. Les annees sont reconstruites depuis ``old_economy`` (trimestres clos,
le plus recent en tete) de la sauvegarde finale ; la partie commence au 1er
janvier et dure un nombre entier d'annees, donc les trimestres [4k, 4k+4) sont
exactement l'annee ``fin - 1 - k``.

Usage (Docker) :
  python3 sweeps/duel_yearly_ratio.py --arms C115=OpexAI \
      "C121=OpexAI[c121_air_economics=1,...]" --seeds 42 100 --years 3
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (  # noqa: E402
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, decode_stations, decode_vehicles,
    enable_savegame_cleanup, make_cfg, quarter_profit,
)

STARTING_YEAR = 1970


def _player(chunks, owner):
    players = chunks.get("PLYR") or {}
    return players.get(owner) or players.get(str(owner)) or {}


def yearly_profits(closed, years):
    """{annee_index: profit} pour les annees entierement couvertes."""
    out = {}
    for k in range(years):
        quarters = [quarter_profit(e) for e in (closed or [])[4 * k:4 * k + 4]]
        if len(quarters) == 4 and all(q is not None for q in quarters):
            out[years - 1 - k] = sum(quarters)
    return out


def yearly_ratios(opex, aaa):
    ratios = {}
    for idx in sorted(set(opex) & set(aaa)):
        ratios[idx] = opex[idx] / aaa[idx] if aaa[idx] > 0 else None
    return ratios


def _territory(chunks, owner):
    """Aeroports et avions/vehicules primaires d'une compagnie a cette sauvegarde."""
    try:
        v = decode_vehicles(chunks.get("VEHS"), target_owner=owner)
        s = decode_stations(chunks.get("STNN"), target_owner=owner)
    except Exception:  # noqa: BLE001 - diagnostic seulement
        return None
    return {
        "airports": s["stations_by_facility"].get("airport", 0) if s["chunk_valid"] else None,
        "stations": s["total_stations"] if s["chunk_valid"] else None,
        "aircraft": v["primary_vehicles_by_mode"].get("air", 0) if v["chunk_valid"] else None,
        "vehicles": v["primary_vehicles_count"] if v["chunk_valid"] else None,
        "by_mode": v["primary_vehicles_by_mode"] if v["chunk_valid"] else None,
        "stations_by_facility": s["stations_by_facility"] if s["chunk_valid"] else None,
    }


def make_keep(years):
    def keep(row):
        chunks = row.get("chunks", {})
        opex = yearly_profits(_player(chunks, 0).get("old_economy"), years)
        aaa = yearly_profits(_player(chunks, 1).get("old_economy"), years)
        return ({
            "arm": row["experiment"]["bench_arm"],
            "seed": row["experiment"]["seed"],
            "date": str(row.get("date", "")),
            "opex_year": opex, "aaa_year": aaa,
            "ratio_year": yearly_ratios(opex, aaa),
            "quarters": [len(_player(chunks, o).get("old_economy") or []) for o in (0, 1)],
            "territory": {str(o): _territory(chunks, o) for o in (0, 1)},
        },)
    return keep


def summarize(latest, arms, seeds, years):
    summary = {}
    for arm in arms:
        per_year = {}
        for y in range(years):
            vals = [latest[(arm, s)]["ratio_year"].get(y) for s in seeds if (arm, s) in latest]
            vals = [v for v in vals if v is not None]
            per_year[STARTING_YEAR + y] = {
                "mean_pct": 100 * statistics.mean(vals) if vals else None,
                "median_pct": 100 * statistics.median(vals) if vals else None,
                "n": len(vals),
            }
        summary[arm] = per_year
    return summary


def paired(latest, a, b, seeds, years):
    """Delta de ratio (points de %) a-b par annee, et victoires."""
    out = {}
    for y in range(years):
        d = []
        for s in seeds:
            ra = latest.get((a, s), {}).get("ratio_year", {}).get(y)
            rb = latest.get((b, s), {}).get("ratio_year", {}).get(y)
            if ra is not None and rb is not None:
                d.append(100 * (ra - rb))
        out[STARTING_YEAR + y] = {
            "delta_pts_mean": statistics.mean(d) if d else None,
            "wins": sum(x > 0 for x in d), "losses": sum(x < 0 for x in d), "n": len(d),
        }
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arms", nargs="+", required=True, help="NOM=OpexAI[...] ; le premier est la reference")
    p.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    p.add_argument("--years", type=int, default=3)
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    named = [a.split("=", 1) for a in args.arms]
    built = build_arms([spec for _, spec in named] + ["AAAHogEx"])
    aaa = built["AAAHogEx"]
    enable_savegame_cleanup()
    cfg = make_cfg(STARTING_YEAR)
    # Jusqu'a fin janvier de l'annee de fin : Q4 de la derniere annee clos, pas d'autre trimestre.
    days = (date(STARTING_YEAR + args.years, 1, 1) - date(STARTING_YEAR, 1, 1)).days + 32
    experiments = [
        {"bench_arm": name, "seed": seed, "days": days,
         "openttd_config": cfg, "ais": (built[spec], aaa)}
        for name, spec in named for seed in args.seeds
    ]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=experiments, max_workers=args.workers, result_processor=make_keep(args.years),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    latest = {}
    for r in rows:
        k = (r["arm"], r["seed"])
        if k not in latest or r["date"] > latest[k]["date"]:
            latest[k] = r
    # Territoire en fin d'annee : premiere sauvegarde de l'annee suivante.
    for r in rows:
        k = (r["arm"], r["seed"])
        yr = int(r["date"][:4]) - 1
        snaps = latest[k].setdefault("territory_year_end", {})
        if yr >= STARTING_YEAR and (str(yr) not in snaps or r["date"] < snaps[str(yr)]["date"]):
            snaps[str(yr)] = {"date": r["date"], **r["territory"]}
    names = [n for n, _ in named]
    summary = summarize(latest, names, args.seeds, args.years)
    pairs = {f"{n}-{names[0]}": paired(latest, n, names[0], args.seeds, args.years) for n in names[1:]}
    payload = {"metric": "profit_opex(y)/profit_aaahogex(y)", "starting_year": STARTING_YEAR,
               "years": args.years, "seeds": args.seeds, "arms": dict(named),
               "summary": summary, "pairs": pairs,
               "runs": [latest[k] for k in sorted(latest)], "complete": len(latest) == len(experiments)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")

    print("annee | " + " | ".join(names))
    for y in range(args.years):
        cells = [summary[n][STARTING_YEAR + y]["mean_pct"] for n in names]
        print(f"{STARTING_YEAR + y} | " + " | ".join("n/a" if c is None else f"{c:.1f} %" for c in cells))
    for key, per in pairs.items():
        for yr, v in per.items():
            if v["delta_pts_mean"] is not None:
                print(f"{key} {yr}: {v['delta_pts_mean']:+.1f} pts  W/L {v['wins']}/{v['losses']}")
    print("territoire fin d'annee (moyenne) : aeroports O/A | avions O/A")
    for n in names:
        for y in range(args.years):
            yr = str(STARTING_YEAR + y)
            snaps = [latest[(n, s)].get("territory_year_end", {}).get(yr) for s in args.seeds if (n, s) in latest]
            snaps = [x for x in snaps if x and x.get("0") and x.get("1")]
            if not snaps:
                continue
            m = lambda o, f: statistics.mean(x[o][f] or 0 for x in snaps)  # noqa: E731
            print(f"{n} {yr}: {m('0','airports'):.1f}/{m('1','airports'):.1f} | "
                  f"{m('0','aircraft'):.1f}/{m('1','aircraft'):.1f}  (n={len(snaps)})")
    print(f"JSON: {args.out}  complet={payload['complete']}")


if __name__ == "__main__":
    main()
