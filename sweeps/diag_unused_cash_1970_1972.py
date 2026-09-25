"""Diagnostic solo de la tresorerie OpexAI au demarrage (1970-1972).

Le jeu publie sous ``probe_portfolio=1`` quatre panneaux annuels passifs :

* ``UC`` : cash, emprunt, reserve ;
* ``UP`` : capital disponible, besoin du projet en tete, mode ;
* ``UR`` : phase de la recherche rail et capital du candidat rail ;
* ``US`` : causes C49 cash/site/decision/none sur l'annee.

Ce script ne depend pas de stdout ``script=4`` : il lit le chunk SIGN du
dernier save, les panneaux s'accumulant sur la carte.
"""

import argparse
import json
import re
import statistics
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, make_cfg


UC_RE = re.compile(r"^UC\|(\d+)\|(-?\d+)\|(-?\d+)\|(-?\d+)$")
UP_RE = re.compile(r"^UP\|(\d+)\|(-?\d+)\|(-?\d+)\|([A-Za-z0-9_]+)$")
UR_RE = re.compile(r"^UR\|(\d+)\|(\d+)\|(-?\d+)$")
US_RE = re.compile(r"^US\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
UT_RE = re.compile(r"^UT\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
UB_RE = re.compile(r"^UB\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")


def retain(row):
    signs = [
        value.get("name", "")
        for value in (row.get("chunks", {}).get("SIGN", {}) or {}).values()
        if isinstance(value, dict)
    ]
    return ({
        "date": str(row["date"]),
        "seed": row["experiment"]["seed"],
        "signs": signs,
    },)


def parse_signs(signs):
    years = {}
    for sign in signs:
        match = UC_RE.match(sign)
        if match:
            yy, cash, loan, reserve = match.groups()
            years.setdefault(int(yy), {}).update(
                cash=int(cash), loan=int(loan), reserve=int(reserve)
            )
            continue
        match = UP_RE.match(sign)
        if match:
            yy, available, head_need, head_mode = match.groups()
            years.setdefault(int(yy), {}).update(
                available=int(available), head_need=int(head_need), head_mode=head_mode
            )
            continue
        match = UR_RE.match(sign)
        if match:
            yy, phase, rail_need = match.groups()
            years.setdefault(int(yy), {}).update(
                rail_phase=int(phase), rail_need=int(rail_need)
            )
            continue
        match = US_RE.match(sign)
        if match:
            yy, cash_n, site_n, decision_n, none_n = match.groups()
            # C49 est publie au premier report de l'annee suivante : US|71
            # decrit donc l'annee civile 1970.
            closed_year = int(yy) - 1
            if closed_year < 70:
                continue
            years.setdefault(closed_year, {}).update(
                scarcity_cash=int(cash_n), scarcity_site=int(site_n),
                scarcity_decision=int(decision_n), scarcity_none=int(none_n),
            )
            continue
        match = UT_RE.match(sign)
        if match:
            yy, k_pass, cash_stop, rail_search, list_end, other = match.groups()
            closed_year = int(yy) - 1
            if closed_year < 70:
                continue
            years.setdefault(closed_year, {}).update(
                stop_k_pass=int(k_pass), stop_cash=int(cash_stop),
                stop_rail_search=int(rail_search), stop_list_end=int(list_end),
                stop_other=int(other),
            )
            continue
        match = UB_RE.match(sign)
        if match:
            yy, passes, builds, multi = match.groups()
            closed_year = int(yy) - 1
            if closed_year < 70:
                continue
            years.setdefault(closed_year, {}).update(
                project_passes=int(passes), project_builds=int(builds), multi_build_passes=int(multi)
            )
    for values in years.values():
        available = values.get("available")
        need = values.get("head_need")
        values["head_affordable"] = (
            available is not None and need is not None and need >= 0 and need <= available
        )
        phase = values.get("rail_phase", 0)
        values["rail_searching"] = phase == 1
        values["rail_build_pending"] = phase == 2
    return years


def mean(values):
    values = [value for value in values if value is not None]
    return statistics.mean(values) if values else None


def aggregate(per_seed):
    all_years = sorted({year for row in per_seed for year in row["years"]})
    result = []
    for year in all_years:
        rows = [row["years"].get(year) for row in per_seed]
        rows = [row for row in rows if row]
        if not rows:
            continue
        counts = {key: sum(1 for row in rows if row.get(key)) for key in
                  ("head_affordable", "rail_searching", "rail_build_pending")}
        result.append({
            "year": year,
            "n": len(rows),
            "cash_mean": mean([row.get("cash") for row in rows]),
            "loan_mean": mean([row.get("loan") for row in rows]),
            "reserve_mean": mean([row.get("reserve") for row in rows]),
            "available_mean": mean([row.get("available") for row in rows]),
            "head_need_mean": mean([row.get("head_need") for row in rows if (row.get("head_need") or -1) >= 0]),
            "head_affordable_count": counts["head_affordable"],
            "rail_searching_count": counts["rail_searching"],
            "rail_build_pending_count": counts["rail_build_pending"],
            "scarcity_cash": sum(row.get("scarcity_cash", 0) for row in rows),
            "scarcity_site": sum(row.get("scarcity_site", 0) for row in rows),
            "scarcity_decision": sum(row.get("scarcity_decision", 0) for row in rows),
            "scarcity_none": sum(row.get("scarcity_none", 0) for row in rows),
            "stop_k_pass": sum(row.get("stop_k_pass", 0) for row in rows),
            "stop_cash": sum(row.get("stop_cash", 0) for row in rows),
            "stop_rail_search": sum(row.get("stop_rail_search", 0) for row in rows),
            "stop_list_end": sum(row.get("stop_list_end", 0) for row in rows),
            "stop_other": sum(row.get("stop_other", 0) for row in rows),
            "project_passes": sum(row.get("project_passes", 0) for row in rows),
            "project_builds": sum(row.get("project_builds", 0) for row in rows),
            "multi_build_passes": sum(row.get("multi_build_passes", 0) for row in rows),
        })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "diag_unused_cash_1970_1972_5x3.json")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    opex = local_folder(
        str(ROOT / "ai" / "OpexAI"), "OpexAI", (("probe_portfolio", 1),)
    )
    experiments = [
        {
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": make_cfg(1970),
            "ais": (opex,),
        }
        for seed in args.seeds
    ]
    captures = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.workers,
        result_processor=retain,
        experiments=experiments,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    per_seed = []
    for seed in args.seeds:
        series = sorted((row for row in captures if row["seed"] == seed), key=lambda row: row["date"])
        latest = series[-1] if series else None
        raw_signs = latest["signs"] if latest else []
        probe_signs = [s for s in raw_signs if s.startswith(("UC|", "UP|", "UR|", "US|", "UT|", "UB|"))]
        years = parse_signs(probe_signs)
        per_seed.append({
            "seed": seed,
            "last_date": latest["date"] if latest else None,
            "years": years,
            "probe_signs": sorted(probe_signs),
        })

    payload = {
        "years_run": args.years,
        "seeds": args.seeds,
        "arm": "OpexAI[probe_portfolio=1] solo",
        "per_seed": per_seed,
        "annual_mean": aggregate(per_seed),
    }
    args.out.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")

    print("year n cash loan reserve avail head_need affordable rail_search cash/site/decision/none stops(k/c/r/l/o) passes/builds/multi")
    for row in payload["annual_mean"]:
        print(
            row["year"], row["n"],
            round(row["cash_mean"] or 0), round(row["loan_mean"] or 0),
            round(row["reserve_mean"] or 0), round(row["available_mean"] or 0),
            round(row["head_need_mean"] or 0),
            f"{row['head_affordable_count']}/{row['n']}",
            f"{row['rail_searching_count']}/{row['n']}",
            f"{row['scarcity_cash']}/{row['scarcity_site']}/{row['scarcity_decision']}/{row['scarcity_none']}",
            f"{row['stop_k_pass']}/{row['stop_cash']}/{row['stop_rail_search']}/{row['stop_list_end']}/{row['stop_other']}",
            f"{row['project_passes']}/{row['project_builds']}/{row['multi_build_passes']}",
        )
    print("out", args.out)


if __name__ == "__main__":
    main()
