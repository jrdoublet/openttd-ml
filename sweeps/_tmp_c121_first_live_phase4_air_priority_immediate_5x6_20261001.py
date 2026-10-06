#!/usr/bin/env python3
"""C121 cadence: isolate strict immediate AIR priority inside phase4 live 1->2."""

import sys

import run_c66_reference as launcher
from _tmp_c121_first_live_growth_phase4_5x6_20261001 import VARIANT as PHASE4


REFERENCE = PHASE4[:-1] + ",c121_air_first_live_air_priority=0]"
PRIORITY = PHASE4[:-1] + ",c121_air_first_live_air_priority=1]"


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_phase4_air_priority_immediate_5x6_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_first_live_growth_bal90_phase4",
        "--variant", PRIORITY,
        "--variant-policy-id", "c121_first_live_growth_bal90_phase4_air_priority_immediate",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "8", "--cpus", "8", "--memory", "12g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
