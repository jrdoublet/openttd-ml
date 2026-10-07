"""R21 engine exposure: prove destination-side freight collapse from existing signs.

This diagnostic does not change OpexAI behaviour.  It joins the annual IA/OZ/OU/DL
signs already emitted by the normal freight report.  A DL event with a live,
productive source and implicit revenue <= 0 can only come from R21's real
destination-acceptance check (or an invalid destination station), because
``srcSuffering`` is false by construction.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from openttdlab import bananas_ai_library, local_folder, run_experiments


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""

RE_IA = re.compile(r"^IA\|(\d+)\|(\d+)\|(-?\d)\|(-?\d)\|(-?\d+)$")
RE_OZ = re.compile(r"^OZ\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OU = re.compile(r"^OU\|(\d+)\|(\d+)\|(\d+)\|(-?\d+)$")
RE_DL = re.compile(r"^DL\|(\d+)\|(\d+)\|(\d+)$")


def signs_in_order(chunks):
    signs = (chunks or {}).get("SIGN", {})
    def key(item):
        try:
            return int(item[0])
        except (TypeError, ValueError):
            return 0
    return [sign.get("name", "") for _, sign in sorted(signs.items(), key=key)]


def keep(row):
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "signs": signs_in_order(row.get("chunks", {})),
        "output": row.get("output", ""),
    },)


def analyse(signs):
    annual = {}
    dead = []
    for sign in signs:
        if m := RE_IA.match(sign):
            key = (int(m.group(1)), int(m.group(2)))
            row = annual.setdefault(key, {})
            row.update(src_alive=int(m.group(3)), dst_alive=int(m.group(4)), src_prod=int(m.group(5)))
        elif m := RE_OZ.match(sign):
            key = (int(m.group(1)), int(m.group(2)))
            annual.setdefault(key, {})["profit"] = int(m.group(3))
        elif m := RE_OU.match(sign):
            key = (int(m.group(1)), int(m.group(2)))
            row = annual.setdefault(key, {})
            row.update(vehicles=int(m.group(3)), run_cost=int(m.group(4)))
        elif m := RE_DL.match(sign):
            dead.append({"year": int(m.group(1)), "line": int(m.group(2)), "stage": int(m.group(3))})

    dead_by_key = {(row["line"], row["year"]): row["stage"] for row in dead if row["stage"] <= 2}
    exposed = []
    healthy_zero_revenue = []
    for (line, year), row in sorted(annual.items()):
        if not {"src_alive", "src_prod", "profit", "run_cost"}.issubset(row):
            continue
        implicit_revenue = row["profit"] + row["run_cost"]
        if row["src_alive"] == 1 and row["src_prod"] > 0 and implicit_revenue <= 0:
            item = {"line": line, "year": year, "implicit_revenue": implicit_revenue, **row}
            stage = dead_by_key.get((line, year))
            if stage is not None:
                item["dead_streak"] = stage
                exposed.append(item)
            else:
                healthy_zero_revenue.append(item)

    consecutive = []
    by_line = {}
    for row in exposed:
        by_line.setdefault(row["line"], []).append(row)
    for line, rows in by_line.items():
        rows.sort(key=lambda row: row["year"])
        for a, b in zip(rows, rows[1:]):
            if b["year"] == a["year"] + 1 and a["dead_streak"] == 1 and b["dead_streak"] >= 2:
                consecutive.append({"line": line, "first": a, "second": b})

    return {
        "annual_records": len(annual),
        "dead_events": dead,
        "r21_destination_exposures": exposed,
        "accepting_or_noncollapsed_counterexamples": healthy_zero_revenue,
        "consecutive_destination_collapse": consecutive,
        "mechanism_exposed": bool(exposed),
        "hysteresis_exposed": bool(consecutive),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=20)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    if out.exists():
        raise FileExistsError(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI")
    experiments = [{"seed": seed, "days": 365 * args.years, "openttd_config": CFG, "ais": (ai,)}
                   for seed in args.seeds]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=min(args.workers, len(experiments)),
        result_processor=keep,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
    ))
    final = {}
    for row in rows:
        if row["seed"] not in final or row["date"] > final[row["seed"]]["date"]:
            final[row["seed"]] = row
    runs = []
    for seed in args.seeds:
        row = final[seed]
        report = analyse(row["signs"])
        report.update(seed=seed, date=row["date"],
                      script_error=("Your script made an error" in row["output"] or
                                    "The script died unexpectedly" in row["output"]))
        runs.append(report)
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "runs": runs,
        "mechanism_exposed": any(run["mechanism_exposed"] for run in runs),
        "hysteresis_exposed": any(run["hysteresis_exposed"] for run in runs),
        "script_errors": any(run["script_error"] for run in runs),
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("mechanism_exposed", "hysteresis_exposed", "script_errors")}, indent=2))
    print(f"ecrit {out}")


if __name__ == "__main__":
    main()
