"""Strict OFF view of the V284 orchestrator tick on the merged ROAD+RAIL tree.

The prior a9437f8 witness remains frozen. The merged source has additional
independent policy callbacks, so its new full-function SHA is separate.
"""

import hashlib
import json
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "v284_merged_20261105.json"

PO01C_HOOK = (
    "  /* Shared by normal and profiled loops; once per tick, before other workers\n"
    "   * consume the remaining opcodes. No queue entry and no work while idle. */\n"
    "  if (PO01C_REGEN_SPLIT && (this._po01cPending || this._po01cJob != null)) OpexPO01CStep(this);\n"
)

V284_HOOK = (
    "  /* Point commun aux boucles normale et _mainLoopProfiled. OFF court-circuite. */\n"
    "  if (V284_RAIL_GROWTH > 0) OpexV284Tick(this);\n"
    "  if (V284_RAIL_GROWTH <= 0 || !OpexV284Busy(this)) this._v257ReactiveStep();"
)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def project_orchestrator(body):
    witness = json.loads(FIXTURE.read_text(encoding="utf-8"))["merged_orchestrator"]
    digest = _sha(body)
    if digest == witness["function_off_sha256"]:
        return body
    if digest != witness["function_on_sha256"]:
        raise AssertionError("V284 merge orchestrator: unreviewed source SHA")
    if body.count(PO01C_HOOK) != 1 or body.count(V284_HOOK) != 1:
        raise AssertionError("V284 merge orchestrator: missing/duplicated guard")
    projected = body.replace(PO01C_HOOK, "", 1).replace(
        V284_HOOK, "  this._v257ReactiveStep();", 1)
    if _sha(projected) != witness["function_off_sha256"]:
        raise AssertionError("V284 merge orchestrator: OFF SHA changed")
    return projected


RAIL_SELECT = (
    "  /* Port du declencheur V270 c71b707 : avant la garde A*, sans prendre son creneau. */\n"
    "  if (V284_RAIL_GROWTH > 0 && OpexV284Select(this, year)) return;\n"
)
RAIL_SUPPRESS = (
    '        if (V284_RAIL_GROWTH > 0 && this._v284State != null && (("kind" in line) && line.kind == "freight")) continue;\n'
)


def reviewed_task_rail(live, after_search_prio):
    """Independent V284 witness without silently projecting worker-1's V233.

    SEARCH-PRIO OFF has already removed the later RAIL additions. Its merged
    source retains earlier V233L code; this test only owns the V284 guards.
    """
    witness = json.loads(FIXTURE.read_text(encoding="utf-8"))["merged_task_rail"]
    if (_sha(live) != witness["live_sha256"]
            or _sha(after_search_prio) != witness["search_prio_off_sha256"]):
        raise AssertionError("V284 merge task_rail: unknown composite source SHA")
    return after_search_prio


def reviewed_config(name, live, after_search_prio):
    """Freeze V284's config view independently of worker-1's V233L witnesses."""
    case = json.loads(FIXTURE.read_text(encoding="utf-8"))["merged_config"].get(name)
    if case is None or (_sha(live) != case["live_sha256"]
            or _sha(after_search_prio) != case["search_prio_off_sha256"]):
        raise AssertionError(f"V284 merge {name}: unknown config source SHA")
    return after_search_prio


def project_expansion(body):
    witness = json.loads(FIXTURE.read_text(encoding="utf-8"))["merged_task_rail"]
    digest = _sha(body)
    if digest == witness["expansion_off_sha256"]:
        return body
    if digest != witness["expansion_on_sha256"]:
        raise AssertionError("V284 merge expansion: unknown source SHA")
    if body.count(RAIL_SELECT) != 1 or body.count(RAIL_SUPPRESS) != 1:
        raise AssertionError("V284 merge expansion: changed/duplicated hook")
    projected = body.replace(RAIL_SELECT, "", 1).replace(RAIL_SUPPRESS, "", 1)
    if _sha(projected) != witness["expansion_off_sha256"]:
        raise AssertionError("V284 merge expansion: incorrect OFF SHA")
    return projected
