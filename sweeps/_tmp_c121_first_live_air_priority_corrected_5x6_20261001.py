#!/usr/bin/env python3
"""C121 cadence: corrected full-horizon first-live growth + direct new-AIR priority."""

import sys

import run_c66_reference as launcher
from _tmp_c121_first_live_growth_5x6_20261001_r2 import REFERENCE, VARIANT as LIVE


PRIORITY = LIVE.replace(
    "c121_air_first_live_air_priority=0",
    "c121_air_first_live_air_priority=1",
)


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_air_priority_corrected_5x6_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_base_live_shadow",
        "--variant", PRIORITY,
        "--variant-policy-id", "c121_first_live_growth_bal90_air_priority_corrected",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "10", "--cpus", "10", "--memory", "12g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
