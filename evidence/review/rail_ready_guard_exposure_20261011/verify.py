"""Vérification en lecture seule du sous-paquet documentaire P0 RAIL."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    index = json.loads((HERE / "index.json").read_text(encoding="utf-8"))
    assert index["schema"] == "opex-review-evidence-v1"
    seen_sources, seen_archives = set(), set()
    local = 0
    for row in index["artifacts"]:
        assert row["source"] not in seen_sources
        assert row["evidence"] not in seen_archives
        seen_sources.add(row["source"])
        seen_archives.add(row["evidence"])
        source, archive = (ROOT / row[k] for k in ("source", "evidence"))
        assert archive.resolve().is_relative_to(HERE.resolve())
        assert source.resolve().is_relative_to((ROOT / "results").resolve())
        packed = archive.read_bytes()
        raw = gzip.decompress(packed)
        for kind, data in (("gzip", packed), ("raw", raw)):
            assert len(data) == row[kind + "_bytes"], row["source"]
            assert sha(data) == row[kind + "_sha256"], row["source"]
        if source.is_file():
            assert source.read_bytes() == raw, row["source"]
            local += 1
    excerpts = json.loads((HERE / "source_excerpts.json").read_text(encoding="utf-8"))
    bundle = ROOT / "results/rail_ready_readmission_A2/rail_ready_readmission_diag_40x5_20261010_r1_bundle"
    source_files = 0
    if bundle.is_dir():
        for row in excerpts["files"]:
            path = bundle / row["bundle_relative_path"]
            assert sha(path.read_bytes()) == row["full_file_sha256"]
            lines = path.read_text(encoding="utf-8").splitlines()
            for block in row["excerpts"]:
                assert len(block["numbered_lines"]) == block["end_line"] - block["start_line"] + 1
                for line in block["numbered_lines"]:
                    assert lines[line["line"] - 1] == line["text"]
            source_files += 1
    print(json.dumps({"archives_verified": len(seen_archives), "local_originals_verified": local,
                      "frozen_source_files_verified": source_files, "global_index_modified": False}))

if __name__ == "__main__":
    main()
