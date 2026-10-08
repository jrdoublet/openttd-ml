"""Optional diagnostic archive before the existing OpenTTDLab cleanup."""
import hashlib
import json
from pathlib import Path
import shutil


def archive_savegames(experiment_dir, destination, index):
    """Refuse overwrite; retain bytes and checksums, including failed-engine saves."""
    source = Path(experiment_dir)
    target = Path(destination) / str(index)
    target.mkdir(parents=True, exist_ok=False)
    records = []
    for saved in sorted(source.rglob("*.sav")):
        relative = saved.relative_to(source)
        copied = target / relative
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(saved, copied)
        digest = hashlib.sha256(copied.read_bytes()).hexdigest()
        records.append({"path": relative.as_posix(), "bytes": copied.stat().st_size,
                        "sha256": digest})
    (target / "archive.json").write_text(json.dumps({"experiment_index": index,
        "savegames": records}, indent=2) + "\n", encoding="utf-8")
    return records
