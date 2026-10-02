#!/usr/bin/env python3
"""C121 engine-only realization: paired seed42 6y causal probe."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_engine_realization_seed42_6y_20260929",
        "--years", "6",
        "--seeds", "42",
        "--max-workers", "2", "--cpus", "4", "--memory", "6g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_engine_realization=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_engine_realization=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0]",
        "--policy-id", "c121_engine_realization_off",
        "--variant-policy-id", "c121_engine_realization_on",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--script-debug",
        "--out", "results/c121_engine_realization_seed42_6y_20260929.json",
    ]
    launcher.main()
