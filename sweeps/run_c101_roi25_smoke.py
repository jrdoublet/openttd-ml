#!/usr/bin/env python3
"""C101 ROI25: causal smoke 1x3 on seed 42."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c101_roi25_engine_choice_1x3_20260926",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c101_air_physical_engine_choice=0]",
        "--variant", "OpexAI[c101_air_physical_engine_choice=1]",
        "--variant-policy-id", "c101_roi25",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c101_roi25_engine_choice_1x3_20260926.json",
    ]
    launcher.main()
