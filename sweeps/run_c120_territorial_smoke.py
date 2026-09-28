import sys

import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c120_territorial_1x3_20260928_r8",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=0,c118_air_territorial_expansion=0,c118_air_coverage_probe=1,c120_air_territorial_ranking=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=0,c118_air_territorial_expansion=0,c118_air_coverage_probe=1,c120_air_territorial_ranking=1]",
        "--variant-policy-id", "c120_territorial",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c120_territorial_1x3_20260928_r8.json",
    ]
    launcher.main()
