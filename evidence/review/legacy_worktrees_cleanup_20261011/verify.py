"""Verify every byte preserved when retiring the three legacy worktrees."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    index = json.loads((HERE / "index.json").read_text(encoding="utf-8"))
    assert len(index["archives"]) == 3
    for item in index["archives"]:
        archive = HERE / Path(item["archive_path"]).name
        assert archive.stat().st_size == item["archive_bytes"]
        assert sha256(archive.read_bytes()) == item["archive_sha256"]
        with ZipFile(archive) as z:
            assert z.testzip() is None
            manifest = json.loads(z.read("manifest.json"))
            assert manifest["head"] == item["head"]
            assert manifest["branch"] == item["branch"]
            assert sha256(z.read("git/tracked_changes.patch")) == manifest["tracked_patch_sha256"]
            assert len(z.read("git/tracked_changes.patch")) == item["tracked_patch_bytes"]
            assert sha256(z.read("git/staged_changes.patch")) == manifest["staged_patch_sha256"]
            assert sha256(z.read("git/status_porcelain_z.bin")) == manifest["status_porcelain_sha256"]
            assert len(manifest["files"]) == item["files_count"]
            assert sum(f["kind"] == "ignored" for f in manifest["files"]) == item["ignored_count"]
            assert sum(f["kind"] == "untracked" for f in manifest["files"]) == item["untracked_count"]
            expected = {"manifest.json", "git/tracked_changes.patch", "git/staged_changes.patch", "git/status_porcelain_z.bin"}
            for f in manifest["files"]:
                path = Path(f["path"])
                assert not path.is_absolute() and ".." not in path.parts
                member = "files/" + f["path"]
                expected.add(member)
                data = z.read(member)
                assert len(data) == f["bytes"], member
                assert sha256(data) == f["sha256"], member
            assert set(z.namelist()) == expected
        print(f"OK {item['key']}: {item['files_count']} files, {item['archive_bytes']} ZIP bytes")


if __name__ == "__main__":
    main()
