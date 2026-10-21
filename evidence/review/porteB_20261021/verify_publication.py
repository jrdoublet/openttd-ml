#!/usr/bin/env python3
"""Verify the published benchmarks; optionally archive local JSONL checkpoints.

Verification requires only the contents of this directory. --archive-checkpoints
additionally requires the original three sibling benchmark worktrees.
No OpenTTD process or benchmark is launched.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CAMPAIGNS = (
    ("v294all_pc_stage_20261020", "v294all_adapt400_complet_1970_40x10_pc_20261021", 40),
    ("porteB-adapt400", "adapt400_porteB_20x10_pc_20261021", 20),
    ("porteB-v297", "v297_porteB_20x10_pc_20261021", 20),
    ("porteB-finpartie", "finpartie_porteB_20x10_pc_20261021", 20),
    ("porteB-v296clean", "v296clean_porteB_20x10_pc_20261021", 20),
    ("porteB-v301", "v301_porteB_20x10_pc_20261021", 20),
)
INDEX = HERE / "SHA256SUMS.json"
CHUNK = 1024 * 1024


def digest(path):
    sha = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK):
            sha.update(chunk)
            size += len(chunk)
    return sha.hexdigest(), size


def archive_checkpoints():
    records = json.loads(INDEX.read_text(encoding="utf-8"))
    by_file = {row["file"]: row for row in records["files"]}
    for worktree, campaign, _pairs in CAMPAIGNS:
        filename = campaign + ".jsonl.gz"
        original = ROOT.parent / worktree / "results" / (campaign + ".jsonl")
        archive = HERE / filename
        if filename in by_file:
            print("Already indexed:", filename)
            continue
        if not original.is_file():
            raise FileNotFoundError(f"Missing source checkpoints: {original}")
        if archive.exists():
            raise FileExistsError(f"Unindexed archive already exists: {archive}")
        raw_hash = hashlib.sha256()
        raw_bytes = 0
        lines = 0
        temp = HERE / (filename + ".tmp")
        try:
            with original.open("rb") as src, temp.open("wb") as out:
                with gzip.GzipFile(filename="", fileobj=out, mode="wb", compresslevel=6, mtime=0) as packed:
                    while chunk := src.read(CHUNK):
                        raw_hash.update(chunk)
                        raw_bytes += len(chunk)
                        lines += chunk.count(b"\n")
                        packed.write(chunk)
            temp.replace(archive)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
        archived_sha, archived_bytes = digest(archive)
        row = dict(
            file=filename,
            bytes=archived_bytes,
            sha256=archived_sha,
            original_file=campaign + ".jsonl",
            original_bytes=raw_bytes,
            original_sha256=raw_hash.hexdigest(),
            original_lines=lines,
            source_worktree=worktree,
        )
        records["files"].append(row)
        INDEX.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Archived {filename}: {raw_bytes} -> {archived_bytes} bytes, {lines} lines")


def verify():
    records = json.loads(INDEX.read_text(encoding="utf-8"))
    rows = records["files"]
    by_file = {row["file"]: row for row in rows}
    assert len(by_file) == len(rows), "Duplicate filename in SHA256 index"
    for row in rows:
        file = HERE / row["file"]
        sha, size = digest(file)
        assert (sha, size) == (row["sha256"], row["bytes"]), f"Bad archive hash: {file.name}"
        if file.suffix == ".gz":
            rawhash = hashlib.sha256()
            rawbytes = 0
            lines = 0
            with gzip.open(file, "rb") as data:
                while chunk := data.read(CHUNK):
                    rawhash.update(chunk)
                    rawbytes += len(chunk)
                    lines += chunk.count(b"\n")
            assert (rawhash.hexdigest(), rawbytes, lines) == (
                row["original_sha256"], row["original_bytes"], row["original_lines"]
            ), f"Bad gzip content: {file.name}"
    for _worktree, campaign, pairs in CAMPAIGNS:
        report = json.loads((HERE / (campaign + ".json")).read_text(encoding="utf-8"))
        comparison = report["policy_comparison"]
        assert report["campaign_id"] == campaign
        assert report["years"] == 10 and report["start_year"] == 1970
        assert len(report["seeds"]) == pairs and len(report["failed_runs"]) == 0
        assert comparison["comparison_complete"] and comparison["complete_pairs"] == pairs
        assert len(report["games"]) == 2 * pairs
        assert all(game["game_ok"] and game["status"] == "complete" for game in report["summary"])
        manifest_hash, _size = digest(HERE / (campaign + ".manifest.json"))
        assert manifest_hash == report["manifest_sha256"], f"Manifest changed: {campaign}"
    total_pairs = sum(pairs for _, _, pairs in CAMPAIGNS)
    print(f"Verified {len(rows)} archives, {len(CAMPAIGNS)} intact campaigns, "
          f"{total_pairs} complete pairs, {2 * total_pairs} games.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-checkpoints", action="store_true", help="Compress original sibling JSONL files not yet indexed")
    args = parser.parse_args()
    if args.archive_checkpoints:
        archive_checkpoints()
    verify()
