#!/usr/bin/env python3
"""C122.3 causal smoke with matched passive classifier/annotation overhead."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    shared = "c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c121_air_project_realization=0,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=1,c121_air_defensive_floor=0,b9_air_demand_shadow=0"
    sys.argv = [
        sys.argv[0],
        "--campaign", "c122_3_shadow_control_smoke_seed42_1x3_20260929_r3",
        "--years", "3",
        "--seeds", "42",
        "--max-workers", "1", "--cpus", "1", "--memory", "4g",
        "--reference", f"OpexAI[{shared},c122_air_regime_priority=0]",
        "--variant", f"OpexAI[{shared},c122_air_regime_priority=1]",
        "--policy-id", "c121_shadow_classifier_control",
        "--variant-policy-id", "c122_3_regime_priority",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--script-debug",
        "--out", "results/c122_3_shadow_control_smoke_seed42_1x3_20260929_r3.json",
    ]
    launcher.main()
