"""Banc de nuit 2026-09-06 : vagues A -> B -> C sans intervention.

Vague A : 10 bras x 20 graines x 10 ans.
Vague B : 5 finalistes x 40 graines x 10 ans (si A a produit un JSON).
Vague C : 6 bras x 20 graines x 20 ans (si A a produit un JSON).

Sans script=4. keep() rend un tuple. Overlap/voirie explicites sur chaque bras OpexAI.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (  # noqa: E402
    OPENTTD_VERSION,
    OPENGFX_VERSION,
    SEEDS as CANONICAL_SEEDS,
    SUCCESS_METRICS,
    arm_statistics,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    keep,
    make_cfg,
    paired_comparisons,
    summarise,
    write_json_atomically,
)
import bench_v2  # noqa: E402

DOCS = ROOT / "docs"
STATUS = DOCS / "night_2026_09_06_status.txt"
LIBS = (
    bananas_ai_library("51554648", "Queue.FibonacciHeap"),
    bananas_ai_library("5046524c", "Pathfinder.Rail"),
)

EXTRA_SEEDS = (
    13, 19, 29, 37, 41, 53, 67, 89, 97, 101,
    131, 151, 181, 191, 223, 227, 251, 271, 281, 307,
)
SEEDS_40 = tuple(CANONICAL_SEEDS) + EXTRA_SEEDS

R00 = "OpexAI[road_pax_overlap=0,road_pax_voirie=0]"
R10 = "OpexAI[road_pax_overlap=1,road_pax_voirie=0]"
R01 = "OpexAI[road_pax_overlap=0,road_pax_voirie=1]"
R11 = "OpexAI[road_pax_overlap=1,road_pax_voirie=1]"
C11 = "OpexAI[road_pax_overlap=1,road_pax_voirie=1,air_cheap_site=1]"
K11 = "OpexAI[road_pax_overlap=1,road_pax_voirie=1,portfolio_cache=1]"
CK11 = "OpexAI[road_pax_overlap=1,road_pax_voirie=1,air_cheap_site=1,portfolio_cache=1]"
T11 = "OpexAI[road_pax_overlap=1,road_pax_voirie=1,road_cheap_trace=1]"
CT11 = "OpexAI[road_pax_overlap=1,road_pax_voirie=1,air_cheap_site=1,road_cheap_trace=1]"
HOG = "AAAHogEx"

WAVES = (
    {
        "name": "A",
        "years": 10,
        "seeds": CANONICAL_SEEDS,
        "arms": (R00, R10, R01, R11, C11, K11, CK11, T11, CT11, HOG),
        "out": DOCS / "bench_night_A_10y_20seeds.json",
    },
    {
        "name": "B",
        "years": 10,
        "seeds": SEEDS_40,
        "arms": (R00, R11, C11, CK11, HOG),
        "out": DOCS / "bench_night_B_10y_40seeds.json",
    },
    {
        "name": "C",
        "years": 20,
        "seeds": CANONICAL_SEEDS,
        "arms": (R00, R11, C11, CK11, CT11, HOG),
        "out": DOCS / "bench_night_C_20y_20seeds.json",
    },
)


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}Z  {msg}"
    print(line, flush=True)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    with STATUS.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def run_wave(wave: dict, max_workers: int) -> dict:
    name = wave["name"]
    years = wave["years"]
    seeds = list(wave["seeds"])
    arms = list(wave["arms"])
    out = Path(wave["out"])
    n = len(seeds) * len(arms)
    log(f"WAVE {name} START years={years} arms={len(arms)} seeds={len(seeds)} games={n} out={out.name}")
    t0 = time.monotonic()
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    built = build_arms(arms)
    cfg = make_cfg(1970)
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=max_workers,
        result_processor=keep,
        experiments=experiments(built, seeds, years, 1, 1970),
        ai_libraries=LIBS,
    ))
    summary = summarise(rows)
    failed = [r for r in summary if not r["run_ok"]]
    payload = {
        "wave": name,
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": years,
        "starting_year": 1970,
        "seeds": seeds,
        "arms": arms,
        "repeats": 1,
        "openttd_config": cfg,
        "elapsed_s": round(time.monotonic() - t0, 1),
        "success_metrics": list(SUCCESS_METRICS),
        "paired_reading": "mean(A(seed) - B(seed))",
        "checkpoint": str(bench_v2.CHECKPOINT_PATH),
        "summary": summary,
        "failed_runs": [
            {"arm": r["arm"], "seed": r["seed"], "failure_reason": r["failure_reason"]}
            for r in failed
        ],
        "statistics": arm_statistics(summary, arms),
        "paired_comparisons": paired_comparisons(summary, arms),
    }
    write_json_atomically(out, payload)
    elapsed = payload["elapsed_s"]
    log(
        f"WAVE {name} DONE elapsed_s={elapsed} games={len(summary)} "
        f"failed={len(failed)} out={out}"
    )
    return payload


def a_is_runnable_for_followup(payload: dict | None) -> bool:
    if payload is None:
        return False
    n = len(payload.get("summary") or [])
    failed = len(payload.get("failed_runs") or [])
    if n == 0:
        return False
    if failed / n > 0.25:
        log(f"WAVE A dirty: failed {failed}/{n} > 25%; B and C still run (night fill)")
    return True


def main() -> int:
    max_workers = 3
    if STATUS.exists():
        STATUS.unlink()
    log("NIGHT START max_workers=3 no script=4")
    payloads = {}
    try:
        payloads["A"] = run_wave(WAVES[0], max_workers)
    except Exception:
        log("WAVE A EXCEPTION\n" + traceback.format_exc())
        log("NIGHT ABORT: no A JSON, skip B and C")
        return 1

    if not a_is_runnable_for_followup(payloads["A"]):
        log("NIGHT ABORT after A: empty summary")
        return 1

    for wave in WAVES[1:]:
        try:
            payloads[wave["name"]] = run_wave(wave, max_workers)
        except Exception:
            log(f"WAVE {wave['name']} EXCEPTION\n" + traceback.format_exc())
            log(f"WAVE {wave['name']} SKIPPED remainder continues")

    report = {
        "waves": {
            name: {
                "out": str(WAVES[i]["out"]),
                "years": WAVES[i]["years"],
                "n_seeds": len(WAVES[i]["seeds"]),
                "n_arms": len(WAVES[i]["arms"]),
                "elapsed_s": (payloads[name].get("elapsed_s") if name in payloads else None),
                "failed": len((payloads.get(name) or {}).get("failed_runs") or []),
                "n_summary": len((payloads.get(name) or {}).get("summary") or []),
            }
            for i, name in enumerate(("A", "B", "C"))
        }
    }
    write_json_atomically(DOCS / "bench_night_2026_09_06_index.json", report)
    log("NIGHT DONE " + json.dumps(report["waves"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
