#!/usr/bin/env python3
"""C121 cadence: A/A control for shared-duel variance on seed 5678."""

import sys

import run_c66_reference as launcher
from _tmp_c121_first_live_air_priority_immediate_5x6_20261001 import REFERENCE


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--campaign", "c121_first_live_aa_seed5678_6y_20261001_r1",
        "--reference", REFERENCE,
        "--policy-id", "c121_first_live_aa_ref",
        "--variant", REFERENCE,
        "--variant-policy-id", "c121_first_live_aa_copy",
        "--primary-metric", "profit_year",
        "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--years", "6",
        "--seeds", "5678",
        "--repeats", "3",
        "--max-workers", "6", "--cpus", "6", "--memory", "8g",
        "--line-telemetry", "--script-debug",
    ]
    launcher.main()
