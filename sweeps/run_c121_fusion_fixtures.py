"""Test-only general winner fusion; original functions and production untouched."""
from __future__ import annotations
import argparse
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import sys

from .run_c121_winner_fixtures import cached_libraries, markers as winner_markers
from .diag_r1_r3_mechanisms import source_hashes, new_directory, write_new
from .run_mechanism_fixtures import digest, tree_hashes, replace_once, parse_saves, phase_integrity

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/mechanisms/c121_fusion_vm.nut"


def prototype(source):
    """Generate the candidate from the exact staged body, keeping its argmax.

    Explicit single anchors fail on incompatible source drift. No production
    rewrite or regex removal of code; the old functions remain the witness.
    """
    a = source.index("function OpexC121AirEconomics(")
    b = source.index("function OpexC121EngineEconomics(", a)
    air = source[a:source.rfind("/* Evaluation C121", a, b)].rstrip()
    end = source.index("function OpexC121InitialEngineUpperScore(", b)
    engine = source[b:source.rfind("/* Borne superieure", b, end)].rstrip()
    anchor = "    if (decisionOnly && fixedPlanes <= 0 && planes < maxAllowed && scoreBest != null"
    if air.count(anchor) != 1:
        raise ValueError("Expected unchanged full-scan pruning anchor")
    if "openingOut = null" in air:
        # The production candidate is now integrated; test a renamed exact copy.
        air = replace_once(air, "function OpexC121AirEconomics(", "function FxFAirEconomics(")
        air = air.replace("OpexC121OpeningEconomics", "FxFOpeningEconomics")
        engine = replace_once(engine, "function OpexC121EngineEconomics(", "function FxFEngineEconomics(")
        engine = replace_once(engine, "local economics = OpexC121AirEconomics(", "local economics = FxFAirEconomics(")
        return "/* Exact integrated candidate copy for comparison. */\n" + air + "\n\n" + engine + "\n"
    final_start = air.index("  if (best != null && scoreBest != null) {")
    final = air[final_start:air.rfind("  return best;")]
    final = final.replace("decisionOnly && fixedPlanes <= 0 && fleetEvaluated < fleetScanCap", "false")
    helper = ("function FxFFinalize(best, scoreBest, decisionKDec, fleetEvaluated)\n{\n"
              + final + "  return best;\n}\n")
    air = replace_once(air, "function OpexC121AirEconomics(", "function FxFAirEconomics(")
    air = replace_once(air, "decisionOnly = false, decisionScoreFloor = null)",
                       "decisionOnly = false, decisionScoreFloor = null, openingOut = null)")
    capture = """    if (openingOut != null && !decisionOnly && fixedPlanes <= 0 && planes == 1
        && best != null && scoreBest != null) {
      openingOut.initial = FxFFinalize(clone best, clone scoreBest, decisionKDec, 1);
    }
"""
    air = replace_once(air, anchor, capture + anchor)
    engine = replace_once(engine, "function OpexC121EngineEconomics(", "function FxFEngineEconomics(")
    engine = replace_once(engine, "decisionScoreFloor = null)", "decisionScoreFloor = null, openingOut = null)")
    engine = replace_once(engine, "local economics = OpexC121AirEconomics(", "local economics = FxFAirEconomics(")
    engine = replace_once(engine, "fixedPlanes, decisionOnly, decisionScoreFloor);",
                         "fixedPlanes, decisionOnly, decisionScoreFloor, openingOut);")
    engine = replace_once(engine, "  return economics;", """  if (openingOut != null && openingOut.initial != null) {
    openingOut.initial.engineMailKnown <- mailKnown;
    openingOut.initial.decisionEconomics.engineMailKnown <- mailKnown;
  }
  return economics;""")
    return "/* Generated test copy; original functions remain unchanged. */\n" + helper + air + "\n\n" + engine + "\n"


def stage(folder):
    target = folder / "ai/OpexAI"
    shutil.copytree(ROOT / "ai/OpexAI", target)
    source = (target / "air_economics_c121.nut").read_text(encoding="utf-8")
    (target / "c121_fusion_candidate.nut").write_text(prototype(source), encoding="utf-8")
    # Reuse the previous matrix/comparator, with cap 6/13 instead of 2/4.
    base = (ROOT / "tests/mechanisms/c121_winner_vm.nut").read_text(encoding="utf-8")
    base = replace_once(base, "foreach (cap in [1, 2, 4])", "foreach (cap in [1, 6, 13])")
    (target / "c121_winner_vm.nut").write_text(base, encoding="utf-8")
    shutil.copy2(FIXTURE, target / FIXTURE.name)
    main = target / "main.nut"
    text = replace_once(main.read_text(encoding="utf-8"), "function OpexAI::Start()",
        'require("c121_fusion_candidate.nut");\nrequire("c121_winner_vm.nut");\nrequire("c121_fusion_vm.nut");\n\nfunction OpexAI::Start()')
    text = replace_once(text, "  OpexLoadSettings();", "  OpexLoadSettings();\n  FxFStart(this);")
    main.write_text(text, encoding="utf-8")
    return target


