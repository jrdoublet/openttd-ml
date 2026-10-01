"""Source textuelle de projects.nut avec ses sous-fichiers projects_*.nut (R14).

projects.nut requiert ses etapes via ``require("projects_*.nut");``. Pour les tests
textuels, chaque ligne require est remplacee sur place par le contenu du fichier
requis : l'ordre historique de definition est ainsi conserve.
"""
from __future__ import annotations

import re
from pathlib import Path

AI_DIR = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
_REQUIRE = re.compile(r'^require\("(projects_[A-Za-z0-9_]+\.nut)"\);[ \t]*$', re.M)


def read_projects_source(ai_dir: Path | None = None) -> str:
    base = Path(ai_dir) if ai_dir is not None else AI_DIR
    text = (base / "projects.nut").read_text(encoding="utf-8")
    return _REQUIRE.sub(lambda m: (base / m.group(1)).read_text(encoding="utf-8"), text)
