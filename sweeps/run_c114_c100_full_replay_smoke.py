#!/usr/bin/env python3
"""C114: replay the first positive C100 globally, causal smoke seed42 x3y."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c114_c100_full_replay_1x3_20260927",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c114_air_c100_full_replay=0]",
        "--variant", "OpexAI[c114_air_c100_full_replay=1]",
        "--variant-policy-id", "c114_c100_full_replay",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c114_c100_full_replay_1x3_20260927.json",
    ]
    launcher.main()
