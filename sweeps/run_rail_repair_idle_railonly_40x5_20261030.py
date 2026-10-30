"""Pre-registered, paired rail-only 40x5 gate for six-month-idle rail repairs.

Frozen dependencies: use existing local validated BaNaNaS tarballs, NEVER
download substitutes during a benchmark. Requires manifest and tarballs under
results/ from the 30/10/2026 rail repair validation.

Runner deliberately calls bench_v2.main() rather than replicating game settings.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
import bench_v2
from campaign_freeze import _frozen_library_descriptor

MANIFEST = ROOT / "results/v233l_frozen_manifest_libraries_20261030.json"
LIBRARIES = ROOT / "results/frozen_rail_libraries_20261030"
GROUPS = {item["requested_unique_id"]: item["resolved"]
          for item in json.loads(MANIFEST.read_text(encoding="utf8"))}
for group in GROUPS.values():
    for entry in group:
        file = LIBRARIES / entry["filename"]
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise RuntimeError(f"Frozen library checksum mismatch: {file}")


def frozen(unique_id, name):
    return _frozen_library_descriptor(name, GROUPS[unique_id], LIBRARIES)


bench_v2.bananas_ai_library = frozen
REF = "OpexAI[mode_air=0,mode_road=0,mode_water=0,mode_rail=1]"
TREAT = (
    "OpexAI[mode_air=0,mode_road=0,mode_water=0,mode_rail=1,"
    "rail_repair_join_site=1,rail_repair_v131_focus=1,"
    "rail_repair_astar_pair=1,rail_repair_pose_order=1]"
)
OUT = ROOT / "results/rail_repair_idle_railonly_gateA_40x5_20261030.json"
sys.argv = [
    "bench_v2.py", "--arms", REF, TREAT, "--seeds",
    *(str(s) for s in bench_v2.SEEDS_40),
    "--years", "5", "--max-workers", "8",
    "--out", str(OUT),
]

if __name__ == "__main__":
    bench_v2.main()
