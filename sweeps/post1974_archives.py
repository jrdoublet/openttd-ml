"""Read-only audit of post-1974 signals from the three qualified ESTIM31 20x10s.

Use FINAL (1979-12-01) snapshots for cumulative sign ledgers.  Never sum
the same ledger from successive annual snapshots.  These signs are *not*
project IDs, physical viability tests, or gross paid CAPEX.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

SUITES = {
    "v161": "estim31_v161_safe20261030/mix_a200_r075_w15_slope",
    "v161coeff": "estim31_v161_coeff20261030/v161_a250_r075_w15",
    "v161cap": "estim31_v161_motorcap20261030/mix_a200_r075_w15_slope",
}
YEARS = tuple(range(1970, 1980))
TERMINAL = "1979-12-01"
REQUIRED = ("project_builds_sign_by_year", "c75_bypass_years", "rail_attempt_sign_by_year")


def read_campaign(path: Path, policy: str, source_sha: str, expected_seeds: set[int]):
    final = defaultdict(dict)
    yearly = defaultdict(lambda: defaultdict(dict))
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            row = json.loads(raw)
            if row.get("duel_policy_id") != policy or row.get("date", "")[:4] not in {str(y) for y in YEARS}:
                continue
            seed = int(row["run"][1])
            if seed not in expected_seeds:
                continue
            role = row["run"][0]
            if role not in ("OpexAI", "AAAHogEx"):
                continue
            if row.get("source_bundle_sha256") != source_sha:
                raise ValueError(f"Source SHA mismatch: {path.name} seed={seed}")
            year = int(row["date"][:4])
            if row["date"] == f"{year}-12-01":
                if role in yearly[seed][year]:
                    raise ValueError(f"Duplicate annual row: {seed}/{year}/{role}")
                yearly[seed][year][role] = row
            if row["date"] == TERMINAL:
                if role in final[seed]:
                    raise ValueError(f"Duplicate final row: {seed}/{role}")
                final[seed][role] = row
    if set(final) != expected_seeds:
        raise ValueError(f"Expected {len(expected_seeds)} seeds; have {len(final)}: {set(final)}")
    for seed in expected_seeds:
        if set(final[seed]) != {"OpexAI", "AAAHogEx"}:
            raise ValueError(f"Incomplete final company pair seed={seed}")
        if set(yearly[seed]) != set(YEARS):
            raise ValueError(f"Missing annual snapshots seed={seed}: {set(YEARS) - set(yearly[seed])}")
        for year in YEARS:
            if set(yearly[seed][year]) != {"OpexAI", "AAAHogEx"}:
                raise ValueError(f"Missing annual company seed={seed}, year={year}")
        opex = final[seed]["OpexAI"]
        if any(key not in opex for key in REQUIRED):
            raise ValueError(f"Missing retained signs seed={seed}")
        if not opex.get("company_present") or opex.get("engine_failure"):
            raise ValueError(f"Unhealthy Opex company seed={seed}")
    return final, yearly


def analyze_suite(final, yearly):
    by_year = {}
    by_seed = {}
    for seed, pair in sorted(final.items()):
        r = pair["OpexAI"]
        c75 = r["c75_bypass_years"]
        builds = r["project_builds_sign_by_year"]
        rails = r["rail_attempt_sign_by_year"]
        by_seed[str(seed)] = {}
        for year in YEARS:
            k = str(year)
            osnap = yearly[seed][year]["OpexAI"]
            asnap = yearly[seed][year]["AAAHogEx"]
            old = yearly[seed].get(year - 1)
            os_prev = old["OpexAI"] if old else None
            as_prev = old["AAAHogEx"] if old else None
            # C75 annual panels are flushed after year-end.  The last 1979
            # panel may not exist on a December 1979 checkpoint; that is
            # censored, emphatically not zero eligible projects.
            c = c75.get(k)
            t = rails.get(k, {})
            value = {
                "project_build_signs": builds.get(k, 0),
                "c75_eligible": c.get("eligible", 0) if c is not None else None,
                "c75_consumed": c.get("consumed", 0) if c is not None else None,
                "c75_stops": ({reason: c.get("stop_" + reason, 0) for reason in ("k_pass", "cash", "rail_search", "list_end", "other")} if c is not None else None),
                "rail_attempt_signs": t.get("or_signs", 0),
                "rail_attempt_reasons": t.get("reasons", {}),
                "rail_attempt_iteration_budget": t.get("iteration_budget", 0),
                "rail_attempt_iterations": t.get("iterations", 0),
                "rail_attempt_opcodes_observed": t.get("opcodes", 0),
                "rail_attempt_ob_signs": t.get("ob_signs", 0),
                "profit_opex": osnap.get("profit_year"),
                "profit_aaa": asnap.get("profit_year"),
                "cash_opex": osnap.get("money"),
                "airports_delta_opex": (osnap.get("air_airports", 0) - os_prev.get("air_airports", 0)) if os_prev else None,
                "airports_delta_aaa": (asnap.get("air_airports", 0) - as_prev.get("air_airports", 0)) if as_prev else None,
                "rail_vehicles_delta_opex": (osnap.get("primary_vehicles_by_mode", {}).get("rail", 0) - os_prev.get("primary_vehicles_by_mode", {}).get("rail", 0)) if os_prev else None,
                "rail_vehicles_delta_aaa": (asnap.get("primary_vehicles_by_mode", {}).get("rail", 0) - as_prev.get("primary_vehicles_by_mode", {}).get("rail", 0)) if as_prev else None,
            }
            by_seed[str(seed)][k] = value
    for year in YEARS:
        k = str(year)
        seed_rows = [vals[k] for vals in by_seed.values()]
        additive = ("project_build_signs", "c75_eligible", "c75_consumed", "rail_attempt_signs", "rail_attempt_ob_signs", "rail_attempt_iterations", "rail_attempt_iteration_budget", "rail_attempt_opcodes_observed")
        total = {name: (sum(row[name] for row in seed_rows) if all(row[name] is not None for row in seed_rows) else None) for name in additive}
        total["c75_observed_seed_count"] = sum(row["c75_eligible"] is not None for row in seed_rows)
        total["c75_stops"] = (dict(sorted(sum((Counter(row["c75_stops"]) for row in seed_rows), Counter()).items())) if total["c75_observed_seed_count"] == len(seed_rows) else None)
        total["rail_attempt_reasons"] = dict(sorted(sum((Counter(row["rail_attempt_reasons"]) for row in seed_rows), Counter()).items()))
        for key in ("airports_delta_opex", "airports_delta_aaa", "rail_vehicles_delta_opex", "rail_vehicles_delta_aaa"):
            total[key] = sum(r[key] for r in seed_rows if r[key] is not None) if year > 1970 else None
        total["mean_cash_opex"] = sum(r["cash_opex"] for r in seed_rows) / len(seed_rows)
        op = [r["profit_opex"] for r in seed_rows]
        aa = [r["profit_aaa"] for r in seed_rows]
        total["ratio_of_mean_profits_pct"] = (100 * sum(op) / sum(aa)) if all(isinstance(v, (int, float)) for v in op + aa) and sum(aa) else None
        by_year[k] = total
    return {"by_year": by_year, "by_seed": by_seed, "audit": {
        "or_count": sum(len(p["OpexAI"]["rail_attempt_sign_or"]) for p in final.values()),
        "ob_count": sum(len(p["OpexAI"]["rail_attempt_sign_ob"]) for p in final.values()),
        "or_ob_key_gaps": [p["OpexAI"].get("rail_attempt_sign_key_coverage", {}) for p in final.values()],
        "invalid_rail_signs": [p["OpexAI"].get("rail_attempt_sign_invalid", {}) for p in final.values()],
        "source": "1979-12-01 cumulative retained signs; annual physical stocks 1970-1979",
        "limitations": "OR/OB lack OD/cargo and cannot certify viability; retained signs may be clipped or overwritten; C75 only bypass and annual 1979 unflushed; project-build signs are builds, not new lines; paid CAPEX by mode absent; logs empty at probes=2",
    }}


def generate(results_root: Path, ranking_path: Path):
    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
    seeds = set(ranking["same_seed_set"])
    output = {"source_ranking": ranking_path.name, "n_seeds": len(seeds), "terminal": TERMINAL, "suites": {}}
    for entry in ranking["ranked_healthy_20x10"]:
        suite = entry["suite"]
        basedir = results_root / SUITES[suite] / "results"
        path = basedir / (entry["campaign"] + ".jsonl")
        if not path.is_file():
            raise FileNotFoundError(path)
        final, yearly = read_campaign(path, entry["policy_id"], entry["source_bundle_sha256"], seeds)
        data = analyze_suite(final, yearly)
        op = sum(pair["OpexAI"]["profit_year"] for pair in final.values()) / len(final)
        aa = sum(pair["AAAHogEx"]["profit_year"] for pair in final.values()) / len(final)
        if abs(op - entry["opex_profit_mean"]) > 0.01 or abs(aa - entry["aaa_profit_mean"]) > 0.01:
            raise ValueError(f"Ranking mismatch: {suite}")
        output["suites"][suite] = {"path": str(path.relative_to(results_root)), "policy_id": entry["policy_id"], "source_sha256": entry["source_bundle_sha256"], **data}
    return output


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=root.parent / "results")
    parser.add_argument("--ranking", type=Path, default=root / "docs/estim31_top3_20x10_20261030.json")
    parser.add_argument("--output", type=Path, default=root / "docs/post1974_archives_20261030.json")
    args = parser.parse_args()
    result = generate(args.results_root, args.ranking)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for suite, data in result["suites"].items():
        print(suite, "archive validé", len(data["by_seed"]), "graines")
        for y in range(1974, 1980):
            row = data["by_year"][str(y)]
            print(y, "built", row["project_build_signs"], "C75", row["c75_eligible"], "rail OR", row["rail_attempt_signs"], row["rail_attempt_reasons"])


if __name__ == "__main__":
    main()
