"""Lanceur hote du diagnostic B9 AIR sous le lab Docker borne."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="openttd-lab:latest")
    parser.add_argument("--cpus", type=int, default=6)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--out", default="results/review_b9_air_catchment_5x6.json")
    parser.add_argument("--demand-shadow", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.cpus <= 6:
        parser.error("--cpus doit etre entre 1 et 6")
    if not 1 <= args.workers <= 6:
        parser.error("--workers doit etre entre 1 et 6")

    command = [
        "docker", "run", "--rm",
        f"--cpus={args.cpus}", "--memory=2g", "--memory-swap=2g",
        "-v", "openttd-lab-home:/home/lab",
        "-v", f"{ROOT}:/work",
        "-w", "/work",
        args.image,
        "python3", "sweeps/run_b9_air_catchment_5x6.py",
        "--years", str(args.years),
        "--seeds", *(str(seed) for seed in args.seeds),
        "--workers", str(args.workers),
        "--out", args.out,
    ]
    if args.demand_shadow:
        command.append("--demand-shadow")
    completed = subprocess.run(command, cwd=ROOT)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
