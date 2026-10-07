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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fixture", "smoke", "measure"), required=True)
    parser.add_argument("--fusion", type=int, choices=(0, 1), required=True)
    parser.add_argument("--seed", type=int, choices=(42, 100), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--library-manifest", type=Path, required=True)
    parser.add_argument("--source-copy", type=Path)
    parser.add_argument("--use-default-settings", action="store_true", help="Smoke without explicit overrides")
    args = parser.parse_args(argv)
    if args.use_default_settings and args.mode != "smoke":
        parser.error("Default settings are reserved for the delivery smoke")
    if args.mode == "fixture" and args.fusion != 0:
        parser.error("Fixture observes the OFF witness and calls the ON pair alongside it")
    if args.source_copy and args.mode != "measure":
        parser.error("--source-copy is reserved for measurements")
    folder = new_directory(args.out, ROOT / "results/c121_winner_integration")
    sys.path.insert(0, str(ROOT / "sweeps"))
    import openttdlab
    from . import save_load_roundtrip as driver
    from .game_health import assess_game, parse_script_errors
    from .campaign_freeze import parse_ai_settings
    before = source_hashes()
    target = stage(folder, args.mode, args.source_copy)
    copied = tree_hashes(target)
    source_copy_hashes = tree_hashes(args.source_copy) if args.source_copy else None
    fixture_hashes = {p.name: digest(p) for p in ROOT.glob("tests/mechanisms/c121*vm.nut")}
    driver.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    driver.SCRIPT_DEBUG_LEVEL = "4"
    libraries, groups = cached_libraries(args.library_manifest, driver.CACHE_DIR, folder / "ai_libraries")
    settings = () if args.use_default_settings else (
        ("c121_air_economics", 1), ("c121_air_winner_fusion", args.fusion),
        ("catalog_cost_probe", int(args.mode == "measure")))
    defaults = parse_ai_settings(target / "info.nut")
    resolved = {**defaults, **dict(settings)}
    loaded_fusion = int(bool(resolved["c121_air_economics"] and resolved["c121_air_winner_fusion"]))
    loaded_probe = int(bool(resolved["catalog_cost_probe"]))
    cfg = driver.bench_v2.make_cfg(1970)
    arm = openttdlab.local_folder(str(target), "OpexAI", settings)
    shutil.copy2(Path(__file__), folder / "executed_runner.py")
    write_new(folder / "plan.json", {"kind": "integrated_opcode_experiment_not_adoption",
        "mode": args.mode, "fusion": args.fusion,
        "seed": args.seed, "years": 1, "workers": 1,
        "settings": settings, "resolved_settings": resolved,
        "source_hashes": measured_sources(before, copied) if args.source_copy else before,
        "live_source_hashes": before, "source_copy": str(args.source_copy) if args.source_copy else None,
        "copied_ai_hashes": copied, "fixture_hashes": fixture_hashes, "configuration": cfg,
        "libraries": groups, "image": os.environ.get("DIAG_DOCKER_IMAGE_ID"),
        "metrics": ["c121_winner_ops", "air_ops", "total_ops"],
        "limits": ["same-source OFF/ON; one-year solos", "probe changes scheduling", "no economic verdict",
                   "scripted epoch boundary is a routing check, not measured inflation calibration"]})
    original = driver.run_experiments
    def frozen_run(**kwargs):
        kwargs["ai_libraries"] = libraries
        return original(**kwargs)
    try:
        driver.run_experiments = frozen_run
        _, log, saves = driver.run_phase_a(args.seed, 1, arm, cfg, folder / "rows.jsonl", folder / "saves")
    finally:
        driver.run_experiments = original
    log = log or ""
    (folder / "engine.log").write_text(log, encoding="utf-8")
    records = parse_saves(saves)
    for r in records:
        r["company"]["run"][1] = args.seed
    phase = {"records": records, "script_errors": parse_script_errors(log),
        "health": assess_game([r["company"] for r in records], starting_year=1970, years=1,
                              expected_companies=("OpexAI",), engine_log=log)}
    phase["integrity"] = phase_integrity(phase, "1970-01-01", 1)
    checks = {**phase["integrity"], "game_health": phase["health"]["game_ok"],
              "loaded_setting_receipt": f"C121_INTEGRATION_RECEIPT fusion={loaded_fusion} probe={loaded_probe}" in log,
              "sources_unchanged": (measured_sources(before, copied) == measured_sources(source_hashes(), copied)
                                    and source_copy_hashes == tree_hashes(args.source_copy)) if args.source_copy else before == source_hashes(),
              "copy_unchanged": copied == tree_hashes(target),
              "fixtures_unchanged": fixture_hashes == {p.name: digest(p) for p in ROOT.glob("tests/mechanisms/c121*vm.nut")}}
    evidence = None
    if args.mode == "fixture":
        evidence = markers(log)
        checks.update(evidence["checks"])
        checks["integrated_fixture"] = "C121_INTEGRATION_START pass=1" in log
        checks["boundary_routes"] = "C121_INTEGRATION_BOUNDARY checks=5 restored=1 pass=1" in log
    elif args.mode == "measure":
        evidence = probe_evidence(log, str(folder / "engine.log"))
        checks.update(evidence["checks"])
    else:
        checks["no_fixture_active"] = "C121_FUSION_START" not in log and "C121_INTEGRATION_START" not in log
    report = {"mode": args.mode, "fusion": args.fusion, "seed": args.seed, "checks": checks,
              "pass": all(checks.values()), "phase": phase, "evidence": evidence,
              "economic_verdict": "not_evaluated"}
    write_new(folder / "report.json", report)
    print(json.dumps({"checks": checks, "totals": evidence.get("totals") if evidence else None,
                      "checked_count": evidence.get("checked_count") if evidence else None}, indent=2), flush=True)
    if not report["pass"]:
        raise RuntimeError("Integration non-validated; retained evidence")


if __name__ == "__main__":
    main()
