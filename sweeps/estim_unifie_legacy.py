"""Strict OFF source projection of ESTIM-1 bits 1, 2, 4 and 8.

The reviewed reverse hunks live in ``estim_unifie_off_lots.py``. This module
keeps the existing ``estim_off``/``estim_off_bytes`` API for callers such as
``n75_mc_legacy.historical_bytes``. No git command is run during projection.
"""

from estim_unifie_off_lots import PATCHES, estim_off, estim_off_bytes


# Existing tests and historical-projection callers iterate this mapping.
# The contents are (current source, HEAD source) unified-diff hunks, per file.
EDITS = PATCHES
