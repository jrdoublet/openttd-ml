#!/usr/bin/env python3
"""C121 cadence: isolate strict immediate new-AIR priority inside corrected first-live growth."""

import sys

import run_c66_reference as launcher
from _tmp_c121_first_live_growth_5x6_20261001 import VARIANT as LIVE


REFERENCE = LIVE[:-1] + ",c121_air_first_live_air_priority=0]"
PRIORITY = LIVE[:-1] + ",c121_air_first_live_air_priority=1]"


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_air_priority_immediate_5x6_20261001_r2",
        "--reference", REFERENCE,
        "--policy-id", "c121_first_live_growth_bal90_fallback",
        "--variant", PRIORITY,
        "--variant-policy-id", "c121_first_live_growth_bal90_air_priority_immediate",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "10", "--cpus", "10", "--memory", "12g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
