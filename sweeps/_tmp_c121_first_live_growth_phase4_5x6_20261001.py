#!/usr/bin/env python3
"""C121 cadence: 5x6 live 1->2 override limited to opening four years."""

import sys

import run_c66_reference as launcher
from _tmp_c121_first_live_growth_5x6_20261001 import REFERENCE, VARIANT as LIVE_VARIANT


VARIANT = LIVE_VARIANT.replace(
    "c121_air_first_live_growth=1",
    "c121_air_first_live_growth=1,c121_air_first_live_growth_phase_years=4",
)


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_growth_phase4_5x6_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_base_live_shadow",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_live_growth_bal90_phase4",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "10", "--cpus", "10", "--memory", "12g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
