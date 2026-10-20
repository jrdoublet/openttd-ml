"""Create deterministic archives from the original local V277+V279 results."""

import gzip
import hashlib
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
RESULTS = REPO / "results"
PREFIX = "v277v279_porteB_20x10_pc_20261020"


def main():
    main_json = json.loads((RESULTS / (PREFIX + ".json")).read_bytes())
    index = {
        "schema": "v277v279-evidence-v1",
        "execution_git_sha": "fb6b9ebeffff5b99f7aa4d9796e2ba8686082f77",
        "source_bundle_sha256": main_json["source_bundle_sha256"],
        "manifest_sha256": main_json["manifest_sha256"],
        "scope": "smoke and paired 20x10; source bundle, JSONL, engine logs remain local",
        "artifacts": [],
    }
    outdir = ROOT / "artifacts"
    outdir.mkdir(parents=True, exist_ok=True)
    for suffix in ("_smoke.json", "_smoke.manifest.json", ".json", ".manifest.json"):
        source = RESULTS / (PREFIX + suffix)
        raw = source.read_bytes()
        stream = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", compresslevel=9, mtime=0, fileobj=stream) as archive:
            archive.write(raw)
        compressed = stream.getvalue()
        destination = outdir / (source.name + ".gz")
        destination.write_bytes(compressed)
        index["artifacts"].append(
            {
                "source": source.relative_to(REPO).as_posix(),
                "evidence": "artifacts/" + destination.name,
                "raw_bytes": len(raw),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "gzip_bytes": len(compressed),
                "gzip_sha256": hashlib.sha256(compressed).hexdigest(),
            }
        )
    (ROOT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Archived", len(index["artifacts"]), "files")


if __name__ == "__main__":
    main()
