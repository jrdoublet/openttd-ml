#!/usr/bin/env python3
"""C110 choice-only engine calibration: causal smoke seed 42 x 3 years."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c110_engine_calibration_choice_only_1x3_20260927",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c110_air_engine_calibration_choice_only=0]",
        "--variant", "OpexAI[c110_air_engine_calibration_choice_only=1]",
        "--variant-policy-id", "c110_engine_calibration_choice_only",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c110_engine_calibration_choice_only_1x3_20260927.json",
    ]
    launcher.main()
