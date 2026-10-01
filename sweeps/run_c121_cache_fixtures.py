"""C121 cache correctness only: copied AI, real NoAI VM and scan-boundary reload.

No run on import. Reuses the existing save/load driver, physical decoder and
health checks. Synthetic VM doubles are restored before natural game activity.
Never edits production AI; refuses existing output directories.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import inspect
import json
import os
from pathlib import Path
import re
import shutil

from .diag_r1_r3_mechanisms import source_hashes, new_directory, write_new
from .run_mechanism_fixtures import digest, tree_hashes, replace_once, parse_saves, phase_integrity

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/mechanisms/c121_cache_vm.nut"


def stage(folder, fixture):
    target = folder / "ai/OpexAI"
    shutil.copytree(ROOT / "ai/OpexAI", target)
    if not fixture:
        return target
    shutil.copy2(FIXTURE, target / FIXTURE.name)
    main = target / "main.nut"
    text = replace_once(main.read_text(encoding="utf-8"), "function OpexAI::Start()",
                        'require("c121_cache_vm.nut");\n\nfunction OpexAI::Start()')
    text = replace_once(text, "  OpexLoadSettings();", "  OpexLoadSettings();\n  FxCStart(this);")
    main.write_text(text, encoding="utf-8")
    persist = target / "persist.nut"
    text = replace_once(persist.read_text(encoding="utf-8"), "function OpexAI::Save()\n{",
                        "function OpexAI::Save()\n{\n  FxCSaveBoundary(this);")
    persist.write_text(text, encoding="utf-8")
    return target


def scan_checkpoint(records, log):
    """Only saves explicitly observed with a nonempty, unfinished scan qualify.

    NoAI Save date precedes DATE by one day in the pinned 15.3 runtime, as
    validated by run_mechanism_fixtures. Never fall back to a median date.
    """
    days = re.findall(r"C121_CACHE_BOUNDARY active=1 entries=[1-9]\d* date=(\d+)", log)
    dates = {str(date(1, 1, 1) + timedelta(days=int(day) - 365)) for day in days}
    eligible = [row for row in records if row["date"] in dates]
    if not eligible:
        return None
    chosen = min(eligible, key=lambda row: row["date"])
    if sum(row["date"] == chosen["date"] for row in records) != 1:
        raise ValueError("Ambiguous scan-boundary checkpoint")
    return chosen


def checks_for_logs(logs):
    return {
        "synthetic_vm": bool(re.search(r"C121_CACHE_VM complete=1 checks=[1-9]\d* restored=1", logs[0])),
        "live_cache_hit": bool(re.search(r"C121_CACHE_LIVE arm=\w+ pass=1", logs[0])),
        "reload_empty_cache": len(logs) == 2 and "C121_CACHE_RELOAD empty=1" in logs[1],
        "reload_rebuild_hit": len(logs) == 2 and bool(re.search(r"C121_CACHE_LIVE arm=\w+ pass=1", logs[1])),
        "reload_reconciled": len(logs) == 2 and "LOAD_RECONCILE" in logs[1],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile", choices=("default", "cache"), required=True)
    args = parser.parse_args(argv)
    folder = new_directory(args.out, ROOT / "results/c121_cache_coherence")
    import openttdlab
    from . import save_load_roundtrip as reload
    from .game_health import assess_game, parse_script_errors

    before = source_hashes()
    fixture_hash = digest(FIXTURE)
    target = stage(folder, args.profile == "cache")
    copied = tree_hashes(target)
    reload.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    reload.SCRIPT_DEBUG_LEVEL = "4"
    settings = () if args.profile == "default" else (("c121_air_economics", 1), ("c121_catalog_incremental", 1))
    arm = openttdlab.local_folder(str(target), "OpexAI", settings)
    cfg = reload.bench_v2.make_cfg(1970)
    write_new(folder / "plan.json", {
        "kind": "correctness_not_economic", "profile": args.profile, "seed": 42,
        "years_per_phase": 1, "workers": 1, "settings": settings,
        "configuration": cfg, "source_hashes": before, "copied_ai_hashes": copied,
        "fixture_sha256": fixture_hash, "git_sha": None,
        "image": os.environ.get("DIAG_DOCKER_IMAGE_ID"),
        "reload_selection": "earliest explicitly marked nonempty unfinished scan",
    })
    phases, logs = [], []
    checkpoint = None
    for index in range(1 if args.profile == "default" else 2):
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
            _, log, saves = reload.run_phase_b(42, 1, arm, cfg, part / "rows.jsonl", checkpoint["path"], part / "saves")
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
        if "C121_CACHE_ASSERT" in log or not all(phase["integrity"].values()):
            break
        if index == 0 and args.profile == "cache":
            checkpoint = scan_checkpoint(records, log)
            print("SCAN_CHECKPOINT", None if checkpoint is None else checkpoint["date"], flush=True)

    checks = {} if args.profile == "default" else checks_for_logs(logs)
    checks.update({
        "phase_count": len(phases) == (1 if args.profile == "default" else 2),
        "all_phase_integrity": bool(phases) and all(all(p["integrity"].values()) for p in phases),
        "no_fixture_assertion": all("C121_CACHE_ASSERT" not in log for log in logs),
        "sources_unchanged": before == source_hashes(),
        "copy_unchanged": copied == tree_hashes(target),
        "fixture_unchanged": fixture_hash == digest(FIXTURE),
    })
    report = {"checks": checks, "pass": all(checks.values()), "phases": phases,
              "economic_verdict": "not_evaluated", "profile": args.profile,
              "live_topologies": [sorted(set(re.findall(r"C121_CACHE_LIVE arm=(\w+) pass=1", log))) for log in logs]}
    write_new(folder / "report.json", report)
    print(json.dumps(checks, indent=2), flush=True)
    if not report["pass"]:
        raise RuntimeError("Cache correctness non-validated; see retained evidence")


if __name__ == "__main__":
    main()