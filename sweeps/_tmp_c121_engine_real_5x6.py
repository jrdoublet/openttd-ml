#!/usr/bin/env python3
"""C121 engine-realization-only qualification: canonical 5x6."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_engine_real_5x6_20260929",
        "--years", "6",
        "--seeds", "42", "100", "999", "1234", "5678",
        "--max-workers", "6", "--cpus", "6", "--memory", "8g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_engine_realization=0,c121_air_project_realization=0,c121_air_defensive_floor=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_engine_realization=1,c121_air_project_realization=0,c121_air_defensive_floor=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0]",
        "--policy-id", "c121_current",
        "--variant-policy-id", "c121_engine_realization",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--script-debug",
        "--out", "results/c121_engine_real_5x6_20260929.json",
    ]
    launcher.main()
