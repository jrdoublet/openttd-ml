#!/usr/bin/env python3
"""C121 anti-monopoly floor exemption: paired 42/100 x 6y probe."""

import sys
import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_defensive_floor_42_100_6y_20260929",
        "--years", "6",
        "--seeds", "42", "100",
        "--max-workers", "4", "--cpus", "6", "--memory", "8g",
        "--reference", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0]",
        "--variant", "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=1,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,b9_air_demand_shadow=0]",
        "--policy-id", "c115_reference",
        "--variant-policy-id", "c121_causal",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--line-telemetry",
        "--script-debug",
        "--out", "results/c121_defensive_floor_42_100_6y_20260929.json",
    ]
    launcher.main()
