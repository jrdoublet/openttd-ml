#!/usr/bin/env python3
"""C109 speed-elasticity physical economics: causal smoke seed 42 x 3 years."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c109_speed_elasticity_1x3_20260927",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c109_air_speed_elasticity_physical=0]",
        "--variant", "OpexAI[c109_air_speed_elasticity_physical=1]",
        "--variant-policy-id", "c109_speed_elasticity",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c109_speed_elasticity_1x3_20260927.json",
    ]
    launcher.main()
