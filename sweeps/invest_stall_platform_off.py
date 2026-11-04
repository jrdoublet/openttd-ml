"""Remove only the reviewed INVEST-STALL platform development layer.

The new snapshot records the dirty worktree before this development. All older
fixtures remain immutable. Context hunks allow unrelated older opt-ins to be
projected first; modified, missing or duplicated new hunks are rejected.
"""

import hashlib
import json
from pathlib import Path
from invest_stall_diagnostic_off import off_source as diagnostic_off
from rail_long_v3_multi_off import upgrade_reservation_off


FIXTURE = Path(__file__).parent / "fixtures" / "invest_stall_platform_off_20261104.json"


def off_source(name, source):
    source = upgrade_reservation_off(name, diagnostic_off(name, source))
    entry = json.loads(FIXTURE.read_text(encoding="utf8"))["files"].get(name)
    if entry is None:
        return source
    edits = entry["edits"]
    present = [edit["after"] in source for edit in edits]
    if not any(present):
        if entry["marker"] in source:
            raise AssertionError(f"INVEST-STALL platform {name}: unknown layer")
        return source
    digest = hashlib.sha256(source.encode("utf8")).hexdigest()
    for edit in reversed(edits):
        if source.count(edit["after"]) != 1:
            raise AssertionError(f"INVEST-STALL platform {name}: missing or duplicated hunk")
        source = source.replace(edit["after"], edit["before"], 1)
    if entry["marker"] in source:
        raise AssertionError(f"INVEST-STALL platform {name}: residual marker")
    if digest == entry["after_sha256"]:
        if hashlib.sha256(source.encode("utf8")).hexdigest() != entry["before_sha256"]:
            raise AssertionError(f"INVEST-STALL platform {name}: historical bytes changed")
    return source
