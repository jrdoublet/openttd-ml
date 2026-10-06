#!/usr/bin/env python3
"""Smoke causal C121 first-live balanced90 on seed 42."""

import sys
import run_c66_reference as launcher
from _tmp_c121_first_live_growth_5x6_20261001 import argv


if __name__ == "__main__":
    sys.argv = argv(
        "c121_first_live_growth_bal90_smoke_seed42_3y_20261001_r1",
        3, (42,), 2, 2,
    )
    launcher.main()
