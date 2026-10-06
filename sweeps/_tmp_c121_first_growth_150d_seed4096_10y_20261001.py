#!/usr/bin/env python3
"""Repair run for seed 4096 of the C121 150-day 20x10 cadence campaign."""

import sys
import run_c66_reference as launcher
from _tmp_c121_first_growth_2x3_20261001 import BASE


VARIANT = BASE.replace(
    "c121_air_first_observation_growth=0",
    "c121_air_first_observation_growth=1,c121_air_first_growth_min_days=150",
)


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_growth_150d_seed4096_10y_20261001_r1",
        "--reference", BASE,
        "--policy-id", "c121_base",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_observation_growth_150d",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "10",
        "--seeds", "4096",
        "--max-workers", "2", "--cpus", "2", "--memory", "2g",
    ]
    launcher.main()
