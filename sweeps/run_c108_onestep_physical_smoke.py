#!/usr/bin/env python3
"""C108 one-step marginal choice + C100.1 physical economics: seed 42 x 3 years."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c108_onestep_physical_1x3_20260927",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c108_air_onestep_physical_economics=0]",
        "--variant", "OpexAI[c108_air_onestep_physical_economics=1]",
        "--variant-policy-id", "c108_onestep_physical",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c108_onestep_physical_1x3_20260927.json",
    ]
    launcher.main()
