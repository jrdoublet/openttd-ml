"""Projection stricte INVEST-STALL v2 vers le bundle R1 du 3 novembre 2026.

Le manifeste figé contient les hunks *before*/*after*, leurs positions dans
le fichier v2, et les SHA avant/après. La projection n'est autorisée que sur
les octets v2 exactement contrôlés : une édition imprévue échoue fermée.
Les sources R1 figées sont celles du bundle du smoke R1, jamais recalculées
depuis le worktree courant par les tests.
"""

import hashlib
import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "invest_stall_v2_off_20261103.json"


def _fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf8"))


def off_source(name, source):
    from fleet_arb_off import off_source as fleet_off
    source = fleet_off(name, source)
    """Restitue exactement la source pré-v2 ou lève en cas de dérive.

    Cette fonction est idempotente pour une source déjà projetée. Les hunks
    sont restaurés en ordre inverse de leurs positions (non-relocalisables).
    """
    from invest_stall_merged_off import project_merge_stage
    merged = project_merge_stage(name, source, "v2")
    if merged is not None:
        return merged
    entry = _fixture()["files"].get(name)
    if entry is None:
        return source
    digest = hashlib.sha256(source.encode("utf8")).hexdigest()
    if digest == entry["before_sha256"]:
        return source
    if digest != entry["after_sha256"]:
        raise AssertionError(f"INVEST-STALL v2 {name}: modification non revue {digest}")
    lines = source.splitlines(keepends=True)
    for hunk in reversed(entry["edits"]):
        start = hunk["after_start"]
        end = start + len(hunk["after"])
        if lines[start:end] != hunk["after"]:
            raise AssertionError(f"INVEST-STALL v2 {name}: hunk invalide à {start + 1}")
        lines[start:end] = hunk["before"]
    projected = "".join(lines)
    if hashlib.sha256(projected.encode("utf8")).hexdigest() != entry["before_sha256"]:
        raise AssertionError(f"INVEST-STALL v2 {name}: projection non identique au bundle R1")
    return projected
