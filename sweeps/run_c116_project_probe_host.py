#!/usr/bin/env python3
"""Lance la sonde passive C116.3 dans Docker avec CPU borne."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="openttd-lab:latest")
    parser.add_argument("--cpus", type=int, default=3)
    parser.add_argument("--years", type=int, default=4)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", default="results/diag_c116_project_probe_3x4.json")
    parser.add_argument("--library-campaign", default="c115_c100_capital_replay_20x10_20260927_corrected")
    args = parser.parse_args()
    if not 1 <= args.cpus <= 10:
        parser.error("--cpus doit etre entre 1 et 10")
    if not 1 <= args.workers <= 10:
        parser.error("--workers doit etre entre 1 et 10")
    command = [
        "docker", "run", "--rm", f"--cpus={args.cpus}",
        "--memory=4g", "--memory-swap=4g",
        "-v", "openttd-lab-home:/home/lab", "-v", f"{ROOT}:/work", "-w", "/work",
        args.image, "python3", "sweeps/diag_c116_project_probe.py",
        "--years", str(args.years), "--seeds", *(str(seed) for seed in args.seeds),
        "--max-workers", str(args.workers), "--out", args.out,
        "--library-manifest", f"results/{args.library_campaign}.manifest.json",
        "--library-dir", f"results/{args.library_campaign}_bundle/ai_libraries",
    ]
    completed = subprocess.run(command, cwd=ROOT)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
