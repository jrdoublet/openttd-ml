"""Host-side launcher for reproducible C66.3 shared 1v1 campaigns.

This launcher intentionally runs outside the container.  It captures the Git state
and the exact Docker image ID immediately before ``docker run`` and injects them into
the benchmark, while enforcing the repository's CPU/RAM/cache-volume limits.
"""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _output(args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--image", default="openttd-lab:latest")
    parser.add_argument("--policy-id", default="reference")
    parser.add_argument("--reference")
    parser.add_argument("--variant")
    parser.add_argument("--variant-policy-id")
    parser.add_argument("--primary-metric")
    parser.add_argument("--min-useful-primary-delta", type=float)
    parser.add_argument("--value-guard-max-loss-pct", type=float)
    parser.add_argument("--years", type=int)
    parser.add_argument("--seeds", nargs="+", type=int)
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--max-workers", type=int)
    parser.add_argument("--engine-timeout", type=int)
    parser.add_argument("--line-telemetry", action="store_true")
    parser.add_argument("--cpus", type=int, default=3)
    parser.add_argument("--out")
    args = parser.parse_args()

    git_sha = _output(["git", "rev-parse", "HEAD"])
    git_status = _output(["git", "status", "--porcelain=v1", "--untracked-files=all"])
    git_dirty = "1" if git_status else "0"
    git_status_b64 = base64.b64encode(git_status.encode("utf-8")).decode("ascii")
    image_id = _output(["docker", "image", "inspect", args.image, "--format", "{{.Id}}"])

    benchmark = [
        "python3", "sweeps/bench_1v1_5y_20seeds.py",
        "--campaign", args.campaign,
        "--policy-id", args.policy_id,
    ]
    if args.years is not None:
        benchmark += ["--years", str(args.years)]
    if args.seeds is not None:
        benchmark += ["--seeds", *(str(seed) for seed in args.seeds)]
    if args.repeats is not None:
        benchmark += ["--repeats", str(args.repeats)]
    if args.max_workers is not None:
        benchmark += ["--max-workers", str(args.max_workers)]
    if args.engine_timeout is not None:
        benchmark += ["--engine-timeout", str(args.engine_timeout)]
    if args.line_telemetry:
        benchmark += ["--line-telemetry"]
    if args.variant is not None:
        benchmark += ["--variant", args.variant]
    if args.reference is not None:
        benchmark += ["--reference", args.reference]
    if args.variant_policy_id is not None:
        benchmark += ["--variant-policy-id", args.variant_policy_id]
    if args.primary_metric is not None:
        benchmark += ["--primary-metric", args.primary_metric]
    if args.min_useful_primary_delta is not None:
        benchmark += ["--min-useful-primary-delta", str(args.min_useful_primary_delta)]
    if args.value_guard_max_loss_pct is not None:
        benchmark += ["--value-guard-max-loss-pct", str(args.value_guard_max_loss_pct)]
    if args.out is not None:
        benchmark += ["--out", args.out]

    command = [
        "docker", "run", "--rm",
        f"--cpus={args.cpus}", "--memory=2g", "--memory-swap=2g",
        "-e", f"C66_DOCKER_IMAGE={args.image}",
        "-e", f"C66_DOCKER_IMAGE_ID={image_id}",
        "-e", f"C66_DOCKER_CPUS={args.cpus}",
        "-e", "C66_DOCKER_MEMORY=2g",
        "-e", "C66_DOCKER_MEMORY_SWAP=2g",
        "-e", f"C66_GIT_SHA={git_sha}",
        "-e", f"C66_GIT_DIRTY={git_dirty}",
        "-e", f"C66_GIT_STATUS_B64={git_status_b64}",
        "-v", "openttd-lab-home:/home/lab",
        "-v", f"{ROOT}:/work",
        "-w", "/work",
        args.image,
        *benchmark,
    ]

    print(f"{'C66.4' if args.variant else 'C66.3'} campaign: {args.campaign}")
    print(f"Git: {git_sha} dirty={git_dirty}")
    print(f"Docker: {args.image} {image_id}")
    completed = subprocess.run(command, cwd=ROOT)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
