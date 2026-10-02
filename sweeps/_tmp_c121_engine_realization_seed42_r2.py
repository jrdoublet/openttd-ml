#!/usr/bin/env python3
"""Diagnostic shadow: C121 engine realization by EngineID on seed 42."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_engine_realization_seed42_4y_r2_20260929",
        "--years", "4",
        "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "4g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=1,b9_air_demand_shadow=0]",
        "--policy-id", "c121_no_shadow",
        "--variant-policy-id", "c121_engine_shadow",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--script-debug",
        "--out", "results/c121_engine_realization_seed42_4y_r2_20260929.json",
    ]
    launcher.main()
