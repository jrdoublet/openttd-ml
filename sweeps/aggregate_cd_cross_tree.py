"""Aggregate disjoint cross-tree comparisons after independently frozen C66.3 duels."""

import argparse
import json
from pathlib import Path
from statistics import mean, median
if __package__:
    from .compare_cd_cross_tree_c66 import ci
else:
    from compare_cd_cross_tree_c66 import ci


def aggregate(paths):
    reports = [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]
    assert reports and all(x["valid"] for x in reports)
    ref = reports[0]
    seen = set()
    for item in reports:
        assert item["source_sha256"] == ref["source_sha256"], "Different code bundles across populations"
        assert item["years"] == ref["years"]
        seeds = set(item["seeds"])
        assert len(seeds) == item["n"] and not seeds.intersection(seen)
        seen.update(seeds)
    out = {
        "scope": "disjoint canonical seeds, independently frozen C66.3 campaigns",
        "valid": True, "n": len(seen), "seeds": sorted(seen),
        "years": ref["years"], "source_sha256": ref["source_sha256"],
        "economic": {}, "opcode": {},
    }
    for domain in ("economic", "opcode"):
        for metric in ref[domain]:
            if metric == "complete_years":
                out[domain][metric] = ref[domain][metric]
                continue
            deltas = {}
            for item in reports:
                row = item[domain][metric]
                for seed, diff in row["by_seed_delta"].items():
                    assert seed not in deltas
                    deltas[seed] = diff
            assert len(deltas) == len(seen)
            vals = list(deltas.values())
            mean_ref = sum(item["n"] * item[domain][metric]["mean_reference"]
                           for item in reports) / len(seen)
            out[domain][metric] = {
                "mean_delta": mean(vals), "median_delta": median(vals),
                "mean_reference": mean_ref,
                "ratio_of_means": mean(vals) / mean_ref if mean_ref else None,
                "bootstrap_95_ci": ci(vals, n=20000),
                "wins_or_increases": sum(x > 0 for x in vals),
                "losses_or_decreases": sum(x < 0 for x in vals),
                "ties": sum(x == 0 for x in vals),
                "by_seed_delta": deltas,
            }
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("comparisons", nargs="+", type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    r = aggregate(a.comparisons)
    a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: r[key] for key in ("valid", "n", "economic", "opcode")},
                     ensure_ascii=False)[:4800])
