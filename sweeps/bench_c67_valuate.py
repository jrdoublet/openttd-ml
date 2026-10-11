"""C67 Valuate terrain reader benchmark and verification harness.

Measures:
  (a) Exactitude of Valuate reader against reference tile-by-tile reader (5x5 and 10x10)
  (b) Opcode cost comparison (reference vs Valuate)
  (c) Non-suspendable bound (maximum opcode cost of an atomic call)

Contract: docs/c67_cartographie_contrat.md
No economic consumer; diagnostic AI only.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

NAME = "TerrainValuateProbe"
PASS_SIGN = "C67V|PASS"
SIGN_RE = re.compile(r"^C67V\|([A-Z0-9_]+)\|([A-Z0-9_]+)\|(-?\d+)$")
LOG_SUMMARY_RE = re.compile(
    r"C67V_SUMMARY\s+side=(?P<side>\d+)\s+blocks=(?P<blocks>\d+)\s+errors=(?P<errors>\d+)\s+"
    r"ref_total=(?P<ref_total>\d+)\s+val_total=(?P<val_total>\d+)\s+"
    r"ref_mean=(?P<ref_mean>\d+)\s+val_mean=(?P<val_mean>\d+)\s+"
    r"max_single=(?P<max_single>\d+)\s+max_block=(?P<max_block>\d+)\s+"
    r"saving_pct=(?P<saving_pct>-?\d+)"
)


def stage_fixture(destination: Path, root: Path = ROOT) -> dict[str, str]:
    destination.mkdir(parents=True, exist_ok=False)
    sources = {
        "main.nut": root / "sweeps/fixtures/TerrainValuateProbe/main.nut",
        "info.nut": root / "sweeps/fixtures/TerrainValuateProbe/info.nut",
        "terrain_valuate.nut": root / "ai/OpexAI/terrain_valuate.nut",
        "terrain_map.nut": root / "ai/OpexAI/terrain_map.nut",
        "budget.nut": root / "ai/OpexAI/budget.nut",
    }
    manifest = {}
    for name, path in sources.items():
        shutil.copyfile(path, destination / name)
        manifest[name] = hashlib.sha256((destination / name).read_bytes()).hexdigest()
    (destination / "sources.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def parse_signs(chunks: dict) -> tuple[dict[str, dict[str, int]], bool]:
    signs = (chunks or {}).get("SIGN") or {}
    entries = signs.values() if isinstance(signs, dict) else signs
    found: dict[str, dict[str, int]] = defaultdict(dict)
    passed = False
    for sign in entries:
        if not isinstance(sign, dict):
            continue
        text = str(sign.get("name", ""))
        if text == PASS_SIGN:
            passed = True
            continue
        match = SIGN_RE.fullmatch(text)
        if match:
            section, key, raw = match.groups()
            found[section][key] = int(raw)
    return dict(found), passed


def parse_logs(output: str) -> dict[int, dict[str, int]]:
    summaries: dict[int, dict[str, int]] = {}
    for match in LOG_SUMMARY_RE.finditer(output or ""):
        data = {k: int(v) for k, v in match.groupdict().items()}
        summaries[data["side"]] = data
    return summaries


def keep(row: dict) -> tuple[dict]:
    signs, passed = parse_signs(row.get("chunks") or {})
    return ({
        "run": row.get("experiment", {}).get("bench_run", [NAME, 42, 0]),
        "date": str(row.get("date", "")),
        "signs": signs,
        "passed": passed,
        "output": row.get("output") or "",
        "engine_failure": row.get("engine_failure"),
        "error": bool(row.get("error")),
    },)


def assess(records: list[dict], years: int = 1) -> dict:
    from game_health import (
        checkpoint_reaches, expected_last_checkpoint, inspect_checkpoints,
        parse_script_errors, engine_failure_from_records,
    )

    records = sorted(records, key=lambda r: str(r.get("date", "")))
    dates = [str(r.get("date", "")) for r in records]
    horizon = bool(dates and checkpoint_reaches(dates[-1], expected_last_checkpoint(1970, years)))
    checks = inspect_checkpoints(records, expected_companies=[NAME])
    logs = "\n".join(str(r.get("output") or "") for r in records)
    errors = parse_script_errors(logs, {0: {"company_id": 0, "name": NAME}})
    engine_failure = engine_failure_from_records(records)

    last_record = records[-1] if records else {}
    passed = any(r.get("passed") for r in records)
    signs = last_record.get("signs", {})

    log_summaries = parse_logs(logs)

    # Telemetry data extraction
    s5_signs = signs.get("S5", {})
    s10_signs = signs.get("S10", {})
    s5_log = log_summaries.get(5, {})
    s10_log = log_summaries.get(10, {})

    s5_blocks = s5_signs.get("BLOCKS", s5_log.get("blocks", 0))
    s5_errors = s5_signs.get("ERR", s5_log.get("errors", 999))
    s10_blocks = s10_signs.get("BLOCKS", s10_log.get("blocks", 0))
    s10_errors = s10_signs.get("ERR", s10_log.get("errors", 999))

    exactitude_pass = (s5_errors == 0 and s10_errors == 0 and s5_blocks > 0 and s10_blocks > 0)

    # Opcode costs
    s5_ref_mean = s5_signs.get("REF", s5_log.get("ref_mean", 0))
    s5_val_mean = s5_signs.get("VAL", s5_log.get("val_mean", 0))
    s10_ref_mean = s10_signs.get("REF", s10_log.get("ref_mean", 0))
    s10_val_mean = s10_signs.get("VAL", s10_log.get("val_mean", 0))

    opcode_saving_pass = (s5_val_mean > 0 and s5_val_mean < s5_ref_mean and
                          s10_val_mean > 0 and s10_val_mean < s10_ref_mean)

    # Non-suspendable bound check
    s5_max_call = s5_signs.get("MAX", s5_log.get("max_single", 0))
    s10_max_call = s10_signs.get("MAX", s10_log.get("max_single", 0))
    s5_max_block = s5_signs.get("BMAX", s5_log.get("max_block", 0))
    s10_max_block = s10_signs.get("BMAX", s10_log.get("max_block", 0))

    # All non-suspendable calls must be strictly <= 10 000 opcodes (tick limit)
    TICK_LIMIT = 10000
    bound_pass = (0 < s5_max_call <= TICK_LIMIT and
                  0 < s10_max_call <= TICK_LIMIT and
                  0 < s5_max_block <= TICK_LIMIT and
                  0 < s10_max_block <= TICK_LIMIT)

    monthly = {date[:7] for date in dates if date.startswith("1970-")}
    coverage = monthly == {f"1970-{month:02d}" for month in range(1, 13)}

    ok = bool(
        passed and horizon and coverage and not checks["duplicates"]
        and not checks["missing_companies"] and not errors["attributed"]
        and not errors["unattributed"] and not errors["engine_marker"]
        and not engine_failure and exactitude_pass and opcode_saving_pass and bound_pass
    )

    return {
        "ok": ok,
        "fixture_pass": passed,
        "exactitude": {
            "pass": exactitude_pass,
            "s5_blocks": s5_blocks,
            "s5_errors": s5_errors,
            "s10_blocks": s10_blocks,
            "s10_errors": s10_errors,
        },
        "opcodes": {
            "pass": opcode_saving_pass,
            "s5": {
                "ref_mean_ops": s5_ref_mean,
                "val_mean_ops": s5_val_mean,
                "saving_pct": s5_signs.get("PCT", s5_log.get("saving_pct", 0)),
            },
            "s10": {
                "ref_mean_ops": s10_ref_mean,
                "val_mean_ops": s10_val_mean,
                "saving_pct": s10_signs.get("PCT", s10_log.get("saving_pct", 0)),
            },
        },
        "non_suspendable_bound": {
            "pass": bound_pass,
            "tick_limit": TICK_LIMIT,
            "s5_max_single_call_ops": s5_max_call,
            "s5_max_block_ops": s5_max_block,
            "s10_max_single_call_ops": s10_max_call,
            "s10_max_block_ops": s10_max_block,
        },
        "coverage": len(monthly),
        "horizon": horizon,
        "script_errors": errors,
        "engine_failure": engine_failure,
    }


def run_selftest() -> None:
    # Test sign parsing
    chunks = {
        "SIGN": {
            1: {"name": "C67V|S5|BLOCKS|64"},
            2: {"name": "C67V|S5|ERR|0"},
            3: {"name": "C67V|S5|REF|2800"},
            4: {"name": "C67V|S5|VAL|390"},
            5: {"name": "C67V|S5|MAX|120"},
            6: {"name": "C67V|S5|BMAX|420"},
            7: {"name": "C67V|S5|PCT|86"},
            8: {"name": "C67V|S10|BLOCKS|64"},
            9: {"name": "C67V|S10|ERR|0"},
            10: {"name": "C67V|S10|REF|11200"},
            11: {"name": "C67V|S10|VAL|1180"},
            12: {"name": "C67V|S10|MAX|340"},
            13: {"name": "C67V|S10|BMAX|1250"},
            14: {"name": "C67V|S10|PCT|89"},
            15: {"name": "C67V|PASS"},
        }
    }
    signs, passed = parse_signs(chunks)
    assert passed, "PASS sign not found"
    assert signs["S5"]["ERR"] == 0
    assert signs["S10"]["ERR"] == 0
    assert signs["S5"]["VAL"] == 390

    # Test log parsing
    log_text = (
        "C67V_SUMMARY side=5 blocks=64 errors=0 ref_total=179200 val_total=24960 "
        "ref_mean=2800 val_mean=390 max_single=120 max_block=420 saving_pct=86\n"
        "C67V_SUMMARY side=10 blocks=64 errors=0 ref_total=716800 val_total=75520 "
        "ref_mean=11200 val_mean=1180 max_single=340 max_block=1250 saving_pct=89\n"
        "C67V_ALL_PASS\n"
    )
    logs = parse_logs(log_text)
    assert logs[5]["errors"] == 0
    assert logs[10]["val_mean"] == 1180

    # Test assess with synthetic records
    records = [
        {
            "run": [NAME, 42, 0],
            "date": f"1970-{m:02d}-01",
            "signs": signs,
            "passed": (m == 12),
            "output": log_text if m == 12 else "",
            "engine_failure": None,
            "error": False,
        }
        for m in range(1, 13)
    ]
    records.append({
        "run": [NAME, 42, 0],
        "date": "1971-01-01",
        "signs": signs,
        "passed": True,
        "output": log_text,
        "engine_failure": None,
        "error": False,
    })
    res = assess(records, years=1)
    assert res["ok"], f"assess failed on valid mock: {res}"
    assert res["exactitude"]["pass"]
    assert res["opcodes"]["pass"]
    assert res["non_suspendable_bound"]["pass"]
    print("selftest passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="Target JSON result file")
    parser.add_argument("--seed", type=int, default=42, help="World seed (default: 42)")
    parser.add_argument("--blocks", type=int, default=64, help="Blocks to sample per side (default: 64)")
    parser.add_argument("--years", type=int, default=1, help="Simulation horizon (default: 1 year)")
    parser.add_argument("--selftest", action="store_true", help="Run offline selftest")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if not args.out:
        parser.error("--out is required when not running --selftest")

    if not Path("/work").is_dir():
        parser.error("Run inside canonical openttd-lab Docker with the repository mounted at /work")

    if args.out.exists() or args.out.with_suffix(".jsonl").exists():
        parser.error(f"Output already exists: {args.out}")

    import bench_v2
    from game_health import enable_engine_failure_capture
    from openttdlab import local_folder, run_experiments

    bundle = args.out.with_name(args.out.stem + "_fixture")
    manifest = stage_fixture(bundle)
    arm = local_folder(str(bundle.resolve()), NAME, (("blocks", args.blocks),))
    config = bench_v2.make_cfg(1970, 8)
    bench_v2.enable_savegame_cleanup()
    enable_engine_failure_capture()

    days = args.years * 365
    rows = list(run_experiments(
        openttd_version=bench_v2.OPENTTD_VERSION,
        opengfx_version=bench_v2.OPENGFX_VERSION,
        max_workers=1,
        result_processor=keep,
        ai_libraries=(),
        experiments=[{
            "seed": args.seed,
            "days": days,
            "openttd_config": config,
            "ais": (arm,),
            "bench_run": [NAME, args.seed, 0],
        }],
    ))

    args.out.with_suffix(".jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    verdict = assess(rows, years=args.years)
    result_data = {
        "kind": "C67 Valuate terrain reader benchmark",
        "openttd_version": bench_v2.OPENTTD_VERSION,
        "opengfx_version": bench_v2.OPENGFX_VERSION,
        "seed": args.seed,
        "years": args.years,
        "blocks_per_side": args.blocks,
        "sources": manifest,
        "config": config,
        "assessment": verdict,
    }
    bench_v2.write_json_atomically(args.out, result_data)
    print(json.dumps(verdict, indent=2))
    if not verdict["ok"]:
        raise SystemExit("C67 Valuate fixture verification failed")


if __name__ == "__main__":
    main()
