"""Run the v2 baseline design unchanged, writing the post-11000-tick-barrier v3 artifact."""
from pathlib import Path

source_path = Path("sweeps/phase2_baseline_v2.py")
source = source_path.read_text()
old = 'OUTPUT_JSON = "docs/phase2_baseline_v2.json"'
new = 'OUTPUT_JSON = "docs/phase2_baseline_v3.json"'
old_barrier = '"barrier_base_tick": 5000'
new_barrier = '"barrier_base_tick": 11000'
if source.count(old) != 1 or source.count(old_barrier) != 1:
    raise RuntimeError("Expected v2 output/barrier declarations exactly once")
source = source.replace(old, new).replace(old_barrier, new_barrier)
exec(compile(source, str(source_path), "exec"), {"__name__": "__main__", "__file__": str(source_path)})
