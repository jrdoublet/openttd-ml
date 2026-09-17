"""Mesure externe 10.5 / M4-16.4 : empreinte RAM de MinchinWeb.Lakes.

Le mode par defaut est un micro-banc constructeur : deux IA de mesure identiques, dont une
seule reproduit exactement l'allocation dominante de ``_MinchinWeb_Lakes_`` (un ``AIList``
persistant avec une entree par tuile). Le delta RSS resident entre les deux bras isole donc le
cout de cette structure sans dependre de la rare exposition eau de l'IA complete.

Le mode ``opex`` conserve l'ancien diagnostic apparie ``water_lakes_connectivity=0/1`` et les
jalons C56. Il est utile uniquement si le bras Lakes atteint reellement ``lakes_enter``.

Hors ``--selftest``, il refuse de tourner si ``/work`` n'est pas monte : les parties
OpenTTD doivent rester dans le conteneur canonique.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import threading
import time

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import bench_v2
from bench_v2 import build_arms, enable_savegame_cleanup, write_json_atomically


DEFAULT_SEED = 24
DEFAULT_MAP_SIZES = (8, 9, 10, 11)  # 256, 512, 1024, 2048 carres
REFERENCE_SETTINGS = (
    ("c56_task_trace", 1),
    # Atteindre l'eau sans attendre la cascade de bootstrap. Identique dans les deux bras.
    ("staged_bootstrap", 0),
    ("air_early_slot", 1),
    ("abandon_gen_filter", 1),
    ("abandon_cooldown_days", 365),
    ("portfolio_fresh_budget", 0),
)

_REAL_CHECK_OUTPUT = openttdlab.subprocess.check_output
_MEMORY_DIR: Path | None = None
_RUN_TOKEN: str | None = None
_TRACE_NAME_RE = re.compile(r"C56_TASK\s+\S+\s+name=(\S+)")


def parse_proc_status(text: str) -> dict[str, int]:
    wanted = {"VmRSS", "VmHWM", "VmSize", "RssAnon", "RssFile", "RssShmem"}
    out: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        if key not in wanted:
            continue
        match = re.search(r"(-?\d+)", raw)
        if match:
            out[key] = int(match.group(1))
    return out


def read_proc_status(pid: int) -> dict[str, int] | None:
    try:
        return parse_proc_status(Path(f"/proc/{pid}/status").read_text(encoding="utf-8"))
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None


def _experiment_identity(args, cwd: str | os.PathLike[str] | None) -> dict:
    argv = [str(value) for value in args]
    seed = None
    if "-G" in argv:
        try:
            seed = int(argv[argv.index("-G") + 1])
        except (ValueError, IndexError):
            pass
    config_text = ""
    script_text = ""
    if cwd is not None:
        base = Path(cwd)
        cfg = base / "openttdlab.cfg"
        script = base / "scripts" / "game_start.scr"
        if cfg.exists():
            config_text = cfg.read_text(encoding="utf-8", errors="replace")
        if script.exists():
            script_text = script.read_text(encoding="utf-8", errors="replace")
    map_match = re.search(r"(?m)^map_x\s*=\s*(\d+)\s*$", config_text)
    lakes_match = re.search(r"\bwater_lakes_connectivity=(\d+)\b", script_text)
    allocate_match = re.search(r"\ballocate=(\d+)\b", script_text)
    map_size = int(map_match.group(1)) if map_match else None
    try:
        experiment_index = int(Path(cwd).name) if cwd is not None else None
    except ValueError:
        experiment_index = None
    return {
        "seed": seed,
        "experiment_index": experiment_index,
        "map_size": map_size,
        "map_width": (1 << map_size) if map_size is not None else None,
        "tile_count": (1 << (2 * map_size)) if map_size is not None else None,
        "water_lakes_connectivity": int(lakes_match.group(1)) if lakes_match else None,
        "probe_allocate": int(allocate_match.group(1)) if allocate_match else None,
    }


def _memory_check_output(args, *rest, **kwargs):
    game_run = any(str(arg).startswith("-vnull:ticks=") for arg in args)
    if not game_run:
        return _REAL_CHECK_OUTPUT(args, *rest, **kwargs)
    if rest:
        raise TypeError("diag_water_memory: positional check_output arguments unsupported")

    command = tuple(args)
    identity = _experiment_identity(command, kwargs.get("cwd"))
    if identity.get("probe_allocate") is None and not any(str(arg) == "-d" for arg in command):
        command = command[:1] + ("-d", "script=4") + command[1:]

    popen_kwargs = dict(kwargs)
    timeout = popen_kwargs.pop("timeout", None)
    if popen_kwargs.pop("input", None) is not None:
        raise TypeError("diag_water_memory: check_output input= unsupported")
    popen_kwargs["stdout"] = subprocess.PIPE
    proc = subprocess.Popen(command, **popen_kwargs)

    stop = threading.Event()
    lock = threading.Lock()
    sampled = {
        "samples": 0,
        "max_rss_kib": 0,
        "max_hwm_kib": 0,
        "max_anon_kib": 0,
        "first": None,
        "last": None,
    }

    def sample_once():
        status = read_proc_status(proc.pid)
        if not status:
            return None
        with lock:
            sampled["samples"] += 1
            sampled["max_rss_kib"] = max(sampled["max_rss_kib"], status.get("VmRSS", 0))
            sampled["max_hwm_kib"] = max(sampled["max_hwm_kib"], status.get("VmHWM", 0))
            sampled["max_anon_kib"] = max(sampled["max_anon_kib"], status.get("RssAnon", 0))
            if sampled["first"] is None:
                sampled["first"] = dict(status)
            sampled["last"] = dict(status)
        return status

    def sampler():
        while not stop.is_set():
            sample_once()
            if proc.poll() is not None:
                break
            time.sleep(0.01)
        sample_once()

    thread = threading.Thread(target=sampler, name=f"rss-{proc.pid}", daemon=True)
    thread.start()
    markers: dict[str, dict] = {}
    output_parts = []
    started = time.monotonic()
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            output_parts.append(line)
            match = _TRACE_NAME_RE.search(line)
            if match and match.group(1) not in markers:
                markers[match.group(1)] = {
                    "elapsed_s": round(time.monotonic() - started, 6),
                    "memory_kib": sample_once(),
                }
        returncode = proc.wait(timeout=timeout)
    finally:
        stop.set()
        thread.join(timeout=2)

    output = "".join(output_parts)
    record = {
        "schema": "opex-water-memory-process-v1",
        "run_token": _RUN_TOKEN,
        **identity,
        "pid": proc.pid,
        "returncode": returncode,
        "elapsed_s": round(time.monotonic() - started, 6),
        "process_memory_kib": sampled,
        "markers": markers,
        "lakes_exposed": "lakes_enter" in markers,
    }
    before = markers.get("lakes_enter", {}).get("memory_kib")
    after = markers.get("lakes_init_enter", {}).get("memory_kib")
    if before and after and before.get("VmRSS") is not None and after.get("VmRSS") is not None:
        record["lakes_init_local_rss_delta_kib"] = after["VmRSS"] - before["VmRSS"]
        record["lakes_init_local_hwm_delta_kib"] = after.get("VmHWM", 0) - before.get("VmHWM", 0)
    else:
        record["lakes_init_local_rss_delta_kib"] = None
        record["lakes_init_local_hwm_delta_kib"] = None

    if _MEMORY_DIR is not None:
        _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        if identity.get("probe_allocate") is not None:
            factor_tag = f"alloc{identity.get('probe_allocate')}"
        else:
            factor_tag = f"lakes{identity.get('water_lakes_connectivity')}"
        tag = (f"m{identity.get('map_size')}_seed{identity.get('seed')}_"
               f"{factor_tag}_i{identity.get('experiment_index')}_pid{proc.pid}.json")
        Path(_MEMORY_DIR, tag).write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    if returncode:
        raise subprocess.CalledProcessError(returncode, command, output=output)
    return output


def keep_trace(row):
    arm, seed, repeat = row["experiment"]["bench_run"]
    config_text = row["experiment"].get("openttd_config", "")
    map_match = re.search(r"(?m)^map_x\s*=\s*(\d+)\s*$", config_text)
    map_size = int(map_match.group(1)) if map_match else None
    probe = None
    signs = row.get("chunks", {}).get("SIGN", {}) or {}
    records = signs.values() if isinstance(signs, dict) else signs
    for sign in records:
        if not isinstance(sign, dict):
            continue
        name = str(sign.get("name", ""))
        if not name.startswith("WMP|"):
            continue
        parts = name.split("|")
        if len(parts) not in (3, 4, 5):
            continue
        try:
            probe = {
                "probe_ops": int(parts[1]),
                "probe_ticks": int(parts[2]),
                "probe_map_tiles": int(parts[3]) if len(parts) >= 4 else None,
                "probe_map_width": int(parts[4]) if len(parts) >= 5 else None,
            }
        except ValueError:
            continue
        break
    return ({
        "arm": arm, "seed": seed, "repeat": repeat, "map_size": map_size,
        "date": str(row["date"]),
        "output": row.get("output", ""), "error": bool(row.get("error")),
        "probe_done": probe is not None,
        "probe_ops": probe["probe_ops"] if probe is not None else None,
        "probe_ticks": probe["probe_ticks"] if probe is not None else None,
        "probe_map_tiles": probe["probe_map_tiles"] if probe is not None else None,
        "probe_map_width": probe["probe_map_width"] if probe is not None else None,
    },)


def _arm(lakes: int) -> str:
    values = [*REFERENCE_SETTINGS, ("water_lakes_connectivity", lakes)]
    return "OpexAI[" + ",".join(f"{key}={value}" for key, value in values) + "]"


def _fixture_arms():
    folder = str(ROOT / "sweeps" / "fixtures" / "WaterMemoryProbe")
    return {
        "control": local_folder(folder, "WaterMemoryProbe", (("allocate", 0),)),
        "allocate": local_folder(folder, "WaterMemoryProbe", (("allocate", 1),)),
    }


def _median(values):
    return statistics.median(values) if values else None


def _mean(values):
    return statistics.mean(values) if values else None


def summarise_fixture_memory(records: list[dict]) -> dict:
    by_pair = defaultdict(dict)
    for record in records:
        size = record.get("map_size")
        allocate = record.get("probe_allocate")
        repeat = record.get("repeat")
        if size is not None and allocate in (0, 1) and repeat is not None:
            by_pair[(size, repeat)][allocate] = record

    scales = []
    for size in sorted({key[0] for key in by_pair}):
        pairs = []
        for (pair_size, repeat), arms in sorted(by_pair.items()):
            if pair_size != size or 0 not in arms or 1 not in arms:
                continue
            control, allocate = arms[0], arms[1]
            control_last = (control["process_memory_kib"].get("last") or {}).get("VmRSS")
            allocate_last = (allocate["process_memory_kib"].get("last") or {}).get("VmRSS")
            resident_delta = (allocate_last - control_last
                              if control_last is not None and allocate_last is not None else None)
            control_ops = control.get("probe_ops") if control.get("probe_done") else None
            allocate_ops = allocate.get("probe_ops") if allocate.get("probe_done") else None
            net_ops = (allocate_ops - control_ops
                       if allocate_ops is not None and control_ops is not None else None)
            pairs.append({
                "repeat": repeat,
                "control_last_rss_kib": control_last,
                "allocate_last_rss_kib": allocate_last,
                "resident_rss_delta_kib": resident_delta,
                "peak_rss_delta_kib": (allocate["process_memory_kib"]["max_rss_kib"]
                                       - control["process_memory_kib"]["max_rss_kib"]),
                "peak_hwm_delta_kib": (allocate["process_memory_kib"]["max_hwm_kib"]
                                       - control["process_memory_kib"]["max_hwm_kib"]),
                "allocate_peak_hwm_kib": allocate["process_memory_kib"]["max_hwm_kib"],
                "allocation_complete": bool(allocate.get("probe_done")),
                "control_probe_opcodes": control_ops,
                "allocation_opcodes_gross": allocate_ops,
                "allocation_opcodes_net": net_ops,
                "allocation_ticks": allocate.get("probe_ticks"),
                "probe_map_tiles": allocate.get("probe_map_tiles"),
                "probe_map_width": allocate.get("probe_map_width"),
            })
        resident = [p["resident_rss_delta_kib"] for p in pairs if p["resident_rss_delta_kib"] is not None]
        hwm = [p["peak_hwm_delta_kib"] for p in pairs]
        complete_ops = [p["allocation_opcodes_net"] for p in pairs
                        if p["allocation_complete"] and p["allocation_opcodes_net"] is not None]
        complete_ticks = [p["allocation_ticks"] for p in pairs
                          if p["allocation_complete"] and p["allocation_ticks"] is not None]
        tiles = 1 << (2 * size)
        median_resident = _median(resident)
        median_ops = _median(complete_ops)
        scales.append({
            "map_size": size,
            "map_width": 1 << size,
            "tile_count": tiles,
            "paired_repeats": len(pairs),
            "pairs": pairs,
            "resident_rss_delta_kib_median": median_resident,
            "resident_rss_delta_kib_mean": _mean(resident),
            "resident_rss_delta_kib_min": min(resident) if resident else None,
            "resident_rss_delta_kib_max": max(resident) if resident else None,
            "resident_bytes_per_tile_median": (
                median_resident * 1024.0 / tiles if median_resident is not None else None
            ),
            "peak_hwm_delta_kib_median": _median(hwm),
            "max_allocate_hwm_kib": max((p["allocate_peak_hwm_kib"] for p in pairs), default=None),
            "completed_allocations": len(complete_ops),
            "allocation_opcodes_net_median": median_ops,
            "allocation_opcodes_net_per_tile_median": (
                median_ops / tiles if median_ops is not None else None
            ),
            "allocation_ticks_median": _median(complete_ticks),
            "probe_map_tiles": next((p.get("probe_map_tiles") for p in pairs
                                     if p.get("probe_map_tiles") is not None), None),
            "probe_map_width": next((p.get("probe_map_width") for p in pairs
                                     if p.get("probe_map_width") is not None), None),
            "map_size_matches_probe": (
                next((p.get("probe_map_tiles") for p in pairs
                      if p.get("probe_map_tiles") is not None), None) == tiles
            ),
        })
    return {
        "mode": "constructor_microbench",
        "scales": scales,
        "all_pairs_complete": bool(scales) and all(item["paired_repeats"] > 0 for item in scales),
        "all_allocations_complete": bool(scales) and all(
            item["completed_allocations"] == item["paired_repeats"] for item in scales
        ),
        "all_map_sizes_match_probe": bool(scales) and all(
            item["map_size_matches_probe"] for item in scales
        ),
        "primary_measure": "paired retained-process VmRSS delta; allocation stays live until exit",
        "secondary_measure": "paired VmHWM delta; map generation can dominate this high-water mark",
        "opcode_measure": "paired net constructor-loop opcodes: allocate arm minus control arm using GetTick/GetOpsTillSuspend formula",
    }


def summarise_memory(records: list[dict]) -> dict:
    by_size = defaultdict(dict)
    for record in records:
        size = record.get("map_size")
        lakes = record.get("water_lakes_connectivity")
        if size is not None and lakes in (0, 1):
            by_size[size][lakes] = record
    scales = []
    for size in sorted(by_size):
        control = by_size[size].get(0)
        lakes = by_size[size].get(1)
        item = {
            "map_size": size,
            "map_width": 1 << size,
            "tile_count": 1 << (2 * size),
            "control_present": control is not None,
            "lakes_present": lakes is not None,
            "lakes_exposed": bool(lakes and lakes.get("lakes_exposed")),
            "local_rss_delta_kib": lakes.get("lakes_init_local_rss_delta_kib") if lakes else None,
            "local_hwm_delta_kib": lakes.get("lakes_init_local_hwm_delta_kib") if lakes else None,
            "paired_peak_rss_delta_kib": None,
            "paired_peak_hwm_delta_kib": None,
        }
        if control and lakes:
            item["paired_peak_rss_delta_kib"] = (
                lakes["process_memory_kib"]["max_rss_kib"] - control["process_memory_kib"]["max_rss_kib"]
            )
            item["paired_peak_hwm_delta_kib"] = (
                lakes["process_memory_kib"]["max_hwm_kib"] - control["process_memory_kib"]["max_hwm_kib"]
            )
        scales.append(item)
    return {
        "scales": scales,
        "all_lakes_arms_exposed": bool(scales) and all(item["lakes_exposed"] for item in scales),
        "interpretation": {
            "local_delta": "RSS/HWM between C56 lakes_enter and lakes_init_enter; closest external estimate of singleton allocation, scheduling can blur the boundary.",
            "paired_peak_delta": "Whole-process high-water difference lakes=1 minus lakes=0; includes later behavioural divergence, not a pure allocation cost.",
        },
    }


def selftest():
    parsed = parse_proc_status("Name:\topenttd\nVmSize:\t1000 kB\nVmHWM:\t222 kB\nVmRSS:\t200 kB\nRssAnon:\t150 kB\n")
    assert parsed == {"VmSize": 1000, "VmHWM": 222, "VmRSS": 200, "RssAnon": 150}, parsed
    fake = [
        {"map_size": 8, "water_lakes_connectivity": 0,
         "process_memory_kib": {"max_rss_kib": 100, "max_hwm_kib": 110}, "lakes_exposed": False},
        {"map_size": 8, "water_lakes_connectivity": 1,
         "process_memory_kib": {"max_rss_kib": 180, "max_hwm_kib": 190}, "lakes_exposed": True,
         "lakes_init_local_rss_delta_kib": 70, "lakes_init_local_hwm_delta_kib": 72},
    ]
    summary = summarise_memory(fake)
    assert summary["scales"][0]["paired_peak_hwm_delta_kib"] == 80, summary
    assert summary["scales"][0]["local_rss_delta_kib"] == 70, summary
    fixture = [
        {"map_size": 8, "probe_allocate": 0, "repeat": 0,
         "process_memory_kib": {"last": {"VmRSS": 100}, "max_rss_kib": 110, "max_hwm_kib": 120}},
        {"map_size": 8, "probe_allocate": 1, "repeat": 0,
         "process_memory_kib": {"last": {"VmRSS": 180}, "max_rss_kib": 190, "max_hwm_kib": 200}},
    ]
    fixture_summary = summarise_fixture_memory(fixture)
    scale = fixture_summary["scales"][0]
    assert scale["resident_rss_delta_kib_median"] == 80, fixture_summary
    assert scale["resident_bytes_per_tile_median"] == 1.25, fixture_summary
    print("diag_water_memory selftest OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fixture", "opex"), default="fixture")
    parser.add_argument("--years", type=int, default=1)
    parser.add_argument("--days", type=int, default=90,
                        help="fixture only: fixed game duration; ignored in opex mode")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--map-sizes", nargs="+", type=int, default=list(DEFAULT_MAP_SIZES))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--custom-towns", type=int, default=0,
        help=("scenario de mesure uniquement: 0 garde la densite de duel; une valeur >0 "
              "force number_towns=4/custom_town_number=N pour exposer des paires eau"),
    )
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "review_water_memory_10_5_16_4.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    if not Path("/work").exists():
        parser.error("ce diagnostic OpenTTD doit tourner dans le Docker canonique monte sur /work")
    if args.years < 1:
        parser.error("--years doit etre >= 1")
    if args.days < 56:
        parser.error("--days doit etre >= 56 pour produire au moins deux sauvegardes mensuelles")
    if args.repeats < 1:
        parser.error("--repeats doit etre >= 1")
    if not 1 <= args.workers <= 2:
        parser.error("--workers doit etre 1 ou 2 ; la mesure RAM privilegie l'isolation")
    if any(size < 8 or size > 11 for size in args.map_sizes):
        parser.error("--map-sizes accepte 8..11 (256..2048 carres)")
    if not 0 <= args.custom_towns <= 255:
        parser.error("--custom-towns doit etre entre 0 et 255")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    global _MEMORY_DIR, _RUN_TOKEN
    _MEMORY_DIR = args.out.with_name(args.out.stem + "_raw")
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    _RUN_TOKEN = f"{time.time_ns()}_{os.getpid()}"
    openttdlab.subprocess.check_output = _memory_check_output
    enable_savegame_cleanup()
    experiments = []
    if args.mode == "fixture":
        arms = _fixture_arms()
        for map_size in args.map_sizes:
            cfg = bench_v2.make_cfg(1970, map_size)
            for arm_name, arm in arms.items():
                for repeat in range(args.repeats):
                    experiments.append({
                        "seed": args.seed, "days": args.days, "openttd_config": cfg,
                        "ais": (arm,), "bench_run": [arm_name, args.seed, repeat],
                    })
        libraries = ()
    else:
        arms = build_arms([_arm(0), _arm(1)])
        for map_size in args.map_sizes:
            planned = bench_v2.experiments(
                arms, [args.seed], args.years, args.repeats, 1970, map_size=map_size
            )
            if args.custom_towns > 0:
                for experiment in planned:
                    experiment["openttd_config"] = f"""[difficulty]
