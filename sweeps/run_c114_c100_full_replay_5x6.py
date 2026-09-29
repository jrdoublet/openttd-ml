#!/usr/bin/env python3
"""C114 full replay of the first positive C100: causal 5 seeds x 6 years."""

from __future__ import annotations

import sys

import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c114_c100_full_replay_5x6_20260927",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "5", "--cpus", "5", "--memory", "6g",
        "--reference", "OpexAI[c114_air_c100_full_replay=0]",
        "--variant", "OpexAI[c114_air_c100_full_replay=1]",
        "--policy-id", "reference",
        "--variant-policy-id", "c114_full_replay",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--out", "results/c114_c100_full_replay_5x6_20260927.json",
    ]
    launcher.main()
