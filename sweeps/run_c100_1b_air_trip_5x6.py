#!/usr/bin/env python3
"""C100.1b: causal 5x6, current default vs corrected physical AIR trip model."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c100_1b_air_trip_physical_vs_default_5x6_20260926",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "3", "--cpus", "3", "--memory", "4g",
        "--reference", "OpexAI[c100_air_trip_physical=0]",
        "--variant", "OpexAI[c100_air_trip_physical=1]",
        "--policy-id", "c100_1b_ref",
        "--variant-policy-id", "c100_1b_physical",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--out", "results/c100_1b_air_trip_physical_vs_default_5x6_20260926.json",
    ]
    launcher.main()
