#!/usr/bin/env python3
"""C122.2 territorial priority: seed42 trace smoke after rejected causal smoke."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c122_2_regime_priority_trace_seed42_1x3_20260929",
        "--years", "3",
        "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "4g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c122_air_regime_priority=0,b9_air_demand_shadow=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c122_air_regime_priority=1,b9_air_demand_shadow=0]",
        "--policy-id", "c121_current",
        "--variant-policy-id", "c122_2_regime_priority_trace",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--script-debug",
        "--out", "results/c122_2_regime_priority_trace_seed42_1x3_20260929.json",
    ]
    launcher.main()
