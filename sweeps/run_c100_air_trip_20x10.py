#!/usr/bin/env python3
"""C100 : host launcher for paired 20x10 qualification."""

from __future__ import annotations

import sys

import run_c66_reference as launcher


if __name__ == "__main__":
    sys.argv = [
        sys.argv[0], "--campaign", "c100_air_trip_physical_vs_default_20x10_20260926",
        "--years", "10",
        "--seeds", "42", "100", "7", "999", "2026", "1", "17", "73", "314", "512",
        "1024", "1337", "4096", "8191", "12345", "54321", "65537", "123456", "424242", "8675309",
        "--max-workers", "10", "--cpus", "10", "--memory", "12g",
        "--reference", "OpexAI[c100_air_trip_physical=0]",
        "--variant", "OpexAI[c100_air_trip_physical=1]",
        "--policy-id", "c100_ref", "--variant-policy-id", "c100_physical",
        "--primary-metric", "profit_year", "--min-useful-primary-delta", "50000",
        "--value-guard-max-loss-pct", "5",
        "--out", "results/c100_air_trip_physical_vs_default_20x10_20260926.json",
    ]
    launcher.main()
