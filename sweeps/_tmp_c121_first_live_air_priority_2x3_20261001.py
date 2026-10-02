#!/usr/bin/env python3
"""C121 cadence: screen direct new-AIR priority over live first 1->2 growth."""

import sys
import run_c66_reference as launcher
from _tmp_c121_first_live_growth_5x6_20261001 import VARIANT as LIVE


REFERENCE = LIVE[:-1] + ",c121_air_first_live_air_priority=0]"
PRIORITY = LIVE[:-1] + ",c121_air_first_live_air_priority=1]"


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_air_priority_2x3_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_first_live_growth_bal90",
        "--variant", PRIORITY,
        "--variant-policy-id", "c121_first_live_growth_bal90_air_priority",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "3",
        "--seeds", "42", "100",
        "--max-workers", "4", "--cpus", "4", "--memory", "8g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