number_towns = 4
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = {map_size}
map_y = {map_size}
custom_town_number = {args.custom_towns}
"""
            experiments.extend(planned)
        libraries = (
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        )

    experiment_meta = {
        index: {"arm": exp["bench_run"][0], "repeat": exp["bench_run"][2]}
        for index, exp in enumerate(experiments)
    }

    rows = list(run_experiments(
        openttd_version=bench_v2.OPENTTD_VERSION,
        opengfx_version=bench_v2.OPENGFX_VERSION,
        max_workers=args.workers,
        result_processor=keep_trace,
        experiments=experiments,
        ai_libraries=libraries,
    ))

    records = []
    for path in sorted(_MEMORY_DIR.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if record.get("run_token") != _RUN_TOKEN:
            continue
        meta = experiment_meta.get(record.get("experiment_index"))
        if meta is not None:
            record.update(meta)
        records.append(record)

    latest = {}
    for row in rows:
        key = (row["arm"], row["seed"], row["repeat"], row.get("map_size"))
        if key not in latest or row["date"] > latest[key]["date"]:
            latest[key] = row
    health = [{
        "arm": arm, "seed": seed, "repeat": repeat, "map_size": map_size,
        "last_date": row["date"],
        "script_error": row["error"],
        "fatal_marker": "The script died unexpectedly" in (row.get("output") or ""),
        "probe_done": row.get("probe_done"),
        "probe_ops": row.get("probe_ops"),
        "probe_ticks": row.get("probe_ticks"),
        "probe_map_tiles": row.get("probe_map_tiles"),
        "probe_map_width": row.get("probe_map_width"),
    } for (arm, seed, repeat, map_size), row in sorted(latest.items(), key=lambda item: str(item[0]))]

    probe_by_arm_repeat_size = {
        (item["arm"], item["repeat"], item.get("map_size")): {
            "probe_done": item.get("probe_done"),
            "probe_ops": item.get("probe_ops"),
            "probe_ticks": item.get("probe_ticks"),
            "probe_map_tiles": item.get("probe_map_tiles"),
            "probe_map_width": item.get("probe_map_width"),
        }
        for item in health
    }
    for record in records:
        meta = probe_by_arm_repeat_size.get(
            (record.get("arm"), record.get("repeat"), record.get("map_size"))
        )
        if meta is not None:
            record.update(meta)

    payload = {
        "schema": "opex-water-memory-review-v1",
        "purpose": "10.5 / M4-16.4 external RAM measurement only; no AI policy/default adoption.",
        "mode": args.mode,
        "seed": args.seed, "years": args.years, "days": args.days,
        "map_sizes": args.map_sizes, "repeats": args.repeats,
        "custom_towns": args.custom_towns,
        "settings_common": dict(REFERENCE_SETTINGS) if args.mode == "opex" else {},
        "factor": "probe_allocate" if args.mode == "fixture" else "water_lakes_connectivity",
        "fixture": ("sweeps/fixtures/WaterMemoryProbe" if args.mode == "fixture" else None),
        "records": records,
        "summary": (summarise_fixture_memory(records) if args.mode == "fixture"
                    else summarise_memory(records)),
        "health": health,
    }
    write_json_atomically(args.out, payload)
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    print(f"Sortie: {args.out}")
    expected_records = len(args.map_sizes) * 2 * args.repeats
    if len(records) != expected_records:
        raise SystemExit(f"mesure incomplete : {len(records)}/{expected_records} processus mesures")
    if any(item["script_error"] or item["fatal_marker"] for item in health):
        raise SystemExit("mesure invalide : erreur script detectee")
    if args.mode == "fixture":
        if any(item["paired_repeats"] != args.repeats for item in payload["summary"]["scales"]):
            raise SystemExit("mesure fixture incomplete : une paire/repetition manque")
        if not payload["summary"].get("all_allocations_complete"):
            raise SystemExit("mesure fixture incomplete : allocation non terminee avant horizon")
        if not payload["summary"].get("all_map_sizes_match_probe"):
            raise SystemExit("mesure fixture invalide : taille API differente de la carte demandee")
    elif any(not item["control_present"] or not item["lakes_present"] for item in payload["summary"]["scales"]):
        raise SystemExit("mesure Opex incomplete : un bras manque")


if __name__ == "__main__":
    main()
