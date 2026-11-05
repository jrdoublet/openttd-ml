"""Retire le seul raffinement v2-r2, identique aux octets du bundle v2-r1.

Idempotent et fail-closed, sans aucun recalcul des SHA dans les tests.
"""

import hashlib
import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "invest_stall_v2_r2_off_20261103.json"


def off_source(name, source):
    from invest_stall_merged_off import project_merge_stage
    merged = project_merge_stage(name, source, "r2")
    if merged is not None:
        return merged
    entry = json.loads(FIXTURE.read_text(encoding="utf8"))["files"].get(name)
    if entry is None:
        return source
    digest = hashlib.sha256(source.encode("utf8")).hexdigest()
    # L'idempotence du projecteur composé accepte aussi les octets R1
    # déjà projetés à travers les DEUX couches, mais rien d'autre.
    r1 = json.loads((FIXTURE.parent / "invest_stall_v2_off_20261103.json")
                    .read_text(encoding="utf8"))["files"][name]["before_sha256"]
    if digest in (entry["before_sha256"], r1):
        return source
    if digest != entry["after_sha256"]:
        raise AssertionError(f"INVEST-STALL v2-r2 {name}: hunk non revu {digest}")
    rows = source.splitlines(keepends=True)
    for edit in reversed(entry["edits"]):
        at = edit["after_start"]
        end = at + len(edit["after"])
        if rows[at:end] != edit["after"]:
            raise AssertionError(f"INVEST-STALL v2-r2 {name}: ancre modifiée à {at + 1}")
        rows[at:end] = edit["before"]
    restored = "".join(rows)
    if hashlib.sha256(restored.encode("utf8")).hexdigest() != entry["before_sha256"]:
        raise AssertionError(f"INVEST-STALL v2-r2 {name}: projection non identique")
    return restored
