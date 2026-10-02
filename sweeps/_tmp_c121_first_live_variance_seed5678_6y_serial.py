#!/usr/bin/env python3
"""C121 cadence: serial reference-only determinism control on seed 5678."""

import sys

import run_c66_reference as launcher
from _tmp_c121_first_live_air_priority_immediate_5x6_20261001 import REFERENCE


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_variance_seed5678_6y_serial_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_first_live_growth_bal90_fallback",
        "--years", "6",
        "--seeds", "5678",
        "--repeats", "3",
        "--max-workers", "1", "--cpus", "1", "--memory", "4g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
