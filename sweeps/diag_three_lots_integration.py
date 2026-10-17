"""Central wrapper for the lightweight selection probe (amortisation shadow removed 17/10)."""
import argparse
import sys

LIGHT_ARMS = {"reference": "OpexAI", "light": "OpexAI[catalog_cost_probe=1]"}


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--lot", choices=("light",), required=True)
    args, rest = parser.parse_known_args()
    if any(arg == "--probe" or arg.startswith("--probe=") for arg in rest):
        parser.error("Broad probes forbidden: interventions must stay separate")
    from sweeps import diag_cadence_duel as shared
    from sweeps import bench_v2
    arms = LIGHT_ARMS
    for resolved in bench_v2.resolved_arm_settings(list(arms.values())).values():
        effective = resolved["settings"]["effective"]
        protected = {}
        removed = ("r19_fault_inject", "c84_air_target_fleet", "c85_air_equipment_frontier", "exp_scheduler_skip_not_due",
                   "exp_air_hub_pair_prefilter")
        if any(effective.get(key) != value for key, value in protected.items()):
            raise ValueError("Protected default drift")
        if any(key in effective for key in removed):
            raise ValueError("Removed setting still exposed")
    sys.argv = [sys.argv[0], *rest]
    shared.main(arm_specs=arms, force_debug=True,
                purpose=f"three_lots_{args.lot}_exposure_not_economic_qualification")


if __name__ == "__main__":
    main()