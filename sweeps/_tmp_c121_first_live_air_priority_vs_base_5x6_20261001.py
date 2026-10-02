#!/usr/bin/env python3
"""C121 cadence: repaired first-live growth (AIR priority) versus C121 base."""

import sys
import run_c66_reference as launcher
from _tmp_c121_first_live_growth_5x6_20261001 import REFERENCE, VARIANT


CANDIDATE = VARIANT[:-1] + ",c121_air_first_live_air_priority=1]"


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_air_priority_vs_base_5x6_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_base_live_shadow",
        "--variant", CANDIDATE,
        "--variant-policy-id", "c121_first_live_growth_bal90_air_priority",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "5", "--cpus", "5", "--memory", "8g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
