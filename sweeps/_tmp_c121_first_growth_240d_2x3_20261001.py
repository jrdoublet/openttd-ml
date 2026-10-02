#!/usr/bin/env python3
"""C121 cadence: first 1->2 after positive report, with 240-day minimum age."""

import sys
import run_c66_reference as launcher
from _tmp_c121_first_growth_2x3_20261001 import BASE


VARIANT = BASE.replace(
    "c121_air_first_observation_growth=0",
    "c121_air_first_observation_growth=1,c121_air_first_growth_min_days=240",
)


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_growth_240d_2x3_20261001_r1",
        "--reference", BASE,
        "--policy-id", "c121_base",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_observation_growth_240d",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "3",
        "--seeds", "42", "100",
        "--max-workers", "2", "--cpus", "3", "--memory", "2g",
    ]
    launcher.main()
