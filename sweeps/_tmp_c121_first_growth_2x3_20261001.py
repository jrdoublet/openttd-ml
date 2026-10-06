#!/usr/bin/env python3
"""C121 cadence: isolate first positive-observation 1->2 reinforcement."""

import sys
import run_c66_reference as launcher


BASE = "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_catalog_incremental=1,c121_catalog_air_first_year=0,c121_air_decision_depth_economics=0,c121_air_portfolio_depth_economics=0,c121_air_portfolio_split_economics=0,c121_air_observation_growth=0,c121_air_first_observation_growth=0,c121_fleet_stock_growth=0,c121_territory_first=0,c121_aaa_line=0,c121_air_engine_realization=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c121_air_initial_project_economics=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c122_air_regime_priority=0,c122_air_regime_shadow=0,c122_air_threat_probe=0,b9_air_demand_shadow=0]"
VARIANT = BASE.replace("c121_air_first_observation_growth=0", "c121_air_first_observation_growth=1")


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_growth_2x3_20261001_r1",
        "--reference", BASE,
        "--policy-id", "c121_base",
        "--variant", VARIANT,
        "--variant-policy-id", "c121_first_observation_growth",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "3",
        "--seeds", "42", "100",
        "--max-workers", "2", "--cpus", "3", "--memory", "2g",
    ]
    launcher.main()
