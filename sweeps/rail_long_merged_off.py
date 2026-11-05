"""Strict ROAD1Y+RAIL composite witnesses for RAIL-LONG v1/v2/v3.

The 3 November fixtures belong to the RAIL-only tree.  This module adds
separate, SHA-locked merge stages without modifying their historical bytes.
All changed fragments are borrowed from reviewed, frozen fixtures.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parent / "fixtures"
MANIFEST = ROOT / "rail_long_merged_20261105.json"


def _manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def sha(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def already_v1_off(name, source):
    entry = _manifest()["v1"].get(name)
    return entry is not None and sha(source) in (
        entry["off_sha256"], entry["historical_off_sha256"],
        entry.get("search_prio_after_v1_sha256"))


def already_v2_off(name, source):
    manifest = _manifest()
    digest = sha(source)
    row = manifest["v2"].get(name)
    if row and digest in (row["off_sha256"], row.get("historical_off_sha256")):
        return True
    v1 = manifest["v1"].get(name)
    return v1 is not None and digest in (
        v1["off_sha256"], v1["historical_off_sha256"])


def verify_stage(stage, name, original, projected):
    """Check full-file source AND output SHA for every known merged stage.

    Unknown inputs keep the original projectors' historical hunk validation,
    rather than whitelisting arbitrary near-matches as merged input.
    """
    row = _manifest()[stage].get(name)
    if row is None:
        return
    before, after = sha(original), sha(projected)
    pairs = [(row["on_sha256"], row["off_sha256"])]
    if stage == "v2":
        pairs.append((row["post_v3_sha256"], row["off_sha256"]))
        if "historical_on_sha256" in row:
            pairs.extend((
                (row["historical_on_sha256"], row["historical_off_sha256"]),
                (row["historical_post_v3_sha256"], row["historical_off_sha256"]),
            ))
    if stage == "v1":
        pairs.append((row["post_v2_sha256"], row["off_sha256"]))
    for known_before, known_after in pairs:
        if before == known_before:
            if after != known_after:
                raise AssertionError(
                    f"RAIL-LONG {stage} {name}: merged stage SHA {after} != {known_after}")
            return
    for _, known_after in pairs:
        if before == known_after and before != after:
            raise AssertionError(f"RAIL-LONG {stage} {name}: idempotence changed")


def platform_after_v3(name, source):
    """Revert platform after the v3 layer, at an exact merged SHA only.

    This valid order differs from the earlier RAIL-only fixture because
    v3 edits the surrounding task_rail source.  All other inputs use the
    existing strict INVEST-STALL platform projector unchanged.
    """
    fixture = _manifest()
    entry = fixture["platform_after_v3"].get(name)
    digest = sha(source)
    variant = None
    if entry and digest == entry["on_sha256"]:
        variant = "off_sha256"
    elif entry and digest == entry.get("historical_on_sha256"):
        variant = "historical_off_sha256"
    if variant is not None:
        path = ROOT / "invest_stall_platform_off_20261104.json"
        if hashlib.sha256(path.read_bytes()).hexdigest() != (
                fixture["original_fixture_sha256"]["invest_stall_platform"]):
            raise AssertionError("RAIL-LONG merge: platform fixture changed")
        edits = json.loads(path.read_text(encoding="utf-8"))["files"][name]["edits"]
        for edit in reversed(edits):
            after, before = edit["after"], edit["before"]
            if not after or source.count(after) != 1:
                raise AssertionError(f"RAIL-LONG merge {name}: platform hunk changed/duplicated")
            source = source.replace(after, before, 1)
        if sha(source) != entry[variant]:
            raise AssertionError(f"RAIL-LONG merge {name}: platform OFF SHA changed")
        return source
    from invest_stall_platform_off import off_source
    return off_source(name, source)


def before_v1_double_grow(name, source):
    """Handle one double-projector order, without weakening INVEST's SHA gate.

    The legacy v1 behavior test removes v2 before DOUBLE-GROW; the latter's
    generic projector cannot prove that intermediate against its platform
    SHA snapshot.  Delete precisely the single DOUBLE-GROW hunk only from
    this specifically-reviewed v2-OFF task_rail source.
    """
    transition = _manifest()["v1"].get(name)
    if transition is None or sha(source) != transition.get("pre_double_grow_sha256"):
        return source
    from double_grow_off import INSERTIONS
    inserts = INSERTIONS[name]
    if len(inserts) != 1 or source.count(inserts[0]) != 1:
        raise AssertionError(f"RAIL-LONG merge {name}: DOUBLE-GROW altered/duplicated")
    result = source.replace(inserts[0], "", 1)
    if sha(result) != transition["post_double_grow_sha256"]:
        raise AssertionError(f"RAIL-LONG merge {name}: DOUBLE-GROW OFF SHA changed")
    return result
