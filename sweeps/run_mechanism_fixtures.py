"""Real NoAI VM matrix and directed fleet fixtures, copied AI only.

GS bank commands and held mechanism boundaries make this an engineered test
world, NEVER an economic benchmark. All runtime/decoding comes from existing
helpers. Existing outputs are refused. No game runs on import.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/mechanisms"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, payload):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected one staging anchor: {old!r}")
    return text.replace(old, new)


def stage(folder):
    from .diag_r1_r3_mechanisms import stage_ai
    target = stage_ai(folder)
    for name in ("fleet_vm.nut", "world_fleet.nut"):
        shutil.copy2(FIXTURES / name, target / name)
    patches = {
        "main.nut": [
            ('function OpexAI::Start()', 'require("fleet_vm.nut");\nrequire("world_fleet.nut");\n\nfunction OpexAI::Start()'),
            ('  OpexLoadSettings();', '  OpexLoadSettings();\n  if (!this._loadedFromSave) FxMatrix();'),
            ('  if (this._loadedFromSave) this._reconcileAfterLoad();',
             '  if (this._loadedFromSave) this._reconcileAfterLoad();\n  FxResume(this);'),
        ],
        "task_air.nut": [('        plan.append(fleetEntry);', '        plan.append(fleetEntry);\n        FxEntry(this, fleetEntry);')],
        "persist.nut": [
            ('function OpexAI::Save()\n{', 'function OpexAI::Save()\n{\n  FxLog("phase=save state=" + FX.phase);'),
            ('    return shortSave;', '    shortSave.fixture <- FX;\n    return shortSave;'),
            ('  return saveObj;', '  saveObj.fixture <- FX;\n  return saveObj;'),
            ('  if (data == null) return;', '  if (data == null) return;\n  if ("fixture" in data) FX = data.fixture;'),
        ],
        "air_fleet.nut": [
            ('  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);\n  if (money < need) {',
             '  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);\n'
             '  FxLog("phase=guard price=" + price + " need=" + need + " cash=" + money);\n'
             '  if (money < need) {'),
        ],
    }
    for name, edits in patches.items():
        path = target / name
        text = path.read_text(encoding="utf-8")
        for old, new in edits:
            text = replace_once(text, old, new)
        path.write_text(text, encoding="utf-8")
    return target


def tree_hashes(folder):
    return {p.relative_to(folder).as_posix(): digest(p)
            for p in sorted(folder.rglob("*")) if p.is_file()}


def stage_bypass(folder, scenario):
    if scenario not in ("r3_dead", "r3_cash", "r3_failure"):
        raise ValueError("Unknown R3 scenario")
    target = stage(folder)
    shutil.copy2(FIXTURES / "world_bypass.nut", target / "world_bypass.nut")
    main = target / "main.nut"
    text = main.read_text(encoding="utf-8")
    text = replace_once(text, 'require("world_fleet.nut");',
                        f'require("world_fleet.nut");\nconst FX3_SCENARIO = "{scenario}";\nrequire("world_bypass.nut");')
    main.write_text(text, encoding="utf-8")
    air = target / "task_air.nut"
    text = replace_once(air.read_text(encoding="utf-8"), "        FxEntry(this, fleetEntry);", "")
    # The normal failure discard gate omits decision_log. Retain the actual
    # builder result in this test copy, without inventing errors or returns.
    text = replace_once(text,
                        '        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({',
                        '        if (R1_R3_TEST_ONLY || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) passDiscards.append({')
    air.write_text(text, encoding="utf-8")
    tasks = target / "task_projects.nut"
    text = tasks.read_text(encoding="utf-8")
    text = replace_once(text, "  local c73Cash = 0;", "  FxR3Prepare(this);\n  local c73Cash = 0;")
    text = replace_once(text, "      OpexC122ThreatNoteOutcome(project, i, attempt);",
                        "      FxR3Outcome(this, project, attempt);\n      OpexC122ThreatNoteOutcome(project, i, attempt);")
    text = replace_once(text,
                        '  if (fallthroughProbeActive) {\n    OpexC41ProjectsFallthroughLog("phase=exit',
                        '  FxR3Finish(this);\n  if (fallthroughProbeActive) {\n    OpexC41ProjectsFallthroughLog("phase=exit')
    tasks.write_text(text, encoding="utf-8")
    construction = target / "air_construction.nut"
    text = construction.read_text(encoding="utf-8")
    text = replace_once(text, "    local okA = levelA.ok && AIAirport.BuildAirport",
                        "    FxR3Obstacle(plan, levelA);\n    local okA = levelA.ok && AIAirport.BuildAirport")
    construction.write_text(text, encoding="utf-8")
    return target


def checkpoint_dates(log, state):
    # NoAI's date in Save() is the previous day at the monthly console save.
    # OpenTTD DATE is already at the next day. Pin this observed 15.3 offset;
    # select_checkpoint also verifies the entire save sequence below.
    return {str(date(1, 1, 1) + timedelta(days=int(d) - 365)) for d in re.findall(
        rf"FXWORLD phase=save state={re.escape(state)} date=(\d+)", log)}


def select_checkpoint(records, log, state):
    all_days = re.findall(r"FXWORLD phase=save state=\w+ date=(\d+)", log)
    actual = sorted(r["date"] for r in records)
    marked = sorted(str(date(1, 1, 1) + timedelta(days=int(d) - 365)) for d in all_days)
    if marked != actual and marked != actual[1:]:
        raise RuntimeError("Save log/file sequence mismatch; refuse inferred checkpoint")
    eligible = [r for r in records if r["date"] in checkpoint_dates(log, state)]
    if not eligible:
        raise RuntimeError(f"No save at mechanism boundary {state}; not validated")
    first = min(eligible, key=lambda row: row["date"])
    if sum(r["date"] == first["date"] for r in eligible) != 1:
        raise RuntimeError("Ambiguous boundary checkpoint")
    return first


def parse_saves(paths):
    import openttdlab
    from bench_1v1_5y_20seeds import extract_company_record
    records = []
    for path in paths:
        with open(path, "rb") as handle:
            game = openttdlab.parse_savegame(iter(lambda: handle.read(65536), b""))
        chunks = {k: v["records"] for k, v in game["chunks"].items()}
        stamp = str(date(1, 1, 1) + timedelta(days=chunks["DATE"]["0"]["date"] - 366))
        records.append({"path": str(path), "sha256": digest(path), "date": stamp,
                        "company": extract_company_record(chunks, 0, ["OpexAI", 42, 0], stamp)})
    return records


def verify_markers(logs):
    joined = "\n".join(logs)
    matrix = [int(x) for x in re.findall(r"FXVM case=(\d+).* pass=1", logs[0])]
    result = {"vm_matrix": matrix == list(range(1, 49)) and
              "FXVM complete=1 cases=48 boundary_checks=9 settings_restored=1" in logs[0]}
    for scenario in ("r1_below", "r1_exact", "r1_repeat", "r1_reload", "r1_stale"):
        result[scenario] = len(re.findall(rf"FXWORLD scenario={scenario} pass=1\b", joined)) == 1
    guards = re.findall(r"FXWORLD phase=guard price=(\d+) need=(\d+) cash=(\d+)", logs[1])
    result["exact_real_purchase_guard"] = bool(guards and guards[0][1] == guards[0][2])
    result["reload_reconciled"] = all("LOAD_RECONCILE" in log for log in logs[1:])
    result["real_bank_command"] = all("FXBANK" in log and " ok=1 " in log for log in logs)
    return result


def phase_integrity(phase, start, years):
    """Validate the actual reload interval, not fictitious pre-reload months.

    Keep assess_game's January-based report unchanged alongside this receipt.
    schema_version is metadata, never an error. Missing error fields fail closed.
    """
    from .game_health import inspect_checkpoints
    errors = phase["script_errors"]
    clean = all(key in errors and not errors[key]
                for key in ("attributed", "unattributed", "engine_marker"))
    first = date.fromisoformat(start)
    months = first.year * 12 + first.month - 1
    expected = [f"{(months + n) // 12:04d}-{(months + n) % 12 + 1:02d}-01"
                for n in range(years * 12 + 1)]
    records = phase["records"]
    checkpoints = inspect_checkpoints([r["company"] for r in records],
                                     expected_companies=("OpexAI",), expected_dates=expected)
    complete = (sorted(r["date"] for r in records) == expected
                and not checkpoints["duplicates"] and not checkpoints["missing_companies"]
                and not any(checkpoints["missing_checkpoints"].values()))
    return {"no_script_errors": clean, "exact_monthly_interval": complete}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scenario", choices=("r1", "r3_dead", "r3_cash", "r3_failure"), default="r1")
    args = parser.parse_args(argv)
    folder = args.out.resolve()
    allowed = (ROOT / "results/mechanism_completion").resolve()
    if not folder.is_relative_to(allowed) or folder == allowed:
        parser.error("Expected new child of results/mechanism_completion")
    folder.mkdir(parents=True)  # refuse existing folders including empty ones
    sys.path.insert(0, str(ROOT / "sweeps"))
    import openttdlab
    from . import save_load_roundtrip as reload
    from .diag_r1_r3_mechanisms import source_hashes, analyse_text
    from .game_health import assess_game, parse_script_errors
    before = source_hashes()
    target = stage(folder) if args.scenario == "r1" else stage_bypass(folder, args.scenario)
    copied = tree_hashes(target)
    fixtures = tree_hashes(FIXTURES)
    reload.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    reload.SCRIPT_DEBUG_LEVEL = "4"
    original = reload._REAL_CHECK_OUTPUT

    def with_gs(command, *rest, **kwargs):
        if reload._is_game_launch(command):
            cwd = Path(kwargs["cwd"])
            shutil.copytree(FIXTURES / "bank_gs", cwd / "game/FixtureBank")
        return original(command, *rest, **kwargs)

    reload._REAL_CHECK_OUTPUT = with_gs
    arm = openttdlab.local_folder(str(target), "OpexAI", (("decision_log", 1),))
    cfg = reload.bench_v2.make_cfg(1970) + '\n[game_scripts]\nFixtureBank = \n'
    write(folder / "plan.json", {"kind": "engineered_world_not_economic", "seed": 42,
          "scenario": args.scenario, "phase_years": [2, 1, 1] if args.scenario == "r1" else [2], "workers": 1, "source_hashes": before,
          "copied_ai_hashes": copied, "fixture_hashes": fixtures, "configuration": cfg,
          "image": os.environ.get("DIAG_DOCKER_IMAGE_ID"), "git_sha": None,
          "checkpoint_selection": "earliest save while coordinator holds selected / purchased",
          "scope": "VM arithmetic; R1 generated want=4; single-candidate common selector; real GS balance"})
    logs, phases = [], []
    checkpoint = None
    try:
        for index, years in enumerate((2, 1, 1) if args.scenario == "r1" else (2,)):
            phase = folder / f"phase_{index}"
            phase.mkdir()
            if index == 0:
                _, log, saves = reload.run_phase_a(42, years, arm, cfg, phase / "rows.jsonl", phase / "saves")
                starting_year = 1970
            else:
                assert digest(checkpoint["path"]) == checkpoint["sha256"]
                _, log, saves = reload.run_phase_b(42, years, arm, cfg, phase / "rows.jsonl", checkpoint["path"], phase / "saves")
                starting_year = int(checkpoint["date"][:4])
            (phase / "engine.log").write_text(log or "", encoding="utf-8")
            logs.append(log or "")
            records = parse_saves(saves)
            health = assess_game([r["company"] for r in records], starting_year=starting_year,
                                 years=years, expected_companies=("OpexAI",), engine_log=log)
            # Health is reported separately: the fixture deliberately suspends
            # the scheduler, so economic activity is NOT a pass requirement.
            errors = parse_script_errors(log or "")
            phase_report = {"records": records, "health": health, "script_errors": errors,
                            "input_checkpoint": checkpoint, "log_sha256": digest(phase / "engine.log")}
            phase_report["fixture_integrity"] = phase_integrity(
                phase_report, checkpoint["date"] if checkpoint else "1970-01-01", years)
            write(phase / "report.json", phase_report)
            phases.append(phase_report)
            if "FIXTURE_ASSERT" in log or "Your script made an error" in log or "The script died unexpectedly" in log:
                raise RuntimeError("Engine fixture failure; artifacts retained")
            if index < 2 and args.scenario == "r1":
                checkpoint = select_checkpoint(records, log, "selected" if index == 0 else "purchased")
                print("CHECKPOINT", index, checkpoint["date"], checkpoint["sha256"], flush=True)
        if args.scenario == "r1":
            checks = verify_markers(logs)
        else:
            trace = analyse_text(logs[0], "phase_0/engine.log", "engine_log")
            write(folder / "trace.json", trace)
            initial = re.findall(r"FXWORLD phase=r3_initial.* rank=(\d+).* live=1", logs[0])
            checks = {"initial_liveness": initial == ["0", "1", "2"],
                      "trace": trace["trace_summary"][args.scenario] == "pass",
                      "physical_completion": f"FXWORLD phase=r3_complete scenario={args.scenario}" in logs[0]}
        checks["all_phase_integrity"] = all(all(p["fixture_integrity"].values()) for p in phases)
        checks["sources_unchanged"] = before == source_hashes()
        checks["copy_unchanged"] = copied == tree_hashes(target)
        checks["fixtures_unchanged"] = fixtures == tree_hashes(FIXTURES)
        report = {"checks": checks, "pass": all(checks.values()), "phases": phases,
                  "economic_verdict": "not_evaluated", "scenario": args.scenario,
                  "scope": "engineered_world_common_selector_subset_not_full_catalogue"}
        write(folder / "report.json", report)
        print(json.dumps(checks, indent=2), flush=True)
        if not report["pass"]:
            raise RuntimeError("Incomplete directed fixture evidence")
    finally:
        reload._REAL_CHECK_OUTPUT = original
        openttdlab.subprocess.check_output = original


if __name__ == "__main__":
    main()