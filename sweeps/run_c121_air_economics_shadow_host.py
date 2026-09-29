"""Lanceur hote Docker borne pour le shadow C121 AIR."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="openttd-lab:latest")
    parser.add_argument("--cpus", type=int, default=6)
    parser.add_argument("--memory", default="6g")
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--line-telemetry", action="store_true")
    parser.add_argument("--engine-replay", action="store_true")
    parser.add_argument("--out", default="results/c121_air_economics_shadow_5x6_20260928.json")
    args = parser.parse_args()
    if not 1 <= args.cpus <= 6:
        parser.error("--cpus doit etre entre 1 et 6")
    if not 1 <= args.workers <= 6:
        parser.error("--workers doit etre entre 1 et 6")

    command = [
        "docker", "run", "--rm",
        f"--cpus={args.cpus}", f"--memory={args.memory}", f"--memory-swap={args.memory}",
        "-v", "openttd-lab-home:/home/lab",
        "-v", f"{ROOT}:/work",
        "-w", "/work",
        args.image,
        "python3", "sweeps/run_c121_air_economics_shadow.py",
        "--years", str(args.years),
        "--seeds", *(str(seed) for seed in args.seeds),
        "--workers", str(args.workers),
        "--out", args.out,
    ]
    if args.line_telemetry:
        command.append("--line-telemetry")
    if args.engine_replay:
        command.append("--engine-replay")
    completed = subprocess.run(command, cwd=ROOT)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
