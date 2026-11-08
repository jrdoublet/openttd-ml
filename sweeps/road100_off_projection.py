"""Exact ROAD100 opt-in source hunks projected away for frozen legacy audits.

The fixture was built from the original working tree versus the strictly
default-OFF ROAD100 experiments. Each replacement requires an exact, unique
current hunk; partial or silently modified experiments fail closed. Historical
SHA fixtures remain untouched. This is a source-level projection, not a claim
about runtime equivalence (verified by real paired smoke benches separately).

To recreate a fixture during initial review only:
    python -X utf8 sweeps/road100_off_projection.py --generate
Never regenerate a fixture to make a failing legacy hash pass; inspect source.
"""
from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).with_name("fixtures") / "road100_optin_hunks.json"
SITE_FIRST_FIXTURE = Path(__file__).with_name("fixtures") / "road100_site_first_hunks.json"
V30A_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v30a_optin_hunks.json"
V31_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v31_optin_hunks.json"
V31B_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v31b_optin_hunks.json"
V32_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v32_optin_hunks.json"
V33_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v33_optin_hunks.json"
V34_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v34_optin_hunks.json"
V35_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v35_optin_hunks.json"
V36_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v36_optin_hunks.json"
FILES = (
    "builder_road.nut", "candidates.nut", "economy.nut", "globals_pre.nut",
    "info.nut", "opcode_exact.nut", "settings.nut", "task_projects.nut",
    "task_road.nut", "po01c_regen.nut", "po01c_generators.nut", "persist.nut",
)


# ROAD1Y-B2 was recorded on origin/master with seven unrelated RAIL-SIBLING /
# RAIL-OPEN additions embedded inside its very large contextual hunks.  Those
# additions are not ROAD1Y code and MUST survive projection of the merged
# master+RAIL bundle.  Keep the historical fixture and its normal projection
# entirely unchanged; the reviewed merge is the sole exception, identified by
# its exact input AND B2-projected SHA256.  Unknown revisions fail closed via
# the historical exact-hunk matcher rather than silently losing rail features.
# Each tuple is (merged SHA, B2-projected SHA, indices of RAIL-only hunks).
ROAD1Y_B2_RAIL_MERGE = {
    "candidates.nut": (
        "7f25e7b1c77a88ebebfb797518cfce289c9242363f9a103d5b67b393e8a94ed4",
        "a94a6b536e8fa44b4af2255925febd9738016d522003753068d3702321e7d4a1",
        (7, 8, 9, 10),
    ),
    "globals_pre.nut": (
        "891e9795640fa86d7c7c341bb82b2359c38e3f75a67bb07493aca667a9fb9d45",
        "2b5a41762fbee05d4263f311b3ffdf6389d9bebc4649f50d219fe9dd03e3a62d",
        (1,),
    ),
    "info.nut": (
        "cb3b8fabe78e230d7f208988c476c545a14eec15eafabd7b55d0001d4c413bc2",
        "db4e98d70522a49ae3242441b5479e22ae3422bc0eca772677da37f8aa04f0d2",
        (0,),
    ),
    "settings.nut": (
        "090f030d888cf34a89e260d136e56212ba7e0686d007530dec4bd9ecde86709d",
        "e9a77ce85ffb1a8b552c2022b3aa1f6abf53797c9813a09b62118d9840de1ec4",
        (2,),
    ),
}

# Selected callers remove newer RAIL policies *before* calling ROAD100 (notably
# n75_mc_legacy.historical_bytes).  Those intermediate sources are distinct
# from the live merged file, but remain fixed and reviewed.  The pairs below
# pin their exact SHA256 before and after subtracting ROAD1Y-B2.  The stages
# are RAIL-LONG OFF, RAIL-SEARCH-PRIO OFF, then RAIL-DEPOT-SIGNAL OFF, in that
# order.  Identical stages (no edit for that file) need only one pair.
ROAD1Y_B2_RAIL_MERGE_STAGES = {
    "candidates.nut": (
        ("a369a0b15b28d4e8408267efecf50e6fc395d8148a63c66c9e7a73fd726d0cec",
         "82253f50c21aa1545f65997a5c1aaf880cc99737ebca4f38dcf9029490f456bd"),
        # The fully stripped candidate source is BYTE-IDENTICAL to
        # origin/master.  Do not whitelist it: source alone cannot distinguish
        # that legacy input from a merged intermediate, so preserve the
        # historical projection for this SHA.
    ),
    "globals_pre.nut": (
        ("c7da52bf57c8ac501063e501d57b1e1a26e0acffcd420ed17333b73a7272034c",
         "d217d8e57fa5d104617c9c8bed5d797820fccee0a0f7afd751e0f033f2d23a13"),
        ("81f7b56c56fdfdf84262b7efff446d99ccdba61337bfea004a82128af9c121eb",
         "ef576d5db14d2b2fe2e93382c8334b9ca112145c074400de645ca94187faba1c"),
        ("4ccc29bfa824bbcddb226f70da5716bf801badb6007f610b4388f2bb42cfd72c",
         "fa47271e6f9483e7f6d8fa2225fe4b6da8009b1acf94a92413ae85cb279fab31"),
    ),
    "info.nut": (
        ("9f3ff1552c2ea4a6fb936946f81614159c23ba06892bb330f3bd78999a803f72",
         "46b702bbe37532bc8212af5058147caa5b12cce41ac427f3a3b58d244907d19f"),
        ("c56a5a612ae20dbf8f0a663d42613337fbaa1a09472162748b1dbf067a9fbdb0",
         "8bf5ca75fe04815effbfa632386adc2118bd78b2147e951a8a067505eb817bdc"),
        ("f446b1d7b2b13cda603265fe5275a00ef96d767843e3360b53569a72267d536b",
         "65c458f5290ceb7c0d36e706bf25a9ac796e6cb833ad534242786868fafd6057"),
    ),
    "settings.nut": (
        ("91f8e32a63273157970a72fe65a67132ec58080d0b1e94e2222eae2a2c00a520",
         "5739b3a18c226c969200f142dfa5e173002dec76ff094090b3c120f2fc597bb2"),
        ("2d1a10528f6bfc8c7a8bbceeb0bb645d6d452c33e6cdd45dce55883a9f66a108",
         "5a9c5cddcd059ba8b8679f949d19d75d8c5213427d60375a9421a17dbe362567"),
        ("d6faf8504c9ee1612d618e0712444cae6deace8d966caef48682d1af9b98146f",
         "4ac2ffaed7f5a5c7236591422a5154162570d649c48ff36d8db34384dcd20ff9"),
    ),
}


