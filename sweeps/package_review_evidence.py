"""Audit explicit JSON citations; package only with --write and complete inputs.

The default is read-only. Historical archives remain evidence of their original
campaigns, not proof of current economic performance. Bare campaign names and
JSONL logs are outside this citation audit's scope.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import zlib


ROOT = Path(__file__).resolve().parents[1]
RESULT_REF_RE = re.compile(r"\bresults/[A-Za-z0-9_./-]+\.json\b(?![A-Za-z0-9_.-])")


def documentation_paths(root: Path) -> list[Path]:
    """Include all docs/journals/archives, root guides and local AI instructions."""
    return sorted({
        *root.glob("*.md"),
        *(root / "docs").rglob("*.md"),
        *(root / "ai").rglob("AGENTS.md"),
        *(root / "ai").rglob("CLAUDE.md"),
    })


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cited_results(root: Path = ROOT) -> list[str]:
    refs: set[str] = set()
    for doc in documentation_paths(root):
        refs.update(RESULT_REF_RE.findall(doc.read_text(encoding="utf-8", errors="replace")))
    return sorted(refs)


def gzip_deterministic(raw: bytes) -> bytes:
    # gzip.compress supports mtime=0 and produces deterministic bytes on the
    # Python versions used by the review harness.
    return gzip.compress(raw, compresslevel=9, mtime=0)


def contained_path(root: Path, rel: str, prefix: str) -> Path:
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts or not rel.startswith(prefix):
        raise ValueError(f"Unsafe path: {rel}")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes workspace: {rel}")
    return resolved


def audit(root: Path = ROOT) -> dict:
    """Verify existing archives, report missing inputs and unarchived citations."""
    index_path = root / "evidence" / "review" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"artifacts": []}
    entries = index["artifacts"]
    errors, verified, destinations = [], set(), set()
    for entry in entries:
        rel = entry["source"]
        try:
            source = contained_path(root, rel, "results/")
            dest = contained_path(root, entry["evidence"], "evidence/review/")
            if rel in verified or dest in destinations:
                raise ValueError("Duplicate source or archive path")
            packed = dest.read_bytes()
            raw = gzip.decompress(packed)
            for data, kind in ((raw, "raw"), (packed, "gzip")):
                if len(data) != entry[kind + "_bytes"] or sha256(data) != entry[kind + "_sha256"]:
                    raise ValueError(f"{kind} hash/size mismatch")
            if source.exists() and sha256(source.read_bytes()) != entry["raw_sha256"]:
                raise ValueError("Local result differs from archived evidence; do not overwrite")
            verified.add(rel)
            destinations.add(dest)
        except (OSError, EOFError, ValueError, zlib.error) as exc:
            errors.append(f"{rel}: {exc}")
    refs = cited_results(root)
    missing, pending = [], []
    for rel in refs:
        try:
            source = contained_path(root, rel, "results/")
            if rel not in verified:
                (pending if source.is_file() else missing).append(rel)
        except ValueError as exc:
            errors.append(str(exc))
    return {"citations": refs, "missing": missing, "pending": pending,
            "errors": errors, "entries": entries,
            "documents": [p.relative_to(root).as_posix() for p in documentation_paths(root)]}


def main(argv=None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Package only if every cited input is available; preserve old archives")
    args = parser.parse_args(argv)
    try:
        report = audit(root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"INVALID INDEX: {exc}")
        return 2
    print(f"cited={len(report['citations'])} missing={len(report['missing'])} unarchived={len(report['pending'])} errors={len(report['errors'])}")
    for category in ("missing", "pending", "errors"):
        for message in report[category]:
            print(f"{category.upper()} {message}")
    # Never replace a complete historical index with an incomplete local snapshot.
    if report["missing"] or report["errors"]:
        return 2
    if not args.write:
        return 2 if report["pending"] else 0
    entries = list(report["entries"])
    writes = []
    for rel in report["pending"]:
        raw = contained_path(root, rel, "results/").read_bytes()
        packed = gzip_deterministic(raw)
        # Preserve subdirectories so equal basenames cannot overwrite each other.
        dest_rel = "evidence/review/" + rel + ".gz"
        dest = contained_path(root, dest_rel, "evidence/review/")
        if dest.exists() and dest.read_bytes() != packed:
            print(f"CONFLICT: {dest_rel}; no files written")
            return 2
        writes.append((dest, packed))
        entries.append({"source": rel, "evidence": dest_rel,
                        "raw_bytes": len(raw), "raw_sha256": sha256(raw),
                        "gzip_bytes": len(packed), "gzip_sha256": sha256(packed)})
    index = {"schema": "opex-review-evidence-v1",
             "description": "Verified JSON evidence snapshot; see documents for citation coverage, not economic qualification.",
             "documents": report["documents"], "artifacts": entries, "missing": []}
    for dest, packed in writes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(packed)
    index_path = root / "evidence" / "review" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"packaged={len(writes)} preserved={len(report['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
