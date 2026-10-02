#!/usr/bin/env python3
"""C121 cadence: 150-day first 1->2 in years 0-2, then 90 days, versus fixed 90 days."""

import sys
import run_c66_reference as launcher
from _tmp_c121_first_growth_2x3_20261001 import BASE


REFERENCE = BASE.replace(
    "c121_air_first_observation_growth=0",
    "c121_air_first_observation_growth=1,c121_air_first_growth_min_days=90",
)
VARIANT = BASE.replace(
    "c121_air_first_observation_growth=0",
    "c121_air_first_observation_growth=1,c121_air_first_growth_min_days=150,c121_air_first_growth_phase_years=3,c121_air_first_growth_late_days=90",
)


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_growth_phase150to90_5x6_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_first_growth_90d",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_growth_phase150to90",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "3", "--cpus", "3", "--memory", "2g",
    ]
    launcher.main()
