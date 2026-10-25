"""Profil d'opcodes sous C121 (diagnostic, pas un banc d'adoption).

Bras « reference » : C121 + bits probe_loop_ops (2048) et probe_scheduler (1024).
Bras « light » : C121 + bit probe_loop_ops seulement,
pour mesurer la perturbation du canal scheduler sur les agregats de boucle.
Usage : python3 sweeps/diag_opcode_profile.py --out results/<nom>.json [options diag_cadence_duel]
"""
import os
ONLY_LIGHT = os.environ.get("OPPROF_ONLY_LIGHT") == "1"


def main():
    from sweeps import diag_cadence_duel as shared
    arms = {
        "reference": "OpexAI[probes=3074]",
        "light": "OpexAI[probes=2050]",
    }
    if ONLY_LIGHT:
        # Sous-profil : un seul bras leger, nomme reference pour le collecteur partage.
        arms = {"reference": arms["light"]}
    shared.main(arm_specs=arms, force_debug=True, purpose="diagnostic_opcode_profile_c121_not_adoption")


if __name__ == "__main__":
    main()
