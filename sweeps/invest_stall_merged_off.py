"""Strict bridge for INVEST-STALL's pre-merge, whole-file SHA witnesses.

The 3 November v2/v2-r2/v3 fixtures were captured from the RAIL-only tree.
ROAD1Y additions on master survive the merge and change surrounding offsets
and full-file hashes, even though the actual INVEST-STALL edits remain intact.

This bridge does *not* replace or rebase those historical witnesses. It accepts
only the individually reviewed SHA transitions from the exact 5 November
ROAD1Y+RAIL merge, applies the frozen original hunks at unique byte anchors,
then proves the exact SHA of the resulting merged source. Unknown or partially
modified input falls back to the original, strictly fail-closed projectors.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parent / "fixtures"
MERGED_FIXTURE = ROOT / "invest_stall_merged_20261105.json"
FROZEN = {
    "v3": ROOT / "invest_stall_v3_off_20261103.json",
    "r2": ROOT / "invest_stall_v2_r2_off_20261103.json",
    "v2": ROOT / "invest_stall_v2_off_20261103.json",
}
MERGED = json.loads(MERGED_FIXTURE.read_text(encoding="utf-8"))


def _sha(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _frozen_edits(name, stage):
    fixture = FROZEN[stage]
    expected = MERGED["historical_fixture_sha256"][stage]
    if hashlib.sha256(fixture.read_bytes()).hexdigest() != expected:
        raise AssertionError(f"INVEST-STALL merge: historical {stage} fixture changed")
    entry = json.loads(fixture.read_text(encoding="utf-8"))["files"].get(name)
    if entry is None:
        raise AssertionError(f"INVEST-STALL merge: absent historical {stage} file {name}")
    return entry["edits"]


def merged_off_sha(name):
    """The *merged* OFF witness, not the historical pre-merge SHA."""
    entry = MERGED["files"].get(name)
    return None if entry is None else entry["off_sha256"]


def already_merged_off(name, source):
    witness = merged_off_sha(name)
    if witness is None:
        return False
    digest = _sha(source)
    if digest == witness:
        return True
    return any(
        digest == row["off_sha256"]
        for row in MERGED["files"][name].get("variants", {}).values()
    )


def project_merge_stage(name, source, stage):
    """Apply one precisely reviewed merged SHA transition or return None.

    None means that the caller must follow its original historical projector.
    This function never silently accepts a source with an altered or missing
    INVEST-STALL guard.
    """
    entry = MERGED["files"].get(name)
    if entry is None or stage not in entry["stages"]:
        return None
    digest = _sha(source)
    transitions = [entry["stages"][stage]]
    for variant in entry.get("variants", {}).values():
        if stage in variant["stages"]:
            transitions.append(variant["stages"][stage])
    transition = next((row for row in transitions if digest == row["on_sha256"]), None)
    if transition is None:
        if any(digest == row["off_sha256"] for row in transitions):
            return source
        return None
    for edit in reversed(_frozen_edits(name, stage)):
        after, before = "".join(edit["after"]), "".join(edit["before"])
        if not after or source.count(after) != 1:
            raise AssertionError(f"INVEST-STALL merge {stage} {name}: changed/duplicated hunk")
        source = source.replace(after, before, 1)
    if _sha(source) != transition["off_sha256"]:
        raise AssertionError(f"INVEST-STALL merge {stage} {name}: wrong projected SHA")
    return source
