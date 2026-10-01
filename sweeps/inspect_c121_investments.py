"""Offline correction of probe identity and descriptive investment inspection.

Does not replay games or infer realised line profit from C121_BUILD forecasts.
The old recovery report is retained; a new receipt explicitly supersedes its
ON/OFF interpretation, not the recorded health or numerical observations.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from .diag_c121_postbuild import number, parse_fields, probe_identity, write_new

BUILD = re.compile(r"\[script:\d+\]\s*\[0\].*?\bC121_BUILD\s+(.*)$")


def investments(text):
    rows = [parse_fields(m[1]) for line in text.splitlines() if (m := BUILD.search(line))]
    comparable = [r for r in rows if all(number(r, k) is not None
                                         for k in ("decision_n", "actual_n", "target_n"))]
    return {
        "build_events": len(rows), "comparable_counts": len(comparable),
        "missing_counts": len(rows) - len(comparable),
        "count_triples": dict(Counter(f'{r["decision_n"]}/{r["actual_n"]}/{r["target_n"]}'
                                      for r in comparable)),
        "decision_n_above_built": sum(int(r["decision_n"]) > int(r["actual_n"]) for r in comparable),
        "target_n_above_built": sum(int(r["target_n"]) > int(r["actual_n"]) for r in comparable),
        "built_one": sum(int(r["actual_n"]) == 1 for r in comparable),
        "realised_line_profit": None,
        "scope": "build_events_instrumented_trajectory; actual_profit_is_model_forecast",
    }


def inspect(folder, out):
    if out.exists():
        raise FileExistsError(out)
    old_path = folder / "recovery_report_r1.json"
    old = json.loads(old_path.read_text(encoding="utf-8"))
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    input_hashes = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                    for name in old["input_hashes"]}
    if input_hashes != old["input_hashes"]:
        raise ValueError("Original inputs changed since recovery")
    logs = {(arm, seed): (folder / f"{arm}_{seed}.log").read_text(encoding="utf-8")
            for arm in plan["arms"] for seed in plan["seeds"]}
    identity = probe_identity(logs)
    # Fixed named cohort, not a favourable selection or double-counted ON/OFF.
    analysis = {str(seed): investments(logs["c121", seed]) for seed in plan["seeds"]}
    receipt = {
        "supersedes": "recovery_report_r1.json: perturbation and untraced_comparison interpretations",
        "prior_report_sha256": hashlib.sha256(old_path.read_bytes()).hexdigest(),
        "plan_sha256": hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest(),
        "reader_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_hashes": input_hashes, "original_inputs_unchanged": True,
        "probe_identity": identity, "on_off_comparison_valid": identity["pass"],
        "perturbation_verdict": "not_evaluated" if identity["pass"] else "invalid_contaminated_controls",
        "economic_adoption": False, "replayed_games": 0,
        "investment_inspection": analysis,
        "limitations": ["staged_copy_hashes_do_not_prove_loaded_source_identity",
                        "aggregate_company_profit_does_not_attribute_line_profit",
                        "no_continuous_affordability_or_demand_evidence"],
    }
    write_new(out, receipt)
    print(json.dumps(receipt, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    inspect(args.input.resolve(), args.out.resolve())


if __name__ == "__main__":
    main()