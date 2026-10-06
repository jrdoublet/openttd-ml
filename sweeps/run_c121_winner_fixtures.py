"""Winner cap=1 prototype: copied AI, NoAI equivalence and opcode evidence.

Descriptive instrumented game, not an economic or adoption benchmark. Reuses
the current save/load driver, monthly decoders and health checks. No run on import.
"""
from __future__ import annotations

import argparse
from collections import Counter
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import sys

from .diag_r1_r3_mechanisms import source_hashes, new_directory, write_new
from .run_mechanism_fixtures import digest, tree_hashes, replace_once, parse_saves, phase_integrity

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/mechanisms/c121_winner_vm.nut"


def stage(folder):
    target = folder / "ai/OpexAI"
    shutil.copytree(ROOT / "ai/OpexAI", target)
    shutil.copy2(FIXTURE, target / FIXTURE.name)
    main = target / "main.nut"
    text = replace_once(main.read_text(encoding="utf-8"), "function OpexAI::Start()",
                        'require("c121_winner_vm.nut");\n\nfunction OpexAI::Start()')
    text = replace_once(text, "  OpexLoadSettings();", "  OpexLoadSettings();\n  FxWStart(this);")
    main.write_text(text, encoding="utf-8")
    return target


def markers(log):
    matrix = [dict(zip(("case", "cap", "mail", "mode", "aaa", "stable", "eligible", "old_ops", "new_ops"),
                       map(int, row))) for row in re.findall(
        r"C121_WINNER_MATRIX case=(\d+) cap=(\d+) mail=(\d+) mode=(\d+) aaa=(\d+) stable=(\d+) eligible=(\d+) old_ops=(\d+) new_ops=(\d+) pass=1", log)]
    live = [dict(zip(("arm", "cap", "mail", "eligible", "stable", "full_ops", "copy_ops"), row))
            for row in re.findall(
                r"C121_WINNER_LIVE arm=(\w+) cap=(\d+) mail=(\w+) eligible=(\d+) stable=(\d+) full_ops=(\d+) copy_ops=(-?\d+) pass=1", log)]
    for row in live:
        for key in ("cap", "eligible", "stable", "full_ops", "copy_ops"):
            row[key] = int(row[key])
    counts = Counter((r["arm"], r["mail"], r["cap"]) for r in live)
    eligible = [r for r in live if r["eligible"]]
    return {"matrix": matrix, "live": live,
            "distribution": [{"arm": arm, "mail": mail, "cap": cap, "count": count}
                             for (arm, mail, cap), count in sorted(counts.items())],
            "live_count": len(live), "eligible_count": len(eligible),
            "eligible_share": len(eligible) / len(live) if live else None,
            "eligible_full_ops": sum(r["full_ops"] for r in eligible),
            "eligible_copy_ops": sum(r["copy_ops"] for r in eligible),
            "checks": {"start": "C121_WINNER_START active=1 production_result=old" in log,
                       "matrix_cases": [r["case"] for r in matrix] == list(range(1, 73)),
                       "matrix_stable": bool(matrix) and all(r["stable"] for r in matrix),
                       "matrix_restored": "C121_WINNER_VM complete=1 cases=72 restored=1" in log,
                       "live_exposed": bool(live),
                       "no_fixture_assertion": "C121_WINNER_ASSERT" not in log}}


