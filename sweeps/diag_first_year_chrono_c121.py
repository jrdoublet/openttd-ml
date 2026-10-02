"""Chronologie de la premiere annee d'OpexAI sous C121 (diagnostic, pas un banc d'adoption).

Bras « reference » : C121 (c121_air_economics + c121_catalog_incremental) + probe_scheduler
et catalog_cost_probe. Bras « light » : C121 sans sonde, temoin de perturbation. Duel contre
AAAHogEx-115, journal de script force (-d script=4). Variable OPEX_CHRONO_EXTRA : reglages
ajoutes au bras reference (ex. « probe_span_trace=1 »).
Usage : python3 -m sweeps.diag_first_year_chrono_c121 --years 1 --out results/<nom>.json
"""
import os

C121 = "c121_air_economics=1,c121_catalog_incremental=1"


def main():
    from sweeps import diag_cadence_duel as shared
    extra = os.environ.get("OPEX_CHRONO_EXTRA", "").strip(",")
    probes = "probe_scheduler=1,catalog_cost_probe=1" + ("," + extra if extra else "")
    arms = {
        "reference": f"OpexAI[{C121},{probes}]",
        "light": f"OpexAI[{C121}]",
    }
    shared.main(arm_specs=arms, force_debug=True, purpose="diagnostic_first_year_chronology_c121_not_adoption")


if __name__ == "__main__":
    main()
