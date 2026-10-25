#!/usr/bin/env python3
"""Exact functional comparison of frozen OFF JSON/JSONL campaigns.

Compare only policy=reference for CARTO2 and clean reference campaigns.
Drop only metadata identifying the campaign/bundle/log location, never
economic numbers, opcodes, checkpoint dates or diagnostic counters.

Usage:
  python sweeps/compare_carto2_off.py PATH_TO_CARTO2_JSON PATH_TO_CLEAN_JSON
  python sweeps/compare_carto2_off.py PATH_TO_CARTO2_JSON PATH_TO_CLEAN_JSON --json
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


PROVENANCE = frozenset({
    "campaign_id", "game_id", "source_bundle_sha256",
    "engine_log_path", "engine_log_dir", "manifest_path", "manifest_sha256",
})
MISSING = object()


def canonical(item):
    if isinstance(item, dict):
        return {k: canonical(v) for k, v in item.items() if k not in PROVENANCE}
    if isinstance(item, list):
        return [canonical(v) for v in item]
    return item


def diffs(a, b, *, path="", limit=20):
    """Count all mismatched leaves and show first paths; no fuzzy tolerance."""
    sample = []
    groups = Counter()

    def compare(x, y, loc):
        if x == y and x is not MISSING and y is not MISSING:
            return
        if isinstance(x, dict) and isinstance(y, dict):
            for key in sorted(x.keys() | y.keys()):
                compare(x.get(key, MISSING), y.get(key, MISSING), f"{loc}.{key}")
            return
        if isinstance(x, list) and isinstance(y, list):
            for i in range(max(len(x), len(y))):
                compare(x[i] if i < len(x) else MISSING,
                        y[i] if i < len(y) else MISSING, f"{loc}[{i}]")
            return
        groups[loc.split(".")[1].split("[")[0] if "." in loc else loc] += 1
        if len(sample) < limit:
            sample.append({
                "path": loc,
                "left": repr(x)[:170] if x is not MISSING else "<missing>",
                "right": repr(y)[:170] if y is not MISSING else "<missing>",
            })
    compare(a, b, path or "root")
    return {"n": sum(groups.values()), "sample": sample,
            "top_level_fields": dict(sorted(groups.items()))}


def records(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    seen = {}
    for lineno, line in enumerate(lines, 1):
        item = json.loads(line)
        # The "run" identity names OpexAI/AAAHogEx rather than policy.
        key = (item.get("duel_policy_id"), item["run"][0], item["run"][1],
               item["run"][2], item["date"])
        if key in seen:
            raise ValueError(f"{path}:{lineno} duplicate checkpoint {key}")
        seen[key] = canonical(item)
    return seen


def select_checkpoint_rows(path, policy):
    result = {}
    for key, value in records(path).items():
        if key[0] == policy:
            result[key[1:]] = value
    return result


def compare_jsonl(left, right, *, left_policy="reference", right_policy="reference"):
    a = select_checkpoint_rows(left, left_policy)
    b = select_checkpoint_rows(right, right_policy)
    dates = sorted(set(a) | set(b), key=lambda row: (row[1], row[2], row[0], row[3]))
    breakdown = defaultdict(lambda: {"count": 0, "changed_checkpoints": 0,
                                     "different_leaves": 0, "missing": 0,
                                     "samples": [], "changed_dates": []})
    results = []
    for key in dates:
        arm, seed, rep, when = key
        entry = breakdown[(arm, seed, rep)]
        entry["count"] += 1
        missing = key not in a or key not in b
        if missing:
            entry["missing"] += 1
        diff = diffs(a.get(key, MISSING), b.get(key, MISSING),
                     path="checkpoint", limit=10)
        if diff["n"]:
            entry["changed_checkpoints"] += 1
            entry["different_leaves"] += diff["n"]
            entry["changed_dates"].append(when)
            if len(entry["samples"]) < 5:
                entry["samples"].append({"date": when, **diff})
        results.append((key, diff["n"]))
    groups = {}
    for key, value in sorted(breakdown.items()):
        groups[f"{key[0]} seed{key[1]} r{key[2]}"] = value
    return {
        "left_checkpoints": len(a), "right_checkpoints": len(b),
        "compared_keys": len(dates),
        "changed_checkpoints": sum(x["changed_checkpoints"] for x in groups.values()),
        "different_leaves": sum(x["different_leaves"] for x in groups.values()),
        "missing_checkpoints": sum(x["missing"] for x in groups.values()),
        "per_arm_seed": groups,
    }


def subset_json(root, policy="reference"):
    root = canonical(root)
    # Compare only the policy's own game, its reporting and metrics.
    games = [g for g in root.get("games", []) if g.get("policy_id") == policy]
    summary = [s for s in root.get("summary", [])
               if s.get("duel_policy_id") == policy]
    summary.sort(key=lambda s: (s.get("arm", ""), s.get("seed", 0), s.get("repeat", 0)))
    reports = root.get("policy_reports")
    if isinstance(reports, dict):
        reports = reports.get(policy)
    elif isinstance(reports, list):
        reports = [r for r in reports if isinstance(r, dict)
                   and r.get("policy_id", r.get("id")) == policy]
    return {
        "scope": {key: root.get(key) for key in (
            "map_size", "years", "seeds", "repeats", "start_year",
            "expected_last_year", "expected_last_checkpoint",
            "openttd_version", "opengfx_version")},
        "games": sorted(games, key=lambda g: (g["seed"], g["repeat"])),
        "policy_reports": reports,
        "summary": summary,
        "failed_runs": [g for g in root.get("failed_runs", [])
                        if g.get("policy_id") == policy] if all(
                        isinstance(g, dict) for g in root.get("failed_runs", [])) else [],
    }


def compare(left, right):
    left_path, right_path = Path(left), Path(right)
    ja, jb = (json.loads(path.read_text(encoding="utf8")) for path in (left_path, right_path))
    # This avoids mixing two different policies in JSONL when comparing
    # two-arm CARTO-2 run to single-arm clean baseline.
    json_diff = diffs(subset_json(ja), subset_json(jb), path="json")
    lines = compare_jsonl(left_path.with_suffix(".jsonl"), right_path.with_suffix(".jsonl"))
    return {
        "left": str(left_path), "right": str(right_path),
        "left_source_bundle_sha256": ja.get("source_bundle_sha256"),
        "right_source_bundle_sha256": jb.get("source_bundle_sha256"),
        "left_campaign_id": ja.get("campaign_id"),
        "right_campaign_id": jb.get("campaign_id"),
        "json": json_diff,
        "jsonl": lines,
        "identical_functional_checkpoints": lines["different_leaves"] == 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path, help="CARTO-2 OFF/other campaign JSON")
    parser.add_argument("right", type=Path, help="Clean reference campaign JSON")
    parser.add_argument("--json", action="store_true", help="JSON report")
    args = parser.parse_args(argv)
    result = compare(args.left, args.right)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"{result['left_campaign_id']} vs {result['right_campaign_id']}")
        print(f"JSON: {result['json']['n']} differences "
              f"in {result['json']['top_level_fields']}")
        for item in result["json"]["sample"][:5]:
            print(f"  {item['path']} : {item['left']} != {item['right']}")
        cp = result["jsonl"]
        print(f"JSONL: {cp['left_checkpoints']} vs {cp['right_checkpoints']} "
              f"checkpoints; {cp['changed_checkpoints']}/{cp['compared_keys']} "
              f"changed; {cp['different_leaves']} leaf mismatches")
        for name, row in cp["per_arm_seed"].items():
            print(f"  {name}: {row['changed_checkpoints']}/{row['count']} checkpoints "
                  f"changed, {row['different_leaves']} values, missing {row['missing']}")
            for sample in row["samples"][:2]:
                print(f"    {sample['date']}: {sample['n']} diffs")
                for diff in sample["sample"][:3]:
                    print(f"      {diff['path']} : {diff['left']} != {diff['right']}")


if __name__ == "__main__":
    main()
