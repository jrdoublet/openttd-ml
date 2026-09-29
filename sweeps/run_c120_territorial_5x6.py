import sys

import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "diag_c120_territorial_5x6_20260928",
        "--years", "6", "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "3", "--cpus", "3", "--memory", "6g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=0,c118_air_territorial_expansion=0,c118_air_coverage_probe=0,c120_air_territorial_ranking=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=0,c118_air_territorial_expansion=0,c118_air_coverage_probe=0,c120_air_territorial_ranking=1]",
        "--variant-policy-id", "c120_territorial",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/diag_c120_territorial_5x6_20260928.json",
    ]
    launcher.main()
