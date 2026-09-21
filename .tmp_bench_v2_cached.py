import contextlib
from functools import partial
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
from sweeps import bench_v2

CACHE = Path("/home/lab/.cache/OpenTTDLab/0.0.75/bananas")

@contextlib.contextmanager
def _file_contents(path):
    with Path(path).open("rb") as handle:
        yield iter(lambda: handle.read(65536), b"")

def cached_bananas_ai_library(unique_id, ai_library_name, md5=None):
    matches = sorted(CACHE.glob(f"{unique_id}-*.tar_dependencies"))
    if len(matches) != 1:
        raise RuntimeError(f"cached Bananas manifest missing/ambiguous for {unique_id}: {matches}")
    manifest = matches[0]
    @contextlib.contextmanager
    def _copy(get_http_client, get_cache_dir):
        rows = []
        for line in manifest.read_text(encoding="utf-8").strip().splitlines():
            content_id, filename, license_name, md5sum = line.split(",", 3)
            archive = CACHE / filename
            rows.append((content_id, filename, license_name, md5sum,
                         partial(_file_contents, archive)))
        yield rows
    return ai_library_name, _copy

bench_v2.bananas_ai_library = cached_bananas_ai_library
bench_v2.main()
