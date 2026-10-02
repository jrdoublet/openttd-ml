#!/usr/bin/env python3
"""C121 cadence: passive cold-vs-warm K_dec shadow screening."""

import sys

import run_c66_reference as launcher
from _tmp_c121_first_live_growth_5x6_20261001 import VARIANT as LIVE


REFERENCE = LIVE[:-1] + ",c121_kdec_cold_shadow=0]"
SHADOW = LIVE[:-1] + ",c121_kdec_cold_shadow=1]"


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_kdec_cold_shadow_2x3_20261002_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_first_live_growth_bal90_fallback",
        "--variant", SHADOW,
        "--variant-policy-id", "c121_first_live_growth_bal90_kdec_cold_shadow",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "3",
        "--seeds", "42", "100",
        "--max-workers", "4", "--cpus", "4", "--memory", "8g",
        "--script-debug",
    ]
    launcher.main()
