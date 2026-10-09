#!/usr/bin/env python3
"""P0 : banc Save/Load existant avec des dossiers temporaires uniques.

La suite generique supprime ses propres phaseA_saves/phaseB_saves. Lui fournir
des emplacements propres evite de detruire les resultats de travaux simultanes.
"""
from pathlib import Path

import save_load_roundtrip as runner


runner.WORK_DIR = Path("/work/.scratch_saveload_p0_capital_20261009_r1")
runner.CACHE_DIR = runner.WORK_DIR / "cache"

if __name__ == "__main__":
    runner.main()
