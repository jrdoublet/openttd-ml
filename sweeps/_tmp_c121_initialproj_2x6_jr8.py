#!/usr/bin/env python3
"""C121 initial-project economics isolation: paired seeds 42/1234 x 6 years."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    common = "c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_engine_realization=0,c121_air_project_realization=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0"
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_initialproj_2x6_jr8_20260929",
        "--years", "6",
        "--seeds", "42", "1234",
        "--max-workers", "4", "--cpus", "4", "--memory", "6g",
        "--reference", "OpexAI[" + common + ",c121_air_initial_project_economics=0]",
        "--variant", "OpexAI[" + common + ",c121_air_initial_project_economics=1]",
        "--policy-id", "c121_current",
        "--variant-policy-id", "c121_initial_project",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--script-debug",
        "--out", "results/c121_initialproj_2x6_jr8_20260929.json",
    ]
    launcher.main()
