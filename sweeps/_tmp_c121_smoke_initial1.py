#!/usr/bin/env python3
"""C121 AIR economics: paired Docker smoke on seed 42."""

import sys

import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_causal_smoke_seed42_2y_initial1_20260929",
        "--years", "2",
        "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "4g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0]",
        "--policy-id", "c115_reference",
        "--variant-policy-id", "c121_causal",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--script-debug",
        "--out", "results/c121_causal_smoke_seed42_2y_initial1_20260929.json",
    ]
    launcher.main()