def markers(log):
    matrix = winner_markers(log)["matrix"]
    live = []
    for row in re.findall(r"C121_FUSION_LIVE arm=(\w+) cap=(\d+) mail=(\w+) checked=(\d+) old_ops=(\d+) new_ops=(\d+) pass=1", log):
        arm, cap, mail, checked, old, new = row
        live.append(dict(arm=arm, cap=int(cap), mail=mail, checked=int(checked), old_ops=int(old), new_ops=int(new)))
    checked = [r for r in live if r["checked"]]
    domain = {(cap, mail, aaa) for cap in (1, 6, 13) for mail in range(3) for aaa in range(2)}
    checks = {"start": "C121_FUSION_START active=1 production_result=old" in log,
              "matrix_cases": [r["case"] for r in matrix] == list(range(1, 19)),
              "matrix_domain": {(r["cap"], r["mail"], r["aaa"]) for r in matrix} == domain,
              "matrix_stable": bool(matrix) and all(r["stable"] for r in matrix),
              "matrix_restored": "C121_WINNER_VM complete=1 cases=18 restored=1" in log,
              "null_contract": "C121_FUSION_NULL pass=1" in log,
              "live_exposed": bool(checked), "natural_large_cap": any(r["cap"] >= 6 for r in checked),
              "no_fixture_assertion": "C121_WINNER_ASSERT" not in log}
    return {"matrix": matrix, "live": live, "checks": checks,
            "checked_count": len(checked), "live_count": len(live),
            "old_ops": sum(r["old_ops"] for r in checked), "new_ops": sum(r["new_ops"] for r in checked)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=(42, 100), required=True)
    parser.add_argument("--library-manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    folder = new_directory(args.out, ROOT / "results/c121_winner_fusion")
    sys.path.insert(0, str(ROOT / "sweeps"))
    import openttdlab
    from . import save_load_roundtrip as driver
    from .game_health import assess_game, parse_script_errors
    before = source_hashes()
    target = stage(folder)
    copied = tree_hashes(target)
    driver.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    driver.SCRIPT_DEBUG_LEVEL = "4"
    libraries, groups = cached_libraries(args.library_manifest, driver.CACHE_DIR, folder / "ai_libraries")
    # Keep the historical witness explicit after fusion becomes the default.
    settings = (("c121_air_economics", 1), ("c121_air_winner_fusion", 0))
    arm = openttdlab.local_folder(str(target), "OpexAI", settings)
    cfg = driver.bench_v2.make_cfg(1970)
    fixture_hashes = {p.name: digest(p) for p in (FIXTURE, ROOT / "tests/mechanisms/c121_winner_vm.nut")}
    # Retain the generator and its driver in addition to the generated Squirrel.
    shutil.copy2(Path(__file__), folder / "executed_runner.py")
    write_new(folder / "plan.json", {"kind": "general_fusion_correctness_and_opcodes_not_economic",
        "seed": args.seed, "years": 1, "workers": 1, "settings": settings, "configuration": cfg,
        "source_hashes": before, "copied_ai_hashes": copied, "fixture_hashes": fixture_hashes,
        "libraries": groups, "image": os.environ.get("DIAG_DOCKER_IMAGE_ID"),
        "matrix": "caps 1/6/13 x three MAIL states x four modes x AAA 0/1",
        "limitations": ["instrumentation perturbs scheduling", "same-day samples only", "inflation OFF",
                        "old results returned in natural game", "no economic/adoption verdict"]})
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
    health = assess_game([r["company"] for r in records], starting_year=1970, years=1,
                         expected_companies=("OpexAI",), engine_log=log)
    phase = {"records": records, "health": health, "script_errors": parse_script_errors(log)}
    phase["integrity"] = phase_integrity(phase, "1970-01-01", 1)
    evidence = markers(log)
    checks = {**evidence["checks"], **phase["integrity"], "game_health": health["game_ok"],
              "sources_unchanged": before == source_hashes(), "copy_unchanged": copied == tree_hashes(target),
              "fixtures_unchanged": fixture_hashes == {p.name: digest(p) for p in (FIXTURE, ROOT / "tests/mechanisms/c121_winner_vm.nut")}}
    report = {"seed": args.seed, "checks": checks, "pass": all(checks.values()),
              "evidence": evidence, "phase": phase, "economic_verdict": "not_evaluated"}
    write_new(folder / "report.json", report)
    print(json.dumps({"checks": checks, "live_count": evidence["live_count"],
                      "checked_count": evidence["checked_count"], "old_ops": evidence["old_ops"], "new_ops": evidence["new_ops"]}, indent=2), flush=True)
    if not report["pass"]:
        raise RuntimeError("Fusion non-validated; retained evidence")


if __name__ == "__main__":
    main()
