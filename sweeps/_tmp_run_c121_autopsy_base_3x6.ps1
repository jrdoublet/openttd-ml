$ErrorActionPreference = 'Stop'

$ref = 'OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=0,c121_catalog_incremental=0,c121_air_decision_depth_economics=0,c121_air_portfolio_depth_economics=0,c121_air_portfolio_split_economics=0,c121_air_first_live_growth=0,c121_air_first_live_shadow=0,c121_air_first_observation_growth=0,c121_air_observation_growth=0,c121_fleet_stock_growth=0,c121_territory_first=0,c121_aaa_line=0,c121_air_engine_realization=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c121_air_initial_project_economics=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c122_air_regime_priority=0,c122_air_regime_shadow=0,c122_air_threat_probe=0,b9_air_demand_shadow=0]'
$var = 'OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_catalog_incremental=1,c121_air_decision_depth_economics=0,c121_air_portfolio_depth_economics=0,c121_air_portfolio_split_economics=0,c121_air_first_live_growth=0,c121_air_first_live_shadow=0,c121_air_first_observation_growth=0,c121_air_observation_growth=0,c121_fleet_stock_growth=0,c121_territory_first=0,c121_aaa_line=0,c121_air_engine_realization=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_defensive_floor=0,c121_air_initial_project_economics=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c122_air_regime_priority=0,c122_air_regime_shadow=0,c122_air_threat_probe=0,b9_air_demand_shadow=0]'

python -X utf8 sweeps/run_c66_reference.py `
  --campaign c121_autopsy_base_3x6_20261002_r1 `
  --policy-id c115_reference `
  --reference $ref `
  --variant $var `
  --variant-policy-id c121_current `
  --primary-metric profit_year `
  --min-useful-primary-delta 50000 `
  --value-guard-max-loss-pct 5 `
  --years 6 `
  --seeds 42 100 999 `
  --repeats 1 `
  --max-workers 3 `
  --engine-timeout 1800 `
  --line-telemetry `
  --line-telemetry-monthly `
  --cpus 3 `
  --memory 2g

exit $LASTEXITCODE
