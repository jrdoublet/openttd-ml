"""Directed NoAI contracts in a copied AI, using the existing phase/health harness.

Legacy helpers must be exported from the immutable c68d50a source before running.
No production source is edited. This is correctness evidence, not economics.
"""
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import re
import shutil

from .diag_r1_r3_mechanisms import source_hashes, new_directory, write_new
from .run_mechanism_fixtures import digest, tree_hashes, replace_once, parse_saves, phase_integrity

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/mechanisms/c121_kdec_cold_vm.nut"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--legacy-source", type=Path, required=True)
    parser.add_argument("--project-legacy-source", type=Path,
                        help="Optional pre-removal model source for project-factor parity with its abandoned switch OFF")
    args = parser.parse_args()
    folder = new_directory(args.out, ROOT / "results/c121_kdec_cold_contracts")
    import openttdlab
    from . import save_load_roundtrip as reload
    from .game_health import assess_game, parse_script_errors

    before = source_hashes()
    target = folder / "ai/OpexAI"
    shutil.copytree(ROOT / "ai/OpexAI", target)
    legacy = args.legacy_source.read_text(encoding="utf-8")
    extracted = []
    for start, end in (("function OpexC121ProjectHasRealization", "/* C70 : facteur"),
                       ("function OpexC70Profit", "/* C82 : facteur du moteur"),
                       ("function OpexC82Profit", "/* Profit calibre des scores")):
        text = legacy[legacy.index(start):legacy.index(end, legacy.index(start))]
        for name, replacement in (("OpexC121ProjectHasRealization", "FxKLegacyHasRealization"),
                                  ("OpexC70Profit", "FxKLegacyC70Profit"),
                                  ("OpexC82Profit", "FxKLegacyC82Profit")):
            text = text.replace(name, replacement)
        extracted.append(text)
    extra = ""
    project_fixture = ROOT / "tests/mechanisms/c121_project_realization_cleanup_vm.nut"
    if args.project_legacy_source is not None:
        project_source = args.project_legacy_source.read_text(encoding="utf-8")
        start = project_source.index("function OpexC121RealizationFactor")
        end = project_source.index("function ", start + len("function "))
        project_helper = project_source[start:end]
        project_helper = project_helper.replace("OpexC121RealizationFactor", "FxPLegacyRealizationFactor")
        project_helper = re.sub(r"\bC121_AIR_PROJECT_REALIZATION\b", "false", project_helper)
        extra = project_helper + project_fixture.read_text(encoding="utf-8")
    (target / "c121_kdec_cold_vm.nut").write_text("\n".join(extracted) + FIXTURE.read_text(encoding="utf-8") + extra, encoding="utf-8")
    main = target / "main.nut"
    text = replace_once(main.read_text(encoding="utf-8"), "function OpexAI::Start()",
                        'require("c121_kdec_cold_vm.nut");\n\nfunction OpexAI::Start()')
    fixture_calls = "  OpexLoadSettings();\n  FxKStart();"
    if args.project_legacy_source is not None:
        fixture_calls += "\n  FxPStart();"
    text = replace_once(text, "  OpexLoadSettings();", fixture_calls)
    main.write_text(text, encoding="utf-8")
    copied = tree_hashes(target)
    reload.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    reload.SCRIPT_DEBUG_LEVEL = "4"
    settings = (("c121_air_economics", 1), ("c121_catalog_incremental", 1))
    arm = openttdlab.local_folder(str(target), "OpexAI", settings)
    cfg = reload.bench_v2.make_cfg(1970)
    write_new(folder / "plan.json", {"kind": "correctness_not_economic", "seed": 42,
              "years": 1, "workers": 1, "legacy_git_sha": "c68d50a09a9e8fd3ffa8dae063fe4b281e10c408",
              "legacy_source_sha256": digest(args.legacy_source), "fixture_sha256": digest(FIXTURE),
              "project_legacy_source_sha256": digest(args.project_legacy_source) if args.project_legacy_source else None,
              "project_fixture_sha256": digest(project_fixture) if args.project_legacy_source else None,
              "source_hashes": before, "copied_ai_hashes": copied, "settings": settings})
    _, log, saves = reload.run_phase_a(42, 1, arm, cfg, folder / "rows.jsonl", folder / "saves")
    log = log or ""
    (folder / "engine.log").write_text(log, encoding="utf-8")
    records = parse_saves(saves)
    health = assess_game([r["company"] for r in records], starting_year=1970,
                         years=1, expected_companies=("OpexAI",), engine_log=log)
    phase = {"records": records, "health": health, "script_errors": parse_script_errors(log),
             "input_checkpoint": None, "log_sha256": digest(folder / "engine.log")}
    integrity = phase_integrity(phase, "1970-01-01", 1)
    match = re.search(r"C121_KDEC_VM complete=1 checks=(\d+) restored=1", log)
    project_match = re.search(r"C121_PROJECT_CLEANUP_VM complete=1 checks=(\d+) restored=1", log)
    checks = {"noai_contracts": match is not None and int(match[1]) == 53,
              "no_assertion": "C121_KDEC_VM_ASSERT" not in log,
              "phase_integrity": all(integrity.values()), "sources_unchanged": before == source_hashes(),
              "copy_unchanged": copied == tree_hashes(target)}
    if args.project_legacy_source is not None:
        checks["project_factor_parity"] = project_match is not None and int(project_match[1]) == 322
    write_new(folder / "report.json", {"pass": all(checks.values()), "checks": checks,
              "vm_assertions": int(match[1]) if match else None,
              "project_vm_assertions": int(project_match[1]) if project_match else None,
              "phase": phase, "integrity": integrity,
              "economic_verdict": "not_evaluated"})
    print(json.dumps(checks, indent=2), flush=True)
    if not all(checks.values()):
        raise RuntimeError("C121 K_dec VM contracts not validated")


if __name__ == "__main__":
    main()
