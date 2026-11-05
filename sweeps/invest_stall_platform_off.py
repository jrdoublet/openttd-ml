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
    from fleet_arb_off import off_source as fleet_off
    source = fleet_off(name, source)
    source = upgrade_reservation_off(name, diagnostic_off(name, source))
    entry = json.loads(FIXTURE.read_text(encoding="utf8"))["files"].get(name)
    if entry is None:
        return source
    # The merged ROAD1Y+RAIL task_rail.nut has independent historical repair
    # edits. Its INVEST-STALL platform hunk is unchanged, but whole-file SHA
    # differs from the 04/11 RAIL-only witness. Keep both witnesses immutable.
    from invest_stall_merged_off import MERGED
    merged = MERGED.get("platform", {}).get(name)
    if merged is not None:
        frozen_digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        if frozen_digest != MERGED["historical_fixture_sha256"]["platform"]:
            raise AssertionError("INVEST-STALL platform historical fixture changed")
        source_sha = hashlib.sha256(source.encode("utf8")).hexdigest()
        allowed = (merged["on_sha256"], merged["off_sha256"],
                   entry["after_sha256"], entry["before_sha256"])
        if source_sha in (merged["already_absent_sha256"]
                          + merged["historical_absent_sha256"]):
            # DOUBLE-GROW's reviewed rollback already removes this same
            # platform hunk. Only these exact independently projected bytes
            # are accepted as an absent layer, never a guessed near-match.
            if entry["marker"] in source or any(
                    edit["after"] in source for edit in entry["edits"]):
                raise AssertionError(f"INVEST-STALL platform {name}: incomplete OFF layer")
            return source
        if source_sha not in allowed:
            raise AssertionError(f"INVEST-STALL platform {name}: unreviewed merged SHA")
        if source_sha == merged["off_sha256"]:
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
    if merged is not None and digest == merged["on_sha256"]:
        if hashlib.sha256(source.encode("utf8")).hexdigest() != merged["off_sha256"]:
            raise AssertionError(f"INVEST-STALL platform {name}: merged bytes changed")
    return source
