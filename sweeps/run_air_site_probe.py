#!/usr/bin/env python3
"""Frozen solo diagnostic using bench_v2 collection, cleanup and health helpers.

Run inside the AGENTS.md Docker profile. One game per method and seed. Six years
only lets the 1975 pass finish; it adds no measurement date or construction.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = None
REAL_CHECK_OUTPUT = subprocess.check_output


def debug_checked(command, *args, **kwargs):
    command = tuple(command)
    if any(str(part).startswith("-vnull") for part in command):
        command = command[:1] + ("-d", "script=4") + command[1:]
    return REAL_CHECK_OUTPUT(command, *args, **kwargs)


def keep(row):
    import bench_v2 as bench
    from game_health import write_engine_log
    seed = row["experiment"]["seed"]
    method = row["experiment"]["bench_method"]
    write_engine_log(LOG_DIR / f"seed{seed}_{method}.log", row.get("output", ""))
    return bench.keep(row)


def company_records(rows, seed, method):
    """bench_run[0] identifies the method; health expects the company name there."""
    return [{**r, "run": ["OpexAI", *r["run"][1:]]}
            for r in rows if r["run"][1] == seed and r["run"][0] == method]


def evaluate(rows, seeds, years, log_dir):
    from diag_air_site_probe import METHODS, analyse, read_log, probe_health
    from game_health import assess_game
    health = {}
    for seed in seeds:
        for method in METHODS:
            log = log_dir / f"seed{seed}_{method}.log"
            health[f"{seed}:{method}"] = assess_game(company_records(rows, seed, method),
                starting_year=1970, years=years, expected_companies=("OpexAI",),
                slot_map={0: {"company_id": 0, "name": "OpexAI"}}, engine_log_path=str(log))
    analysis = analyse([read_log(log_dir / f"seed{seed}_{method}.log")
                        for seed in seeds for method in METHODS])
    return {"health": health, "analysis": analysis, "probe_health": probe_health(health, analysis, seeds, years)}


def run_worker(manifest_path):
    global LOG_DIR
    import bench_v2 as bench
    import openttdlab
    from openttdlab import local_folder, run_experiments
    from campaign_freeze import benchmark_opex_settings, _frozen_library_descriptor
    from game_health import enable_engine_failure_capture
    from diag_air_site_probe import METHODS

    manifest = json.loads(manifest_path.read_text())
    out = Path(manifest["out"])
    bundle = Path(manifest["bundle"])
    LOG_DIR = out.with_name(out.stem + "_engine")
    LOG_DIR.mkdir()
    bench.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    bench.enable_savegame_cleanup()
    enable_engine_failure_capture(timeout_sec=1200)
    openttdlab.subprocess.check_output = debug_checked
    libraries = tuple(_frozen_library_descriptor(item["requested_name"], item["resolved"], bundle / "libraries")
                      for item in manifest["libraries"])
    experiments = [{"seed": seed, "days": 365 * manifest["years"], "openttd_config": manifest["config"],
                    "ais": (local_folder(str(bundle / "OpexAI"), "OpexAI",
                        benchmark_opex_settings((("air_site_probe", index + 1),))),),
                    "bench_run": [method, seed, 0], "bench_method": method}
                   for seed in manifest["seeds"] for index, method in enumerate(METHODS)]
    rows = list(run_experiments(openttd_version=bench.OPENTTD_VERSION, opengfx_version=bench.OPENGFX_VERSION,
                               max_workers=3, result_processor=keep, experiments=experiments, ai_libraries=libraries))
    payload = {"manifest": str(manifest_path), **evaluate(rows, manifest["seeds"], manifest["years"], LOG_DIR),
               "seeds": manifest["seeds"], "years": manifest["years"], "ai_fingerprint": manifest["ai_fingerprint"],
               "series": [{k: v for k, v in r.items() if k != "openttd_output"} for r in rows]}
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"out": str(out), "probe_health": payload["probe_health"],
                      "comparisons": payload["analysis"]["comparisons"],
                      "truncated": [p for p in payload["analysis"]["passes"] if p["truncated"]]}, indent=2))
    if not payload["probe_health"]["smoke_ok"]:
        raise SystemExit(2)


def freeze(args):
    import bench_v2 as bench
    from campaign_freeze import fingerprint_tree, freeze_bananas_libraries, git_state
    from campaign_freeze import effective_ai_settings
    from diag_air_site_probe import METHODS

    out = args.out.resolve()
    bundle = out.with_name(out.stem + "_bundle")
    manifest_path = out.with_suffix(".manifest.json")
    for path in (out, bundle, manifest_path, out.with_suffix(".jsonl"), out.with_name(out.stem + "_engine")):
        if path.exists():
            raise FileExistsError(path)
    git = git_state(ROOT)
    bundle.mkdir(parents=True)
    shutil.copytree(ROOT / "ai/OpexAI", bundle / "OpexAI")
    ai_fingerprint = fingerprint_tree(bundle / "OpexAI")
    if args.years == 6:
        smoke = json.loads(args.smoke_result.read_text())
        if smoke["ai_fingerprint"]["sha256"] != ai_fingerprint["sha256"]:
            raise ValueError("AI changed since smoke; same frozen AI is required")
    harness = bundle / "harness"
    harness.mkdir()
    for name in ("run_air_site_probe.py", "diag_air_site_probe.py", "bench_v2.py", "campaign_freeze.py",
                 "game_health.py", "physical_counters.py"):
        shutil.copy2(ROOT / "sweeps" / name, harness / name)
    _, libraries = freeze_bananas_libraries((
        {"unique_id": "51554648", "name": "Queue.FibonacciHeap"},
        {"unique_id": "5046524c", "name": "Pathfinder.Rail"}), bundle / "libraries")
    manifest = {"schema": 4, "purpose": "separate_solo_games_per_method_no_construction_not_AB", "git": git,
                "seeds": args.seeds, "years": args.years, "config": bench.make_cfg(), "out": str(out),
                "bundle": str(bundle), "fingerprint": fingerprint_tree(bundle), "libraries": libraries,
                "ai_fingerprint": ai_fingerprint,
                "settings": {method: effective_ai_settings(bundle / "OpexAI/info.nut", (("air_site_probe", i + 1),))
                             for i, method in enumerate(METHODS)},
                "runtime": {"openttd": bench.OPENTTD_VERSION, "opengfx": bench.OPENGFX_VERSION,
                            "docker_image_id": args.image_id, "cpus": 3, "memory": "2g", "swap": "2g", "workers": 3},
                "protocol": {"dates": ["1970-01-02", "1972-01-01", "1975-01-01"],
                             "validity": "complete passes, equal START fingerprints and exact start dates across methods, no vehicles/stations/loan changes",
                             "terminal_margin": "six years authorized solely to finish the 1975 pass; truncated passes excluded",
                             "budget": "1500 BuildAirport tests per method/town/type; ranked phase <=12 shared with spiral fallback; exhaustive oracle unlimited",
                             "oracle": "complete per-corner leveling admission, catchment acceptance >=8, max C96 then min total quote",
                             "cost": "direct BuildAirport exact; slope total estimated tariff + native leveling + original clearing (possible overlap)",
                             "stop": "invalid smoke blocks three-seed diagnostic"}}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    subprocess.run([sys.executable, str(harness / "run_air_site_probe.py"), "--worker", str(manifest_path)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--reanalyse", type=Path, help="offline rereading; preserve original result and frozen inputs")
    parser.add_argument("--docker", action="store_true", help="host launcher with Git metadata and VPS limits")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--years", type=int, choices=(1, 6), default=1)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--image-id", default=os.environ.get("AIR_PROBE_IMAGE_ID"))
    parser.add_argument("--smoke-result", type=Path, help="required healthy 42x1 all-method result before diagnostics")
    args = parser.parse_args()
    if args.reanalyse:
        if args.out is None or args.out.exists():
            parser.error("reanalysis requires a new --out")
        previous = json.loads(args.reanalyse.read_text())
        log_dir = args.reanalyse.with_name(args.reanalyse.stem + "_engine")
        result = {**previous, **evaluate(previous["series"], previous["seeds"], previous["years"], log_dir),
                  "reanalysis_of": str(args.reanalyse.resolve())}
        args.out.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result["probe_health"], indent=2))
        return
    if not args.worker and args.years == 6:
        if args.smoke_result is None:
            parser.error("diagnostics require --smoke-result with smoke_ok=true")
        smoke = json.loads(args.smoke_result.read_text())
        if (not smoke.get("probe_health", {}).get("smoke_ok") or smoke.get("seeds") != [42]
                or smoke.get("years") != 1 or smoke.get("analysis", {}).get("schema") != 4):
            parser.error("smoke is not a valid 42x1 separate-game diagnostic")
    if args.docker:
        if args.out is None:
            parser.error("--out required")
        from campaign_freeze import git_state
        state = git_state(ROOT)
        relative = args.out.resolve().relative_to(ROOT)
        image_id = subprocess.check_output(["docker", "image", "inspect", "openttd-lab", "--format", "{{.Id}}"], text=True).strip()
        context = subprocess.check_output(["docker", "context", "show"], text=True).strip()
        if context != "default":
            parser.error("VPS launcher requires the inspected default Docker context")
        command = ["docker", "run", "--rm", "--cpus=3", "--memory=2g", "--memory-swap=2g",
                   "-v", "openttd-lab-home:/home/lab", "-v", f"{ROOT}:/work", "-w", "/work",
                   "-e", "C66_GIT_SHA=" + state["sha"], "-e", "C66_GIT_DIRTY=" + str(int(state["dirty"])),
                   "-e", "C66_GIT_STATUS_B64=" + base64.b64encode("\n".join(state["status_porcelain"]).encode()).decode(),
                   image_id, "python3", "/work/sweeps/run_air_site_probe.py", "--out", "/work/" + relative.as_posix(),
                   "--years", str(args.years), "--seeds", *map(str, args.seeds), "--image-id", image_id]
        if args.smoke_result:
            command += ["--smoke-result", "/work/" + args.smoke_result.resolve().relative_to(ROOT).as_posix()]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        host_log = args.out.with_suffix(".host.log")
        with host_log.open("x") as output:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
        print(f"exit={result.returncode} log={host_log}")
        raise SystemExit(result.returncode)
    elif args.worker:
        run_worker(args.worker)
    elif args.out is None or len(set(args.seeds)) != len(args.seeds):
        parser.error("unique --seeds and --out required")
    else:
        freeze(args)


if __name__ == "__main__":
    main()
