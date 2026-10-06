#!/usr/bin/env python3
"""C121 cadence: 20x10 qualification of 150-day first 1->2 growth."""

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
        "--campaign", "c121_first_growth_150d_20x10_20261001_r1",
        "--reference", BASE,
        "--policy-id", "c121_base",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_observation_growth_150d",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "10",
        "--seeds", "42", "100", "7", "999", "2026", "1", "17", "73", "314", "512",
        "1024", "1337", "4096", "8191", "12345", "54321", "65537", "123456", "424242", "8675309",
        "--max-workers", "10", "--cpus", "10", "--memory", "12g",
    ]
    launcher.main()
