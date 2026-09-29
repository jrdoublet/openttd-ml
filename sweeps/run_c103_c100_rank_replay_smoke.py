#!/usr/bin/env python3
"""C103 C100 rank replay: causal smoke 1x3 on seed 42."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c103_c100_rank_replay_1x3_20260927_r1",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c103_air_c100_rank_replay=0]",
        "--variant", "OpexAI[c103_air_c100_rank_replay=1]",
        "--variant-policy-id", "c103_rank_replay",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c103_c100_rank_replay_1x3_20260927_r1.json",
    ]
    launcher.main()
