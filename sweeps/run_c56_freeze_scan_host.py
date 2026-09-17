"""Lanceur hote borne pour le diagnostic C56 sous Linux/Docker.

Le diagnostic depend de la surcharge ``openttdlab.subprocess.check_output`` qui ajoute
``-d script=4``. Sous Windows/multiprocessing spawn, cette surcharge n'est pas fiable dans les
workers ; le runner officiel doit donc rester dans le meme environnement Linux que les bancs.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="openttd-lab:latest")
    parser.add_argument("--cpus", type=int, default=6)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--arm", default="OpexAI[c56_task_trace=1]")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not 1 <= args.cpus <= 6 or not 1 <= args.workers <= 6:
        parser.error("cpus/workers doivent etre entre 1 et 6")
    if "c56_task_trace=1" not in args.arm:
        parser.error("--arm doit conserver c56_task_trace=1")

    command = [
        "docker", "run", "--rm",
        f"--cpus={args.cpus}", "--memory=2g", "--memory-swap=2g",
        "-v", "openttd-lab-home:/home/lab",
        "-v", f"{ROOT}:/work", "-w", "/work",
        args.image, "python3", "sweeps/diag_c56_freeze_scan.py",
        "--years", str(args.years),
        "--seeds", *(str(seed) for seed in args.seeds),
        "--max-workers", str(args.workers),
        "--arm", args.arm,
        "--out", args.out,
    ]
    raise SystemExit(subprocess.run(command, cwd=ROOT).returncode)


if __name__ == "__main__":
    main()
