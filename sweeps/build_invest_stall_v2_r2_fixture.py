"""Gel EXPLICITE de la correction de priorité après le smoke v2-r1.

Compare le bundle moteur immuable v2-r1 avec le candidat v2-r2. L'ancienne
fixture v2 et tous les SHA historiques sont conservés sans modification.
Refuse tout écrasement de cette nouvelle fixture après son premier gel.
"""

import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results" / "invest_stall_smoke_4x10_20261103_v2_r1_bundle" / "ai" / "OpexAI" / "candidates.nut"
CURRENT = ROOT / "ai" / "OpexAI" / "candidates.nut"
DEST = ROOT / "sweeps" / "fixtures" / "invest_stall_v2_r2_off_20261103.json"


def main():
    if DEST.exists():
        raise SystemExit("Fixture v2-r2 déjà gelée : refus de régénérer")
    before, after = BASE.read_text(encoding="utf8"), CURRENT.read_text(encoding="utf8")
    a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
    edits = [dict(after_start=j1, before=a[i1:i2], after=b[j1:j2])
             for tag, i1, i2, j1, j2 in
             difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
             if tag != "equal"]
    restored = list(b)
    for edit in reversed(edits):
        at = edit["after_start"]
        assert restored[at:at + len(edit["after"])] == edit["after"]
        restored[at:at + len(edit["after"])] = edit["before"]
    assert "".join(restored) == before
    digest = lambda x: hashlib.sha256(x.encode("utf8")).hexdigest()
    data = {"reason": "Post-v2-r1: rated origin supply cannot fill existing mother station capacity",
            "files": {"candidates.nut": dict(before_sha256=digest(before),
                                            after_sha256=digest(after), edits=edits)}}
    DEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print("v2-r2 hunks", len(edits), "before", digest(before), "after", digest(after))


if __name__ == "__main__":
    main()
