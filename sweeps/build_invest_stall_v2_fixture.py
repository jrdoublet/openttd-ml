"""Outil EXPLICITE de gel des hunks INVEST-STALL v2, jamais appelé par les tests.

L'origine est le bundle effectivement exécuté lors du smoke INVEST-STALL R1,
antérieur à la correction v2. Ne pas relancer pour masquer une régression :
après revue, le JSON et ses SHA constituent les nouvelles références figées.
"""

import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "results" / "invest_stall_smoke_4x10_20261103_r1_bundle" / "ai" / "OpexAI"
SOURCE = ROOT / "ai" / "OpexAI"
OUTPUT = ROOT / "sweeps" / "fixtures" / "invest_stall_v2_off_20261103.json"

FILES = (
    "candidates.nut",
    "po01c_generators.nut",
    "lines.nut",
    "builder_rail.nut",
    "task_v284.nut",
)


def sha(text):
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Refus : fixture déjà figée. Pas de régénération implicite.")
    result = {"baseline": "INVEST-STALL R1 4x10 bundle 2a297b009a498566e413995a5090c67224a3cf18eef534d99888adfbad76743e",
              "files": {}}
    for name in FILES:
        before = (BUNDLE / name).read_text(encoding="utf8")
        after = (SOURCE / name).read_text(encoding="utf8")
        a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
        edits = [
            {"after_start": j1, "before": a[i1:i2], "after": b[j1:j2]}
            for tag, i1, i2, j1, j2 in
            difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
            if tag != "equal"
        ]
        restored = list(b)
        for edit in reversed(edits):
            start = edit["after_start"]
            end = start + len(edit["after"])
            assert restored[start:end] == edit["after"], (name, start)
            restored[start:end] = edit["before"]
        assert "".join(restored) == before, name
        result["files"][name] = {
            "before_sha256": sha(before), "after_sha256": sha(after), "edits": edits,
        }
        print(name, "hunks", len(edits), "OFF", sha(before), "ON", sha(after))
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
