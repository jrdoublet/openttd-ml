"""Per-arm terminal profit ratios for paired OpexAI vs AAAHogEx C66.4.

Usage:
  python sweeps/analyse_nuit75_gate_ratios.py results/campaign.json
  python sweeps/analyse_nuit75_gate_ratios.py /absolute/path/to/other.json

Separately reports ratio of means and median of per-seed paired ratios.
Never merges AAA data between policy arms (different shared-map worlds).
"""
import argparse
import json
from pathlib import Path
from statistics import mean, median


def analyze(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    pairs = {}
    for row in data["summary"]:
        policy = row.get("duel_policy_id")
        if not policy or row.get("arm") not in ("OpexAI", "AAAHogEx"):
            continue
        key = (policy, row["seed"], row.get("repeat", 0))
        entries = pairs.setdefault(key, {})
        if row["arm"] in entries:
            raise AssertionError(f"Duplicate arm: {key} {row['arm']}")
        entries[row["arm"]] = row
    policies = [p["id"] for p in data["policies"]]
    response = {"campaign": data["campaign_id"], "terminal_year": data["expected_last_year"],
                "bundle_sha256": data["source_bundle_sha256"], "policies": {}}
    for policy in policies:
        relevant = [(key, arms) for key, arms in pairs.items() if key[0] == policy]
        if not relevant:
            raise AssertionError(f"No results for policy {policy}")
        usable = []
        missing = []
        for key, arms in relevant:
            if set(arms) != {"OpexAI", "AAAHogEx"}:
                missing.append(key)
                continue
            o, a = arms["OpexAI"], arms["AAAHogEx"]
            if not all(r.get("run_ok") and r.get("game_ok")
                       and r.get("horizon_complete") and r.get("include_in_economic_stats")
                       for r in (o, a)):
                missing.append(key)
                continue
            if (o.get("profit_year") is None or a.get("profit_year") is None
                    or a["profit_year"] <= 0):
                missing.append(key)
                continue
            usable.append((key, o["profit_year"], a["profit_year"]))
        if not usable:
            raise AssertionError(f"No complete positive-denominator pairs: {policy}")
        ovals = [x[1] for x in usable]
        avals = [x[2] for x in usable]
        ratios = [o/a for _, o, a in usable]
        response["policies"][policy] = {
            "n_candidate_pairs": len(relevant),
            "n_complete_positive_aaa_pairs": len(usable),
            "excluded_keys": [list(k) for k in missing],
            "opex_mean": mean(ovals), "aaahogex_mean": mean(avals),
            "ratio_of_mean_profits_pct": 100*sum(ovals)/sum(avals),
            "median_of_paired_ratios_pct": 100*median(ratios),
            "mean_of_paired_ratios_pct": 100*mean(ratios),
            "per_seed": [{"seed": k[1], "repeat": k[2], "opex": o,
                          "aaahogex": a, "ratio_pct": 100*o/a} for k, o, a in usable]
        }
    return response


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--output", help="Optional JSON path")
    args = p.parse_args()
    report = analyze(args.file)
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    for k, v in report["policies"].items():
        print(f"{k}: pairs={v['n_complete_positive_aaa_pairs']}/{v['n_candidate_pairs']} "
              f"Opex={v['opex_mean']:.2f} AAA={v['aaahogex_mean']:.2f} "
              f"ratio_means={v['ratio_of_mean_profits_pct']:.4f}% "
              f"median_paired={v['median_of_paired_ratios_pct']:.4f}% "
              f"mean_paired={v['mean_of_paired_ratios_pct']:.4f}%")
        if v["excluded_keys"]:
            print(f"  excluded: {v['excluded_keys']}")


if __name__ == "__main__":
    main()
