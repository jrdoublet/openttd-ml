#!/usr/bin/env python3
import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    common = "c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_engine_realization=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_defensive_floor=0,c121_air_initial_project_economics=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0"
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_pressure_phase_5x2_20260929",
        "--years", "2",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "6", "--cpus", "6", "--memory", "8g",
        "--reference", "OpexAI[" + common + ",c121_air_pressure_probe=0]",
        "--variant", "OpexAI[" + common + ",c121_air_pressure_probe=1]",
        "--policy-id", "c121_current",
        "--variant-policy-id", "c121_pressure_probe",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--script-debug",
        "--out", "results/c121_pressure_phase_5x2_20260929.json",
    ]
    launcher.main()
