#!/usr/bin/env python3
"""C121 cadence: exact-defer diagnostic on seed 5678 over six years."""

import sys

import run_c66_reference as launcher
from _tmp_c121_first_live_air_priority_immediate_5x6_20261001 import REFERENCE, PRIORITY


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_air_priority_immediate_seed5678_6y_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_first_live_growth_bal90_fallback",
        "--variant", PRIORITY,
        "--variant-policy-id", "c121_first_live_growth_bal90_air_priority_immediate",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "5678",
        "--max-workers", "2", "--cpus", "2", "--memory", "4g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