def build_hunks(original: str, modified: str):
    """Keep two unchanged lines of context around each exact reviewed edit."""
    old_lines = original.splitlines(keepends=True)
    new_lines = modified.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    out = []
    for group in matcher.get_grouped_opcodes(n=2):
        start_old, end_old = group[0][1], group[-1][2]
        start_new, end_new = group[0][3], group[-1][4]
        before = "".join(old_lines[start_old:end_old])
        after = "".join(new_lines[start_new:end_new])
        if not after or modified.count(after) != 1:
            raise AssertionError("ROAD100 hunk is not uniquely anchored in current source")
        out.append({"before": before, "after": after})
    return out


def generate():
    all_hunks = {}
    for name in FILES:
        old = subprocess.check_output(["git", "show", "HEAD:ai/OpexAI/" + name], cwd=ROOT).decode("utf-8")
        new = (ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")
        edits = build_hunks(old, new)
        if edits:
            all_hunks[name] = edits
        reconstructed = off_source(name, new, hunk_data=all_hunks)
        if reconstructed != old:
            raise AssertionError("ROAD100 projection does not reconstruct " + name)
    FIXTURE.write_text(json.dumps(all_hunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ROAD100 exact hunk fixture:", {name: len(ops) for name, ops in all_hunks.items()})


def _subtract_exact(name: str, source: str, edits, label: str) -> str:
    if not edits:
        return source
    present = [source.count(edit["after"]) == 1 for edit in edits]
    if not any(present):
        # Grouped hunks can contain old context that occurs multiple times,
        # and later legacy projectors can rewrite other parts of that context.
        # A fully projected source must carry no ROAD100 identifier at all.
        # Other frozen SHA checks still validate its remaining exact bytes.
        if any(token in source for token in ("ROAD100_", "road100_", "Road100")):
            raise AssertionError(f"{label} {name}: source is neither exact ON nor exact OFF")
        return source
    if not all(present):
        # One short, unchanged context region may survive BOTH projections
        # (info.nut's first ROAD100-7 group). A fully historical OFF file has
        # no ROAD100 identifiers; the frozen SHA validators then check bytes.
        if not any(token in source for token in ("ROAD100_", "road100_", "Road100")):
            return source
        raise AssertionError(f"{label} {name}: mixed or altered opt-in source hunks")
    for edit in reversed(edits):
        source = source.replace(edit["after"], edit["before"], 1)
    return source


def _subtract_road1y_b2(name: str, source: str, edits) -> str:
    """Project ROAD only; preserve unrelated RAIL hunks on one frozen merge.

    The seven skipped fixture hunks contain *only* RAIL code insertions.
    Never infer a merge from substrings, branch names, or a partial match:
    both input and output SHA checks apply to every reviewed source stage.
    """
    reviewed = ROAD1Y_B2_RAIL_MERGE.get(name)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    approved = () if reviewed is None else (
        ((reviewed[0], reviewed[1]),) + ROAD1Y_B2_RAIL_MERGE_STAGES.get(name, ())
    )
    expected = next((out_sha for in_sha, out_sha in approved if in_sha == digest), None)
    if expected is None:
        return _subtract_exact(name, source, edits, "ROAD1Y-B2")
    if not edits or max(reviewed[2]) >= len(edits):
        raise AssertionError(f"ROAD1Y-B2 {name}: missing reviewed merge hunks")
    rail_only = set(reviewed[2])
    for index in rail_only:
        before, after = edits[index]["before"], edits[index]["after"]
        operations = difflib.SequenceMatcher(
            None, before.splitlines(keepends=True), after.splitlines(keepends=True),
            autojunk=False,
        ).get_opcodes()
        changes = [tag for tag, *_ in operations if tag != "equal"]
        if not changes or any(tag != "insert" for tag in changes):
            raise AssertionError(f"ROAD1Y-B2 {name}: RAIL-only fixture hunk changed")
    projected = _subtract_exact(
        name, source, [edit for i, edit in enumerate(edits) if i not in rail_only],
        "ROAD1Y-B2-merge",
    )
    if hashlib.sha256(projected.encode("utf-8")).hexdigest() != expected:
        raise AssertionError(f"ROAD1Y-B2 {name}: merge projection SHA mismatch")
    return projected


def off_source(name: str, source: str, *, hunk_data=None) -> str:
    # ROAD1Y-B2: exact reviewed layer above origin/master 481e7c08.
    # Older ROAD100 fixtures stay frozen and must not match that parent.
    districts = json.loads((FIXTURE.parent / "road100_bus_districts_hunks.json").read_text(encoding="utf-8"))
    source = _subtract_road1y_b2(name, source, districts.get(name))
    # ROAD100-36 is a new opt-in above all frozen historic layers. Remove
    # only its exact current hunks, then use the unchanged V35..V7 fixtures.
    v36_hunks = json.loads(V36_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v36_hunks.get(name), "ROAD100-36")
    # V35's near-first scanner and portal dispatch layer sits above the
    # frozen V34 market telemetry and V33 sparse implementation.
    v35_hunks = json.loads(V35_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v35_hunks.get(name), "ROAD100-35")
    # ROAD100-34 observes native monthly PASS units before LONG pathfinding.
    # It never participates in ranking or construction; its exact additions
    # must be removed independently before V33 and older fixed layers.
    v34_hunks = json.loads(V34_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v34_hunks.get(name), "ROAD100-34")
    # New opt-ins have separate, exact source layers. V31b's fixed-fleet
    # implementation was finalized after V32 but before V33, although its
    # historical smoke preceded V33. Do not mix those helper hunks into V32
    # or V33: older frozen ESTIM/V262 and V31 source must remain untouched.
    v33_hunks = json.loads(V33_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v33_hunks.get(name), "ROAD100-33")
    v31b_hunks = json.loads(V31B_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v31b_hunks.get(name), "ROAD100-31b")
    # ROAD100-32 was isolated against the frozen V31 motor source, not against
    # a regenerated V262 or historic fixture. Strip its exact unique additions
    # first, then the frozen ROAD100-31 / 30a / 7 and original opt-ins.
    v32_hunks = json.loads(V32_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v32_hunks.get(name), "ROAD100-32")
    v31_hunks = json.loads(V31_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v31_hunks.get(name), "ROAD100-31")
    v30_hunks = json.loads(V30A_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v30_hunks.get(name), "ROAD100-30a")
    site_hunks = json.loads(SITE_FIRST_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, site_hunks.get(name), "ROAD100-7")
    if hunk_data is None:
        hunk_data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return _subtract_exact(name, source, hunk_data.get(name), "ROAD100")


def generate_site_first():
    """Initial ROAD100-7 review only: derive its delta from old, frozen opt-ins."""
    old_hunks = json.loads(FIXTURE.read_text(encoding="utf-8"))
    new_hunks = {}
    for name in FILES:
        baseline = subprocess.check_output(
            ["git", "show", "HEAD:ai/OpexAI/" + name], cwd=ROOT
        ).decode("utf-8")
        before_new = baseline
        cursor = 0
        for edit in old_hunks.get(name, []):
            # The original reviewed fixture has one short unchanged context
            # block (candidates.nut) repeated elsewhere. Diff groups are
            # ordered; forward-apply the first occurrence AFTER the preceding
            # group rather than rewriting the old historical fixture.
            pos = before_new.find(edit["before"], cursor)
            if pos < 0:
                raise AssertionError(f"{name}: existing historic hunk cannot be applied")
            before_new = before_new[:pos] + edit["after"] + before_new[pos + len(edit["before"]):]
            cursor = pos + len(edit["after"])
        current = (ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")
        edits = build_hunks(before_new, current)
        if edits:
            new_hunks[name] = edits
        if _subtract_exact(name, current, edits, "ROAD100-7") != before_new:
            raise AssertionError(f"{name}: new opt-in projection did not restore prior source")
    SITE_FIRST_FIXTURE.write_text(
        json.dumps(new_hunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("ROAD100-7 exact additions:", {name: len(hunks) for name, hunks in new_hunks.items()})


def off_bytes(name: str, source: bytes) -> bytes:
    return off_source(name, source.decode("utf-8")).encode("utf-8")


if __name__ == "__main__" and sys.argv[1:] == ["--generate"]:
    generate()
elif __name__ == "__main__" and sys.argv[1:] == ["--generate-site-first"]:
    generate_site_first()
