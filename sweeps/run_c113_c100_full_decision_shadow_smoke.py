#!/usr/bin/env python3
"""C113 full C68 decision shadow + C100 replay equipment: causal smoke seed42 x3y."""

import sys
import run_c66_reference as launcher

if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c113_c100_full_decision_shadow_1x3_20260927",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c113_air_c100_full_decision_shadow=0]",
        "--variant", "OpexAI[c113_air_c100_full_decision_shadow=1]",
        "--variant-policy-id", "c113_c100_full_decision_shadow",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c113_c100_full_decision_shadow_1x3_20260927.json",
    ]
    launcher.main()
