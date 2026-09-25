"""Diagnostic passif de la caisse OpexAI pendant 1970-1972."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, experiments, write_json_atomically

ARM = "OpexAI[probe_portfolio=1]"


def keep_cash(row):
    chunks = row.get("chunks") or {}
    players = chunks.get("PLYR") or {}
    player = players.get(0) or players.get("0") or {}
    signs = chunks.get("SIGN") or {}
    records = signs.values() if isinstance(signs, dict) else signs
    names = [str(sign.get("name", "")) for sign in records if isinstance(sign, dict)]
    return ({"run": row["experiment"]["bench_run"], "date": str(row["date"]),
             "money": player.get("money"), "loan": player.get("current_loan"),
             "error": bool(row.get("error")), "signs": names},)


def parse_reports(signs):
    reports = {}
    for sign in signs or []:
        parts = sign.split("|")
        if len(parts) < 3 or parts[0] not in {"UC", "UP", "UR", "US", "UT", "UB"}:
            continue
        try:
            yy = int(parts[1])
            year = 1900 + yy if yy >= 70 else 2000 + yy
            out = reports.setdefault(year, {})
            if parts[0] == "UC" and len(parts) >= 5:
                out.update(cash=int(parts[2]), loan=int(parts[3]), reserve=int(parts[4]))
            elif parts[0] == "UP" and len(parts) >= 5:
                out.update(available=int(parts[2]), head_need=int(parts[3]), head_mode=parts[4])
            elif parts[0] == "UR" and len(parts) >= 4:
                out.update(rail_phase=int(parts[2]), rail_need=int(parts[3]))
            elif parts[0] == "US" and len(parts) >= 6:
                out.update(scarcity_cash=int(parts[2]), scarcity_site=int(parts[3]),
                           scarcity_decision=int(parts[4]), scarcity_none=int(parts[5]))
            elif parts[0] == "UT" and len(parts) >= 7:
                out.update(stop_k_pass=int(parts[2]), stop_cash=int(parts[3]),
                           stop_rail_search=int(parts[4]), stop_list_end=int(parts[5]),
                           stop_other=int(parts[6]))
            elif parts[0] == "UB" and len(parts) >= 5:
                out.update(year_passes=int(parts[2]), year_builds=int(parts[3]),
                           year_multi_passes=int(parts[4]))
        except (TypeError, ValueError):
            continue
    return reports


def avg(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


def aggregate(per_seed):
    years = sorted({y for item in per_seed for y in item["reports"]})
    keys = ("cash", "loan", "reserve", "available", "head_need", "rail_phase", "rail_need",
            "scarcity_cash", "scarcity_site", "scarcity_decision", "scarcity_none",
            "stop_k_pass", "stop_cash", "stop_rail_search", "stop_list_end", "stop_other",
            "year_passes", "year_builds", "year_multi_passes")
    result = {}
    for year in years:
        entries = [item["reports"].get(year, {}) for item in per_seed]
        out = {key: avg([entry.get(key) for entry in entries]) for key in keys}
        out["rail_active_seeds"] = sum((entry.get("rail_phase") or 0) > 0 for entry in entries)
        modes = {}
        for entry in entries:
            mode = entry.get("head_mode")
            if mode:
                modes[mode] = modes.get(mode, 0) + 1
        out["head_modes"] = modes
        out["counter_period"] = str(year - 1)
        result[str(year)] = out
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=4)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.years < 2 or not args.seeds or not 1 <= args.max_workers <= 3:
        parser.error("years >= 2, seeds non vide, max-workers 1..3")

    params = (("probe_portfolio", 1), ("debug_signs", 1))
    arms = {ARM: openttdlab.local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", params)}
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep_cash,
        experiments=experiments(arms, args.seeds, args.years, 1, 1970),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    per_seed = []
    for seed in args.seeds:
        series = sorted((row for row in rows if len(row.get("run") or []) >= 2
                         and int(row["run"][1]) == seed), key=lambda row: row["date"])
        final = series[-1] if series else {}
        per_seed.append({"seed": seed,
                         "run_ok": bool(series) and not any(row.get("error") for row in series),
                         "reports": parse_reports(final.get("signs", [])),
                         "monthly": [{"date": row["date"], "cash": row.get("money"),
                                      "loan": row.get("loan")} for row in series]})
    result = {"years": args.years, "seeds": args.seeds, "arm": ARM,
              "per_seed": per_seed, "annual_report_means": aggregate(per_seed)}
    write_json_atomically(args.out, result)
    print(json.dumps(result["annual_report_means"], ensure_ascii=False, indent=2))
    if not all(item["run_ok"] for item in per_seed):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
