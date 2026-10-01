"""Bounded exposure/perturbation diagnostic, NOT a policy qualification.

Only existing probe settings differ. The reference has no extra probe; script=4
is shared. `probe` in the reused report denotes the optional --probe CLI switch,
not the per-arm settings (the authority is resolved_arms).
Use --years 1 --seeds 42 --workers 2 for the pre-registered integration smoke.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diag_cadence_duel import main as run_diagnostic

PROBES = ("decision_log", "probe_portfolio", "probe_scheduler",
          "probe_candidates_rail", "catalog_cost_probe", "probe_events",
          "probe_catalogue")  # OpexC39Log gates the C41 profile emissions.
ARMS = {
    "reference": "OpexAI",
    "profile": "OpexAI[" + ",".join(f"{key}=1" for key in PROBES) + "]",
}
PURPOSE = "instrumentation_exposure_and_perturbation_only_not_policy_qualification"


def main():
    run_diagnostic(arm_specs=ARMS, purpose=PURPOSE, force_debug=True)


if __name__ == "__main__":
    main()