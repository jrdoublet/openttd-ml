"""AC04-A P0: paired post decomposition of already frozen NoAI LOOP_OPS.

Read-only: no engine, no Docker and no changes to existing evidence. Run:
  python -X utf8 sweeps/test_ac04_causal_existing.py [--out new.json]
An equal invocation count does NOT prove equal inputs or intrinsic-cost parity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/ac_fixes_worktree_20261011/results"
SOURCES = (
    "ac04a_opcode_loop_10x4_20261011_phase_summary.json",
    "ac04a_extension30_opcode_loop_10x4_20261011_phase_summary.json",
)
# Les archives AC04 sont ignorees par Git et resident dans le worktree frere
# lorsque cette suite s'execute depuis un stage imbrique sous results/.
if not all((BASE / filename).is_file() for filename in SOURCES):
    sibling = ROOT.parents[1] / "results/ac_fixes_worktree_20261011/results"
    if all((sibling / filename).is_file() for filename in SOURCES):
        BASE = sibling
WINDOWS = (("1970", "1971"), ("1970", "1971", "1972"))


def source_data(base=BASE):
    results = []
    seeds = set()
    for filename in SOURCES:
        path = base / filename
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["valid"] and record["source_frozen"]
        assert record["observed_complete_years"] == ["1970", "1971", "1972"]
        for seed in record["seeds"]:
            assert seed not in seeds
            seeds.add(seed)
            results.append((seed, record))
    assert len(results) == 40
    return results


def post_totals(record, seed, arm, years):
    matches = [k for k in record["per_game_annual"]
               if k.endswith(f"_{arm}:{seed}")]
    assert len(matches) == 1, (seed, arm, matches)
    entries = record["per_game_annual"][matches[0]]
    output = {}
    for year in years:
        for post, counters in entries[year]["loop_posts"].items():
            if post in ("_year", "sleep_left"):
                continue
            agg = output.setdefault(post, {"n": 0, "ops": 0})
            agg["n"] += counters["n"]
            agg["ops"] += counters["ops"]
    return output


def analyse(base=BASE):
    results = source_data(base)
    windows = {}
    for years in WINDOWS:
        per_seed = {}
        post_names = set()
        for seed, record in results:
            off = post_totals(record, seed, "off", years)
            on = post_totals(record, seed, "on", years)
            names = sorted(set(off) | set(on))
            post_names.update(names)
            pairs = {}
            for post in names:
                a = off.get(post, {"n": 0, "ops": 0})
                b = on.get(post, {"n": 0, "ops": 0})
                pairs[post] = {"delta_ops": b["ops"] - a["ops"],
                               "delta_calls": b["n"] - a["n"],
                               "ref_calls": a["n"], "variant_calls": b["n"],
                               "ref_ops": a["ops"], "variant_ops": b["ops"]}
            per_seed[str(seed)] = pairs
        posts = {}
        for name in sorted(post_names):
            rows = [row.get(name, {"delta_ops": 0, "delta_calls": 0,
                                   "ref_calls": 0, "variant_calls": 0,
                                   "ref_ops": 0, "variant_ops": 0})
                    for row in per_seed.values()]
            equal = [r for r in rows if r["ref_calls"] == r["variant_calls"]]
            changed = [r for r in rows if r["ref_calls"] != r["variant_calls"]]
            posts[name] = {
                "mean_delta_ops": mean(r["delta_ops"] for r in rows),
                "mean_delta_calls": mean(r["delta_calls"] for r in rows),
                "pairs_equal_call_count": len(equal),
                "mean_delta_ops_equal_calls": mean(r["delta_ops"] for r in equal) if equal else None,
                "pairs_changed_call_count": len(changed),
                "mean_delta_ops_changed_calls": mean(r["delta_ops"] for r in changed) if changed else None,
                "within_equal_calls_mean_ops_per_call_diff": (
                    mean(r["variant_ops"] / r["variant_calls"]
                         - r["ref_ops"] / r["ref_calls"]
                         for r in equal if r["ref_calls"] > 0)
                    if any(r["ref_calls"] > 0 for r in equal) else None),
            }
        total = [sum(row["delta_ops"] for row in pairs.values()) for pairs in per_seed.values()]
        windows["+".join(years)] = {
            "pairs": len(per_seed), "mean_loop_delta": mean(total),
            "posts": posts,
            "post_delta_check": mean(sum(per_seed[str(seed)].get(post, {}).get("delta_ops", 0)
                                         for post in post_names) for seed, _ in results),
        }
    return {"source": [str(BASE / f) for f in SOURCES], "matched_seeds": 40,
            "method": "pair same frozen source + same seed, aggregate disjoint LOOP_OPS posts",
            "caution": "same post invocation count != same function inputs, no isolated helper cost",
            "windows": windows}


class TestAC04PriorEvidence(unittest.TestCase):
    def test_40_pairs_disjoint_and_complete(self):
        self.assertEqual(len(source_data()), 40)

    def test_40x4_global_delta_agrees_with_preserved_report(self):
        observed = analyse()["windows"]
        self.assertAlmostEqual(observed["1970+1971"]["mean_loop_delta"], 213973.95)
        self.assertAlmostEqual(observed["1970+1971+1972"]["mean_loop_delta"], 497230.5)
        for v in observed.values():
            self.assertAlmostEqual(v["mean_loop_delta"], v["post_delta_check"])


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--out", type=Path)
    cli.add_argument("--test", action="store_true")
    opts = cli.parse_args()
    if opts.test:
        unittest.main(argv=[__file__])
    else:
        data = analyse()
        if opts.out:
            with opts.out.open("x", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
        else:
            for window, values in data["windows"].items():
                print(window, "mean_loop_delta", values["mean_loop_delta"])
                for key, stats in sorted(values["posts"].items(),
                                         key=lambda item: abs(item[1]["mean_delta_ops"]), reverse=True)[:10]:
                    print(key, stats)
