#!/usr/bin/env python3
"""C119 AIR payment model: paired Docker smoke on seed 42."""

import sys

import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c119_air_income_smoke_seed42_20260928",
        "--years", "2",
        "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "4g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c119_air_income_model=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c119_air_income_model=1]",
        "--policy-id", "c115_reference",
        "--variant-policy-id", "c119_air_income",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--out", "results/c119_air_income_smoke_seed42_20260928.json",
    ]
    launcher.main()
