#!/usr/bin/env python3
"""C121 cadence: causal 5x6 of fleet/K_pass skip toward a fundable AIR project."""

import sys

import run_c66_reference as launcher
from _tmp_c121_first_live_growth_5x6_20261001 import VARIANT as LIVE


REFERENCE = LIVE[:-1] + ",c121_kpass_shadow=1,c121_kpass_air_continue=0]"
VARIANT = LIVE[:-1] + ",c121_kpass_shadow=1,c121_kpass_air_continue=1]"


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_kpass_air_continue_5x6_20261002_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_first_live_growth_bal90_kpass_shadow",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_live_growth_bal90_kpass_air_continue",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "10", "--cpus", "10", "--memory", "12g",
        "--script-debug",
    ]
    launcher.main()
