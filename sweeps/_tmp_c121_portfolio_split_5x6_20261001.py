#!/usr/bin/env python3
"""Temporary frozen-harness launcher for the preregistered C121 portfolio-split 5x6."""

import sys
import run_c66_reference as launcher


REFERENCE = "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=0,c121_air_decision_depth_economics=0,c121_air_portfolio_depth_economics=0,c121_air_portfolio_split_economics=0,c121_catalog_incremental=0,c121_catalog_air_first_year=0,c121_air_observation_growth=0,c121_aaa_line=0,c121_territory_first=0,c121_fleet_stock_growth=0,c121_air_engine_realization=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c121_air_initial_project_economics=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c122_air_regime_priority=0,c122_air_regime_shadow=0,c122_air_threat_probe=0,b9_air_demand_shadow=0]"
CANDIDATE = "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_decision_depth_economics=0,c121_air_portfolio_depth_economics=0,c121_air_portfolio_split_economics=1,c121_catalog_incremental=1,c121_catalog_air_first_year=0,c121_air_observation_growth=0,c121_aaa_line=0,c121_territory_first=0,c121_fleet_stock_growth=0,c121_air_engine_realization=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c121_air_initial_project_economics=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c122_air_regime_priority=0,c122_air_regime_shadow=0,c122_air_threat_probe=0,b9_air_demand_shadow=0]"


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_portfolio_split_vs_c115_5x6_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c115_reference",
        "--variant", CANDIDATE,
        "--variant-policy-id", "c121_portfolio_split_candidate",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "3", "--cpus", "3", "--memory", "2g",
    ]
    launcher.main()
