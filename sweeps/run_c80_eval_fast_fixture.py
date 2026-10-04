"""Matched-input hub-hub cost fixture in a copy, through the existing driver."""
import argparse
import inspect
import json
from pathlib import Path
import re
import shutil
from .run_mechanism_fixtures import digest, tree_hashes, replace_once, parse_saves, phase_integrity, write
from .game_health import assess_game, parse_script_errors

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    folder = args.out.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    import openttdlab
    from . import save_load_roundtrip as driver
    before = tree_hashes(ROOT / "ai/OpexAI")
    target = folder / "ai/OpexAI"
    shutil.copytree(ROOT / "ai/OpexAI", target)
    fixture = ROOT / "tests/mechanisms/c80_eval_fast_vm.nut"
    shutil.copy2(fixture, target / fixture.name)
    main_file = target / "main.nut"
    src = replace_once(main_file.read_text(encoding="utf-8"), "function OpexAI::Start()",
                       'require("c80_eval_fast_vm.nut");\nfunction OpexAI::Start()')
    src = replace_once(src, "  OpexLoadSettings();", "  OpexLoadSettings();\n  FqeStart();")
    main_file.write_text(src, encoding="utf-8")
    copied = tree_hashes(target)
    driver.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    driver.SCRIPT_DEBUG_LEVEL = "4"
    settings = (("c121_air_economics", 1), ("c121_catalog_incremental", 1))
    arm = openttdlab.local_folder(str(target), "OpexAI", settings)
    write(folder / "plan.json", {"kind": "matched_input_cost_not_economic",
        "seed": 42, "years": 2, "settings": settings, "source_hashes": before,
        "copy_hashes": copied, "fixture_sha256": digest(fixture),
        "domain": "hub_hub; max4 captured hubs; same catalog, combo, airport, engine; cold caches; alternating order",
        "criteria": "healthy, >=3 stable equivalent samples with >=1 plan, sum(new_ops)<sum(old_ops)",
        "limits": "bounded phase, not full planner; no economic attribution; unstable dates excluded"})
    _, log, saves = driver.run_phase_a(42, 2, arm, driver.bench_v2.make_cfg(1970),
                                     folder / "rows.jsonl", folder / "saves")
    log = log or ""
    (folder / "engine.log").write_text(log, encoding="utf-8")
    records = parse_saves(saves)
    health = assess_game([r["company"] for r in records], starting_year=1970, years=2,
                        expected_companies=("OpexAI",), engine_log=log)
    phase = {"records": records, "health": health, "script_errors": parse_script_errors(log)}
    integrity = phase_integrity(phase, "1970-01-01", 2)
    rows = [dict(zip(("checked", "equivalent", "old_ops", "new_ops", "plans", "order"), map(int, m)))
            for m in re.findall(r"EVAL_FAST_FIXTURE phase=hub_hub checked=(\d+) equivalent=(\d+) old_ops=(\d+) new_ops=(\d+) plans=(\d+) order=(\d+)", log)]
    eligible = [r for r in rows if r["checked"] and r["plans"] > 0]
    checks = dict(integrity, source_unchanged=before==tree_hashes(ROOT/"ai/OpexAI"),
                  copy_unchanged=copied==tree_hashes(target),
                  started="EVAL_FAST_FIXTURE_START active=1" in log,
                  equivalent=all(r["equivalent"] for r in rows if r["checked"]))
    old = sum(r["old_ops"] for r in eligible)
    new = sum(r["new_ops"] for r in eligible)
    valid = all(checks.values())
    report = {"checks": checks, "technical_pass": valid, "samples": rows,
              "eligible_samples": len(eligible), "old_ops": old, "new_ops": new,
              "saving_pct": 100*(old-new)/old if old else None,
              "opcode_gain_measured": valid and len(eligible)>=3 and new<old,
              "economic_verdict": "not_evaluated", "health": health}
    write(folder/"report.json", report)
    print(json.dumps({k:v for k,v in report.items() if k!="health"}), flush=True)
    if not valid:
        raise RuntimeError("Fixture technical failure; inspect retained logs")

if __name__ == "__main__":
    main()
