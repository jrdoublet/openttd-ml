#!/usr/bin/env python3
import runpy
import sys


sys.argv = [
    "sweeps/run_c66_reference.py",
    "--campaign", "rail_origin_reuse_onepass_autopsy_4x5_20261005_r4",
    "--reference", "OpexAI[decision_log=1,rail_geometry_guard=1,rail_origin_reuse=0]",
    "--variant", "OpexAI[decision_log=1,rail_geometry_guard=1,rail_origin_reuse=1,rail_origin_reuse_fallback=1,rail_origin_reuse_pax=0]",
    "--policy-id", "reference",
    "--variant-policy-id", "origin_reuse_freight_onepass",
    "--primary-metric", "profit_year",
    "--decision-rule", "gain_short",
    "--min-useful-primary-delta-pct", "4",
    "--value-guard-max-loss-pct", "5",
    "--required-seeds", "4",
    "--required-years", "5",
    "--years", "5",
    "--seeds", "999", "802204", "983759", "230185",
    "--repeats", "1",
    "--max-workers", "10",
    "--cpus", "10",
    "--memory", "8g",
    "--script-debug",
    "--out", "results/rail_origin_reuse_onepass_autopsy_4x5_20261005_r4.json",
]

runpy.run_path("sweeps/run_c66_reference.py", run_name="__main__")
