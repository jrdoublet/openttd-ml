"""Fige uniquement les modifications contrôlées entre bundle R1 et correctif v3.

Opération explicite, jamais appelée par les tests : conserve les SHA antérieurs.
"""

import difflib
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "results/invest_stall_v3_smoke_4x10_20261103_bundle/ai/OpexAI"
NEW = ROOT / "ai/OpexAI"
OUT = ROOT / "sweeps/fixtures/invest_stall_v3_off_20261103.json"


def digest(code):
    return hashlib.sha256(code.encode("utf8")).hexdigest()


def entry(name):
    original = (OLD / name).read_text(encoding="utf8")
    current = (NEW / name).read_text(encoding="utf8")
    before = original.splitlines(keepends=True)
    after = current.splitlines(keepends=True)
    changes = []
    for tag, a, b, c, d in difflib.SequenceMatcher(
            None, before, after, autojunk=False).get_opcodes():
        if tag != "equal":
            changes.append(dict(after_start=c, before=before[a:b], after=after[c:d]))
    assert 0 < len(changes) <= 5, (name, len(changes))
    return dict(before_sha256=digest(original), after_sha256=digest(current), edits=changes)


if __name__ == "__main__":
    assert not OUT.exists(), f"Refuse de remplacer la fixture: {OUT}"
    data = {"source_bundle": "invest_stall_v3_smoke_4x10_20261103 (cdae36892e7408d)",
            "files": {name: entry(name) for name in ("candidates.nut", "builder_rail.nut")}}
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    from invest_stall_v3_off import off_source
    for name in data["files"]:
        actual = (NEW / name).read_text(encoding="utf8")
        expected = (OLD / name).read_text(encoding="utf8")
        assert off_source(name, actual) == expected
        print(name, len(data["files"][name]["edits"]), "hunks verified")
