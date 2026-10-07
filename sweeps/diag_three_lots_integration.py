"""Central wrappers: separate lightweight and amortisation interventions."""
import argparse
import sys

LIGHT_ARMS = {"reference": "OpexAI", "light": "OpexAI[catalog_cost_probe=1]"}
SHADOW_ARMS = {"reference": "OpexAI", "calculate": "OpexAI[fleet_amort_shadow_probe=1]",
               "snapshot": "OpexAI[fleet_amort_shadow_probe=2]"}


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--lot", choices=("light", "shadow"), required=True)
    args, rest = parser.parse_known_args()
    if any(arg == "--probe" or arg.startswith("--probe=") for arg in rest):
        parser.error("Broad probes forbidden: interventions must stay separate")
    from sweeps import diag_cadence_duel as shared
    from sweeps import bench_v2
    arms = LIGHT_ARMS if args.lot == "light" else SHADOW_ARMS
    for resolved in bench_v2.resolved_arm_settings(list(arms.values())).values():
        effective = resolved["settings"]["effective"]
        protected = {"c115_air_c100_capital_replay": 1, "c84_air_target_fleet": 0,
                     "c85_air_equipment_frontier": 0, "c121_air_economics": 0,
                     "c122_air_regime_priority": 0, "r19_fault_inject": 0,
                     "exp_scheduler_skip_not_due": 0,
                     "exp_air_hub_pair_prefilter": 0}
        if any(effective.get(key) != value for key, value in protected.items()):
            raise ValueError("Protected default drift")
    sys.argv = [sys.argv[0], *rest]
    shared.main(arm_specs=arms, force_debug=True,
                purpose=f"three_lots_{args.lot}_exposure_not_economic_qualification")


if __name__ == "__main__":
    main()