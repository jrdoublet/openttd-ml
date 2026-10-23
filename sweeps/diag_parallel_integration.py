"""Bounded exposure/perturbation diagnostic, NOT a policy qualification.

Only the existing 31-bit probes mask differs. The reference has no extra probe; script=4
is shared. `probe` in the reused report denotes the optional --probe CLI switch,
not the per-arm settings (the authority is resolved_arms).
Use --years 1 --seeds 42 --workers 2 for the pre-registered integration smoke.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diag_cadence_duel import main as run_diagnostic

PROBES = {"decision_log": 256, "probe_portfolio": 131072,
          "probe_scheduler": 1024, "probe_candidates_rail": 16384,
          "probe_events": 1048576, "probe_catalogue": 32768}
# C39 invalidation logging requires the catalogue bit. Preserve default signs bit 2.
PROFILE_MASK = 2 | sum(PROBES.values())
ARMS = {
    "reference": "OpexAI",
    "profile": f"OpexAI[probes={PROFILE_MASK}]",
}
PURPOSE = "instrumentation_exposure_and_perturbation_only_not_policy_qualification"


def main():
    run_diagnostic(arm_specs=ARMS, purpose=PURPOSE, force_debug=True)


if __name__ == "__main__":
    main()
