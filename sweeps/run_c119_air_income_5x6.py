#!/usr/bin/env python3
"""C119 AIR payment model: causal 5 seeds x 6 years against current C115."""

import sys

import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c119_air_income_vs_c115_5x6_20260928",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "6", "--cpus", "6", "--memory", "6g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c119_air_income_model=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c119_air_income_model=1]",
        "--policy-id", "c115_reference",
        "--variant-policy-id", "c119_air_income",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--out", "results/c119_air_income_vs_c115_5x6_20260928.json",
    ]
    launcher.main()
