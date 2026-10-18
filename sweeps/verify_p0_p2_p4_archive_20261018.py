#!/usr/bin/env python3
"""Verify the archival zip hashes and each member's uncompressed SHA-256.

Pure read-only archive validation. No OpenTTD/Docker, source files or worktrees.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "evidence/review/p0_p2_p4_20261018"


def checksum_file(path: Path) -> str:
    hash_obj = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def verify() -> dict:
    manifest = json.loads((FOLDER / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == 1
    total_files = total_bytes = 0
    for group, description in sorted(manifest["archives"].items()):
        path = FOLDER / description["file"]
        assert path.is_file(), path
        assert path.stat().st_size == description["archive_bytes"], path
        assert checksum_file(path) == description["archive_sha256"], path
        with zipfile.ZipFile(path) as archive:
            expected = description["members"]
            assert len(archive.namelist()) == len(expected)
            assert sorted(archive.namelist()) == sorted(m["path"] for m in expected)
            assert len(set(archive.namelist())) == len(expected)
            assert archive.testzip() is None, path
            for member in expected:
                name = member["path"]
                assert not name.startswith("/") and ".." not in Path(name).parts
                checksum = hashlib.sha256()
                length = 0
                with archive.open(name) as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        checksum.update(chunk)
                        length += len(chunk)
                assert length == member["bytes"], name
                assert checksum.hexdigest() == member["sha256"], name
                total_bytes += length
                total_files += 1
        print(f"OK {group}: {len(expected)} files; archive sha256 verified")
    print(f"VERIFIED {len(manifest['archives'])} groups, {total_files} members, {total_bytes} original bytes")
    return {"groups": len(manifest["archives"]), "members": total_files,
            "original_bytes": total_bytes}


if __name__ == "__main__":
    verify()
