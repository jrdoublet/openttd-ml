"""Diagnostic 5 graines x 6 ans pour C55 : Assouplissement des origines route (c55_road_origin_relax).

Compare OpexAI (baseline, relax=0) vs OpexAI[c55_road_origin_relax=1] sous decision_log=1.
Mesure :
- Grandeurs physiques : gares, vehicules (total, bus pax, camions fret, trains, avions).
- Economie : valeur de compagnie, profit annuel, profit trimestre, note mediane.
- Decisions : ROAD_BUILD, projets pax/fret elus, discards par cause.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    make_cfg,
    quarter_profit,
    write_json_atomically,
    year_profit,
)

SEEDS_5 = [100, 12345, 42, 7, 999]
ARMS = (
    "OpexAI[decision_log=1]",
    "OpexAI[c55_road_origin_relax=1,decision_log=1]",
)

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_decisions(output):
    events = Counter()
    road_pax_chosen = 0
    road_freight_chosen = 0
    discards_by_reason = Counter()
    for line in (output or "").splitlines():
        m = OPEX_EVENT_RE.search(line)
        if not m:
            continue
        tag = m.group(4)
        rest = m.group(5)
        events[tag] += 1
        if tag == "PROJECT_CHOSEN":
            if "mode=road" in rest:
                if "kind=pax" in rest:
                    road_pax_chosen += 1
                elif "kind=freight" in rest:
                    road_freight_chosen += 1
        elif tag == "PROJECT_DISCARD":
            if "mode=road" in rest:
                rm = re.search(r"reason=([a-zA-Z0-9_]+)", rest)
                if rm:
                    discards_by_reason[rm.group(1)] += 1
    return {
        "events": dict(events),
        "road_pax_chosen": road_pax_chosen,
        "road_freight_chosen": road_freight_chosen,
        "road_discards": dict(discards_by_reason),
    }


def count_vehicles(vehs_chunk):
    counts = Counter()
    if not isinstance(vehs_chunk, dict):
        return counts
    for v in vehs_chunk.values():
        t = v.get("type")
        if t == 1:
            rv = v.get("roadveh", [])
            common = rv[0].get("common", [{}])[0] if rv and rv[0].get("common") else {}
            if common.get("unitnumber", 0) > 0:
                cargo = common.get("cargo_type", 0)
                if cargo == 0:
                    counts["road_pax"] += 1
                else:
                    counts["road_freight"] += 1
                counts["road_total"] += 1
        elif t == 0:
            tr = v.get("train", [])
            common = tr[0].get("common", [{}])[0] if tr and tr[0].get("common") else {}
            if common.get("unitnumber", 0) > 0:
                counts["trains"] += 1
        elif t == 3:
            air = v.get("aircraft", [])
            common = air[0].get("common", [{}])[0] if air and air[0].get("common") else {}
            if common.get("unitnumber", 0) > 0:
                counts["aircraft"] += 1
        elif t == 2:
            sh = v.get("ship", [])
            common = sh[0].get("common", [{}])[0] if sh and sh[0].get("common") else {}
            if common.get("unitnumber", 0) > 0:
                counts["ships"] += 1
    return counts


def keep(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    dec = parse_decisions(row.get("output", ""))
    py = year_profit(closed)

    stnn = chunks.get("STNN", {})
    stations_list = stnn.values() if isinstance(stnn, dict) else stnn
    ratings = [g["rating"] for s in stations_list for g in s.get("goods", []) if g.get("rating", 0) > 0]
    med_rating = statistics.median(ratings) if ratings else 0

    vehs_chunk = chunks.get("VEHS", {})
    veh_counts = count_vehicles(vehs_chunk)

    exp = row.get("experiment", {})
    arm = exp.get("bench_arm") or (exp["bench_run"][0] if "bench_run" in exp else "unknown")
    seed = exp.get("seed") or (exp["bench_run"][1] if "bench_run" in exp else 0)

    return ({
        "arm": arm,
        "seed": seed,
        "company_value": last_closed.get("company_value", 0),
        "profit_year": py if py is not None else 0,
        "profit": quarter_profit(last_closed) or 0,
        "performance_history": last_closed.get("performance_history", 0),
        "median_station_rating": med_rating,
        "n_vehicles": len(vehs_chunk),
        "n_stations": len(stnn),
        "veh_counts": dict(veh_counts),
        "road_pax_chosen": dec["road_pax_chosen"],
        "road_freight_chosen": dec["road_freight_chosen"],
        "road_builds": dec["events"].get("ROAD_BUILD", 0),
        "road_discards": dec["road_discards"],
        "events": dec["events"],
    },)


def run_selftest():
    sample_output = """
