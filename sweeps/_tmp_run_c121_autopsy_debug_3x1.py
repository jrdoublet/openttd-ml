from __future__ import annotations

import subprocess
import sys


REF = (
    "OpexAI[c115_air_c100_capital_replay=1,c121_air_economics=0,c121_catalog_incremental=0,"
    "c121_air_decision_depth_economics=0,c121_air_portfolio_depth_economics=0,"
    "c121_air_portfolio_split_economics=0,c121_air_first_live_growth=0,"
    "c121_air_first_live_shadow=0,c121_air_first_observation_growth=0,"
    "c121_air_observation_growth=0,c121_fleet_stock_growth=0,c121_territory_first=0,"
    "c121_aaa_line=0,c121_air_engine_realization=0,c121_air_project_realization=0,"
    "c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,"
    "c121_air_defensive_floor=0,c121_air_initial_project_economics=0,"
    "c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,"
    "c122_air_regime_priority=0,c122_air_regime_shadow=0,c122_air_threat_probe=0,"
    "b9_air_demand_shadow=0]"
)
VAR = REF.replace("c121_air_economics=0", "c121_air_economics=1").replace(
    "c121_catalog_incremental=0", "c121_catalog_incremental=1"
)


def main() -> int:
    cmd = [
        sys.executable, "-X", "utf8", "sweeps/run_c66_reference.py",
        "--campaign", "c121_autopsy_debug_3x1_20261002_r1",
        "--policy-id", "c115_reference",
        "--reference", REF,
        "--variant", VAR,
        "--variant-policy-id", "c121_current",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "1",
        "--seeds", "42", "100", "999",
        "--repeats", "1",
        "--max-workers", "3",
        "--engine-timeout", "900",
        "--line-telemetry", "--line-telemetry-monthly", "--script-debug",
        "--cpus", "3", "--memory", "2g",
    ]
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
