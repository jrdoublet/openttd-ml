#!/usr/bin/env python3
"""C116.4 post-selection AIR equipment decoupling: causal 5 seeds x 6 years."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c116_decoupled_5x6_20260927_r1",
        "--years", "6", "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "5", "--cpus", "5", "--memory", "6g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=1]",
        "--variant-policy-id", "c116_decoupled",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/c116_decoupled_5x6_20260927_r1.json",
    ]
    launcher.main()