OPEX 1970-02-01 PROJECT_CHOSEN rank=0 mode=road kind=pax cargo=PASS src=100 dst=200 dist=12 cost=5000 profit=1000 roi=20.0
OPEX 1970-02-01 ROAD_BUILD line=1 src=100 dst=200 cargo=PASS dist=12 profit=1000 cost=4500 vehicles=2
OPEX 1970-03-01 PROJECT_CHOSEN rank=1 mode=road kind=freight cargo=COAL src=300 dst=400 dist=18 cost=7000 profit=1500 roi=21.0
OPEX 1970-03-01 ROAD_BUILD line=2 src=300 dst=400 cargo=COAL dist=18 profit=1500 cost=6800 vehicles=2
OPEX 1970-04-01 PROJECT_DISCARD rank=2 mode=road src=100 dst=500 reason=town_road_line_cap
OPEX 1970-05-01 PROJECT_DISCARD rank=3 mode=road src=300 dst=600 reason=src_origin_served
"""
    dec = parse_decisions(sample_output)
    assert dec["road_pax_chosen"] == 1
    assert dec["road_freight_chosen"] == 1
    assert dec["events"].get("ROAD_BUILD") == 2
    assert dec["road_discards"].get("town_road_line_cap") == 1
    assert dec["road_discards"].get("src_origin_served") == 1

    fixture_path = ROOT / "sweeps" / "fixtures" / "c53_real_chunks_15_3.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            fixture_data = json.load(f)
        vc = count_vehicles(fixture_data.get("VEHS", {}))
        assert vc["road_total"] == 24
        assert vc["road_pax"] == 12
        assert vc["road_freight"] == 12
        assert vc["aircraft"] == 4
        assert vc["trains"] == 2

    print("Selftest passed successfully!")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=SEEDS_5)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    out = args.out or ROOT / "results" / f"diag_c55_road_origin_relax_{args.years}y_{len(args.seeds)}seeds.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    enable_savegame_cleanup()
    built = build_arms(list(ARMS))
    cfg = make_cfg(1970)

    print(f"Lancement du diagnostic C55 road origin relax : {len(args.seeds)} graines x {args.years} ans")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(built, args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    # Regrouper par graine
    by_seed = defaultdict(dict)
    for r in rows:
        arm_label = "RELAX_ON" if "c55_road_origin_relax=1" in r["arm"] else "BASELINE"
        by_seed[r["seed"]][arm_label] = r

    print("\n" + "=" * 80)
    print(f"{'Graine':<8} | {'Bras':<10} | {'Val. Cie':>12} | {'Prof. An':>10} | {'Gares':>6} | {'Veh. Tot':>8} | {'Bus Pax':>8} | {'Cam. Fret':>9} | {'Road Builds':>11}")
    print("-" * 80)

    metrics_diff = defaultdict(list)
    for seed in sorted(by_seed.keys()):
        base = by_seed[seed].get("BASELINE", {})
        on = by_seed[seed].get("RELAX_ON", {})
        if not base or not on:
            continue

        for label, d in (("BASELINE", base), ("RELAX_ON", on)):
            vc = d.get("veh_counts", {})
            print(f"{seed:<8} | {label:<10} | {d.get('company_value', 0):>12,d} | {d.get('profit_year', 0):>10,d} | {d.get('n_stations', 0):>6d} | {d.get('n_vehicles', 0):>8d} | {vc.get('road_pax', 0):>8d} | {vc.get('road_freight', 0):>9d} | {d.get('road_builds', 0):>11d}")
        
        diff_val = on.get("company_value", 0) - base.get("company_value", 0)
        diff_py = on.get("profit_year", 0) - base.get("profit_year", 0)
        diff_st = on.get("n_stations", 0) - base.get("n_stations", 0)
        diff_veh = on.get("n_vehicles", 0) - base.get("n_vehicles", 0)
        diff_pax_veh = on.get("veh_counts", {}).get("road_pax", 0) - base.get("veh_counts", {}).get("road_pax", 0)
        diff_frt_veh = on.get("veh_counts", {}).get("road_freight", 0) - base.get("veh_counts", {}).get("road_freight", 0)
        diff_builds = on.get("road_builds", 0) - base.get("road_builds", 0)
        
        metrics_diff["val"].append(diff_val)
        metrics_diff["profit_year"].append(diff_py)
        metrics_diff["stations"].append(diff_st)
        metrics_diff["vehicles"].append(diff_veh)
        metrics_diff["pax_veh"].append(diff_pax_veh)
        metrics_diff["frt_veh"].append(diff_frt_veh)
        metrics_diff["builds"].append(diff_builds)
        print("-" * 80)

    print("\nSynthese des differences (RELAX_ON - BASELINE) sur 5 graines :")
    for key, vals in metrics_diff.items():
        pos = sum(1 for v in vals if v > 0)
        neg = sum(1 for v in vals if v < 0)
        eq = sum(1 for v in vals if v == 0)
        med = statistics.median(vals)
        mean = statistics.mean(vals)
        print(f"  - {key:<12}: +{pos} / -{neg} / ={eq} | Mediane = {med:+,.1f} | Moyenne = {mean:+,.1f}")

    summary_data = {
        "years": args.years,
        "seeds": args.seeds,
        "rows": rows,
        "metrics_diff": {k: [int(x) for x in v] for k, v in metrics_diff.items()},
    }
    write_json_atomically(out, summary_data)
    print(f"\nResultats enregistres dans {out}")


if __name__ == "__main__":
    main()
