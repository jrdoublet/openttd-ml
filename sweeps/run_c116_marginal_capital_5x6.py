#!/usr/bin/env python3
"""C116 marginal capital opportunity cost: causal 5 seeds x 6 years."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c116_marginal_capital_5x6_20260927",
        "--years", "6", "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "5", "--cpus", "5", "--memory", "6g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=1]",
        "--variant-policy-id", "c116_marginal_capital",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/c116_marginal_capital_5x6_20260927.json",
    ]
    launcher.main()
