"""RAIL-IDLE 10y: frozen 5x10 instrumented maturity; optional uninstrumented B.

Use only in Linux Docker with the same frozen library tarballs as 20261030.
Each run has a fresh output path.  This runner changes no OpexAI sources.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
import bench_v2
import openttdlab
from campaign_freeze import _frozen_library_descriptor

FROZEN = ROOT / "results/frozen_rail_libraries_20261030"
META = ROOT / "results/v233l_frozen_manifest_libraries_20261030.json"
SELECTED = (100, 512, 12345, 54321, 65537)
REF_SETTINGS = "mode_air=0,mode_road=0,mode_water=0,mode_rail=1"
ON_SETTINGS = (
    REF_SETTINGS + ",rail_repair_join_site=1,rail_repair_v131_focus=1,"
    "rail_repair_astar_pair=1,rail_repair_pose_order=1"
)
WATCH = (
    "RAIL_REPAIR_IDLE", "RAIL_SITE_REPAIR", "RAIL_ASTAR_REPAIR",
    "RAIL_POSE_REPAIR", "V131_REPAIR", "RAIL_BUILD",
    "Your script made an error", "The script died unexpectedly",
)


def verify_frozen_libraries():
    libs = json.loads(META.read_text(encoding="utf8"))
    groups = {group["requested_unique_id"]: group["resolved"] for group in libs}
    for members in groups.values():
        for item in members:
            expected = item["sha256"]
            actual = hashlib.sha256((FROZEN / item["filename"]).read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError("Frozen NoAI library differs: " + item["filename"])

    def frozen(uid, name):
        return _frozen_library_descriptor(name, groups[uid], FROZEN)

    bench_v2.bananas_ai_library = frozen


def install_diagnostics():
    # OpenTTDLab launches subprocesses in a Linux fork pool; the patched command
    # propagates there. Do not confuse this observational run with the gate A.
    if os.name == "nt":
        raise RuntimeError("Instrumented replay must run in Docker/Linux")
    from bench_1v1_5y_20seeds import extract_line_telemetry

    original_output = openttdlab.subprocess.check_output

    def debug_script_command(command, *args, **kwargs):
        command = tuple(command)
        if any(str(part).startswith("-vnull") for part in command):
            command = command[:1] + ("-d", "script=4") + command[1:]
        return original_output(command, *args, **kwargs)

    openttdlab.subprocess.check_output = debug_script_command
    original_keep = bench_v2.keep

    def keep_diagnostics(row):
        row = dict(row)
        date = str(row["date"])
        # Preserve all event markers at 1979-12, including any 1974 builds.
        # 1974-12 event log also preserved for cross-check.
        if date in ("1974-12-01", "1979-12-01"):
            row["output"] = "\n".join(
                line for line in (row.get("output") or "").splitlines()
                if any(token in line for token in WATCH)
            )
        else:
            row["output"] = ""
        result = original_keep(row)
        record = result[0]
        if date.endswith("-12-01") and int(date[:4]) >= 1974:
            telemetry = extract_line_telemetry(row["chunks"], 0)
            record["line_telemetry"] = telemetry
        return (record,)

    bench_v2.keep = keep_diagnostics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("pilot", "b", "smoke"), required=True)
    args = parser.parse_args()
    verify_frozen_libraries()
    is_pilot = args.stage in ("pilot", "smoke")
    if is_pilot:
        install_diagnostics()
    seeds = ([100] if args.stage == "smoke" else
             list(SELECTED) if is_pilot else list(bench_v2.SEEDS))
    probes = ",probes=258" if is_pilot else ""
    ref = "OpexAI[" + REF_SETTINGS + probes + "]"
    treat = "OpexAI[" + ON_SETTINGS + probes + "]"
    output = ROOT / ("results/rail_repair_idle_" + args.stage + "_10y_20261031.json")
    if output.exists() or output.with_suffix(".jsonl").exists():
        raise FileExistsError("Refusing to overwrite a frozen benchmark: " + str(output))
    sys.argv = [
        "bench_v2.py", "--arms", ref, treat,
        "--seeds", *(str(seed) for seed in seeds),
        "--years", "10", "--max-workers", "8", "--allow-shared-nondefault",
        "--out", str(output),
    ]
    print("STAGE", args.stage, "SEEDS", seeds, "OUT", output, flush=True)
    bench_v2.main()


if __name__ == "__main__":
    main()
