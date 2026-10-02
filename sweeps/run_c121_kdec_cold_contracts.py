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
    (target / "c121_kdec_cold_vm.nut").write_text("\n".join(extracted) + FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    main = target / "main.nut"
    text = replace_once(main.read_text(encoding="utf-8"), "function OpexAI::Start()",
                        'require("c121_kdec_cold_vm.nut");\n\nfunction OpexAI::Start()')
    text = replace_once(text, "  OpexLoadSettings();", "  OpexLoadSettings();\n  FxKStart();")
    main.write_text(text, encoding="utf-8")
    copied = tree_hashes(target)
    reload.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    reload.SCRIPT_DEBUG_LEVEL = "4"
    settings = (("c121_air_economics", 1), ("c121_catalog_incremental", 1), ("c121_kdec_cold_exempt", 1))
    arm = openttdlab.local_folder(str(target), "OpexAI", settings)
    cfg = reload.bench_v2.make_cfg(1970)
    write_new(folder / "plan.json", {"kind": "correctness_not_economic", "seed": 42,
              "years": 1, "workers": 1, "legacy_git_sha": "c68d50a09a9e8fd3ffa8dae063fe4b281e10c408",
              "legacy_source_sha256": digest(args.legacy_source), "fixture_sha256": digest(FIXTURE),
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
    checks = {"noai_contracts": match is not None and int(match[1]) == 138,
              "no_assertion": "C121_KDEC_VM_ASSERT" not in log,
              "phase_integrity": all(integrity.values()), "sources_unchanged": before == source_hashes(),
              "copy_unchanged": copied == tree_hashes(target)}
    write_new(folder / "report.json", {"pass": all(checks.values()), "checks": checks,
              "vm_assertions": int(match[1]) if match else None, "phase": phase, "integrity": integrity,
              "economic_verdict": "not_evaluated"})
    print(json.dumps(checks, indent=2), flush=True)
    if not all(checks.values()):
        raise RuntimeError("C121 K_dec VM contracts not validated")


if __name__ == "__main__":
    main()
