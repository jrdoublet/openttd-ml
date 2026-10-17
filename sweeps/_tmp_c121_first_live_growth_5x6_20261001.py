#!/usr/bin/env python3
"""C121 cadence: causal 5x6 of balanced90 live-evidence first 1->2 growth."""

import sys

import run_c66_reference as launcher
BASE = "OpexAI[c121_air_economics=1,c121_air_project_realization_adaptive=0,c121_air_pressure_probe=0,c121_air_economics_shadow=0,c121_air_engine_replay_shadow=0,c122_air_regime_shadow=0,c122_air_threat_probe=0,b9_air_demand_shadow=0]"

REFERENCE = BASE[:-1] + ",c121_air_first_live_shadow=1]"
VARIANT = BASE[:-1] + ",c121_air_first_live_shadow=1]"

if __name__ == "__main__":
    raise SystemExit("V237: first-live growth is permanent; the historical OFF/ON campaign is retired")
