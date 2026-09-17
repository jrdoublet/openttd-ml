"""Package review evidence cited by the review docs into deterministic gzip files.

`results/` is intentionally a scratch area and is gitignored.  This helper finds
the JSON artifacts cited by the review documentation, stores byte-for-byte gzip
copies under `evidence/review/`, and writes an index with SHA-256 hashes of both
the raw and compressed forms.  Gzip mtime is forced to zero so reruns are
deterministic.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    ROOT / "docs" / "taches.md",
    ROOT / "docs" / "revue_code_2026-09-15_correctifs.md",
    *(ROOT / "docs" / "revue").glob("*.md"),
]
OUT_DIR = ROOT / "evidence" / "review"
INDEX_PATH = OUT_DIR / "index.json"

RESULT_REF_RE = re.compile(
    r"results/(?:review|p1|bench_early_slot|diag_early_slot|bench_air_demand_plan)"
    r"[A-Za-z0-9_./-]*\.json"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cited_results() -> list[str]:
    refs: set[str] = set()
    for doc in DOCS:
        refs.update(RESULT_REF_RE.findall(doc.read_text(encoding="utf-8", errors="replace")))
    return sorted(refs)


def gzip_deterministic(raw: bytes) -> bytes:
    # gzip.compress supports mtime=0 and produces deterministic bytes on the
    # Python versions used by the review harness.
    return gzip.compress(raw, compresslevel=9, mtime=0)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    missing = []
    for rel in cited_results():
        source = ROOT / rel
        if not source.exists():
            missing.append(rel)
            continue
        raw = source.read_bytes()
        packed = gzip_deterministic(raw)
        dest = OUT_DIR / (Path(rel).name + ".gz")
        dest.write_bytes(packed)
        entries.append(
            {
                "source": rel.replace("\\", "/"),
                "evidence": dest.relative_to(ROOT).as_posix(),
                "raw_bytes": len(raw),
                "raw_sha256": sha256(raw),
                "gzip_bytes": len(packed),
                "gzip_sha256": sha256(packed),
            }
        )

    index = {
        "schema": "opex-review-evidence-v1",
        "description": "Exact gzip copies of JSON evidence cited by docs/revue, docs/taches.md and docs/revue_code_2026-09-15_correctifs.md.",
        "artifacts": entries,
        "missing": missing,
    }
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"packaged={len(entries)} missing={len(missing)} "
        f"raw_bytes={sum(e['raw_bytes'] for e in entries)} "
        f"gzip_bytes={sum(e['gzip_bytes'] for e in entries)}"
    )
    for rel in missing:
        print(f"MISSING {rel}")
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
