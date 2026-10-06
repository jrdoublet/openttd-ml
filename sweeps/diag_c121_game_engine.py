"""Diagnostic C121 « avion de la partie » (pas un banc d'adoption).

Bras « ref » : C121 incremental avec scan moteur complet
(c121_air_game_engine=0, le defaut etant 1). Bras « game_engine » : meme C121 plus
c121_air_game_engine=1. Variable OPEX_GE_EXTRA : reglages ajoutes aux DEUX
bras (ex. « probe_c121_engine_table=1 »).
Usage : python3 -m sweeps.diag_c121_game_engine --years 1 --out results/<nom>.json
"""
import os

C121 = "c121_air_economics=1,c121_catalog_incremental=1"
ARMS = {
    "ref": "OpexAI[c121_air_economics=1,c121_catalog_incremental=1,c121_air_game_engine=0]",
    "game_engine": "OpexAI[c121_air_economics=1,c121_catalog_incremental=1,c121_air_game_engine=1]",
}


def main():
    from sweeps import diag_cadence_duel as shared
    extra = os.environ.get("OPEX_GE_EXTRA", "").strip(",")
    suffix = "," + extra if extra else ""
    ref = ARMS["ref"][:-1] + suffix + "]" if extra else ARMS["ref"]
    variant = ARMS["game_engine"][:-1] + suffix + "]" if extra else ARMS["game_engine"]
    # shared.main apparie contre le bras nomme « reference ».
    arms = {
        "reference": ref,
        "game_engine": variant,
    }
    shared.main(arm_specs=arms, force_debug=True, purpose="diagnostic_c121_game_engine_not_adoption")


if __name__ == "__main__":
    main()
