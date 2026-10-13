"""Compare P4_CHAIN paired monthly snapshots and first divergences, no causal leap.

P4_CHAIN uses decision_log and flip shadow in *both* arms; this is diagnostic
only. Source bundle must match across arms for each paired seed.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

KEYS = ["money", "profit_year", "company_value", "primary_vehicles",
        "n_stations", "air_primary_vehicles", "air_airports", "observed_opcodes_total"]


def analyse(jsonl):
    games = defaultdict(dict)
    with jsonl.open(encoding="utf8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("run", [None])[0] != "OpexAI":
                continue
            games[(obj["run"][1], obj["policy_id"])][obj["date"]] = obj
    policies = sorted({p for _, p in games})
    if len(policies) != 2:
        raise ValueError(f"Need exactly two policies: {policies}")
    baseline = next((p for p in policies if "legacy" in p), policies[0])
    variant = next((p for p in policies if "stable" in p), policies[1])
    byseed = {}
    seeds = sorted({s for s, _ in games})
    for seed in seeds:
        a = games[(seed, baseline)]
        b = games[(seed, variant)]
        dates = sorted(set(a) & set(b))
        if set(a) != set(b):
            raise ValueError(f"Unpaired snapshots seed {seed}")
        bundles = {o["source_bundle_sha256"] for o in list(a.values()) + list(b.values())}
        if len(bundles) != 1:
            raise ValueError(f"Mismatched bundles seed {seed}")
        diffs = {}
        for metric in KEYS:
            occurrences = [date for date in dates if a[date].get(metric) is not None
                           and b[date].get(metric) is not None
                           and a[date][metric] != b[date][metric]]
            diffs[metric] = {
                "first": occurrences[0] if occurrences else None,
                "first_delta": (b[occurrences[0]][metric] - a[occurrences[0]][metric])
                if occurrences else None,
                "terminal_delta": (
                    b[dates[-1]][metric] - a[dates[-1]][metric]
                    if a[dates[-1]].get(metric) is not None and
                    b[dates[-1]].get(metric) is not None else None),
            }
        modechanges = {}
        for mode in ("rail", "road", "air", "water"):
            occurrences = [date for date in dates
                           if a[date]["primary_vehicles_by_mode"][mode]
                           != b[date]["primary_vehicles_by_mode"][mode]]
            modechanges[mode] = occurrences[0] if occurrences else None
        byseed[str(seed)] = {
            "bundle": list(bundles)[0], "n_snapshots": len(dates),
            "metrics": diffs, "first_physical_divergence_by_mode": modechanges,
            "terminal_reference_profit_year": a[dates[-1]].get("profit_year"),
            "terminal_variant_profit_year": b[dates[-1]].get("profit_year"),
        }
    return {"policies": [baseline, variant], "seeds": byseed,
            "warning": "Diagnostic bundles include overhead. Earliest money divergence can precede C70 cohort and cannot be attributed to score."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    obj = analyse(args.jsonl)
    args.out.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf8")
    for seed, info in obj["seeds"].items():
        print(seed, "first_money", info["metrics"]["money"]["first"],
              "first_profit", info["metrics"]["profit_year"]["first"],
              "first_air", info["first_physical_divergence_by_mode"]["air"],
              "first_rail", info["first_physical_divergence_by_mode"]["rail"],
              "terminal_profit_diff", info["metrics"]["profit_year"]["terminal_delta"])


if __name__ == "__main__":
    main()