def cached_libraries(manifest_path, cache, destination):
    """Reuse the frozen-library descriptor and verify every transitive tar."""
    from .campaign_freeze import _frozen_library_descriptor
    groups = json.loads(manifest_path.read_text(encoding="utf-8"))["libraries"]
    if {g["requested_name"] for g in groups} != {"Queue.FibonacciHeap", "Pathfinder.Rail"}:
        raise ValueError("Expected the driver's two library groups")
    destination.mkdir()
    for group in groups:
        for entry in group["resolved"]:
            name = entry["filename"]
            if Path(name).name != name:
                raise ValueError("Invalid library filename")
            source = cache / "bananas" / name
            if digest(source) != entry["sha256"]:
                raise ValueError(f"Cached library hash mismatch: {name}")
            shutil.copy2(source, destination / name)
    return tuple(_frozen_library_descriptor(g["requested_name"], g["resolved"], destination)
                 for g in groups), groups


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=(42, 100), required=True)
    parser.add_argument("--library-manifest", type=Path)
    args = parser.parse_args(argv)
    folder = new_directory(args.out, ROOT / "results/c121_winner_single_scan")
    sys.path.insert(0, str(ROOT / "sweeps"))
    import openttdlab
    from . import save_load_roundtrip as reload
    from .game_health import assess_game, parse_script_errors

    before = source_hashes()
    fixture_hash = digest(FIXTURE)
    target = stage(folder)
    copied = tree_hashes(target)
    reload.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    reload.SCRIPT_DEBUG_LEVEL = "4"
    libraries, groups = None, None
    if args.library_manifest:
        libraries, groups = cached_libraries(args.library_manifest, reload.CACHE_DIR, folder / "ai_libraries")
    # The fixture compares against the unfused production witness.
    settings = (("c121_air_economics", 1), ("c121_air_winner_fusion", 0))
    arm = openttdlab.local_folder(str(target), "OpexAI", settings)
    cfg = reload.bench_v2.make_cfg(1970)
    write_new(folder / "plan.json", {
        "kind": "correctness_and_descriptive_exposure_not_economic", "seed": args.seed,
        "years": 1, "workers": 1, "settings": settings, "configuration": cfg,
        "source_hashes": before, "copied_ai_hashes": copied, "fixture_sha256": fixture_hash,
        "image": os.environ.get("DIAG_DOCKER_IMAGE_ID"),
        "libraries": groups,
        "library_manifest_sha256": digest(args.library_manifest) if args.library_manifest else None,
        "prototype": "cap=1 and opening N=1: clone outer and decisionEconomics; else old calls",
        "matrix": "caps 1/2/4 x unknown/known-zero/known-positive MAIL x four score modes x AAA 0/1",
        "limitations": ["instrumentation changes scheduling", "matrix caps forced, real route inputs",
                        "natural activity returns old economics", "not an A/B or adoption verdict",
                        "opcode difference includes guard/copy, excludes exposure instrumentation",
                        "same-day guard conservative; monthly tariff-boundary fixture deferred"],
    })
    original_run = reload.run_experiments
    def run_with_frozen_libraries(**kwargs):
        kwargs["ai_libraries"] = libraries
        return original_run(**kwargs)
    try:
        if libraries is not None:
            reload.run_experiments = run_with_frozen_libraries
        _, log, saves = reload.run_phase_a(args.seed, 1, arm, cfg, folder / "rows.jsonl", folder / "saves")
    finally:
        reload.run_experiments = original_run
    log = log or ""
    (folder / "engine.log").write_text(log, encoding="utf-8")
    records = parse_saves(saves)
    # Existing decoder helper pins 42 in metadata; physical decoding is seed independent.
    for record in records:
        record["company"]["run"][1] = args.seed
    health = assess_game([r["company"] for r in records], starting_year=1970, years=1,
                         expected_companies=("OpexAI",), engine_log=log)
    phase = {"records": records, "health": health, "script_errors": parse_script_errors(log)}
    phase["integrity"] = phase_integrity(phase, "1970-01-01", 1)
    evidence = markers(log)
    checks = {**evidence["checks"], **phase["integrity"],
              "sources_unchanged": before == source_hashes(),
              "copy_unchanged": copied == tree_hashes(target),
              "fixture_unchanged": fixture_hash == digest(FIXTURE)}
    report = {"checks": checks, "pass": all(checks.values()), "seed": args.seed,
              "phase": phase, "evidence": evidence, "economic_verdict": "not_evaluated",
              "live_shortcut_validated": bool(evidence["eligible_count"]) and all(checks.values())}
    write_new(folder / "report.json", report)
    print(json.dumps({"checks": checks, "live_count": evidence["live_count"],
                      "eligible_count": evidence["eligible_count"], "distribution": evidence["distribution"]}, indent=2), flush=True)
    if not report["pass"]:
        raise RuntimeError("Winner fixture non-validated; see retained evidence")


if __name__ == "__main__":
    main()
