#!/usr/bin/env python3
"""C121 cadence: 5x6 qualification of first positive-observation 1->2 reinforcement."""

import sys
import run_c66_reference as launcher
from _tmp_c121_first_growth_2x3_20261001 import BASE, VARIANT


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_growth_5x6_20261001_r1",
        "--reference", BASE,
        "--policy-id", "c121_base",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_observation_growth",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "3", "--cpus", "3", "--memory", "2g",
    ]
    launcher.main()
