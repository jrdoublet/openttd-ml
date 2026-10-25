"""Chronologie de la premiere annee d'OpexAI sous C121 (diagnostic, pas un banc d'adoption).

Bras « reference » : C121 + probe_scheduler. Bras « light » : C121 sans sonde,
temoin de perturbation. Duel contre
AAAHogEx-115, journal de script force (-d script=4). Variable OPEX_CHRONO_EXTRA : reglages
ajoutes au bras reference (ex. « probes=4098 » pour activer span_trace).
Usage : python3 -m sweeps.diag_first_year_chrono_c121 --years 1 --out results/<nom>.json
"""
import os



def main():
    from sweeps import diag_cadence_duel as shared
    extra = os.environ.get("OPEX_CHRONO_EXTRA", "").strip(",")
    extras = [item for item in extra.split(",") if item]
    mask = 1026
    remaining = []
    for setting in extras:
        if setting.startswith("probes="):
            mask |= int(setting.split("=", 1)[1])
        else:
            remaining.append(setting)
    probes = "probes=" + str(mask) + ("," + ",".join(remaining) if remaining else "")
    arms = {
        "reference": f"OpexAI[{probes}]",
        "light": "OpexAI",
    }
    shared.main(arm_specs=arms, force_debug=True, purpose="diagnostic_first_year_chronology_c121_not_adoption")


if __name__ == "__main__":
    main()
