#!/usr/bin/env python3
"""C122.4 causal local retry: seed42 x 3y, matched passive probe."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c122_4_threat_retry_smoke_seed42_1x3_20260929",
        "--years", "3",
        "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "4g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c122_air_regime_priority=0,c122_air_regime_shadow=0,c122_air_threat_probe=1,c122_air_threat_retry=0,b9_air_demand_shadow=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c122_air_regime_priority=0,c122_air_regime_shadow=0,c122_air_threat_probe=1,c122_air_threat_retry=1,b9_air_demand_shadow=0]",
        "--policy-id", "c122_4_threat_control",
        "--variant-policy-id", "c122_4_threat_retry",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--script-debug",
        "--out", "results/c122_4_threat_retry_smoke_seed42_1x3_20260929.json",
    ]
    launcher.main()
