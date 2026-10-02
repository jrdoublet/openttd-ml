"""Profil d'opcodes sous C121 (diagnostic, pas un banc d'adoption).

Bras « reference » : C121 + toutes les sondes de cout (probe_loop_ops, probe_scheduler,
catalog_cost_probe). Bras « light » : C121 + probe_loop_ops + catalog_cost_probe seulement,
pour mesurer la perturbation de probe_scheduler sur les agregats de boucle.
Usage : python3 sweeps/diag_opcode_profile.py --out results/<nom>.json [options diag_cadence_duel]
"""
C121 = "c121_air_economics=1,c121_catalog_incremental=1"
import os
ONLY_LIGHT = os.environ.get("OPPROF_ONLY_LIGHT") == "1"


def main():
    from sweeps import diag_cadence_duel as shared
    arms = {
        "reference": f"OpexAI[{C121},probe_loop_ops=1,probe_scheduler=1,catalog_cost_probe=1]",
        "light": f"OpexAI[{C121},probe_loop_ops=1,catalog_cost_probe=1]",
    }
    if ONLY_LIGHT:
        # Sous-profil : un seul bras leger, nomme reference pour le collecteur partage.
        arms = {"reference": arms["light"]}
    shared.main(arm_specs=arms, force_debug=True, purpose="diagnostic_opcode_profile_c121_not_adoption")


if __name__ == "__main__":
    main()
