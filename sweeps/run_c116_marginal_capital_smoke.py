#!/usr/bin/env python3
"""C116 marginal capital opportunity cost: causal smoke seed42 x3y."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c116_marginal_capital_1x3_20260927",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=1]",
        "--variant-policy-id", "c116_marginal_capital",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c116_marginal_capital_1x3_20260927.json",
    ]
    launcher.main()
