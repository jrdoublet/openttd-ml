"""Lecture textuelle de builder_air.nut et de ses modules AIR extraits (R11).

builder_air.nut charge ses modules metier par `require("air_*.nut");`. Pour les
contrats textuels, chaque require d'un module extrait est remplace par le corps
du module, sans sa ligne d'en-tete : le texte obtenu est l'ancien builder_air.nut
octet pour octet, ordre des fonctions compris. Les autres require (par exemple
air_recovery.nut) restent intacts.
"""
from pathlib import Path
import re

AI_DIR = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
MODULE_HEADER = "/* Module AIR extrait de builder_air.nut"
_REQUIRE = re.compile(r'require\("(air_[a-z0-9_]+\.nut)"\);\n')


def _expand(match: re.Match) -> str:
    text = (AI_DIR / match.group(1)).read_text(encoding="utf-8")
    if not text.startswith(MODULE_HEADER):
        return match.group(0)
    return text.split("\n", 1)[1]


def read_builder_air() -> str:
    return _REQUIRE.sub(_expand, (AI_DIR / "builder_air.nut").read_text(encoding="utf-8"))
