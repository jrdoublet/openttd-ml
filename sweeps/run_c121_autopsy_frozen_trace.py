#!/usr/bin/env python3
"""Run post-success AIR decision traces from an immutable frozen campaign bundle.

The source used by the game is copied from the named frozen bundle.  The only
test-only changes are: enable C121_AUTOPSY_TEST_ONLY and append a K_pass/built
count log *after* the first AIR construction has already succeeded physically.
No trace work runs before that successful build.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil

from openttdlab import local_folder, run_experiments

from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg
from run_c121_air_economics_shadow import cached_bananas_ai_library


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
AUTOPSY_RE = re.compile(r"C121_AUTOPSY\s+(.*)$", re.MULTILINE)
C121_BUILD_RE = re.compile(r"C121_BUILD\s+(.*)$", re.MULTILINE)
AIR_PLAN_RE = re.compile(r"AIR_PLAN_PERF:?\s+(.*)$", re.MULTILINE)


def parse_fields(text: str) -> dict:
    out = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass
        out[key] = value
    return out


def keep_final(row):
    experiment = row.get("experiment") or {}
    start = date(1970, 1, 1)
    final = start + timedelta(days=int(experiment.get("days", 0) or 0))
    try:
        current = date.fromisoformat(str(row.get("date", ""))[:10])
    except ValueError:
        return ()
    if current < final - timedelta(days=31) or current > final:
        return ()
    output = row.get("output", "") or ""
    lower = output.lower()
    route_lines = []
    for line in output.splitlines():
        if ("Start Build AirRoute" in line
                or "Build succeeded(TestMode) AirStation" in line
                or ("BuildStation failed" in line and "AirStation" in line)
                or ("BuildExec failed" in line and "AirRoute" in line)):
            route_lines.append(line)
    return ({
        "seed": experiment.get("seed"),
        "policy_id": experiment.get("policy_id"),
        "date": str(row.get("date")),
        "autopsy": [parse_fields(x) for x in AUTOPSY_RE.findall(output)],
        "c121_builds": [parse_fields(x) for x in C121_BUILD_RE.findall(output)],
        "air_plan_perf": [parse_fields(x) for x in AIR_PLAN_RE.findall(output)],
        "air_build_trace": route_lines[:80],
        "script_error": "script died unexpectedly" in lower or "script error" in lower,
        "output_tail": output[-12000:],
    },)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_source(bundle: Path, destination: Path) -> dict:
    src = bundle / "ai" / "OpexAI"
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copytree(src, destination)

    selection = destination / "projects_selection.nut"
    text = selection.read_text(encoding="utf-8")
    gate = "const C121_AUTOPSY_TEST_ONLY = 0;"
    if text.count(gate) != 1:
        raise RuntimeError("autopsy gate not found exactly once")
    selection.write_text(text.replace(gate, "const C121_AUTOPSY_TEST_ONLY = 1;", 1), encoding="utf-8")

    task = destination / "task_projects.nut"
    text = task.read_text(encoding="utf-8")
    needle = """      if (attempt.outcome == \"built\") {\n        if (c121FirstYearAirBatch) {"""
    replacement = """      if (attempt.outcome == \"built\") {\n        if (C121_AUTOPSY_TEST_ONLY && !C121_AUTOPSY_DONE) {\n          local autopsyKPass = c75KPassData != null ? c75KPassData.K_pass : 0;\n          OpexC121AutopsyLog(\"PASS\", \"rank=\" + i + \" built_before=\" + liveBuiltCount\n              + \" k_pass=\" + autopsyKPass\n              + \" k_pass_active=\" + ((C75_MULTI_BUILD && liveBuiltCount > 0) ? 1 : 0));\n        }\n        if (c121FirstYearAirBatch) {"""
    if text.count(needle) != 1:
        raise RuntimeError("AIR built insertion point not found exactly once")
    task.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
    return {
        "selection_sha256": sha256(selection),
        "task_projects_sha256": sha256(task),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=(42, 100, 999))
    parser.add_argument("--years", type=int, default=1)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.workers <= 3:
        parser.error("workers must be 1..3 for this diagnostic")

    baseline = args.baseline.resolve()
    payload = json.loads(baseline.read_text(encoding="utf-8"))
    bundle = ROOT / "results" / f"{payload['campaign_id']}_bundle"
    if not bundle.is_dir():
        raise FileNotFoundError(bundle)
    policies = payload.get("policies") or []
    if len(policies) != 2:
        raise RuntimeError("expected two frozen policies")

    source_dir = args.out.with_suffix("")
    source_dir = source_dir.parent / (source_dir.name + "_source")
    source_meta = prepare_source(bundle, source_dir)
    enable_savegame_cleanup()

    cfg = make_cfg(1970)
    experiments = []
    for policy in policies:
        settings = tuple((str(k), int(v)) for k, v in policy.get("explicit_settings", []))
        opex = local_folder(str(source_dir), "OpexAI", settings)
        hogex = local_folder(str(bundle / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
        for seed in args.seeds:
            experiments.append({
                "policy_id": policy["id"],
                "seed": seed,
                "days": 365 * args.years,
                "openttd_config": cfg,
                "ais": (opex, hogex),
            })

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.workers,
        result_processor=keep_final,
        ai_libraries=(
            cached_bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            cached_bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    latest = {}
    for row in rows:
        key = (row.get("policy_id"), row.get("seed"))
        if key not in latest or row.get("date", "") > latest[key].get("date", ""):
            latest[key] = row
    final_rows = [latest[key] for key in sorted(latest)]
    result = {
        "purpose": "post-success autopsy trace from immutable baseline bundle",
        "baseline": str(baseline),
        "baseline_campaign": payload["campaign_id"],
        "baseline_source_bundle_sha256": payload.get("source_bundle_sha256"),
        "instrumentation": "compile-time copy; first AIR post-success only",
        "source_meta": source_meta,
        "seeds": args.seeds,
        "years": args.years,
        "rows": final_rows,
        "health": {
            "expected": len(policies) * len(args.seeds),
            "observed": len(final_rows),
            "script_errors": sum(bool(row.get("script_error")) for row in final_rows),
            "rows_with_autopsy": sum(bool(row.get("autopsy")) for row in final_rows),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"health": result["health"], "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
