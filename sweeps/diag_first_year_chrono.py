"""Chronologie de la premiere annee d'OpexAI (diagnostic, pas un banc d'adoption).

Bras « reference » : defaut + probes=1026 (lignes SCHED_IDLE datees, tache par tache)
et catalog_cost_probe. Bras « light » : defaut sans sonde, temoin de perturbation des
dates de construction. Duel contre AAAHogEx-115, journal de script force (-d script=4).
Usage : python3 sweeps/diag_first_year_chrono.py --years 1 --out results/<nom>.json
"""


def main():
    from sweeps import diag_cadence_duel as shared
    arms = {
        "reference": "OpexAI[probes=1026]",
        "light": "OpexAI",
    }
    shared.main(arm_specs=arms, force_debug=True, purpose="diagnostic_first_year_chronology_not_adoption")


if __name__ == "__main__":
    main()
