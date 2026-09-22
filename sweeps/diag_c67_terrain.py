"""C67.2 isolated 1 seed x 1 year contract smoke, not the C67.3 performance bench.

Reuse bench_v2 configuration, runtime pins and cleanup; game_health checks logs and
checkpoints. A non-transport fixture deliberately has no economic activity to assess.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from game_health import (
    checkpoint_reaches, expected_last_checkpoint, inspect_checkpoints,
    parse_script_errors, engine_failure_from_records,
)

ROOT = Path(__file__).resolve().parents[1]
NAME = "TerrainMapProbe"


def stage_fixture(destination: Path, root: Path = ROOT) -> dict:
    """Freeze exact sources, never copy production code into the versioned fixture."""
    destination.mkdir(parents=True, exist_ok=False)
    sources = {
        "main.nut": root / "sweeps/fixtures/TerrainMapProbe/main.nut",
        "info.nut": root / "sweeps/fixtures/TerrainMapProbe/info.nut",
        "terrain_map.nut": root / "ai/OpexAI/terrain_map.nut",
        "budget.nut": root / "ai/OpexAI/budget.nut",
    }
    manifest = {}
    for name, source in sources.items():
        shutil.copyfile(source, destination / name)
        manifest[name] = hashlib.sha256((destination / name).read_bytes()).hexdigest()
    (destination / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def keep(row):
    signs = (row.get("chunks") or {}).get("SIGN") or {}
    signs = signs.values() if isinstance(signs, dict) else signs
    passed = any(isinstance(s, dict) and s.get("name") == "C67|PASS" for s in signs)
    return ({
        "run": row["experiment"]["bench_run"], "date": str(row.get("date", "")),
        "passed": passed, "output": row.get("output") or "",
        "engine_failure": row.get("engine_failure"),
    },)


def assess(records):
    checks = inspect_checkpoints(records, expected_companies=[NAME])
    logs = "\n".join(str(r.get("output") or "") for r in records)
    errors = parse_script_errors(logs, {0: {"company_id": 0, "name": NAME}})
    engine_failure = engine_failure_from_records(records)
    dates = sorted(str(r.get("date", "")) for r in records)
    horizon = bool(dates and checkpoint_reaches(dates[-1], expected_last_checkpoint(1970, 1)))
    # A last-month pass marker proves the fixture completed, not just started.
    passed = bool(records) and any(r.get("passed") for r in records if str(r.get("date")) == dates[-1])
    # Same monthly coverage convention as bench_v2; duplicates do not fill gaps.
    monthly = {date[:7] for date in dates if date.startswith("1970-")}
    coverage = monthly == {f"1970-{month:02d}" for month in range(1, 13)}
    identity_ok = all(r.get("run") == [NAME, 42, 0] for r in records)
    ok = (passed and horizon and coverage and identity_ok and not checks["duplicates"]
          and not checks["missing_companies"] and not errors["attributed"]
          and not errors["unattributed"] and not errors["engine_marker"] and not engine_failure)
    return {"ok": bool(ok), "fixture_pass": passed, "horizon_complete": horizon,
            "monthly_coverage": len(monthly), "identity_ok": identity_ok,
            "checkpoints": checks, "script_errors": errors,
            "engine_failure": engine_failure, "economic_validation": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not Path("/work").is_dir():
        parser.error("Run inside canonical openttd-lab Docker with the repository mounted at /work")
    if args.out.exists() or args.out.with_suffix(".jsonl").exists():
        parser.error("Output already exists; choose a unique name")
    # Import only for engine execution: host tests cover staging/collection without the runtime.
    import bench_v2
    from game_health import enable_engine_failure_capture
    from openttdlab import local_folder, run_experiments

    bundle = args.out.with_name(args.out.stem + "_fixture")
    manifest = stage_fixture(bundle)
    arm = local_folder(str(bundle.resolve()), NAME, ())
    config = bench_v2.make_cfg(1970, 8)
    bench_v2.enable_savegame_cleanup()
    enable_engine_failure_capture()
    rows = list(run_experiments(
        openttd_version=bench_v2.OPENTTD_VERSION, opengfx_version=bench_v2.OPENGFX_VERSION,
        max_workers=1, result_processor=keep, ai_libraries=(),
        experiments=[{"seed": 42, "days": 365, "openttd_config": config,
                      "ais": (arm,), "bench_run": [NAME, 42, 0]}],
    ))
    args.out.with_suffix(".jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    verdict = assess(rows)
    bench_v2.write_json_atomically(args.out, {
        "kind": "C67.2 contract smoke", "openttd_version": bench_v2.OPENTTD_VERSION,
        "opengfx_version": bench_v2.OPENGFX_VERSION, "seed": 42, "years": 1,
        "sources": manifest, "config": config, "assessment": verdict,
    })
    print(json.dumps(verdict, indent=2))
    if not verdict["ok"]:
        raise SystemExit("C67 fixture smoke incomplete or failed")


if __name__ == "__main__":
    main()
