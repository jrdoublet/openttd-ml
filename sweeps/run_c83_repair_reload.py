"""Bounded technical reload using save_load_roundtrip, with a unique workspace."""
from __future__ import annotations
import argparse
import inspect
import json
from pathlib import Path
import sys
from .run_mechanism_fixtures import tree_hashes, write

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    folder = args.out.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    import openttdlab
    from . import save_load_roundtrip as driver
    root = Path(__file__).resolve().parents[1]
    before = tree_hashes(root / "ai/OpexAI")
    driver.ROOT = root
    driver.WORK_DIR = folder / "work"
    driver.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    write(folder / "plan.json", {"category": "technical_reload_not_economic", "source_hashes": before,
                                "arm": "OpexAI[c83_local_repair=1,save_full_state=1]", "seed": 100})
    sys.argv = ["save_load_roundtrip.py", "--seed", "100", "--years-a", "1", "--years-b", "1",
                "--arm", "OpexAI[c83_local_repair=1,save_full_state=1]", "--out", str(folder / "report.json")]
    driver.main()
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    checks = {"status_ok": report["status"] == "OK", "sources_unchanged": before == tree_hashes(root / "ai/OpexAI"),
              "load_called": report["load_call_proof"]["positive_ai_marker_exists"],
              "no_errors": all(not report[phase][key] for phase in ("phase_a", "phase_b")
                               for key in ("markers_found", "engine_failure_markers_found"))}
    write(folder / "checks.json", checks)
    if not all(checks.values()):
        raise RuntimeError("C83 reload not validated")

if __name__ == "__main__":
    main()
