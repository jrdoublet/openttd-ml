"""EB-2 default-OFF additions; do not rebase historical hashes."""
import json
from pathlib import Path

DELTAS = json.loads((Path(__file__).parent / "fixtures/eb2_off_deltas.json").read_text(encoding="utf-8"))


def off_source(name, text):
    entry = DELTAS.get(name)
    if entry is None:
        return text
    edits = entry if isinstance(entry, list) else [entry]
    for edit in edits:
        if edit["marker"] not in text:
            continue
        fragment = edit["fragment"]
        replacement = edit.get("replacement", "")
        assert text.count(fragment) == 1, f"EB-2 {name}: OFF fragment changed"
        text = text.replace(fragment, replacement, 1)
    return text
