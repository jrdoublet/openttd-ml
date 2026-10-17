"""Integrated winner fusion: VM routing checks, smoke and existing opcode probe.

Sequential one-year solos only; no economic qualification or adoption.
"""
from __future__ import annotations
import argparse
import inspect
import json
import os
from pathlib import Path
import shutil
import sys

from .run_c121_fusion_fixtures import stage as fusion_stage, markers
from .run_c121_winner_fixtures import cached_libraries
from .run_mechanism_fixtures import digest, tree_hashes, replace_once, parse_saves, phase_integrity
from .diag_r1_r3_mechanisms import source_hashes, new_directory, write_new

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/mechanisms/c121_winner_integration_vm.nut"


def stage(folder, mode, source_copy=None):
    if mode == "fixture":
        target = fusion_stage(folder)
        shutil.copy2(FIXTURE, target / FIXTURE.name)
        main = target / "main.nut"
        text = replace_once(main.read_text(encoding="utf-8"), 'require("c121_fusion_vm.nut");',
                            'require("c121_fusion_vm.nut");\nrequire("c121_winner_integration_vm.nut");')
        text = replace_once(text, "  FxFStart(this);", "  FxIStart(this);")
    else:
        target = folder / "ai/OpexAI"
        shutil.copytree(source_copy or ROOT / "ai/OpexAI", target)
        main = target / "main.nut"
        text = main.read_text(encoding="utf-8")
    if source_copy is None:
        text = replace_once(text, "  OpexLoadSettings();", """  OpexLoadSettings();
  AILog.Info("C121_INTEGRATION_RECEIPT fusion=" + (C121_AIR_WINNER_FUSION ? 1 : 0)
      + " probe=" + (CATALOG_COST_PROBE ? 1 : 0));""")
    elif text.count("C121_INTEGRATION_RECEIPT fusion=") != 1:
        raise ValueError("Expected one source-copy receipt")
    main.write_text(text, encoding="utf-8")
    return target


def measured_sources(all_sources, copied):
    # The actual AI copy and runtime modules, not unrelated temporary launchers
    # or tests edited by another task. Raw workspace hashes are retained too.
    runtime = {k: v for k, v in all_sources.items() if k.startswith("sweeps/")
               and not Path(k).name.startswith(("_tmp", "test_"))}
    return {**runtime, **{"ai/OpexAI/" + k: v for k, v in copied.items()}}


def probe_evidence(log, source):
    # Same reader as the current latency audit; keep missing distinct from zero.
    sys.path.insert(0, str(ROOT / "sweeps"))
    from parallel_latency_audit import parse_log, nonnegative
    events, issues = parse_log(log, source)
    costs = [e for e in events if e["tag"] == "CATALOG_COST"]
    valid = [e for e in costs if e["company"] == "0" and e["session"] == 0
             and "1970-01-01" <= e["date"] < "1971-01-01"]
    totals = {}
    keys = ("total_ops", "air_ops", "c121_winner_ops", "c121_calls", "air_new_pairs",
            "air_hub_site_pairs", "air_hub_hub_pairs", "c121_scan_ops", "c121_demand_ops")
    for key in keys:
        values = [nonnegative(e["fields"].get(key)) for e in valid]
        totals[key] = sum(values) if values and all(v is not None for v in values) else None
    return {"events": valid, "parse_issues": issues, "excluded_events": len(costs) - len(valid),
            "totals": totals, "checks": {
                "probe_exposed": bool(valid),
                "no_foreign_or_out_of_interval_cost": len(costs) == len(valid),
                "required_cost_fields": all(totals[k] is not None for k in keys),
                "winner_exposed": totals["c121_calls"] is not None and totals["c121_calls"] > 0,
                "no_parse_issues": not issues}}


def compare_measurements(reference, variant, setting="c121_air_winner_fusion"):
    """Audit a specific OFF/ON pair; trajectories and work volumes may differ."""
    if setting != "c121_air_winner_fusion":
        raise ValueError("Unsupported opcode intervention")
    plans = [json.loads((Path(p) / "plan.json").read_text(encoding="utf-8")) for p in (reference, variant)]
    reports = [json.loads((Path(p) / "report.json").read_text(encoding="utf-8")) for p in (reference, variant)]
    a, b = plans
    executed_sources = [measured_sources(p["live_source_hashes"], p["copied_ai_hashes"])
                        if "live_source_hashes" in p and "copied_ai_hashes" in p else p["source_hashes"]
                        for p in plans]
    diffs = sorted(k for k in set(a["resolved_settings"]) | set(b["resolved_settings"])
                   if a["resolved_settings"].get(k) != b["resolved_settings"].get(k))
    checks = {"both_reports_pass": all(r["pass"] for r in reports),
              "measure_profiles": all(p["mode"] == "measure" for p in plans),
              "same_seed": a["seed"] == b["seed"], "same_configuration": a["configuration"] == b["configuration"],
              "same_sources": executed_sources[0] == executed_sources[1], "same_libraries": a["libraries"] == b["libraries"],
              "same_image": a["image"] is not None and a["image"] == b["image"],
              "only_selected_setting_differs": diffs == [setting],
              "off_on": a["resolved_settings"].get(setting) == 0
                        and b["resolved_settings"].get(setting) == 1}
    left, right = [r["evidence"]["totals"] for r in reports]
    deltas = {}
    for key in ("c121_scan_ops", "c121_winner_ops", "air_ops", "total_ops", "c121_calls"):
        x, y = left.get(key), right.get(key)
        deltas[key] = {"reference": x, "variant": y,
                       "delta": y - x if x is not None and y is not None else None,
                       "percent": 100.0 * (y / x - 1.0) if x and y is not None else None}
    x, y = left.get("c121_calls"), right.get("c121_calls")
    per_call = [totals["c121_winner_ops"] / calls if calls and totals["c121_winner_ops"] is not None else None
                for totals, calls in ((left, x), (right, y))]
    return {"seed": a["seed"], "checks": checks, "comparable": all(checks.values()),
            "differences": diffs, "annual_deltas": deltas, "winner_ops_per_call": per_call,
            "limit": "Annual work and per-call route mix may differ; not a pure matched-input speedup or economic verdict"}


def main(argv=None):
    raise SystemExit("V237: legacy winner-fusion integration is retired; use a frozen historical bundle")


if __name__ == "__main__":
    main()
