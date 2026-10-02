#!/usr/bin/env python3
"""C121 cadence: first 1->2 after positive report, with 180-day minimum age."""

import sys
import run_c66_reference as launcher
from _tmp_c121_first_growth_2x3_20261001 import BASE


REFERENCE = BASE.replace(
    "c121_air_first_observation_growth=0",
    "c121_air_first_observation_growth=0,c121_air_first_growth_min_days=0",
)
VARIANT = BASE.replace(
    "c121_air_first_observation_growth=0",
    "c121_air_first_observation_growth=1,c121_air_first_growth_min_days=180",
)


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_growth_180d_5x6_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_base",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_observation_growth_180d",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "3", "--cpus", "3", "--memory", "2g",
    ]
    launcher.main()
