"""C67.5 water graph diagnostic: contract fixture plus real-map comparison.

Derived from diag_c67_terrain.py: exact production sources are frozen into a unique
fixture folder (water_graph.nut, terrain_map.nut, budget.nut, builder_water.nut), the
bench_v2 configuration/runtime/cleanup are reused and game_health checks logs and
checkpoints. `-d script=4` is injected to collect the per-pair AILog lines.

For each (map size, seed): synthetic adverse and random tests against an exhaustive BFS,
then 200 deterministic water-tile pairs compared between the bounded oracle, an exact
whole-map labelling and the current builder predicate (OpexWaterFindConnection).
No economic claim: WaterGraphProbe does not transport anything.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics

from game_health import (
    checkpoint_reaches, expected_last_checkpoint, inspect_checkpoints,
    parse_script_errors, engine_failure_from_records,
)

ROOT = Path(__file__).resolve().parents[1]
NAME = "WaterGraphProbe"
PASS_SIGN = "C675|PASS"
LINE_RE = re.compile(r"(C675_[A-Z_]+)((?: [a-z_]+=[^ \n]+)*)")


def stage_fixture(destination: Path, root: Path = ROOT) -> dict:
    destination.mkdir(parents=True, exist_ok=False)
    sources = {
        "main.nut": root / "sweeps/fixtures/WaterGraphProbe/main.nut",
        "info.nut": root / "sweeps/fixtures/WaterGraphProbe/info.nut",
        "water_graph.nut": root / "ai/OpexAI/water_graph.nut",
        "terrain_map.nut": root / "ai/OpexAI/terrain_map.nut",
        "budget.nut": root / "ai/OpexAI/budget.nut",
        "builder_water.nut": root / "ai/OpexAI/builder_water.nut",
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
    passed = any(isinstance(s, dict) and s.get("name") == PASS_SIGN for s in signs)
    return ({
        "run": row["experiment"]["bench_run"], "date": str(row.get("date", "")),
        "passed": passed, "output": row.get("output") or "",
        "engine_failure": row.get("engine_failure"),
    },)


def parse_lines(output: str) -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = {}
    for match in LINE_RE.finditer(output or ""):
        fields = {}
        for item in match.group(2).split():
            key, value = item.split("=", 1)
            try:
                fields[key] = int(value)
            except ValueError:
                fields[key] = value
        found.setdefault(match.group(1), []).append(fields)
    return found


def summarise_pairs(pairs: list[dict]) -> dict:
    if not pairs:
        return {"pairs": 0}
    exact_conn = [p for p in pairs if p["exact"] == 1]
    oracle = Counter(p["oracle"] for p in pairs)
    unknown_reasons = Counter(p["reason"] for p in pairs if p["oracle"] == "unknown")
    builder_found = [p for p in pairs if p["builder"] >= 0]
    corridor = [p for p in pairs if p["corridor"] == "found"]
    both = [p for p in corridor if p["builder"] >= 0]

    def spread(values):
        values = [v for v in values if v is not None]
        return None if not values else {"median": statistics.median(values),
                                        "max": max(values), "n": len(values)}
    return {
        "pairs": len(pairs), "exact_connected": len(exact_conn),
        "oracle": dict(oracle), "unknown_reasons": dict(unknown_reasons),
        "wrong": sum(p["wrong"] for p in pairs),
        "builder_found": len(builder_found),
        "builder_false_reject": sum(1 for p in exact_conn if p["builder"] < 0),
        "builder_false_accept": sum(1 for p in pairs if p["builder"] >= 0 and p["exact"] == 0),
        "oracle_connected_builder_reject": sum(1 for p in pairs
                                               if p["oracle"] == "connected" and p["builder"] < 0),
        "corridor_found": len(corridor),
        "corridor_vs_builder": {"equal": sum(p["cdist"] == p["builder"] for p in both),
                                "longer": sum(p["cdist"] > p["builder"] for p in both),
                                "shorter": sum(p["cdist"] < p["builder"] for p in both)},
        "oracle_ops": spread([p["ops"] for p in pairs]),
        "oracle_blocks": spread([p["blocks"] for p in pairs]),
        "builder_ops": spread([p["builder_ops"] for p in pairs]),
        "corridor_ops": spread([p["cops"] for p in corridor]),
    }


def assess(records, run, years):
    checks = inspect_checkpoints(records, expected_companies=[NAME])
    logs = "\n".join(str(r.get("output") or "") for r in records)
    errors = parse_script_errors(logs, {0: {"company_id": 0, "name": NAME}})
    engine_failure = engine_failure_from_records(records)
    dates = sorted(str(r.get("date", "")) for r in records)
    horizon = bool(dates and checkpoint_reaches(dates[-1], expected_last_checkpoint(1970, years)))
    passed = bool(records) and any(r.get("passed") for r in records if str(r.get("date")) == dates[-1])
    identity_ok = all(r.get("run") == run for r in records)
    ok = (passed and horizon and identity_ok and not checks["duplicates"]
          and not checks["missing_companies"] and not errors["attributed"]
          and not errors["unattributed"] and not errors["engine_marker"] and not engine_failure)
    return {"ok": bool(ok), "fixture_pass": passed, "horizon_complete": horizon,
            "identity_ok": identity_ok, "checkpoints": len(records), "script_errors": errors,
            "engine_failure": engine_failure, "economic_validation": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999])
    parser.add_argument("--map-sizes", nargs="+", type=int, default=[8])
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    if not Path("/work").is_dir():
        parser.error("Run inside canonical openttd-lab Docker with the repository mounted at /work")
    if args.out.exists() or args.out.with_suffix(".jsonl").exists():
        parser.error("Output already exists; choose a unique name")
    if any(s not in (8, 9, 10, 11) for s in args.map_sizes) or not 1 <= args.years <= 8:
        parser.error("map sizes 8..11, years 1..8")
    import bench_v2
    import openttdlab
    from game_health import enable_engine_failure_capture
    from openttdlab import local_folder, run_experiments

    real = openttdlab.subprocess.check_output

    def with_script_log(cmd, *rest, **kwargs):
        cmd = tuple(cmd)
        if any(str(a).startswith("-vnull") for a in cmd):
            cmd = cmd[:1] + ("-d", "script=4") + cmd[1:]
        return real(cmd, *rest, **kwargs)

    bundle = args.out.with_name(args.out.stem + "_fixture")
    manifest = stage_fixture(bundle)
    arm = local_folder(str(bundle.resolve()), NAME, ())
    experiments = []
    for size in args.map_sizes:
        config = bench_v2.make_cfg(1970, size)
        for seed in args.seeds:
            experiments.append({"seed": seed, "days": 365 * args.years, "openttd_config": config,
                                "ais": (arm,), "bench_run": [NAME, seed, size]})
    bench_v2.enable_savegame_cleanup()
    enable_engine_failure_capture()
    openttdlab.subprocess.check_output = with_script_log
    try:
        rows = list(run_experiments(
            openttd_version=bench_v2.OPENTTD_VERSION, opengfx_version=bench_v2.OPENGFX_VERSION,
            max_workers=args.max_workers, result_processor=keep, ai_libraries=(),
            experiments=experiments,
        ))
    finally:
        openttdlab.subprocess.check_output = real
    args.out.with_suffix(".jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    runs = []
    for exp in experiments:
        records = sorted((r for r in rows if r["run"] == exp["bench_run"]), key=lambda r: r["date"])
        verdict = assess(records, exp["bench_run"], args.years)
        lines = parse_lines(records[-1]["output"] if records else "")
        runs.append({"seed": exp["bench_run"][1], "map_size": exp["bench_run"][2],
                     "assessment": verdict,
                     "markers": sorted(k for k in lines if k.endswith("PASS")),
                     "random": (lines.get("C675_RANDOM_PASS") or [None])[0],
                     "map": (lines.get("C675_MAP") or [None])[0],
                     "graph": (lines.get("C675_GRAPH") or [None])[0],
                     "pairs": summarise_pairs(lines.get("C675_PAIR", []))})
    all_pairs = []
    for exp in experiments:
        records = sorted((r for r in rows if r["run"] == exp["bench_run"]), key=lambda r: r["date"])
        all_pairs += parse_lines(records[-1]["output"] if records else "").get("C675_PAIR", [])
    payload = {"kind": "C67.5 water graph diagnostic", "openttd_version": bench_v2.OPENTTD_VERSION,
               "opengfx_version": bench_v2.OPENGFX_VERSION, "years": args.years,
               "sources": manifest, "runs": runs, "pooled": summarise_pairs(all_pairs),
               "ok": all(r["assessment"]["ok"] for r in runs)}
    bench_v2.write_json_atomically(args.out, payload)
    print(json.dumps({"ok": payload["ok"], "pooled": payload["pooled"],
                      "runs": [{k: r[k] for k in ("seed", "map_size", "markers", "map", "graph")}
                               | {"ok": r["assessment"]["ok"]} for r in runs]}, indent=2))
    if not payload["ok"]:
        raise SystemExit("C67.5 diagnostic incomplete or failed; inspect JSON")


if __name__ == "__main__":
    main()
