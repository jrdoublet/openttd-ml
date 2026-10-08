"""NoAI target-limit assertions and ordinary Save/Load; correctness only.

Uses the existing save/load driver, source copier, decoders and health checks.
The fixture restores every transient override before natural play resumes.
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
from pathlib import Path
import shutil

from .diag_r1_r3_mechanisms import new_directory, write_new
from .run_c121_cache_fixtures import stage as copy_ai
from .run_mechanism_fixtures import digest, parse_saves, phase_integrity, replace_once, tree_hashes

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/mechanisms/c121_target_limit_vm.nut"


def stage(folder, fixture=FIXTURE):
    target = copy_ai(folder, False)
    shutil.copy2(fixture, target / fixture.name)
    main = target / "main.nut"
    text = replace_once(main.read_text(encoding="utf-8"), "function OpexAI::Start()",
                        f'require("{fixture.name}");\n\nfunction OpexAI::Start()')
    text = replace_once(text, "  OpexLoadSettings();", "  OpexLoadSettings();\n  FxTLStart(this);")
    main.write_text(text, encoding="utf-8")
    task = target / "task_air.nut"
    text = replace_once(task.read_text(encoding="utf-8"),
                        "function OpexAI::_resizeAirFleets(year, plan = null)\n{",
                        "function OpexAI::_resizeAirFleets(year, plan = null)\n{\n  FxTLWorld(this);")
    task.write_text(text, encoding="utf-8")
    return target


def main(argv=None, *, settings=None, fixture=FIXTURE, marker="C121_TARGET", stage_transform=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    folder = new_directory(args.out, ROOT / "results/c121_target_limit")
    import openttdlab
    from . import save_load_roundtrip as reload
    from .game_health import assess_game, parse_script_errors

    target = stage(folder, fixture)
    if stage_transform is not None:
        stage_transform(target)
    copied = tree_hashes(target)
    reload.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    reload.SCRIPT_DEBUG_LEVEL = "4"
    if settings is None:
        settings = (("c121_air_economics", 1), ("c121_catalog_incremental", 1),
                    ("c121_air_target_limit", 1), ("decision_log", 1))
    arm = openttdlab.local_folder(str(target), "OpexAI", settings)
    cfg = reload.bench_v2.make_cfg(1970)
    write_new(folder / "plan.json", {
        "kind": "correctness_not_economic", "seed": 42, "years_per_phase": 1,
        "workers": 1, "settings": settings, "configuration": cfg,
        "copied_ai_hashes": copied, "fixture_sha256": digest(fixture),
        "git_sha": os.environ.get("DIAG_GIT_SHA"),
        "image": os.environ.get("DIAG_DOCKER_IMAGE_ID"),
        "reload_selection": "first retained save after 1970-07-01; ordinary reload, not an exact purchase boundary",
    })
    phases, logs = [], []
    checkpoint = None
    for index in range(2):
        part = folder / f"phase_{index}"
        part.mkdir()
        if index == 0:
            _, log, saves = reload.run_phase_a(42, 1, arm, cfg, part / "rows.jsonl", part / "saves")
            start = "1970-01-01"
        else:
            if checkpoint is None:
                break
            if digest(checkpoint["path"]) != checkpoint["sha256"]:
                raise RuntimeError("Checkpoint changed")
            _, log, saves = reload.run_phase_b(42, 1, arm, cfg, part / "rows.jsonl",
                                               checkpoint["path"], part / "saves")
            start = checkpoint["date"]
        log = log or ""
        (part / "engine.log").write_text(log, encoding="utf-8")
        logs.append(log)
        records = parse_saves(saves)
        health = assess_game([r["company"] for r in records], starting_year=int(start[:4]),
                             years=1, expected_companies=("OpexAI",), engine_log=log)
        phase = {"records": records, "health": health, "script_errors": parse_script_errors(log),
                 "input_checkpoint": checkpoint, "log_sha256": digest(part / "engine.log")}
        phase["integrity"] = phase_integrity(phase, start, 1)
        write_new(part / "report.json", phase)
        phases.append(phase)
        print("PHASE", index, "saves", len(records), "integrity", phase["integrity"], flush=True)
        if marker + "_ASSERT" in log or not all(phase["integrity"].values()):
            break
        if index == 0:
            candidates = [r for r in records if r["date"] >= "1970-07-01"]
            checkpoint = min(candidates, key=lambda r: r["date"]) if candidates else None

    checks = {
        "phase_count": len(phases) == 2,
        "all_phase_integrity": bool(phases) and all(all(p["integrity"].values()) for p in phases),
        "matrix_before_and_after_load": len(logs) == 2 and all(marker + "_MATRIX pass=1" in log for log in logs),
        "world_before_and_after_load": len(logs) == 2 and all(marker + "_WORLD pass=1" in log for log in logs),
        "reload_reconciled": len(logs) == 2 and "LOAD_RECONCILE" in logs[1],
        "no_fixture_assertion": all(marker + "_ASSERT" not in log for log in logs),
        "copy_unchanged": copied == tree_hashes(target),
    }
    report = {"checks": checks, "pass": all(checks.values()), "phases": phases,
              "economic_verdict": "not_evaluated"}
    write_new(folder / "report.json", report)
    print(json.dumps(checks, indent=2), flush=True)
    if not report["pass"]:
        raise RuntimeError("Target limit correctness non-validated; see retained evidence")


if __name__ == "__main__":
    main()
