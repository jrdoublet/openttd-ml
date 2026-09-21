"""Diagnostic apparié C41.40 : cache d'accélération fret OFF vs ON."""
import argparse
import re
import sys
from pathlib import Path
import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, arm_statistics, build_arms, enable_savegame_cleanup, experiments, keep, make_cfg, paired_comparisons, summarise, write_json_atomically
import bench_v2

_real = openttdlab.subprocess.check_output
def _debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args): args = args[:1] + ("-d", "script=4") + args[1:]
    return _real(args, *rest, **kwargs)
openttdlab.subprocess.check_output = _debug

ARMS = ("OpexAI[c39_invalidation_probe=1,c41_rail_candidate_profile=1,c41_rail_freight_acceleration_cache=0]", "OpexAI[c39_invalidation_probe=1,c41_rail_candidate_profile=1,c41_rail_freight_acceleration_cache=1]")
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C41_RAIL_CANDIDATE_PROFILE\s*(.*)")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--years", type=int, default=6)
    p.add_argument("--seeds", nargs="+", type=int, default=[42,100,7,999,12345])
    p.add_argument("--max-workers", type=int, default=3)
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()
    out = a.out or ROOT / "results" / f"diag_c41_40_rail_freight_acceleration_cache_paired_{a.years}y_{len(a.seeds)}seeds.json"
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION, max_workers=a.max_workers, result_processor=keep, experiments=experiments(build_arms(list(ARMS)), a.seeds, a.years, 1, 1970), ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"), bananas_ai_library("5046524c", "Pathfinder.Rail"))))
    summary = summarise(rows)
    for record in summary:
        events = [{key: value for token in fields.split() if "=" in token for key, _, value in (token.partition("="),)} for fields in EVENT_RE.findall(record.get("openttd_output", "") or "")]
        record["c41_rail_candidate_ops"] = sum(int(event.get("ops", 0)) for event in events)
    failed = [r for r in summary if not r["run_ok"]]
    write_json_atomically(out, {"years":a.years,"seeds":a.seeds,"arms":list(ARMS),"openttd_config":make_cfg(1970),"summary":summary,"failed_runs":failed,"statistics":arm_statistics(summary,list(ARMS)),"paired_comparisons":paired_comparisons(summary,list(ARMS))})
    print("failed",len(failed),"out",out)
    if failed: raise SystemExit(1)
if __name__ == "__main__": main()
