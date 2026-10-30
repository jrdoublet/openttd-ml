"""Read-only consistency audit for OFF references across 5×5 and 40×5 runs.

The sole purpose is to distinguish a source regression from cross-run
non-determinism. A source-neutral OFF must also be checked at fixed seeds.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

FIELDS = ("profit_year", "company_value", "money", "air_primary_vehicles",
          "air_airports", "observed_opcodes_total", "air_engine_counts")
DATES = tuple(f"{year}-12-01" for year in range(1970, 1975))


def read(path):
    out = {}
    fingerprints = Counter()
    with path.open(encoding="utf8") as rows:
        for line in rows:
            r = json.loads(line)
            if r.get("date") not in DATES or r.get("duel_policy_id") != "reference":
                continue
            key = (r["date"], r["run"][1], r["run"][0])
            if key in out:
                raise ValueError(f"Duplicated key {key} in {path}")
            out[key] = r
            fingerprints[str(r.get("source_bundle_sha256"))] += 1
    return out, fingerprints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.results_root.resolve() / "results"
    files = {
        "original_5": root / "estim31_engine_dispatch_air15_root_20261029/results/estim31_engine_dispatch_air15_5x5_20261029.jsonl",
        "original_40": root / "estim31_engine_dispatch_air15_root_20261029/results/estim31_engine_dispatch_air15_40x5_20261029.jsonl",
        "new_5": root / "estim31_joint_dispatch20261029/a150_r100_w05/results/dispatch31_a150_r100_w05_5x5_20261029.jsonl",
        "new_40": root / "estim31_joint_dispatch20261029/a150_r100_w05/results/dispatch31_a150_r100_w05_40x5_20261029.jsonl",
        "flat_40": root / "estim31_joint_dispatch20261029/a100_r100_w15_flat/results/dispatch31_a100_r100_w15_flat_40x5_20261029.jsonl",
        "load25_40": root / "estim31_joint_dispatch20261029/a150_r100_w05_flat_load25/results/dispatch31_a150_r100_w05_flat_load25_40x5_20261029.jsonl",
    }
    data = {}
    for label, path in files.items():
        data[label], fingerprints = read(path)
        print("FILE", label, "snapshots", len(data[label]), "hashes", dict(fingerprints))
    for before, after in (("original_5", "new_5"),
                          ("original_5", "original_40"),
                          ("new_5", "new_40"),
                          ("original_40", "new_40"),
                          ("original_40", "flat_40"),
                          ("original_40", "load25_40"),
                          ("new_40", "flat_40"),
                          ("new_40", "load25_40"),
                          ("flat_40", "load25_40")):
        shared = sorted(set(data[before]) & set(data[after]))
        diff = [(key, field, data[before][key].get(field), data[after][key].get(field))
                for key in shared for field in FIELDS
                if data[before][key].get(field) != data[after][key].get(field)]
        by_seed = Counter(key[1] for key, _, _, _ in diff)
        by_year = Counter(key[0][:4] for key, _, _, _ in diff)
        print("COMPARE", before, after, "shared", len(shared),
              "diffs", len(diff), "by_seed", dict(sorted(by_seed.items())),
              "by_year", dict(sorted(by_year.items())))
        print("EXAMPLES", diff[:3])


if __name__ == "__main__":
    main()
