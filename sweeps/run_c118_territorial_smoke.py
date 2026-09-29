import sys

import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "smoke_c118_territorial_1x3_20260927_r5",
        "--years", "3", "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "2g",
        "--line-telemetry",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=0,c118_air_territorial_expansion=0,c118_air_coverage_probe=1]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c116_air_marginal_capital=0,c118_air_territorial_expansion=1,c118_air_coverage_probe=1]",
        "--variant-policy-id", "c118_territorial",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/smoke_c118_territorial_1x3_20260927_r5.json",
    ]
    launcher.main()
