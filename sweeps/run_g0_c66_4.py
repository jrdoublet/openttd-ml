"""Autorite C66.4 G0, pre-enregistree apres le diagnostic factoriel 5x6.

Reference livree : abandon_gen_filter=1, abandon_cooldown_days=365.
Candidat : abandon_gen_filter=0, abandon_cooldown_days=0.
early_slot reste 1 dans les deux politiques.
"""
from pathlib import Path
import runpy
import sys


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]

sys.argv = [
    "bench_1v1_5y_20seeds.py",
    "--years", "10",
    "--max-workers", "6",
    "--campaign", "review_g0_c66_4_20x10",
    "--policy-id", "g0_current_1_365",
    "--reference",
    "OpexAI[air_early_slot=1,abandon_gen_filter=1,abandon_cooldown_days=365]",
    "--variant",
    "OpexAI[air_early_slot=1,abandon_gen_filter=0,abandon_cooldown_days=0]",
    "--variant-policy-id", "g0_candidate_0_0",
    "--primary-metric", "profit_year",
    "--min-useful-primary-delta", "50000",
    "--value-guard-max-loss-pct", "5",
    "--out", str(ROOT / "results" / "review_g0_c66_4_20x10.json"),
]

runpy.run_path(str(ROOT / "sweeps" / "bench_1v1_5y_20seeds.py"), run_name="__main__")
