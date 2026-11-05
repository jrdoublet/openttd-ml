"""Projection stricte des correctifs INVEST-STALL v3 sur le bundle moteur R1.

Les hunks et SHA sont figes dans fixtures/invest_stall_v3_off_20261103.json.
La projection est appliquée avant les projecteurs v2-r2 et v2 ; aucune
empreinte historique n'est modifiée ni recalculée par cette fonction.
"""

import hashlib
import json
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "invest_stall_v3_off_20261103.json"


def off_source(name, source):
    from invest_stall_merged_off import project_merge_stage
    merged = project_merge_stage(name, source, "v3")
    if merged is not None:
        return merged
    entry = json.loads(FIXTURE.read_text(encoding="utf8"))["files"].get(name)
    if entry is None:
        return source
    digest = hashlib.sha256(source.encode("utf8")).hexdigest()
    # Le projecteur complet est idempotent même après projection de TOUTES
    # les couches anciennes, dont le SHA est gelé dans BEFORE.
    from invest_stall_source_off import BEFORE
    if digest in (entry["before_sha256"], BEFORE[name]):
        return source
    if digest != entry["after_sha256"]:
        raise AssertionError(f"INVEST-STALL v3 {name}: modification non revue {digest}")
    rows = source.splitlines(keepends=True)
    for change in reversed(entry["edits"]):
        at = change["after_start"]
        stop = at + len(change["after"])
        if rows[at:stop] != change["after"]:
            raise AssertionError(f"INVEST-STALL v3 {name}: ancre non identique {at + 1}")
        rows[at:stop] = change["before"]
    restored = "".join(rows)
    if hashlib.sha256(restored.encode("utf8")).hexdigest() != entry["before_sha256"]:
        raise AssertionError(f"INVEST-STALL v3 {name}: projection modifie les octets historiques")
    return restored
