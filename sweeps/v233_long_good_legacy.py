"""Project reviewed opt-in V233L edits to OFF for immutable legacy contracts.

The fixture records both sides, anchored by surrounding source. A changed
guard must fail rather than silently get erased. This is a source-level
projection; execution timing and VM equivalence still require a real smoke.
"""
import json
from pathlib import Path

FIXTURE = json.loads((Path(__file__).parent / "fixtures/v233_long_good_off.json").read_text())


def off_source(name, code):
    entry = FIXTURE["files"].get(name)
    if entry is None:
        return code
    for edit in reversed(entry["edits"]):
        assert code.count(edit["guarded"]) == 1, f"V233L {name}: guarded hunk changed"
        code = code.replace(edit["guarded"], edit["off"], 1)
    return code


def off_bytes(name, code):
    return off_source(name, code.decode("utf-8")).encode("utf-8")
