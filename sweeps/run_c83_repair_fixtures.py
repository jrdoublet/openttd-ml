"""Copy-only directed NoAI helper checks through the existing engine driver."""
from __future__ import annotations
import argparse
import inspect
import json
from pathlib import Path
import re
import shutil
from .run_mechanism_fixtures import digest, tree_hashes, replace_once, write

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    folder = args.out.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    import openttdlab
    from . import save_load_roundtrip as driver
    fixture = ROOT / "tests/mechanisms/c83_repair_vm.nut"
    before = tree_hashes(ROOT / "ai/OpexAI")
    target = folder / "ai/OpexAI"
    shutil.copytree(ROOT / "ai/OpexAI", target)
    shutil.copy2(fixture, target / fixture.name)
    main = target / "main.nut"
    text = replace_once(main.read_text(encoding="utf-8"), "function OpexAI::Start()",
                        'require("c83_repair_vm.nut");\nfunction OpexAI::Start()')
    text = replace_once(text, "  OpexLoadSettings();", "  OpexLoadSettings();\n  FxC83Start(this);")
    main.write_text(text, encoding="utf-8")
    driver.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    driver.SCRIPT_DEBUG_LEVEL = "4"
    write(folder / "plan.json", {"kind": "directed_vm_not_economic", "seed": 42, "years": 1,
                                "source_hashes": before, "copied_ai_hashes": tree_hashes(target),
                                "fixture_sha256": digest(fixture)})
    arm = openttdlab.local_folder(str(target), "OpexAI", ())
    _, log, _ = driver.run_phase_a(42, 1, arm, driver.bench_v2.make_cfg(1970),
                                 folder / "rows.jsonl", folder / "saves")
    (folder / "engine.log").write_text(log or "", encoding="utf-8")
    cases = [int(x) for x in re.findall(r"C83_REPAIR_VM case=(\d+) pass=1", log or "")]
    checks = {"cases": cases == list(range(1, 8)), "snapshot_and_restore": "C83_REPAIR_VM complete=1 cases=8 restored=1" in (log or ""),
              "no_assertion": "C83_REPAIR_ASSERT" not in (log or ""),
              "sources_unchanged": before == tree_hashes(ROOT / "ai/OpexAI")}
    write(folder / "report.json", {"checks": checks, "pass": all(checks.values()), "cases": cases})
    print(json.dumps(checks), flush=True)
    if not all(checks.values()):
        raise RuntimeError("Directed C83 fixture non-validated; see engine.log")

if __name__ == "__main__":
    main()
