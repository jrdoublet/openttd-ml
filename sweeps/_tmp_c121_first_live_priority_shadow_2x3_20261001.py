#!/usr/bin/env python3
"""2x3 passive opportunity-cost probe for C121 first-live growth."""

import sys
import run_c66_reference as launcher
from _tmp_c121_first_live_growth_5x6_20261001 import argv


if __name__ == "__main__":
    sys.argv = argv(
        "c121_first_live_priority_shadow_2x3_20261001_r1",
        3, (42, 100), 4, 4,
    )
    launcher.main()
