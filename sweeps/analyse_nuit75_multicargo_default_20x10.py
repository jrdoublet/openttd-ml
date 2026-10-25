"""Audit the user-requested 20x10 N75 multicargo default comparison.

This is an independent post-adoption comparison (not a conditional V102 B
following the failed A40x5). The old default is explicitly set to 0 and
the new default to 2 in the same frozen source bundle.
"""

import argparse
import json
from pathlib import Path

from run_nuit75_newformat_queue_20261025 import ratios, report
from verify_nuit75_gate_integrity_20261025 import verify


BASELINE_SEEDS = [42, 100, 7, 999, 2026, 1, 17, 373684, 314, 512,
                  1024, 1337, 4096, 8191, 12345, 54321, 65537,
                  123456, 424242, 8675309]


def analyze(path):
    data, comparison, economics = report(path)
    integrity = verify(path, 20, 10)
    manifest = json.loads(path.with_suffix(".manifest.json").read_text("utf-8"))
    issues = integrity["issues"]
    if data["seeds"] != BASELINE_SEEDS:
        issues.append("seed cohort differs from the 2026-10-24 baseline (373684 replaces 73)")
    policies = {p["role"]: p for p in data["policies"]}
    expected = {"reference": 0, "variant": 2}
    for role, setting in expected.items():
        config = dict(policies[role].get("explicit_settings", []))
        if config.get("n75_multi_cargo") != setting or config.get("probes") != 2:
            issues.append(f"{role} does not explicitly set multicargo={setting} and probes=2")
    if manifest.get("comparison", {}).get("effective_differences") != {
            "n75_multi_cargo": {"reference": 0, "candidate": 2}}:
        issues.append("unexpected additional policy differences")
    for role, setting in expected.items():
        policies_in_manifest = {p["role"]: p for p in manifest["policies"]}
        config = policies_in_manifest[role]["settings"]
        if (config["defaults"].get("n75_multi_cargo") != 2 or
                config["effective"].get("n75_multi_cargo") != setting):
            issues.append(f"{role} has wrong default/effective multicargo value")
    integrity["ok"] = not issues
    result = {
        "campaign": data["campaign_id"],
        "source_commit": manifest.get("git", {}).get("sha"),
        "bundle": data["source_bundle_sha256"],
        "year": data["expected_last_year"],
        "baseline_seeds": BASELINE_SEEDS,
        "economic_verdict": economics,
        "integrity": integrity,
        "ratios_opex_aaahogex": ratios(data),
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.report_json)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded)
    return 0 if result["integrity"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
