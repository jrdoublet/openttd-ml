#!/usr/bin/env python3
"""Audit reproductible des trajectoires P4-vyear et première application du facteur.

Le calcul utilise uniquement les artefacts du benchmark, sans rejouer OpenTTD.
Il ne revendique pas une attribution de causalité quand une divergence précède
le premier facteur non neutre. Usage :

python sweeps/analyse_scores_p4_vyear_effect_20261013.py \
    results/scores_p4_vyear_clean_dev5x5_20261013.json \
    results/scores_p4_vyear_matched_dev5x5_20261013.json
"""

import argparse
import json
import re
from pathlib import Path


COMPARE_FIELDS = (
    "money", "company_value", "profit_year", "n_vehicles",
    "primary_vehicles_by_mode", "air_primary_vehicles", "n_stations",
    "project_builds_sign_total", "observed_opcodes_total",
)


def read_run(path):
    path = Path(path)
    report = json.loads(path.read_text(encoding="utf-8"))
    records = [json.loads(line) for line in path.with_suffix(".jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    policies = report["policies"]
    ref = next(p["id"] for p in policies if p["role"] == "reference")
    var = next(p["id"] for p in policies if p["role"] == "variant")
    by_arm = {}
    for rec in records:
        if rec.get("run", [None])[0] != "OpexAI":
            continue
        key = (rec["policy_id"], int(rec["run"][1]))
        by_arm.setdefault(key, {})[rec["date"]] = rec
    return path, report, ref, var, by_arm


def active_factors(engine_log):
    """Rapports C70 publiés : exercice N est disponible dès janvier N+1."""
    result = []
    if not engine_log.is_file():
        return result
    for line in engine_log.read_text(encoding="utf-8", errors="replace").splitlines():
        if "P4_VYEAR_MODE " not in line:
            continue
        vals = dict(re.findall(r"(\w+)=([^\s]+)", line.split("P4_VYEAR_MODE ", 1)[1]))
        try:
            applied = int(vals["applied"]) == 1
            factor = float(vals["factor"])
            legacy = float(vals["legacy_k"])
            year = int(vals["exercise"])
        except (ValueError, KeyError):
            continue
        if applied and abs(factor - legacy) > 1e-7:
            result.append({
                "first_usable_date": f"{year + 1}-01-01", "mode": vals["mode"],
                "factor": factor, "legacy_k": legacy, "exercise": year,
            })
    return result


def analyse(path):
    path, report, ref, var, data = read_run(path)
    seeds = [int(x) for x in report["seeds"]]
    output = {
        "campaign_id": report["campaign_id"],
        "source_bundle_sha256": report["source_bundle_sha256"],
        "reference_policy": ref, "variant_policy": var,
        "per_seed": [],
    }
    for seed in seeds:
        a = data.get((ref, seed), {})
        b = data.get((var, seed), {})
        dates = sorted(set(a) & set(b))
        if len(dates) != 12 * int(report["years"]):
            raise ValueError(f"{path.name}: incomplete checkpoints seed={seed}, {len(dates)}")
        if any(a[day]["source_bundle_sha256"] != b[day]["source_bundle_sha256"]
               for day in dates):
            raise ValueError(f"{path.name}: mismatched bundle seed={seed}")
        first = {}
        for field in COMPARE_FIELDS:
            first[field] = next((day for day in dates if a[day].get(field) != b[day].get(field)), None)
        last = dates[-1]
        entry = {
            "seed": seed, "first_difference": first,
            "terminal_date": last,
            "profit_year_reference": a[last].get("profit_year"),
            "profit_year_variant": b[last].get("profit_year"),
            "profit_year_delta": b[last]["profit_year"] - a[last]["profit_year"],
            "company_value_delta": b[last]["company_value"] - a[last]["company_value"],
            "vehicles_delta": b[last]["n_vehicles"] - a[last]["n_vehicles"],
            "stations_delta": b[last]["n_stations"] - a[last]["n_stations"],
            "build_signs_delta": b[last].get("project_builds_sign_total", 0)
                                 - a[last].get("project_builds_sign_total", 0),
            "opcode_signs_delta": b[last].get("observed_opcodes_total", 0)
                                  - a[last].get("observed_opcodes_total", 0),
        }
        log_path = path.with_name(path.stem + "_engine") / f"{var}_seed{seed}_r0.log"
        factors = active_factors(log_path)
        entry["first_non_neutral_factor"] = min(
            (x["first_usable_date"] for x in factors), default=None)
        entry["factor_changes"] = factors
        first_money = first["money"]
        first_factor = entry["first_non_neutral_factor"]
        entry["money_diverged_before_factor"] = (
            first_money is not None and first_factor is not None and first_money < first_factor)
        output["per_seed"].append(entry)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaigns", nargs="+", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    results = [analyse(path) for path in args.campaigns]
    for campaign in results:
        print(f"{campaign['campaign_id']} bundle={campaign['source_bundle_sha256']}")
        print("seed | profit_year Δ | company_value Δ | vehicles Δ | stations Δ | builds Δ | "
              "opcode signs Δ | "
              "first money | first active factor | pre-factor?")
        for row in campaign["per_seed"]:
            print(f"{row['seed']} | {row['profit_year_delta']:+,} | "
                  f"{row['company_value_delta']:+,} | "
                  f"{row['vehicles_delta']:+d} | {row['stations_delta']:+d} | "
                  f"{row['build_signs_delta']:+d} | {row['opcode_signs_delta']:+,} | "
                  f"{row['first_difference']['money']} | "
                  f"{row['first_non_neutral_factor']} | "
                  f"{row['money_diverged_before_factor']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
