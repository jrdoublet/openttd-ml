#!/usr/bin/env python3
"""C111 C100 replay equipment + C68 decision shadow: causal smoke seed42 x3y."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c111_c100_decision_shadow_1x3_20260927",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c111_air_c100_decision_shadow=0]",
        "--variant", "OpexAI[c111_air_c100_decision_shadow=1]",
        "--variant-policy-id", "c111_c100_decision_shadow",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c111_c100_decision_shadow_1x3_20260927.json",
    ]
    launcher.main()
