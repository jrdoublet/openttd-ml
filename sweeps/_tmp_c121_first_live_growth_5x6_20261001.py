#!/usr/bin/env python3
"""C121 cadence: causal 5x6 of balanced90 live-evidence first 1->2 growth."""

import sys

import run_c66_reference as launcher
BASE = "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_catalog_incremental=1,c121_catalog_air_first_year=0,c121_air_engine_realization=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c121_air_initial_project_economics=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c122_air_regime_priority=0,c122_air_regime_shadow=0,c122_air_threat_probe=0,b9_air_demand_shadow=0]"

REFERENCE = BASE[:-1] + ",c121_air_first_live_shadow=1,c121_air_first_live_growth=0]"
VARIANT = BASE[:-1] + ",c121_air_first_live_shadow=1,c121_air_first_live_growth=1]"

if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_growth_5x6_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_base_live_shadow",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_live_growth_bal90",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "10", "--cpus", "10", "--memory", "12g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
