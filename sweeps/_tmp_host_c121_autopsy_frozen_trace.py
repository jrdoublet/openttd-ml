from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cmd = [
        "docker", "run", "--rm",
        "--cpus=3", "--memory=2g", "--memory-swap=2g",
        "-v", "openttd-lab-home:/home/lab",
        "-v", f"{ROOT}:/work", "-w", "/work",
        "openttd-lab:latest",
        "python3", "sweeps/run_c121_autopsy_frozen_trace.py",
        "--baseline", "results/c121_autopsy_base_3x6_20261002_r1.json",
        "--seeds", "42", "100", "999",
        "--years", "1", "--workers", "3",
        "--out", "results/c121_autopsy_frozen_trace_3x1_20261002_r4.json",
    ]
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
