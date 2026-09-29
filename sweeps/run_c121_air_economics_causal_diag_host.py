"""Lanceur hote Docker borne pour le diagnostic causal C121 AIR."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="openttd-lab:latest")
    parser.add_argument("--cpus", type=int, default=1)
    parser.add_argument("--memory", default="4g")
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--causal", type=int, choices=(0, 1), default=1)
    parser.add_argument("--duel", action="store_true")
    parser.add_argument("--throughput-probe", type=int, choices=(0, 1), default=1)
    parser.add_argument("--out", default="results/diag_c121_causal_seed42_2y_20260928.json")
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
        "python3", "sweeps/run_c121_air_economics_causal_diag.py",
        "--years", str(args.years),
        "--seeds", *(str(seed) for seed in args.seeds),
        "--workers", str(args.workers),
        "--causal", str(args.causal),
        "--throughput-probe", str(args.throughput_probe),
        "--out", args.out,
    ]
    if args.duel:
        command.append("--duel")
    completed = subprocess.run(command, cwd=ROOT)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
