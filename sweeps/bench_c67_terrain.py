"""C67.3 technical benchmark: paired control, 5x5 and 10x10 terrain probes.

The production map module is copied byte-for-byte into a frozen fixture. Engine,
configuration, save cleanup and RSS process sampler come from current sweep helpers.
This measures a diagnostic AI only; it is not evidence of OpexAI economic benefit.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import time

import bench_v2
import diag_water_memory as memory
from diag_c67_terrain import ROOT
from game_health import (
    expected_last_checkpoint, checkpoint_reaches, inspect_checkpoints,
    parse_script_errors, engine_failure_from_records,
)

NAME = "TerrainBenchProbe"
ARMS = (0, 5, 10)
PHASES = ("meta", "init", "cold", "warm", "scan", "evict", "invalidate")
SIGN_RE = re.compile(r"^C67\|([a-z]+)\|([a-z]+)\|(-?\d+)$")


def stage_fixture(destination: Path, root: Path = ROOT) -> dict[str, str]:
    destination.mkdir(parents=True, exist_ok=False)
    sources = {
        "main.nut": root / "sweeps/fixtures/TerrainBenchProbe/main.nut",
        "info.nut": root / "sweeps/fixtures/TerrainBenchProbe/info.nut",
        "terrain_map.nut": root / "ai/OpexAI/terrain_map.nut",
        "budget.nut": root / "ai/OpexAI/budget.nut",
    }
    manifest = {}
    for name, path in sources.items():
        shutil.copyfile(path, destination / name)
        manifest[name] = hashlib.sha256((destination / name).read_bytes()).hexdigest()
    (destination / "sources.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def trace_points(width: int, height: int) -> list[tuple[int, int]]:
    return [((i * 97 + 13) % width, (i * 193 + 29) % height) for i in range(64)]


def parse_signs(chunks: dict) -> dict[str, dict[str, int]]:
    signs = (chunks or {}).get("SIGN") or {}
    entries = signs.values() if isinstance(signs, dict) else signs
    found: dict[str, dict[str, int]] = defaultdict(dict)
    for sign in entries:
        if not isinstance(sign, dict):
            continue
        match = SIGN_RE.fullmatch(str(sign.get("name", "")))
        if match and match.group(1) in PHASES:
            phase, key, raw = match.groups()
            value = int(raw)
            if key in found[phase] and found[phase][key] != value:
                raise ValueError(f"conflicting C67 sign: {phase}/{key}")
            found[phase][key] = value
    return dict(found)


def keep(row):
    arm, seed, repeat, size = row["experiment"]["bench_run"]
    record = {
        "arm": arm, "seed": seed, "repeat": repeat, "map_size": size,
        "run": [NAME, seed, repeat, size, arm], "date": str(row["date"]),
        "signs": parse_signs(row.get("chunks") or {}),
        "output": row.get("output") or "", "error": bool(row.get("error")),
        "engine_failure": row.get("engine_failure"),
    }
    bench_v2.append_checkpoint(record)
    return (record,)


def assess_run(records: list[dict], arm: int, seed: int, repeat: int, size: int,
               full: bool, years: int = 1) -> dict:
    records = sorted(records, key=lambda r: r["date"])
    identity = all((r["arm"], r["seed"], r["repeat"], r["map_size"])
                   == (arm, seed, repeat, size) for r in records)
    dates = [r["date"] for r in records]
    months = {d[:7] for d in dates if "1970-" <= d[:7] <= f"{1969 + years}-12"}
    horizon = bool(dates and checkpoint_reaches(dates[-1], expected_last_checkpoint(1970, years)))
    checks = inspect_checkpoints(records, expected_companies=[NAME])
    logs = "\n".join(r.get("output") or "" for r in records)
    errors = parse_script_errors(logs, {0: {"company_id": 0, "name": NAME}})
    final = records[-1]["signs"] if records else {}
    meta = final.get("meta", {})
    required = {"side", "full", "width", "height", "finger", "pass"}
    if arm:
        required_phases = {"cold", "warm", "init"}
        if full:
            required_phases |= {"scan", "evict", "invalidate"}
    else:
        required_phases = set()
    complete = required.issubset(meta) and required_phases.issubset(final)
    if arm:
        complete = complete and final.get("cold", {}).get("errors") == 0
        complete = complete and final.get("cold", {}).get("oracle") == 16
        complete = complete and final.get("init", {}).get("reads") == 0
        complete = complete and final.get("warm", {}).get("reads") == 0
        complete = complete and final.get("cold", {}).get("max", 0) <= 10000
        if full:
            complete = complete and final.get("scan", {}).get("blocks") == (
                ((1 << size) + arm - 1) // arm) ** 2
            complete = complete and final.get("scan", {}).get("resident", 99999) <= 4096
            complete = complete and final.get("scan", {}).get("max", 99999) <= 10000
            complete = complete and final.get("invalidate", {}).get("ready") == 1
    expected_months = {f"{year}-{month:02d}" for year in range(1970, 1970 + years)
                       for month in range(1, 13)}
    ok = (identity and horizon and months == expected_months
          and not checks["duplicates"] and not checks["missing_companies"] and complete
          and meta.get("pass") == 1 and meta.get("side") == arm
          and meta.get("full") == int(full) and meta.get("width") == 1 << size
          and meta.get("height") == 1 << size and not errors["attributed"]
          and not errors["unattributed"] and not errors["engine_marker"]
          and not engine_failure_from_records(records) and not any(r["error"] for r in records))
    return {"ok": bool(ok), "identity": identity, "horizon": horizon,
            "months": len(months), "checkpoints": len(records), "complete": bool(complete),
            "signs": final, "script_errors": errors,
            "engine_failure": engine_failure_from_records(records)}


def summarise(rows: list[dict], raw: list[dict], *, sizes: list[int], seeds: list[int],
              repeats: int, full: bool, years: int = 1) -> dict:
    grouped: dict[tuple[int, int, int, int], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["map_size"], row["seed"], row["repeat"], row["arm"])].append(row)
    process = {}
    for entry in raw:
        key = (entry.get("map_size"), entry.get("seed"), entry.get("repeat"),
               entry.get("probe_allocate"))
        if key in process:
            raise ValueError(f"duplicate process record: {key}")
        process[key] = entry
    assessments = {}
    paired = []
    for size in sizes:
        for seed in seeds:
            for repeat in range(repeats):
                arms = {}
                for arm in ARMS:
                    key = (size, seed, repeat, arm)
                    status = assess_run(grouped.get(key, []), arm, seed, repeat, size, full, years)
                    rss = process.get(key)
                    status["process_memory_kib"] = (rss or {}).get("process_memory_kib")
                    status["returncode"] = (rss or {}).get("returncode")
                    if rss is None or rss.get("returncode") != 0:
                        status["ok"] = False
                    assessments[str(key)] = status
                    arms[arm] = status
                fingerprints = [arms[a]["signs"].get("meta", {}).get("finger") for a in ARMS]
                common = None not in fingerprints and len(set(fingerprints)) == 1
                for arm in (5, 10):
                    variant = arms[arm]
                    control = arms[0]
                    pm = variant["process_memory_kib"] or {}
                    cm = control["process_memory_kib"] or {}
                    delta_kib = (pm.get("max_rss_kib") - cm.get("max_rss_kib")
                                 if pm.get("max_rss_kib") is not None
                                 and cm.get("max_rss_kib") is not None else None)
                    if not common:
                        variant["ok"] = False
                    paired.append({"size": size, "seed": seed, "repeat": repeat,
                                   "side": arm, "inputs_match": common,
                                   "valid": control["ok"] and variant["ok"] and common,
                                   "peak_rss_delta_kib": delta_kib,
                                   "cold": variant["signs"].get("cold"),
                                   "warm": variant["signs"].get("warm"),
                                   "scan": variant["signs"].get("scan")})
    valid = [p for p in paired if p["valid"]]
    by_side = {}
    for side in (5, 10):
        values = [p["peak_rss_delta_kib"] for p in valid
                  if p["side"] == side and p["peak_rss_delta_kib"] is not None]
        by_side[str(side)] = {"valid_pairs": sum(p["side"] == side for p in valid),
                             "peak_rss_delta_kib_median": statistics.median(values) if values else None,
                             "peak_rss_delta_kib_max": max(values) if values else None}
    return {"expected_runs": len(sizes) * len(seeds) * repeats * 3,
            "process_records": len(raw), "assessments": assessments,
            "pairs": paired, "by_side": by_side,
            "complete": len(raw) == len(sizes) * len(seeds) * repeats * 3
                        and len(valid) == len(sizes) * len(seeds) * repeats * 2}


def selftest():
    assert trace_points(256, 256)[0] == (13, 29)
    assert len(set(trace_points(256, 256))) == 64
    parsed = parse_signs({"SIGN": {1: {"name": "C67|cold|ops|123"},
                                   2: {"name": "C67|meta|pass|1"}}})
    assert parsed == {"cold": {"ops": 123}, "meta": {"pass": 1}}
    try:
        parse_signs({"SIGN": [{"name": "C67|cold|ops|1"}, {"name": "C67|cold|ops|2"}]})
    except ValueError:
        pass
    else:
        raise AssertionError("conflicting signs accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--map-sizes", nargs="+", type=int, default=[8, 9, 10, 11])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--full", type=int, choices=[0, 1], default=1)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        print("C67 benchmark selftest OK")
        return
    if not Path("/work").is_dir():
        parser.error("Run inside canonical openttd-lab Docker with repository at /work")
    if any(size not in (8, 9, 10, 11) for size in args.map_sizes):
        parser.error("map sizes must be 8..11")
    if args.repeats < 1 or args.days not in (365, 2920):
        parser.error("C67.3 uses >=1 repeat and a declared one- or eight-year horizon")
    bundle = args.out.with_name(args.out.stem + "_fixture")
    raw_dir = args.out.with_name(args.out.stem + "_raw")
    jsonl = args.out.with_suffix(".jsonl")
    if any(path.exists() for path in (args.out, bundle, raw_dir, jsonl)):
        parser.error("output or associated artifact exists; choose a new campaign name")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    manifest = stage_fixture(bundle)
    raw_dir.mkdir()
    bench_v2.CHECKPOINT_PATH = jsonl
    memory._MEMORY_DIR = raw_dir
    memory._RUN_TOKEN = f"c67_{time.time_ns()}"
    from openttdlab import local_folder, run_experiments
    import openttdlab
    arms = {side: local_folder(str(bundle.resolve()), NAME,
                               (("allocate", side), ("full", args.full))) for side in ARMS}
    experiments = []
    for size in args.map_sizes:
        cfg = bench_v2.make_cfg(1970, size)
        for seed in args.seeds:
            for repeat in range(args.repeats):
                order = ARMS[repeat % 3:] + ARMS[:repeat % 3]
                for side in order:
                    experiments.append({"seed": seed, "days": args.days,
                                        "openttd_config": cfg, "ais": (arms[side],),
                                        "bench_run": [side, seed, repeat, size]})
    manifest_run = {"schema": "c67-terrain-v1", "source_hashes": manifest,
                    "sizes": args.map_sizes, "seeds": args.seeds, "repeats": args.repeats,
                    "days": args.days, "full": bool(args.full),
                    "experiment_order": [exp["bench_run"] for exp in experiments],
                    "trace_points": {str(size): trace_points(1 << size, 1 << size)
                                     for size in args.map_sizes},
                    "openttd_version": bench_v2.OPENTTD_VERSION,
                    "opengfx_version": bench_v2.OPENGFX_VERSION}
    args.out.with_name(args.out.stem + "_manifest.json").write_text(
        json.dumps(manifest_run, indent=2) + "\n", encoding="utf-8")
    original = openttdlab.subprocess.check_output
    try:
        openttdlab.subprocess.check_output = memory._memory_check_output
        bench_v2.enable_savegame_cleanup()
        rows = list(run_experiments(
            openttd_version=bench_v2.OPENTTD_VERSION,
            opengfx_version=bench_v2.OPENGFX_VERSION,
            max_workers=1, result_processor=keep, experiments=experiments,
            ai_libraries=(),
        ))
    finally:
        openttdlab.subprocess.check_output = original
    raw = []
    for path in sorted(raw_dir.glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if item.get("run_token") != memory._RUN_TOKEN:
            continue
        idx = item.get("experiment_index")
        if idx is None or idx < 0 or idx >= len(experiments):
            raise RuntimeError(f"unmapped process record: {path}")
        side, seed, repeat, size = experiments[idx]["bench_run"]
        if (item.get("seed"), item.get("probe_allocate"), item.get("map_size")) != (seed, side, size):
            raise RuntimeError(f"process identity mismatch: {path}")
        item.update({"arm": side, "repeat": repeat})
        raw.append(item)
    summary = summarise(rows, raw, sizes=args.map_sizes, seeds=args.seeds,
                        repeats=args.repeats, full=bool(args.full), years=args.days // 365)
    bench_v2.write_json_atomically(args.out, {"manifest": manifest_run, "summary": summary})
    print(json.dumps({k: v for k, v in summary.items() if k not in ("assessments", "pairs")},
                     indent=2))
    if not summary["complete"]:
        raise SystemExit("C67 benchmark incomplete or invalid; inspect JSON")


if __name__ == "__main__":
    main()
