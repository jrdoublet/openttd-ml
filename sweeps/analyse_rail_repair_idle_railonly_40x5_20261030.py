"""Paired pre-registered 40x5 gate analysis, without replacing failed runs."""

import collections
import hashlib
import json
import statistics
from pathlib import Path

from paired_statistics import exact_wilcoxon_signed_rank_p, bootstrap_mean_ci

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/rail_repair_idle_railonly_gateA_40x5_20261030.json"
DEST = ROOT / "results/rail_repair_idle_railonly_gateA_40x5_20261030_analysis.json"
BOOTSTRAP_REPLAYS = 20000
BOOTSTRAP_SEED = 0


def main():
    raw = SOURCE.read_bytes()
    payload = json.loads(raw)
    arms = payload["arms"]
    if len(arms) != 2:
        raise RuntimeError("Expected exactly two comparator arms")
    ref, variant = arms
    seeds = payload["seeds"]
    summary = payload["summary"]
    by_seed = {(row["arm"], row["seed"], row["repeat"]): row for row in summary}
    failures = payload.get("failed_runs") or []
    missing = []
    invalid = []
    for seed in seeds:
        for arm in arms:
            row = by_seed.get((arm, seed, 0))
            if row is None:
                missing.append({"arm": arm, "seed": seed})
            elif (not row.get("run_ok") or row.get("last_date") != "1974-12-01"
                  or row.get("n_savegames", 0) < 60
                  or row.get("profit_year_coverage") != "complete"):
                invalid.append({
                    "arm": arm, "seed": seed, "reason": row.get("failure_reason"),
                    "date": row.get("last_date"), "snapshots": row.get("n_savegames"),
                    "coverage": row.get("profit_year_coverage"),
                })

    status = "complete" if not (missing or invalid or failures) and len(seeds) == 40 else "invalid"
    output = {
        "status": status,
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "seeds": seeds,
        "n_seeds": len(seeds),
        "arms": arms,
        "required_years": 5,
        "required_pairs": 40,
        "n_summary": len(summary),
        "missing": missing,
        "invalid": invalid,
        "failed_runs": failures,
        "gate": {
            "primary": "profit_year",
            "min_relative_gain_pct": 4,
            "wilcoxon_p_max_exclusive": 0.05,
            "bootstrap_ci95_lower_exclusive": 0,
            "company_value_min_ratio": 0.95,
        },
    }
    if status != "complete":
        DEST.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
        raise RuntimeError(f"Gate invalid: {len(missing)} missing, {len(invalid)} invalid, {len(failures)} failed")

    a = [by_seed[(ref, seed, 0)] for seed in seeds]
    b = [by_seed[(variant, seed, 0)] for seed in seeds]
    delta = [float(y["profit_year"]) - float(x["profit_year"]) for x, y in zip(a, b)]
    ref_mean = statistics.mean(float(x["profit_year"]) for x in a)
    var_mean = statistics.mean(float(y["profit_year"]) for y in b)
    value_ref = statistics.mean(float(x["company_value"]) for x in a)
    value_var = statistics.mean(float(y["company_value"]) for y in b)
    value_ratio = value_var / value_ref if value_ref else None
    gain_pct = 100 * (var_mean - ref_mean) / ref_mean if ref_mean else None
    wilcoxon = exact_wilcoxon_signed_rank_p(delta)
    ci = bootstrap_mean_ci(delta, resamples=BOOTSTRAP_REPLAYS, seed=BOOTSTRAP_SEED)
    checks = {
        "relative_gain_ge_4pct": gain_pct is not None and gain_pct >= 4,
        "wilcoxon_p_lt_0_05": wilcoxon is not None and wilcoxon < 0.05,
        "bootstrap_ci95_lower_gt_0": ci[0] > 0,
        "company_value_ratio_ge_0_95": value_ratio is not None and value_ratio >= 0.95,
    }
    output["profit_year"] = {
        "ref_mean": ref_mean, "variant_mean": var_mean,
        "delta_mean": statistics.mean(delta),
        "delta_median": statistics.median(delta),
        "delta_pct_ref_mean": gain_pct,
        "wins": sum(d > 0 for d in delta),
        "losses": sum(d < 0 for d in delta),
        "ties": sum(d == 0 for d in delta),
        "wilcoxon_exact_two_sided_p": wilcoxon,
        "bootstrap_ci95_delta": list(ci),
        "bootstrap_replays": BOOTSTRAP_REPLAYS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "by_seed": [{"seed": seed, "ref": x["profit_year"], "variant": y["profit_year"],
                     "delta": d} for seed, x, y, d in zip(seeds, a, b, delta)],
    }
    output["company_value"] = {
        "ref_mean": value_ref, "variant_mean": value_var, "ratio": value_ratio,
    }
    output["fleet"] = {
        "ref_trains_mean": statistics.mean(x["primary_vehicles_by_mode"]["rail"] for x in a),
        "variant_trains_mean": statistics.mean(y["primary_vehicles_by_mode"]["rail"] for y in b),
        "ref_stations_mean": statistics.mean(x["n_stations"] for x in a),
        "variant_stations_mean": statistics.mean(y["n_stations"] for y in b),
    }

    # Annual terminal checkpoints only; monthly checkpoints overlap and are
    # never treated as independent statistical observations.
    series = collections.defaultdict(dict)
    for record in payload["series"]:
        if record.get("run") is None:
            continue
        arm, seed, repeat = record["run"]
        date = record["date"]
        if repeat == 0 and date.endswith("-12-01"):
            series[(arm, seed)][int(date[:4])] = record
    trajectory = {}
    for year in range(1970, 1975):
        r = [series[(ref, seed)].get(year, {}).get("profit_year") for seed in seeds]
        v = [series[(variant, seed)].get(year, {}).get("profit_year") for seed in seeds]
        if all(x is not None and y is not None for x, y in zip(r, v)):
            trajectory[str(year)] = {
                "ref_profit_mean": statistics.mean(r),
                "variant_profit_mean": statistics.mean(v),
                "paired_delta_mean": statistics.mean(y - x for x, y in zip(r, v)),
            }
    output["by_year_descriptive"] = trajectory
    output["gate_checks"] = checks
    output["verdict"] = "PASS" if all(checks.values()) else "NO_GO"
    DEST.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("STATUS", status, "PAIRS", len(seeds), "VERDICT", output["verdict"])
    print("PROFIT ref", ref_mean, "variant", var_mean, "delta", statistics.mean(delta),
          "relative_pct", gain_pct)
    print("WINS", output["profit_year"]["wins"], "LOSSES", output["profit_year"]["losses"],
          "TIES", output["profit_year"]["ties"], "p", wilcoxon, "CI95", ci)
    print("VALUE ratio", value_ratio, "CHECKS", checks)
    print("ANALYSIS", DEST)


if __name__ == "__main__":
    main()
